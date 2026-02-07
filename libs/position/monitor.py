"""
Position Monitor - 自管止盈止损监控（分布式架构）

核心功能：
1. 定时扫描所有 OPEN 持仓中带 stop_loss / take_profit 的记录
2. 批量获取价格（一个 symbol 只查一次，不管多少用户）
3. 到价时按节点分发平仓：本机账户直接平，远程节点 POST /api/close-position
4. 全程异步并发，用户再多也不卡

优势：交易所看不到止损位，防止"扫损"

架构：
    ┌─────────────────────────────┐
    │ position_monitor (中心)      │
    │   1. 查 DB: OPEN + 有SL/TP  │
    │   2. 批量获取价格(公共API)    │
    │   3. 判断是否触发             │
    │   4. 分发平仓:               │
    │      - 本机账户 → LiveTrader  │
    │      - 远程账户 → POST 节点   │
    └─────────────────────────────┘

使用方式（在 signal-monitor 中作为后台线程启动）：
    from libs.position.monitor import start_position_monitor, stop_position_monitor
    start_position_monitor(interval=3)  # 每 3 秒检查一次
"""

import asyncio
import time
import threading
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple

import httpx
from sqlalchemy import and_, or_

from libs.core import get_config, get_logger, gen_id
from libs.core.database import get_session
from libs.position.models import Position
from libs.member.models import ExchangeAccount
from libs.facts.models import SignalEvent

log = get_logger("position-monitor")
config = get_config()

# 监控线程停止标志
_monitor_stop_event = threading.Event()
_monitor_thread: Optional[threading.Thread] = None

# 价格缓存（减少 API 调用；key = exchange:symbol, value = (price, timestamp)）
_price_cache: Dict[str, Tuple[float, float]] = {}
_PRICE_CACHE_TTL = 2  # 秒

# 统计
_stats = {
    "last_scan_at": None,
    "positions_monitored": 0,
    "triggers_total": 0,
    "closes_success": 0,
    "closes_failed": 0,
}

# 正在处理中的持仓（防止重复触发）
_closing_in_progress: set = set()  # position_id 集合

# 止损冷却回调（由 signal-monitor 注册，避免循环依赖）
# 签名: callback(symbol: str, strategy_code: str) -> None
_on_sl_triggered_callback = None


def set_on_sl_triggered(callback):
    """注册止损触发回调（由 signal-monitor 在启动时调用）"""
    global _on_sl_triggered_callback
    _on_sl_triggered_callback = callback


# ─────────────────────── 信号事件写入 ───────────────────────

def _write_close_signal_event(
    session,
    position: Position,
    trigger_type: str,
    current_price: float,
    signal_id: str,
    success: bool = True,
    error_msg: str = None,
):
    """
    平仓触发时写入 fact_signal_event，让信号历史能追踪到 SL/TP 平仓。
    注意：不在此处 commit，由调用方 _monitor_cycle 统一 commit，保证事务一致性。
    """
    import json
    try:
        detail = json.dumps({
            "symbol": position.symbol,
            "action": "CLOSE",
            "trigger_type": trigger_type,
            "trigger_price": current_price,
            "entry_price": float(position.entry_price) if position.entry_price else None,
            "stop_loss": float(position.stop_loss) if position.stop_loss else None,
            "take_profit": float(position.take_profit) if position.take_profit else None,
            "position_side": position.position_side,
            "strategy_code": position.strategy_code,
            "account_id": position.account_id,
            "quantity": float(position.quantity) if position.quantity else 0,
        }, ensure_ascii=False)

        event = SignalEvent(
            signal_id=signal_id,
            account_id=position.account_id,
            event_type="EXECUTED" if success else "FAILED",
            status="executed" if success else "failed",
            source_service="position-monitor",
            detail=detail,
            error_message=error_msg,
            created_at=datetime.now(),
        )
        session.add(event)
        # 不做 commit，由 _monitor_cycle 统一提交
    except Exception as e:
        log.warning("write close signal event failed", error=str(e))


# ─────────────────────── 数据库查询 ───────────────────────

