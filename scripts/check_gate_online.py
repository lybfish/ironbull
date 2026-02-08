#!/usr/bin/env python3
"""
线上 Gate 价格和手续费检查脚本

用法:
    PYTHONPATH=. python3 scripts/check_gate_online.py
    PYTHONPATH=. python3 scripts/check_gate_online.py --days 7  # 检查最近7天
    PYTHONPATH=. python3 scripts/check_gate_online.py --fix-price  # 尝试修复价格为0的订单
"""
import argparse
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from libs.core.database import get_db
from libs.core.logger import get_logger, setup_logging
from libs.order_trade.models import Order, Fill

setup_logging(level="INFO", structured=False, service_name="check_gate")
log = get_logger("check_gate")


def check_orders(days: int = 1, fix_price: bool = False):
    """检查 Gate 订单的价格和手续费"""
    log.info(f"=== 检查最近 {days} 天的 Gate 订单 ===")
    
    with get_db() as db:
        since = datetime.now() - timedelta(days=days)
        
        # 查询 Gate 订单
        orders = db.query(Order).filter(
            Order.exchange == "gate",
            Order.created_at >= since
        ).order_by(Order.created_at.desc()).all()
        
        log.info(f"找到 {len(orders)} 个 Gate 订单")
        
        # 统计
        zero_price_count = 0
        zero_fee_count = 0
        has_price_count = 0
        has_fee_count = 0
        total_orders = len(orders)
        
        # 详细检查
        issues = []
        for order in orders:
            has_price = (order.filled_price or 0) > 0
            has_fee = (order.commission or 0) > 0
            is_filled = order.status in ("filled", "partial")
            
            if has_price:
                has_price_count += 1
            else:
                zero_price_count += 1
                if is_filled:
                    issues.append({
                        "type": "zero_price",
                        "order_id": order.order_id,
                        "symbol": order.symbol,
                        "status": order.status,
                        "filled_qty": order.filled_quantity,
                        "created_at": order.created_at,
                    })
            
            if has_fee:
                has_fee_count += 1
            else:
                zero_fee_count += 1
                if is_filled:
                    issues.append({
                        "type": "zero_fee",
                        "order_id": order.order_id,
                        "symbol": order.symbol,
                        "status": order.status,
                        "filled_qty": order.filled_quantity,
                        "created_at": order.created_at,
                    })
        
        # 打印统计
        log.info("\n=== 统计结果 ===")
        log.info(f"总订单数: {total_orders}")
        log.info(f"有价格: {has_price_count} ({has_price_count*100/max(total_orders,1):.1f}%)")
        log.info(f"价格为0: {zero_price_count} ({zero_price_count*100/max(total_orders,1):.1f}%)")
        log.info(f"有手续费: {has_fee_count} ({has_fee_count*100/max(total_orders,1):.1f}%)")
        log.info(f"手续费为0: {zero_fee_count} ({zero_fee_count*100/max(total_orders,1):.1f}%)")
        
        # 打印问题订单
        if issues:
            log.info(f"\n=== 发现 {len(issues)} 个问题订单 ===")
            for issue in issues[:20]:  # 只显示前20个
                log.info(f"  {issue['type']}: {issue['order_id']} | {issue['symbol']} | "
                        f"status={issue['status']} | qty={issue['filled_qty']} | "
                        f"time={issue['created_at']}")
        
        # 尝试修复价格为0的订单（从成交记录中获取）
        if fix_price and issues:
            log.info("\n=== 尝试修复价格为0的订单 ===")
            fixed_count = 0
            for issue in issues:
                if issue['type'] == 'zero_price':
                    # 从成交记录中获取平均价格
                    fills = db.query(Fill).filter(
                        Fill.order_id == issue['order_id']
                    ).all()
                    if fills:
                        total_cost = sum(float(f.price or 0) * float(f.quantity or 0) for f in fills)
                        total_qty = sum(float(f.quantity or 0) for f in fills)
                        if total_qty > 0:
                            avg_price = total_cost / total_qty
                            order = db.query(Order).filter(
                                Order.order_id == issue['order_id']
                            ).first()
                            if order:
                                order.filled_price = Decimal(str(avg_price))
                                db.commit()
                                fixed_count += 1
                                log.info(f"  修复订单 {issue['order_id']}: price={avg_price:.2f}")
            log.info(f"修复了 {fixed_count} 个订单的价格")
        
        # 检查成交记录
        log.info("\n=== 检查成交记录 ===")
        fills = db.query(Fill).join(Order).filter(
            Order.exchange == "gate",
            Fill.created_at >= since
        ).order_by(Fill.created_at.desc()).limit(50).all()
        
        zero_price_fills = 0
        zero_fee_fills = 0
        for fill in fills:
            if (fill.price or 0) == 0:
                zero_price_fills += 1
            if (fill.commission or 0) == 0:
                zero_fee_fills += 1
        
        log.info(f"成交记录总数: {len(fills)}")
        log.info(f"价格为0的成交: {zero_price_fills}")
        log.info(f"手续费为0的成交: {zero_fee_fills}")
        
        # 显示最近的几个订单详情
        log.info("\n=== 最近 10 个订单详情 ===")
        for order in orders[:10]:
            log.info(f"  订单 {order.order_id}:")
            log.info(f"    symbol: {order.symbol}")
            log.info(f"    status: {order.status}")
            log.info(f"    filled_qty: {order.filled_quantity}")
            log.info(f"    filled_price: {order.filled_price}")
            log.info(f"    commission: {order.commission}")
            log.info(f"    commission_asset: {order.commission_asset}")
            log.info(f"    created_at: {order.created_at}")
            
            # 检查成交记录
            fills = db.query(Fill).filter(Fill.order_id == order.order_id).all()
            if fills:
                log.info(f"    成交记录数: {len(fills)}")
                for fill in fills[:3]:  # 只显示前3个
                    log.info(f"      fill {fill.fill_id}: price={fill.price}, qty={fill.quantity}, fee={fill.commission}")


def main():
    parser = argparse.ArgumentParser(description="线上 Gate 价格和手续费检查")
    parser.add_argument("--days", type=int, default=1, help="检查最近N天的订单（默认1天）")
    parser.add_argument("--fix-price", action="store_true", help="尝试修复价格为0的订单（从成交记录中获取）")
    args = parser.parse_args()
    
    try:
        check_orders(days=args.days, fix_price=args.fix_price)
    except Exception as e:
        log.error(f"检查失败: {e}", exc_info=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
