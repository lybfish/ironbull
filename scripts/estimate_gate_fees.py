#!/usr/bin/env python3
"""
估算 Gate 历史订单的手续费（按 Gate 默认费率 0.05% taker）

当无法从 API 获取手续费时，按成交金额的 0.05% 估算。
用法:
    PYTHONPATH=. python3 scripts/estimate_gate_fees.py [--days 7] [--dry-run]
"""
import argparse
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from libs.core.database import get_db
from libs.core.logger import get_logger, setup_logging
from libs.order_trade.models import Order

setup_logging(level="INFO", structured=False, service_name="estimate_gate_fees")
log = get_logger("estimate_gate_fees")

# Gate 默认 taker 费率（0.05%）
GATE_TAKER_FEE_RATE = 0.0005


def estimate_fee(order: Order) -> tuple[float, str]:
    """估算订单手续费"""
    if not order.avg_price or not order.filled_quantity:
        return 0.0, "USDT"
    
    # 成交金额 = 价格 × 数量
    trade_value = float(order.avg_price) * float(order.filled_quantity)
    
    # 手续费 = 成交金额 × 费率
    estimated_fee = trade_value * GATE_TAKER_FEE_RATE
    
    return estimated_fee, order.fee_currency or "USDT"


def main():
    parser = argparse.ArgumentParser(description="估算 Gate 历史订单手续费")
    parser.add_argument("--days", type=int, default=7, help="修复最近N天的订单（默认7天）")
    parser.add_argument("--dry-run", action="store_true", help="仅显示，不实际更新")
    parser.add_argument("--rate", type=float, default=0.0005, help="手续费率（默认0.05%%）")
    args = parser.parse_args()
    
    global GATE_TAKER_FEE_RATE
    GATE_TAKER_FEE_RATE = args.rate
    
    with get_db() as db:
        since = datetime.now() - timedelta(days=args.days)
        
        # 查询手续费为0的 Gate 订单
        orders = db.query(Order).filter(
            Order.exchange == "gate",
            Order.status.in_(["filled", "partial"]),
            (Order.total_fee == 0) | (Order.total_fee.is_(None)),
            Order.created_at >= since,
            Order.avg_price.isnot(None),
            Order.filled_quantity > 0,
        ).order_by(Order.created_at.desc()).all()
        
        log.info(f"找到 {len(orders)} 个需要估算手续费的订单")
        
        if not orders:
            log.info("没有需要修复的订单")
            return 0
        
        fixed_count = 0
        
        for order in orders:
            estimated_fee, fee_currency = estimate_fee(order)
            
            if estimated_fee > 0:
                log.info(f"订单 {order.order_id}: 估算手续费 {estimated_fee:.6f} {fee_currency} "
                        f"(成交金额: {float(order.avg_price) * float(order.filled_quantity):.2f})")
                
                if not args.dry_run:
                    order.total_fee = Decimal(str(estimated_fee))
                    order.fee_currency = fee_currency
                    fixed_count += 1
                    db.commit()
                else:
                    log.info(f"[DRY-RUN] 将更新订单 {order.order_id}: total_fee={estimated_fee:.6f}, fee_currency={fee_currency}")
                    fixed_count += 1
        
        log.info(f"\n=== 估算完成 ===")
        log.info(f"处理: {fixed_count} 个订单")
        
        if not args.dry_run and fixed_count > 0:
            log.info("已提交数据库更改")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