def _get_monitored_positions(session) -> List[Position]:
    """查询所有需要监控的持仓：OPEN + quantity > 0 + 有 SL 或 TP"""
    return session.query(Position).filter(
        Position.status == "OPEN",
        Position.quantity > 0,
        or_(
            Position.stop_loss.isnot(None),
            Position.take_profit.isnot(None),
        ),
    ).all()


def _get_exchange_accounts_map(session, account_ids: List[int]) -> Dict[int, ExchangeAccount]:
    """批量获取交易所账户（一次查询）"""
    if not account_ids:
        return {}
    accounts = session.query(ExchangeAccount).filter(
        ExchangeAccount.id.in_(account_ids),
        ExchangeAccount.status == 1,
    ).all()
    return {a.id: a for a in accounts}


# ─────────────────────── 价格获取（异步批量）───────────────────────

def _normalize_exchange_for_ccxt(exchange_name: str) -> str:
    """
    将 DB 中的交易所名统一映射为 CCXT async_support 模块类名。
    DB 可能存 "binance"/"binanceusdm"/"gate"/"gateio"/"okx" 等多种格式。
    """
    name = (exchange_name or "").lower().strip()
    mapping = {
        "binance": "binanceusdm",      # 合约用 binanceusdm
        "binanceusdm": "binanceusdm",
        "gate": "gateio",
        "gateio": "gateio",
        "okx": "okx",
        "bybit": "bybit",
    }
    return mapping.get(name, name)


async def _fetch_prices_batch(symbols_by_exchange: Dict[str, set]) -> Dict[str, float]:
    """
    异步批量获取价格。按交易所分组，每个交易所只建一个连接。
    返回 {exchange:symbol: price}

    ★ 改进：对交易所名做规范化，确保 "gate" → "gateio"、"binance" → "binanceusdm"。
    返回的 key 仍然使用原始交易所名（与 DB position.exchange 一致），避免 lookup 失配。
    """
    import ccxt.async_support as ccxt_async

    now = time.time()
    results: Dict[str, float] = {}
    need_fetch: Dict[str, set] = {}          # ccxt_name -> symbols
    ccxt_name_to_originals: Dict[str, set] = {}  # ccxt_name -> original exchange names

    # 先查缓存
    for exchange_name, syms in symbols_by_exchange.items():
        for sym in syms:
            key = f"{exchange_name}:{sym}"
            cached = _price_cache.get(key)
            if cached and (now - cached[1]) < _PRICE_CACHE_TTL:
                results[key] = cached[0]
            else:
                ccxt_name = _normalize_exchange_for_ccxt(exchange_name)
                need_fetch.setdefault(ccxt_name, set()).add(sym)
                ccxt_name_to_originals.setdefault(ccxt_name, set()).add(exchange_name)

    # 按交易所并发获取
    async def _fetch_for_exchange(ccxt_exchange_name: str, syms: set):
        exchange_cls = getattr(ccxt_async, ccxt_exchange_name, None)
        if not exchange_cls:
            log.warning(f"unsupported exchange (ccxt class not found): {ccxt_exchange_name}")
            return
        opts = {"enableRateLimit": True}
        if ccxt_exchange_name in ("okx", "gateio"):
            opts["options"] = {"defaultType": "swap"}
        else:
            opts["options"] = {"defaultType": "future"}
        ex = exchange_cls(opts)
        try:
            await ex.load_markets()
            for sym in syms:
                try:
                    ccxt_sym = _resolve_ccxt_symbol(ex, sym)
                    if not ccxt_sym:
                        continue
                    ticker = await ex.fetch_ticker(ccxt_sym)
                    price = float(ticker.get("last") or ticker.get("close") or 0)
                    if price > 0:
                        # 为所有映射到此 ccxt class 的原始交易所名都写入结果
                        for orig_name in ccxt_name_to_originals.get(ccxt_exchange_name, {ccxt_exchange_name}):
                            key = f"{orig_name}:{sym}"
                            results[key] = price
                            _price_cache[key] = (price, time.time())
                except Exception as e:
                    log.debug(f"fetch_ticker failed: {ccxt_exchange_name} {sym}: {e}")
        except Exception as e:
            log.warning(f"exchange init failed: {ccxt_exchange_name}: {e}")
        finally:
            try:
                await ex.close()
            except Exception:
                pass

    if need_fetch:
        tasks = [_fetch_for_exchange(ex, syms) for ex, syms in need_fetch.items()]
        await asyncio.gather(*tasks, return_exceptions=True)

    return results


