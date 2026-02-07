"""
中心向执行节点发起同步：POST /api/sync-balance、/api/sync-positions，并写回 fact_account / fact_position。
"""

import time as _time
from decimal import Decimal
from typing import List, Optional, Dict, Any

import httpx

from libs.core import get_config, get_logger
from libs.execution_node import ExecutionNodeRepository
from libs.member import MemberRepository
from datetime import datetime, timedelta
from libs.ledger import LedgerService
from libs.ledger.states import TransactionType
from libs.ledger.repository import generate_transaction_id
from libs.position import PositionService

log = get_logger("sync-node")


def _retry_on_deadlock(session, fn, label: str, max_retries: int = 2):
    """执行一次数据库写操作，遇到死锁时回滚重试"""
    for attempt in range(max_retries + 1):
        try:
            fn()
            return True
        except Exception as e:
            err_str = str(e)
            if "Deadlock" in err_str and attempt < max_retries:
                log.warning(f"{label} 死锁，重试 {attempt + 1}/{max_retries}")
                try:
                    session.rollback()
                except Exception:
                    pass
                _time.sleep(0.3 * (attempt + 1))
                continue
            # 非死锁错误或重试用尽
            try:
                session.rollback()
            except Exception:
                pass
            log.warning(f"{label} 失败", error=err_str)
            return False
    return False


def _tasks_for_node(accounts: list) -> List[Dict[str, Any]]:
    """把 ExchangeAccount 列表转成节点 API 需要的 tasks 格式"""
    return [
        {
            "account_id": acc.id,
            "tenant_id": acc.tenant_id,
            "user_id": acc.user_id,
            "exchange": acc.exchange or "binance",
            "api_key": acc.api_key,
            "api_secret": acc.api_secret,
            "passphrase": acc.passphrase,
            "market_type": "future" if (acc.account_type or "futures").lower() in ("futures", "future") else "spot",
        }
        for acc in accounts
    ]


