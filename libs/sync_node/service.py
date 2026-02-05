"""
中心向执行节点发起同步：POST /api/sync-balance、/api/sync-positions，并写回 fact_account / fact_position。
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any

import httpx

from libs.core import get_config, get_logger
from libs.execution_node import ExecutionNodeRepository
from libs.member import MemberRepository
from libs.ledger import LedgerService
from libs.position import PositionService

log = get_logger("sync-node")


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
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{base_url}/api/sync-balance", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            log.warning("sync_balance node_id=%s error=%s", node.id, e)
            errors.append({"node_id": node.id, "error": str(e)})
            total_fail += len(accounts)
            continue
        results = data.get("results") or []
        for r in results:
            if not r.get("success"):
                total_fail += 1
                continue
            try:
                ledger_svc.sync_balance_from_exchange(
                    tenant_id=r["tenant_id"],
                    account_id=r["account_id"],
                    currency="USDT",
                    balance=Decimal(str(r.get("balance", 0))),
                    available=Decimal(str(r.get("available", 0))),
                    frozen=Decimal(str(r.get("frozen", 0))),
                )
                total_ok += 1
            except Exception as e:
                log.warning("sync_balance write account_id=%s error=%s", r.get("account_id"), e)
                total_fail += 1
    return {"ok": total_ok, "fail": total_fail, "errors": errors}


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
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{base_url}/api/sync-positions", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            log.warning("sync_positions node_id=%s error=%s", node.id, e)
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
            for pos in r.get("positions") or []:
                try:
                    position_svc.sync_position_from_exchange(
                        tenant_id=r["tenant_id"],
                        account_id=r["account_id"],
                        symbol=pos.get("symbol") or "",
                        exchange=exchange,
                        market_type="future",
                        position_side=pos.get("position_side") or "NONE",
                        quantity=Decimal(str(pos.get("quantity", 0))),
                        avg_cost=Decimal(str(pos.get("entry_price", 0))),
                    )
                    total_ok += 1
                except Exception as e:
                    log.warning("sync_positions write account_id=%s symbol=%s error=%s",
                                r.get("account_id"), pos.get("symbol"), e)
                    total_fail += 1
    return {"ok": total_ok, "fail": total_fail, "errors": errors}