def _resolve_ccxt_symbol(exchange, symbol: str) -> Optional[str]:
    """尝试多种格式解析出 ccxt symbol"""
    for s in [symbol, symbol.replace("/", ""), f"{symbol}:USDT"]:
        if s in exchange.markets:
            return s
    base = symbol.split("/")[0] if "/" in symbol else symbol.replace("USDT", "")
    for candidate in [f"{base}/USDT:USDT", f"{base}/USDT"]:
        if candidate in exchange.markets:
            return candidate
    return None


# ─────────────────────── SL/TP 判断 ───────────────────────

def _check_trigger(position: Position, current_price: float) -> Optional[str]:
    """
    判断是否触发止盈/止损，返回 "SL" / "TP" / None
    """
    side = (position.position_side or "LONG").upper()
    # 止损
    if position.stop_loss:
        sl = float(position.stop_loss)
        if side == "LONG" and current_price <= sl:
            return "SL"
        if side == "SHORT" and current_price >= sl:
            return "SL"
    # 止盈
    if position.take_profit:
        tp = float(position.take_profit)
        if side == "LONG" and current_price >= tp:
            return "TP"
        if side == "SHORT" and current_price <= tp:
            return "TP"
    return None


# ─────────────────────── 平仓执行（异步并发）───────────────────────

async def _close_position_local(
    position: Position,
    account: ExchangeAccount,
    current_price: float,
    trigger_type: str,
    session,
) -> bool:
    """本机账户：直接用 LiveTrader 平仓"""
    from libs.trading.live_trader import LiveTrader
    from libs.trading.base import OrderSide, OrderType, OrderStatus
    from libs.trading.settlement import TradeSettlementService

    side = (position.position_side or "LONG").upper()
    close_side = OrderSide.SELL if side == "LONG" else OrderSide.BUY
    qty = float(position.quantity)
    if qty <= 0:
        return False

    # DB 存的是币数量（如 0.1 ETH），但 Gate/OKX 合约需要张数。
    # 用 amount_usdt 让 LiveTrader 内部统一做 币→张 转换，避免单位错误。
    amount_usdt = qty * current_price

    settlement_svc = TradeSettlementService(
        session=session,
        tenant_id=position.tenant_id,
        account_id=position.account_id,
        currency="USDT",
    )
    trader = LiveTrader(
        exchange=account.exchange,
        api_key=account.api_key,
        api_secret=account.api_secret,
        passphrase=account.passphrase or "",
        sandbox=config.get_bool("exchange_sandbox", True),
        market_type=position.market_type or "future",
        settlement_service=settlement_svc,
        tenant_id=position.tenant_id,
        account_id=position.account_id,
    )
    try:
        log.info(
            f"[LOCAL] {trigger_type}平仓",
            account_id=position.account_id, symbol=position.symbol,
            side=side, qty=qty, amount_usdt=round(amount_usdt, 2), price=current_price,
            entry=float(position.entry_price) if position.entry_price else None,
            sl=float(position.stop_loss) if position.stop_loss else None,
            tp=float(position.take_profit) if position.take_profit else None,
        )
        pm_signal_id = gen_id("PM")
        result = await trader.create_order(
            symbol=position.symbol,
            side=close_side,
            order_type=OrderType.MARKET,
            amount_usdt=amount_usdt,
            price=current_price,
            signal_id=pm_signal_id,
            trade_type="CLOSE",
            close_reason=trigger_type,
            position_side=side,  # 必传：平的是当前持仓方向 LONG/SHORT，否则会当成开反向仓
        )
        ok = result.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)
        if ok:
            position.close_reason = trigger_type
            position.stop_loss = None
            position.take_profit = None
            position.updated_at = datetime.now()
            log.info(f"[LOCAL] {trigger_type}平仓成功",
                     account_id=position.account_id, symbol=position.symbol,
                     filled_qty=result.filled_quantity, filled_price=result.filled_price)
            # 写入信号事件（信号历史可追踪）
            _write_close_signal_event(
                session, position, trigger_type, current_price,
                pm_signal_id, success=True,
            )
            # 止损触发后设置策略冷却，防止立刻重新开仓
            if trigger_type == "SL" and position.strategy_code and _on_sl_triggered_callback:
                try:
                    _on_sl_triggered_callback(position.symbol, position.strategy_code)
                    log.info("止损冷却已触发", symbol=position.symbol, strategy=position.strategy_code)
                except Exception as cd_err:
                    log.warning(f"cooldown callback failed: {cd_err}")
        else:
            log.warning(f"[LOCAL] {trigger_type}平仓失败",
                        account_id=position.account_id, symbol=position.symbol,
                        status=result.status)
            _write_close_signal_event(
                session, position, trigger_type, current_price,
                pm_signal_id, success=False, error_msg=f"status={result.status}",
            )
        return ok
    except Exception as e:
        log.error(f"[LOCAL] {trigger_type}平仓异常",
                  account_id=position.account_id, symbol=position.symbol, error=str(e))
        return False
    finally:
        try:
            await trader.close()
        except Exception:
            pass


