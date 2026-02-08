#!/usr/bin/env python3
"""
修复 Gate 历史订单的手续费

从 Gate API 查询成交记录，补充缺失的手续费。
用法:
    PYTHONPATH=. python3 scripts/fix_gate_fees.py [--days 7] [--dry-run]
"""
import argparse
import sys
import os
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from libs.core.database import get_db
from libs.core.logger import get_logger, setup_logging
from libs.order_trade.models import Order, Fill
from libs.member.models import ExchangeAccount
from libs.trading.live_trader import LiveTrader

setup_logging(level="INFO", structured=False, service_name="fix_gate_fees")
log = get_logger("fix_gate_fees")


async def fix_order_fee(order: Order, fills: list, api_key: str, api_secret: str, passphrase: Optional[str] = None, dry_run: bool = False):
    """修复单个订单的手续费"""
    # 优先从成交记录中提取手续费（如果有）
    total_fee = 0.0
    fee_currency = order.fee_currency or "USDT"
    
    for fill in fills:
        if fill.fee and float(fill.fee) > 0:
            total_fee += float(fill.fee)
            if fill.fee_currency:
                fee_currency = fill.fee_currency
    
    # 如果成交记录中也没有手续费，尝试从 Gate API 查询
    if total_fee == 0 and order.exchange_order_id:
        try:
            # 创建 trader（使用订单关联账户的 API 密钥）
            trader = LiveTrader(
                exchange="gate",
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase,
                market_type="future",
                sandbox=False,
            )
            
            try:
                await trader.exchange.load_markets()
                
                # 等待一下确保成交记录可查
                await asyncio.sleep(0.5)
                
                # 规范化 symbol
                symbol = order.symbol
                if "/" not in symbol and "USDT" in symbol:
                    symbol = symbol.replace("USDT", "/USDT")
                
                # 获取成交记录
                trades = await trader.exchange.fetch_order_trades(order.exchange_order_id, symbol)
                
                if trades:
                    for t in trades:
                        # 提取手续费
                        t_fee = t.get("fee", {})
                        if t_fee and isinstance(t_fee, dict) and t_fee.get("cost") is not None:
                            total_fee += abs(float(t_fee["cost"]))
                            if not fee_currency:
                                fee_currency = t_fee.get("currency", "")
                        
                        # 检查 info 中的原始手续费字段（Gate 特有）
                        if total_fee == 0:
                            t_info = t.get("info", {})
                            if isinstance(t_info, dict):
                                raw_c = (
                                    t_info.get("commission") or 
                                    t_info.get("fee") or 
                                    t_info.get("fill_fee") or
                                    t_info.get("taker_fee") or
                                    t_info.get("maker_fee") or
                                    t_info.get("n")
                                )
                                if raw_c is not None:
                                    try:
                                        total_fee += abs(float(raw_c))
                                    except (ValueError, TypeError):
                                        pass
                                if not fee_currency:
                                    fee_currency = (
                                        t_info.get("commissionAsset") or 
                                        t_info.get("fee_currency") or 
                                        t_info.get("feeCurrency") or
                                        "USDT"
                                    )
            except Exception as e:
                log.debug(f"订单 {order.order_id} 从 API 查询失败: {e}")
            finally:
                await trader.close()
        except Exception as e:
            log.debug(f"订单 {order.order_id} 创建 trader 失败: {e}")
    
    if total_fee > 0:
        log.info(f"订单 {order.order_id}: 找到手续费 {total_fee} {fee_currency}")
        if not dry_run:
            order.total_fee = Decimal(str(total_fee))
            order.fee_currency = fee_currency
            return True
        else:
            log.info(f"[DRY-RUN] 将更新订单 {order.order_id}: total_fee={total_fee}, fee_currency={fee_currency}")
            return True
    else:
        log.warning(f"订单 {order.order_id}: 未找到手续费")
        return False


async def main():
    parser = argparse.ArgumentParser(description="修复 Gate 历史订单手续费")
    parser.add_argument("--days", type=int, default=7, help="修复最近N天的订单（默认7天）")
    parser.add_argument("--dry-run", action="store_true", help="仅显示，不实际更新")
    args = parser.parse_args()
    
    with get_db() as db:
        since = datetime.now() - timedelta(days=args.days)
        
        # 查询手续费为0的 Gate 订单，并关联账户信息
        orders = db.query(Order).join(
            ExchangeAccount, Order.account_id == ExchangeAccount.id
        ).filter(
            Order.exchange == "gate",
            Order.status.in_(["filled", "partial"]),
            (Order.total_fee == 0) | (Order.total_fee.is_(None)),
            Order.created_at >= since,
            Order.exchange_order_id.isnot(None),
            ExchangeAccount.exchange == "gate",
            ExchangeAccount.api_key.isnot(None),
            ExchangeAccount.api_secret.isnot(None),
        ).order_by(Order.created_at.desc()).all()
        
        log.info(f"找到 {len(orders)} 个需要修复的订单")
        
        if not orders:
            log.info("没有需要修复的订单")
            return 0
        
        # 按账户分组，避免重复创建 trader
        orders_by_account = {}
        for order in orders:
            account_id = order.account_id
            if account_id not in orders_by_account:
                orders_by_account[account_id] = []
            orders_by_account[account_id].append(order)
        
        fixed_count = 0
        failed_count = 0
        
        for account_id, account_orders in orders_by_account.items():
            # 获取账户信息
            account = db.query(ExchangeAccount).filter(ExchangeAccount.id == account_id).first()
            if not account or not account.api_key or not account.api_secret:
                log.warning(f"账户 {account_id} 无 API 密钥，跳过")
                failed_count += len(account_orders)
                continue
            
            log.info(f"处理账户 {account_id} 的 {len(account_orders)} 个订单")
            
            for order in account_orders:
                log.info(f"  订单 {order.order_id} ({order.symbol}, {order.created_at})")
                
                # 获取订单的成交记录
                fills = db.query(Fill).filter(Fill.order_id == order.order_id).all()
                
                success = await fix_order_fee(
                    order,
                    fills,
                    account.api_key, 
                    account.api_secret, 
                    account.passphrase,
                    dry_run=args.dry_run
                )
                if success:
                    fixed_count += 1
                    if not args.dry_run:
                        db.commit()
                else:
                    failed_count += 1
        
        log.info(f"\n=== 修复完成 ===")
        log.info(f"成功: {fixed_count}")
        log.info(f"失败: {failed_count}")
        
        if not args.dry_run and fixed_count > 0:
            db.commit()
            log.info("已提交数据库更改")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
