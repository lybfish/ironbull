"""
将远程执行节点返回的 results 在中心写库并结算（submit_order + settle_fill）。
供 signal-monitor 与 node-execute worker 共用。
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any

from libs.core import get_logger, gen_id
from libs.member import ExecutionTarget
from libs.trading.settlement import TradeSettlementService
from libs.exchange.utils import normalize_symbol

log = get_logger("execution-node-apply")


def _write_sl_tp_to_position_remote(
    session,
    target: ExecutionTarget,
    symbol: str,
    side: str,
    filled_price: float,
    stop_loss: float,
    take_profit: float,
    strategy_code: str = "",
):
    """将 SL/TP 写入 fact_position（远程节点结果写回）"""
    from libs.position.repository import PositionRepository
    pos_repo = PositionRepository(session)
    position_side = "LONG" if (side or "BUY").upper() == "BUY" else "SHORT"
    pos = None
    for s in [symbol, symbol.replace("/", "")]:
        pos = pos_repo.get_by_key(
            tenant_id=target.tenant_id,
            account_id=target.account_id,
            symbol=s,
            exchange=target.exchange or "binance",
            position_side=position_side,
        )
        if pos:
            break
    if pos:
        pos.entry_price = Decimal(str(filled_price)) if filled_price else None
        pos.stop_loss = Decimal(str(stop_loss)) if stop_loss else None
        pos.take_profit = Decimal(str(take_profit)) if take_profit else None
        pos.strategy_code = strategy_code or None
        pos_repo.update(pos)
        log.info("SL/TP 已写入持仓表（远程节点）",
                 account_id=target.account_id, symbol=symbol,
                 entry=filled_price, sl=stop_loss, tp=take_profit)


def apply_remote_results(
    session,
    signal: Dict[str, Any],
    targets_by_account: Dict[int, ExecutionTarget],
    response_results: List[Dict],
) -> List[Dict]:
    """
    将远程节点返回的 results 在中心写库并结算（submit_order + settle_fill）。
    targets_by_account: account_id -> ExecutionTarget（含 tenant_id, account_id, user_id, exchange, market_type）
    """
    outcome = []
    # 规范化 symbol（统一为 BTC/USDT 格式，防止 BTCUSDT 与 BTC/USDT 不一致）
    symbol = normalize_symbol((signal or {}).get("symbol", ""), "binance")
    side = (signal or {}).get("side", "BUY")
    strategy_code = (signal or {}).get("strategy") or (signal or {}).get("strategy_code") or ""
    stop_loss = float((signal or {}).get("stop_loss") or 0)
    take_profit = float((signal or {}).get("take_profit") or 0)
    # 信号类型 → trade_type 映射
    sig_type = ((signal or {}).get("signal_type") or "OPEN").upper()
    trade_type = {"OPEN": "OPEN", "CLOSE": "CLOSE", "ADD": "ADD", "HEDGE": "OPEN", "GRID": "OPEN"}.get(sig_type, "OPEN")
    close_reason = (signal or {}).get("close_reason")
    exchange_default = "binance"
    for item in response_results:
        account_id = item.get("account_id")
        target = targets_by_account.get(account_id) if account_id else None
        if not target:
            outcome.append({"account_id": account_id, "success": False, "error": "target not found"})
            continue
        if not item.get("success"):
            outcome.append({
                "account_id": account_id,
                "user_id": target.user_id,
                "success": False,
                "error": item.get("error", "unknown"),
            })
            continue
        order_id = item.get("order_id") or gen_id("ORD")
        exchange_order_id = item.get("exchange_order_id") or ""
        filled_qty = float(item.get("filled_quantity") or 0)
        filled_price = float(item.get("filled_price") or 0)
        if filled_qty <= 0 or filled_price <= 0:
            outcome.append({"account_id": account_id, "user_id": target.user_id, "success": False, "error": "no fill"})
            continue
        market_type = target.market_type or "future"
        position_side = "NONE"
        if market_type == "future":
            position_side = "LONG" if (side or "BUY").upper() == "BUY" else "SHORT"
        try:
            settlement_svc = TradeSettlementService(
                session=session,
                tenant_id=target.tenant_id,
                account_id=target.account_id,
                currency="USDT",
            )
            # 1) 先创建订单记录（fact_order），否则 submit_order / settle_fill 找不到订单
            order_dto = settlement_svc.create_order(
                symbol=symbol or "BTC/USDT",
                exchange=target.exchange or exchange_default,
                side=(side or "BUY").upper(),
                order_type="MARKET",
                quantity=Decimal(str(filled_qty)),
                price=Decimal(str(filled_price)),
                signal_id=(signal or {}).get("signal_id"),
                position_side=position_side,
                market_type=market_type,
                trade_type=trade_type,
                close_reason=close_reason,
            )
            db_order_id = order_dto.order_id  # 数据库中的订单ID
            # 2) 提交订单（写入 exchange_order_id，更新状态）
            settlement_svc.submit_order(order_id=db_order_id, exchange_order_id=exchange_order_id)
            # 3) 结算成交（写 fact_fill → fact_position → fact_ledger）
            settlement_svc.settle_fill(
                order_id=db_order_id,
                symbol=symbol or "BTC/USDT",
                exchange=target.exchange or exchange_default,
                side=(side or "BUY").upper(),
                quantity=Decimal(str(filled_qty)),
                price=Decimal(str(filled_price)),
                fee=Decimal("0"),
                fee_currency="USDT",
                exchange_trade_id=exchange_order_id,
                filled_at=datetime.now(),
                position_side=position_side,
                market_type=market_type,
            )
            # 写入 SL/TP 到持仓表（自管模式）
            if stop_loss or take_profit:
                try:
                    _write_sl_tp_to_position_remote(
                        session, target, symbol, side,
                        filled_price, stop_loss, take_profit, strategy_code,
                    )
                except Exception as sltp_err:
                    log.warning("write sl/tp to position (remote) failed",
                                account_id=account_id, error=str(sltp_err))
            outcome.append({
                "account_id": account_id,
                "user_id": target.user_id,
                "success": True,
                "order_id": db_order_id,
                "exchange_order_id": exchange_order_id,
                "filled_quantity": filled_qty,
                "filled_price": filled_price,
            })
        except Exception as e:
            log.warning("apply_remote_result failed", account_id=account_id, error=str(e))
            outcome.append({"account_id": account_id, "user_id": target.user_id, "success": False, "error": str(e)})
    return outcome