async def _close_position_remote(
    position: Position,
    account: ExchangeAccount,
    current_price: float,
    trigger_type: str,
    node_base_url: str,
    session=None,
) -> bool:
    """远程节点账户：POST /api/close-position 到节点，成功后在中心侧做结算"""
    from libs.trading.settlement import TradeSettlementService

    side = (position.position_side or "LONG").upper()
    close_side = "SELL" if side == "LONG" else "BUY"
    qty = float(position.quantity)
    if qty <= 0:
        return False

    # DB 存币数量，传 amount_usdt 让节点侧 LiveTrader 自动做 币→张 转换
    amount_usdt = qty * current_price

    payload = {
        "account_id": position.account_id,
        "tenant_id": position.tenant_id,
        "exchange": account.exchange,
        "api_key": account.api_key,
        "api_secret": account.api_secret,
        "passphrase": account.passphrase or "",
        "market_type": position.market_type or "future",
        "symbol": position.symbol,
        "side": close_side,
        "amount_usdt": round(amount_usdt, 2),
        "trigger_type": trigger_type,
        "position_side": side,  # 被平仓位方向 LONG/SHORT，节点侧必传否则会开反向仓
    }
    try:
        headers = {}
        secret = config.get_str("node_auth_secret", "").strip()
        if secret:
            headers["X-Center-Token"] = secret
        log.info(
            f"[REMOTE] {trigger_type}平仓 → {node_base_url}",
            account_id=position.account_id, symbol=position.symbol,
            side=side, qty=qty, price=current_price,
        )
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{node_base_url}/api/close-position",
                json=payload,
                headers=headers or None,
            )
            resp.raise_for_status()
            data = resp.json()
        ok = data.get("success", False)
        if ok:
            position.close_reason = trigger_type
            position.stop_loss = None
            position.take_profit = None
            position.updated_at = datetime.now()
            log.info(f"[REMOTE] {trigger_type}平仓成功",
                     account_id=position.account_id, symbol=position.symbol)

            # 在中心侧做结算（写 order + fill + position update + ledger）
            if session:
                try:
                    filled_qty = float(data.get("filled_quantity") or qty)
                    filled_price = float(data.get("filled_price") or current_price)
                    pm_signal_id = gen_id("PM")
                    settlement_svc = TradeSettlementService(
                        session=session,
                        tenant_id=position.tenant_id,
                        account_id=position.account_id,
                        currency="USDT",
                    )
                    order_dto = settlement_svc.create_order(
                        symbol=position.symbol,
                        exchange=account.exchange,
                        side=close_side,
                        order_type="MARKET",
                        quantity=Decimal(str(filled_qty)),
                        price=Decimal(str(filled_price)),
                        signal_id=pm_signal_id,
                        position_side=side,
                        market_type=position.market_type or "future",
                        trade_type="CLOSE",
                        close_reason=trigger_type,
                    )
                    settlement_svc.submit_order(
                        order_id=order_dto.order_id,
                        exchange_order_id=data.get("exchange_order_id") or "",
                    )
                    settlement_svc.settle_fill(
                        order_id=order_dto.order_id,
                        symbol=position.symbol,
                        exchange=account.exchange,
                        side=close_side,
                        quantity=Decimal(str(filled_qty)),
                        price=Decimal(str(filled_price)),
                        fee=Decimal("0"),
                        fee_currency="USDT",
                        position_side=side,
                        market_type=position.market_type or "future",
                    )
                    log.info("[REMOTE] 中心侧结算完成",
                             account_id=position.account_id, symbol=position.symbol)
                except Exception as settle_err:
                    log.warning("[REMOTE] 中心侧结算失败（平仓已成功）",
                                account_id=position.account_id, error=str(settle_err))

            # 止损触发后设置策略冷却
            if trigger_type == "SL" and position.strategy_code and _on_sl_triggered_callback:
                try:
                    _on_sl_triggered_callback(position.symbol, position.strategy_code)
                    log.info("止损冷却已触发（远程）", symbol=position.symbol, strategy=position.strategy_code)
                except Exception as cd_err:
                    log.warning(f"cooldown callback (remote) failed: {cd_err}")
        else:
            log.warning(f"[REMOTE] {trigger_type}平仓失败",
                        account_id=position.account_id, error=data.get("error"))
        return ok
    except Exception as e:
        log.error(f"[REMOTE] {trigger_type}平仓异常",
                  account_id=position.account_id, symbol=position.symbol, error=str(e))
        return False


