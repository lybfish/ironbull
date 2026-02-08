#!/usr/bin/env python3
"""
从订单表同步手续费到成交记录表

当订单的手续费已修复，但成交记录的手续费仍为0时，从订单中同步手续费到成交记录。
用法:
    PYTHONPATH=. python3 scripts/sync_fill_fees_from_orders.py [--days 7] [--dry-run]
"""
import argparse
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from libs.core.database import get_db
from libs.core.logger import get_logger, setup_logging

setup_logging(level="INFO", structured=False, service_name="sync_fill_fees")
log = get_logger("sync_fill_fees")


def main():
    parser = argparse.ArgumentParser(description="从订单表同步手续费到成交记录表")
    parser.add_argument("--days", type=int, default=7, help="修复最近N天的成交记录（默认7天）")
    parser.add_argument("--dry-run", action="store_true", help="仅显示，不实际更新")
    args = parser.parse_args()
    
    with get_db() as db:
        since = datetime.now() - timedelta(days=args.days)
        
        # 查询手续费为0的成交记录，但对应的订单有手续费
        sql = """
            SELECT 
                f.fill_id,
                f.order_id,
                o.exchange,
                o.side,
                o.total_fee as order_fee,
                o.fee_currency as order_fee_currency,
                f.fee as fill_fee,
                f.fee_currency as fill_fee_currency,
                f.price,
                f.quantity
            FROM fact_fill f
            JOIN fact_order o ON f.order_id = o.order_id
            WHERE o.created_at >= :since
                AND o.status IN ('filled', 'partial')
                AND o.total_fee > 0
                AND (f.fee = 0 OR f.fee IS NULL)
            ORDER BY f.created_at DESC
        """
        
        result = db.execute(sql, {"since": since})
        fills = result.fetchall()
        
        log.info(f"找到 {len(fills)} 个需要同步手续费的成交记录")
        
        if not fills:
            log.info("没有需要修复的成交记录")
            return 0
        
        fixed_count = 0
        
        for row in fills:
            fill_id = row[0]
            order_id = row[1]
            exchange = row[2]
            side = row[3]
            order_fee = float(row[4]) if row[4] else 0.0
            order_fee_currency = row[5] or "USDT"
            fill_fee = float(row[6]) if row[6] else 0.0
            fill_fee_currency = row[7]
            price = float(row[8]) if row[8] else 0.0
            quantity = float(row[9]) if row[9] else 0.0
            
            if order_fee > 0:
                log.info(f"成交记录 {fill_id} (订单 {order_id}): "
                        f"从订单同步手续费 {order_fee:.6f} {order_fee_currency} "
                        f"(成交金额: {price * quantity:.2f})")
                
                if not args.dry_run:
                    # 更新成交记录的手续费
                    update_sql = """
                        UPDATE fact_fill
                        SET fee = :fee, fee_currency = :fee_currency
                        WHERE fill_id = :fill_id
                    """
                    db.execute(update_sql, {
                        "fee": Decimal(str(order_fee)),
                        "fee_currency": order_fee_currency,
                        "fill_id": fill_id,
                    })
                    fixed_count += 1
                    db.commit()
                else:
                    log.info(f"[DRY-RUN] 将更新成交记录 {fill_id}: fee={order_fee:.6f}, fee_currency={order_fee_currency}")
                    fixed_count += 1
        
        log.info(f"\n=== 同步完成 ===")
        log.info(f"处理: {fixed_count} 个成交记录")
        
        if not args.dry_run and fixed_count > 0:
            log.info("已提交数据库更改")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