def sync_balance_from_nodes(
    session,
    node_id: Optional[int] = None,
    sandbox: Optional[bool] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    向执行节点发起余额同步，并写回 fact_account。
    node_id 为空则同步所有活跃节点；sandbox 为空则从配置 exchange_sandbox 读取。
    """
    config = get_config()
    sandbox = sandbox if sandbox is not None else config.get_bool("exchange_sandbox", True)
    node_repo = ExecutionNodeRepository(session)
    member_repo = MemberRepository(session)
    ledger_svc = LedgerService(session)

    if node_id is not None:
        node = node_repo.get_by_id(node_id)
        nodes = [node] if node and node.status == 1 else []
    else:
        nodes = node_repo.list_active()

    total_ok = 0
    total_fail = 0
    errors = []

    for node in nodes:
        base_url = (node.base_url or "").rstrip("/")
        if not base_url:
            errors.append({"node_id": node.id, "error": "base_url empty"})
            total_fail += 1
            continue
        accounts = member_repo.list_accounts_by_execution_node(node.id)
        if not accounts:
            continue
        payload = {"tasks": _tasks_for_node(accounts), "sandbox": sandbox}
        node_headers = {}
        secret = config.get_str("node_auth_secret", "").strip()
        if secret:
            node_headers["X-Center-Token"] = secret
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{base_url}/api/sync-balance", json=payload, headers=node_headers or None)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            log.warning("sync_balance failed", node_id=node.id, error=str(e))
            errors.append({"node_id": node.id, "error": str(e)})
            total_fail += len(accounts)
            continue
        results = data.get("results") or []
        for r in results:
            account_id = r.get("account_id")
            if not r.get("success"):
                # 同步失败时更新 ExchangeAccount 的错误信息
                _update_exchange_account_sync_status(
                    session, account_id, success=False,
                    error=r.get("error", "unknown error"),
                )
                total_fail += 1
                continue
            try:
                ledger_svc.sync_balance_from_exchange(
                    tenant_id=r["tenant_id"],
                    account_id=account_id,
                    currency="USDT",
                    balance=Decimal(str(r.get("balance", 0))),
                    available=Decimal(str(r.get("available", 0))),
                    frozen=Decimal(str(r.get("frozen", 0))),
                    unrealized_pnl=Decimal(str(r.get("unrealized_pnl", 0))),
                    margin_used=Decimal(str(r.get("margin_used", 0))),
                    margin_ratio=Decimal(str(r.get("margin_ratio", 0))),
                    equity=Decimal(str(r.get("equity", 0))),
                )
                # 同步成功：同时更新 ExchangeAccount 的余额字段
                _update_exchange_account_sync_status(
                    session, account_id, success=True,
                    balance=float(r.get("balance", 0)),
                    futures_balance=float(r.get("equity", 0) or r.get("balance", 0)),
                    futures_available=float(r.get("available", 0)),
                )
                total_ok += 1
            except Exception as e:
                log.warning("sync_balance write failed", account_id=account_id, error=str(e))
                total_fail += 1
    return {"ok": total_ok, "fail": total_fail, "errors": errors}


def _update_exchange_account_sync_status(
    session,
    account_id: int,
    success: bool,
    error: str = None,
    balance: float = None,
    futures_balance: float = None,
    futures_available: float = None,
):
    """更新 dim_exchange_account 的余额和同步时间"""
    from libs.member.models import ExchangeAccount
    from datetime import datetime
    try:
        acc = session.query(ExchangeAccount).filter(
            ExchangeAccount.id == account_id,
        ).first()
        if not acc:
            return
        acc.last_sync_at = datetime.now()
        if success:
            acc.last_sync_error = None
            if balance is not None:
                acc.balance = Decimal(str(balance))
            if futures_balance is not None:
                acc.futures_balance = Decimal(str(futures_balance))
            if futures_available is not None:
                acc.futures_available = Decimal(str(futures_available))
        else:
            acc.last_sync_error = (error or "unknown")[:255]
        session.merge(acc)
    except Exception as e:
        log.warning("update exchange_account sync status failed",
                    account_id=account_id, error=str(e))


def sync_positions_from_nodes(
    session,
    node_id: Optional[int] = None,
    sandbox: Optional[bool] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    向执行节点发起持仓同步，并写回 fact_position。
    node_id 为空则同步所有活跃节点；sandbox 为空则从配置 exchange_sandbox 读取。
    """
    config = get_config()
    sandbox = sandbox if sandbox is not None else config.get_bool("exchange_sandbox", True)
    node_repo = ExecutionNodeRepository(session)
    member_repo = MemberRepository(session)
    position_svc = PositionService(session)

    if node_id is not None:
        node = node_repo.get_by_id(node_id)
        nodes = [node] if node and node.status == 1 else []
    else:
        nodes = node_repo.list_active()

    total_ok = 0
    total_fail = 0
    errors = []

    for node in nodes:
        base_url = (node.base_url or "").rstrip("/")
        if not base_url:
            errors.append({"node_id": node.id, "error": "base_url empty"})
            total_fail += 1
            continue
        accounts = member_repo.list_accounts_by_execution_node(node.id)
        if not accounts:
            continue
        payload = {"tasks": _tasks_for_node(accounts), "sandbox": sandbox}
        node_headers = {}
        secret = config.get_str("node_auth_secret", "").strip()
        if secret:
            node_headers["X-Center-Token"] = secret
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{base_url}/api/sync-positions", json=payload, headers=node_headers or None)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            log.warning("sync_positions failed", node_id=node.id, error=str(e))
            errors.append({"node_id": node.id, "error": str(e)})
            total_fail += len(accounts)
            continue
        acc_by_id = {acc.id: acc for acc in accounts}
        results = data.get("results") or []
        for r in results:
            if not r.get("success"):
                total_fail += 1
                continue
            acc = acc_by_id.get(r["account_id"])
            exchange = (acc.exchange or "binance") if acc else "binance"

            # 记录本次同步到的持仓 key，用于关闭交易所已无但数据库仍 OPEN 的幽灵持仓
            synced_keys = set()

            for pos in r.get("positions") or []:
                sym = pos.get("symbol") or ""
                ps = pos.get("position_side") or "NONE"
                qty = Decimal(str(pos.get("quantity", 0)))
                lev_raw = pos.get("leverage")
                lev = int(lev_raw) if lev_raw is not None else None
                upnl_raw = pos.get("unrealized_pnl")
                upnl = Decimal(str(upnl_raw)) if upnl_raw is not None else None
                liq_raw = pos.get("liquidation_price")
                liq = Decimal(str(liq_raw)) if liq_raw is not None else None

                def _write_pos(_sym=sym, _ps=ps, _qty=qty, _lev=lev, _upnl=upnl, _liq=liq, _pos=pos):
                    position_svc.sync_position_from_exchange(
                        tenant_id=r["tenant_id"],
                        account_id=r["account_id"],
                        symbol=_sym,
                        exchange=exchange,
                        market_type="future",
                        position_side=_ps,
                        quantity=_qty,
                        avg_cost=Decimal(str(_pos.get("entry_price", 0))),
                        leverage=_lev,
                        unrealized_pnl=_upnl,
                        liquidation_price=_liq,
                    )
                    session.flush()

                ok = _retry_on_deadlock(session, _write_pos,
                                        f"sync_pos {r.get('account_id')}/{sym}")
                if ok:
                    if qty > 0:
                        synced_keys.add((sym, ps))
                    total_ok += 1
                else:
                    total_fail += 1

            # 关闭交易所已无持仓但数据库仍 OPEN 的记录，并记录需要清理条件单的 symbol
            closed_symbols = set()
            try:
                from libs.position.repository import PositionRepository
                from libs.position.models import Position as PositionModel
                pos_repo = PositionRepository(session)
                open_positions = pos_repo.get_positions_by_account(
                    tenant_id=r["tenant_id"],
                    account_id=r["account_id"],
                    has_position=True,
                )
                for db_pos in open_positions:
                    if db_pos.exchange != exchange:
                        continue
                    key = (db_pos.symbol, db_pos.position_side)
                    if key not in synced_keys:
                        log.info("关闭幽灵持仓（交易所已无）",
                                 account_id=r["account_id"], symbol=db_pos.symbol,
                                 position_side=db_pos.position_side, exchange=exchange)
                        _db_sym = db_pos.symbol
                        _db_mt = db_pos.market_type or "future"
                        _db_ps = db_pos.position_side

                        def _close_ghost(_sym=_db_sym, _mt=_db_mt, _ps=_db_ps):
                            position_svc.sync_position_from_exchange(
                                tenant_id=r["tenant_id"],
                                account_id=r["account_id"],
                                symbol=_sym,
                                exchange=exchange,
                                market_type=_mt,
                                position_side=_ps,
                                quantity=Decimal("0"),
                                avg_cost=Decimal("0"),
                            )
                            session.flush()

                        if _retry_on_deadlock(session, _close_ghost,
                                              f"close_ghost {r.get('account_id')}/{_db_sym}"):
                            closed_symbols.add(_db_sym)

                # 补充：查找最近 30 分钟内关闭的持仓，也加入清理列表
                # 这样即使上一轮 cancel-conditionals 失败，后续同步仍会重试取消
                try:
                    _cutoff = datetime.now() - timedelta(minutes=30)
                    recently_closed = session.query(PositionModel).filter(
                        PositionModel.tenant_id == r["tenant_id"],
                        PositionModel.account_id == r["account_id"],
                        PositionModel.exchange == exchange,
                        PositionModel.status == "CLOSED",
                        PositionModel.quantity == 0,
                        PositionModel.updated_at >= _cutoff,
                    ).all()
                    for rp in recently_closed:
                        closed_symbols.add(rp.symbol)
                except Exception as e:
                    log.debug("query recently closed positions failed", error=str(e))

            except Exception as e:
                log.warning("close stale positions failed",
                            account_id=r.get("account_id"), error=str(e))

            # 持仓被关闭后，自动取消该 symbol 的残留条件委托单（止损/止盈触发后另一侧仍在）
            if closed_symbols:
                try:
                    acc = acc_by_id.get(r["account_id"])
                    if acc:
                        cancel_payload = {
                            "tasks": [_tasks_for_node([acc])[0]],
                            "sandbox": sandbox,
                            "symbols": list(closed_symbols),
                        }
                        log.info("发送取消残留条件单请求",
                                 account_id=r["account_id"],
                                 symbols=list(closed_symbols))
                        with httpx.Client(timeout=30) as cancel_client:
                            cancel_resp = cancel_client.post(
                                f"{base_url}/api/cancel-conditionals",
                                json=cancel_payload,
                                headers=node_headers or None,
                            )
                            if cancel_resp.status_code == 200:
                                cancel_data = cancel_resp.json()
                                for cr in cancel_data.get("results", []):
                                    cancelled_n = cr.get("cancelled", 0)
                                    if cancelled_n > 0:
                                        log.info("自动取消残留条件单成功",
                                                 account_id=r["account_id"],
                                                 symbols=list(closed_symbols),
                                                 cancelled=cancelled_n)
                                    else:
                                        log.debug("无残留条件单需取消",
                                                  account_id=r["account_id"],
                                                  symbols=list(closed_symbols))
                            else:
                                log.warning("取消条件单请求失败",
                                            account_id=r["account_id"],
                                            status=cancel_resp.status_code,
                                            body=cancel_resp.text[:200])
                except Exception as e:
                    log.warning("cancel conditionals failed",
                                account_id=r.get("account_id"), error=str(e))

    return {"ok": total_ok, "fail": total_fail, "errors": errors}


def sync_trades_from_nodes(
    session,
    node_id: Optional[int] = None,
    sandbox: Optional[bool] = None,
    symbols: Optional[List[str]] = None,
    since_ms: Optional[int] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    向执行节点发起成交同步，写入 fact_transaction。
    自动去重（通过 source_id = exchange_trade_id）。
    """
    from libs.ledger.models import Transaction, Account

    config = get_config()
    sandbox = sandbox if sandbox is not None else config.get_bool("exchange_sandbox", True)
    node_repo = ExecutionNodeRepository(session)
    member_repo = MemberRepository(session)

    if node_id is not None:
        node = node_repo.get_by_id(node_id)
        nodes = [node] if node and node.status == 1 else []
    else:
        nodes = node_repo.list_active()

    total_ok = 0
    total_skip = 0
    total_fail = 0
    errors = []

    for node in nodes:
        base_url = (node.base_url or "").rstrip("/")
        if not base_url:
            errors.append({"node_id": node.id, "error": "base_url empty"})
            total_fail += 1
            continue
        accounts = member_repo.list_accounts_by_execution_node(node.id)
        if not accounts:
            continue
        payload = {
            "tasks": _tasks_for_node(accounts),
            "sandbox": sandbox,
        }
        if symbols:
            payload["symbols"] = symbols
        if since_ms:
            payload["since_ms"] = since_ms
        node_headers = {}
        secret = config.get_str("node_auth_secret", "").strip()
        if secret:
            node_headers["X-Center-Token"] = secret
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{base_url}/api/sync-trades", json=payload, headers=node_headers or None)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            log.warning("sync_trades failed", node_id=node.id, error=str(e))
            errors.append({"node_id": node.id, "error": str(e)})
            total_fail += len(accounts)
            continue

        acc_by_id = {acc.id: acc for acc in accounts}
        results = data.get("results") or []
        for r in results:
            if not r.get("success"):
                total_fail += 1
                errors.append({"account_id": r.get("account_id"), "error": r.get("error")})
                continue
            account_id = r["account_id"]
            tenant_id = r["tenant_id"]
            # 查找对应的 ledger account
            acct = session.query(Account).filter(
                Account.tenant_id == tenant_id,
                Account.account_id == account_id,
            ).first()
            ledger_account_id = acct.ledger_account_id if acct else f"ACCT-{account_id}"
            current_balance = float(acct.balance) if acct else 0

            for trade in r.get("trades") or []:
                trade_id = trade.get("trade_id") or ""
                source_id = f"TRADE-{account_id}-{trade_id}"
                # 去重：检查是否已存在
                existing = session.query(Transaction).filter(
                    Transaction.source_id == source_id,
                    Transaction.tenant_id == tenant_id,
                ).first()
                if existing:
                    total_skip += 1
                    continue
                try:
                    side = (trade.get("side") or "BUY").upper()
                    cost = Decimal(str(trade.get("cost") or 0))
                    fee = Decimal(str(trade.get("fee") or 0))
                    amount = cost if side == "SELL" else -cost
                    tx_type = "TRADE_SELL" if side == "SELL" else "TRADE_BUY"
                    ts = trade.get("timestamp")
                    tx_at = datetime.utcfromtimestamp(ts / 1000) if ts else datetime.now()

                    txn = Transaction(
                        transaction_id=generate_transaction_id(),
                        ledger_account_id=ledger_account_id,
                        tenant_id=tenant_id,
                        account_id=account_id,
                        currency="USDT",
                        transaction_type=tx_type,
                        amount=amount,
                        fee=fee,
                        balance_after=Decimal(str(current_balance)),
                        available_after=Decimal(str(current_balance)),
                        frozen_after=Decimal("0"),
                        source_type="EXCHANGE_TRADE",
                        source_id=source_id,
                        symbol=trade.get("symbol"),
                        status="COMPLETED",
                        transaction_at=tx_at,
                        remark=f"{side} {trade.get('quantity', 0)} @ {trade.get('price', 0)} (fee: {fee})",
                    )
                    session.add(txn)
                    total_ok += 1
                except Exception as e:
                    log.warning("sync_trades write failed",
                                account_id=account_id, trade_id=trade_id, error=str(e))
                    total_fail += 1
        # flush after each node
        try:
            session.flush()
        except Exception as e:
            log.warning("sync_trades flush failed", error=str(e))

    return {"ok": total_ok, "skip": total_skip, "fail": total_fail, "errors": errors}