# ─────────────────────── 主监控循环 ───────────────────────

async def _monitor_cycle():
    """一次完整的监控扫描周期（异步）"""
    session = get_session()
    triggered: List[Tuple[Position, str, float]] = []  # 提前声明，防止 except 中 NameError
    try:
        # 1. 查询需要监控的持仓
        positions = _get_monitored_positions(session)
        if not positions:
            return
        _stats["positions_monitored"] = len(positions)
        _stats["last_scan_at"] = datetime.now().isoformat()

        # 2. 收集需要查询的 symbol（按交易所分组，一个 symbol 只查一次）
        symbols_by_exchange: Dict[str, set] = defaultdict(set)
        for pos in positions:
            symbols_by_exchange[pos.exchange].add(pos.symbol)

        # 3. 异步批量获取价格
        prices = await _fetch_prices_batch(dict(symbols_by_exchange))
        if not prices:
            return

        # 4. 判断触发，收集需要平仓的持仓（跳过正在处理中的）
        for pos in positions:
            if pos.position_id in _closing_in_progress:
                continue  # 上一轮平仓还没完成，跳过防止重复发单
            price_key = f"{pos.exchange}:{pos.symbol}"
            current_price = prices.get(price_key)
            if current_price is None:
                continue
            trigger = _check_trigger(pos, current_price)
            if trigger:
                triggered.append((pos, trigger, current_price))
                _closing_in_progress.add(pos.position_id)

        if not triggered:
            return

        log.info(f"position_monitor: {len(triggered)} 个持仓触发平仓")
        _stats["triggers_total"] += len(triggered)

        # 5. 批量获取交易所账户凭证
        account_ids = list({pos.account_id for pos, _, _ in triggered})
        accounts_map = _get_exchange_accounts_map(session, account_ids)

        # 6. 获取远程节点信息（按 execution_node_id 查）
        node_urls = _get_node_urls(session, accounts_map)

        # 7. 并发执行平仓
        close_tasks = []
        close_meta = []  # 与 close_tasks 一一对应，记录 (pos, trigger_type, price, is_remote)
        for pos, trigger_type, current_price in triggered:
            account = accounts_map.get(pos.account_id)
            if not account:
                log.warning("账户不可用", account_id=pos.account_id)
                continue
            node_id = account.execution_node_id
            if node_id and node_id in node_urls:
                # 远程节点
                close_tasks.append(
                    _close_position_remote(pos, account, current_price, trigger_type, node_urls[node_id], session)
                )
                close_meta.append((pos, trigger_type, current_price, True))
            else:
                # 本机（本机平仓内部已写信号事件）
                close_tasks.append(
                    _close_position_local(pos, account, current_price, trigger_type, session)
                )
                close_meta.append((pos, trigger_type, current_price, False))

        if close_tasks:
            results = await asyncio.gather(*close_tasks, return_exceptions=True)
            success = sum(1 for r in results if r is True)
            failed = len(results) - success
            _stats["closes_success"] += success
            _stats["closes_failed"] += failed
            if success > 0:
                log.info(f"平仓完成: {success} 成功, {failed} 失败")

            # 远程平仓结果写入信号事件（本机平仓已在内部写入）
            for i, (pos, tt, price, is_remote) in enumerate(close_meta):
                if not is_remote:
                    continue
                ok = results[i] is True if i < len(results) else False
                err_msg = str(results[i]) if not ok and i < len(results) else None
                _write_close_signal_event(
                    session, pos, tt, price,
                    gen_id("PM"), success=ok, error_msg=err_msg,
                )

        # 清除处理中标记（无论成功失败都释放，下一轮可重试失败的）
        for pos, _, _ in triggered:
            _closing_in_progress.discard(pos.position_id)

        session.commit()
    except Exception as e:
        log.warning("position_monitor 周期异常", error=str(e))
        # 异常时也要清除处理中标记，否则永远不会重试
        for pos, _, _ in triggered:
            _closing_in_progress.discard(pos.position_id)
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        try:
            session.close()
        except Exception:
            pass


