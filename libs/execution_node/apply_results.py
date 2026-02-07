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

log = get_logger("execution-node-apply")


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
    symbol = (signal or {}).get("symbol", "")
    side = (signal or {}).get("side", "BUY")
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
                filled_at=datetime.utcnow(),
                position_side=position_side,
                market_type=market_type,
            )
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
