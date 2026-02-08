#!/usr/bin/env python3
"""
估算所有交易所历史订单的手续费（按默认 taker 费率）

支持的交易所：
- Binance: 0.04% taker
- OKX: 0.05% taker
- Gate: 0.05% taker

用法:
    PYTHONPATH=. python3 scripts/estimate_exchange_fees.py [--days 7] [--exchange binance|okx|gate|all] [--dry-run]
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

setup_logging(level="INFO", structured=False, service_name="estimate_exchange_fees")
log = get_logger("estimate_exchange_fees")

# 各交易所默认 taker 费率
EXCHANGE_FEE_RATES = {
    "binance": 0.0004,  # 0.04%
    "okx": 0.0005,      # 0.05%
    "gate": 0.0005,     # 0.05%
}


def estimate_fee(order: Order, fee_rate: float) -> tuple[float, str]:
    """估算订单手续费"""
    if not order.avg_price or not order.filled_quantity:
        return 0.0, "USDT"
    
    # 成交金额 = 价格 × 数量
    trade_value = float(order.avg_price) * float(order.filled_quantity)
    
    # 手续费 = 成交金额 × 费率
    estimated_fee = trade_value * fee_rate
    
    return estimated_fee, order.fee_currency or "USDT"


def main():
    parser = argparse.ArgumentParser(description="估算所有交易所历史订单手续费")
    parser.add_argument("--days", type=int, default=7, help="修复最近N天的订单（默认7天）")
    parser.add_argument("--exchange", type=str, default="all", 
                       choices=["binance", "okx", "gate", "all"],
                       help="指定交易所（默认all）")
    parser.add_argument("--dry-run", action="store_true", help="仅显示，不实际更新")
    args = parser.parse_args()
    
    with get_db() as db:
        since = datetime.now() - timedelta(days=args.days)
        
        # 确定要处理的交易所
        exchanges = [args.exchange] if args.exchange != "all" else list(EXCHANGE_FEE_RATES.keys())
        
        total_fixed = 0
        
        for exchange in exchanges:
            fee_rate = EXCHANGE_FEE_RATES.get(exchange)
            if not fee_rate:
                log.warning(f"未知交易所费率: {exchange}，跳过")
                continue
            
            # 查询手续费为0的订单
            orders = db.query(Order).filter(
                Order.exchange == exchange,
                Order.status.in_(["filled", "partial"]),
                (Order.total_fee == 0) | (Order.total_fee.is_(None)),
                Order.created_at >= since,
                Order.avg_price.isnot(None),
                Order.filled_quantity > 0,
            ).order_by(Order.created_at.desc()).all()
            
            log.info(f"\n=== {exchange.upper()} ===")
            log.info(f"找到 {len(orders)} 个需要估算手续费的订单（费率: {fee_rate*100:.3f}%）")
            
            if not orders:
                continue
            
            fixed_count = 0
            
            for order in orders:
                estimated_fee, fee_currency = estimate_fee(order, fee_rate)
                
                if estimated_fee > 0:
                    trade_value = float(order.avg_price) * float(order.filled_quantity)
                    log.info(f"订单 {order.order_id}: 估算手续费 {estimated_fee:.6f} {fee_currency} "
                            f"(成交金额: {trade_value:.2f})")
                    
                    if not args.dry_run:
                        order.total_fee = Decimal(str(estimated_fee))
                        order.fee_currency = fee_currency
                        fixed_count += 1
                        db.commit()
                    else:
                        log.info(f"[DRY-RUN] 将更新订单 {order.order_id}: total_fee={estimated_fee:.6f}, fee_currency={fee_currency}")
                        fixed_count += 1
            
            log.info(f"{exchange.upper()}: 处理了 {fixed_count} 个订单")
            total_fixed += fixed_count
        
        log.info(f"\n=== 估算完成 ===")
        log.info(f"总计处理: {total_fixed} 个订单")
        
        if not args.dry_run and total_fixed > 0:
            log.info("已提交数据库更改")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