def _get_node_urls(session, accounts_map: Dict[int, ExchangeAccount]) -> Dict[int, str]:
    """获取需要的节点 base_url（一次查询）"""
    node_ids = {
        a.execution_node_id for a in accounts_map.values()
        if a.execution_node_id
    }
    if not node_ids:
        return {}
    try:
        from libs.execution_node.models import ExecutionNode
        nodes = session.query(ExecutionNode).filter(
            ExecutionNode.id.in_(node_ids),
            ExecutionNode.status == 1,
        ).all()
        return {n.id: (n.base_url or "").rstrip("/") for n in nodes if n.base_url}
    except Exception as e:
        log.warning("查询执行节点失败", error=str(e))
        return {}


def _monitor_loop(interval: float = 3.0):
    """
    后台监控主循环（阻塞，在独立线程中运行）。
    内部每个周期用 asyncio 并发处理。
    """
    log.info("position_monitor 启动", interval=interval)
    loop = asyncio.new_event_loop()
    try:
        while not _monitor_stop_event.is_set():
            try:
                loop.run_until_complete(_monitor_cycle())
            except Exception as e:
                log.warning("position_monitor loop error", error=str(e))
            _monitor_stop_event.wait(interval)
    finally:
        loop.close()
    log.info("position_monitor 已停止")


def start_position_monitor(interval: float = 3.0):
    """启动持仓监控后台线程"""
    global _monitor_thread
    if _monitor_thread and _monitor_thread.is_alive():
        log.warning("position_monitor 已在运行")
        return
    _monitor_stop_event.clear()
    _monitor_thread = threading.Thread(
        target=_monitor_loop,
        args=(interval,),
        daemon=True,
        name="position-monitor",
    )
    _monitor_thread.start()
    log.info("position_monitor 线程已启动", interval=interval)


def stop_position_monitor():
    """停止持仓监控"""
    _monitor_stop_event.set()
    if _monitor_thread:
        _monitor_thread.join(timeout=10)
    log.info("position_monitor 线程已停止")


def get_monitor_stats() -> dict:
    """获取监控统计信息"""
    return dict(_stats)


def run_scan_once() -> dict:
    """
    手动触发一次监控扫描（同步接口，供 API 调用）。
    在新的 event loop 中运行一次 _monitor_cycle()。
    返回扫描结果摘要。
    """
    import asyncio as _asyncio
    loop = _asyncio.new_event_loop()
    try:
        loop.run_until_complete(_monitor_cycle())
        return {
            "scanned": True,
            "positions_monitored": _stats.get("positions_monitored", 0),
            "triggers_total": _stats.get("triggers_total", 0),
            "last_scan_at": _stats.get("last_scan_at"),
        }
    except Exception as e:
        return {"scanned": False, "error": str(e)}
    finally:
        loop.close()
