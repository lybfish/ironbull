#!/usr/bin/env python3
"""
清理交易数据脚本 — 清除所有交易相关数据，重新开始。
保留：用户、交易所账户、策略、租户、配额等配置数据。

用法: PYTHONPATH=. python3 scripts/clean_trading_data.py [--yes]
  加 --yes 跳过确认直接执行
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from libs.core.database import get_engine

# 需要清空的表（按依赖关系排序，先删子表再删父表）
TABLES_TO_TRUNCATE = [
    # 交易与结算
    "fact_fill",              # 成交记录
    "fact_order",             # 订单
    "fact_trade",             # 交易记录
    # 持仓
    "fact_position_change",   # 持仓变动
    "fact_position",          # 持仓
    # 资金账户与流水
    "fact_transaction",       # 资金流水
    "fact_account",           # 资金账户
    "fact_equity_snapshot",   # 权益快照
    "fact_ledger",            # 账本
    "fact_freeze",            # 冻结记录
    # 信号与监控
    "fact_signal_event",      # 信号事件
    # 分析统计
    "fact_performance_snapshot",  # 绩效快照
    "fact_trade_statistics",      # 交易统计
    "fact_risk_metrics",          # 风险指标
    # 分销与利润
    "fact_reward_log",        # 奖励日志
    "fact_user_reward",       # 用户奖励
    "fact_profit_pool",       # 利润池
]

# 需要重置余额的表
RESET_EXCHANGE_ACCOUNTS = True  # 重置 dim_exchange_account 的余额字段
RESET_BINDING_STATS = True      # 重置 dim_strategy_binding 的统计字段


def main():
    skip_confirm = "--yes" in sys.argv

    print("=" * 60)
    print("  IronBull 交易数据清理工具")
    print("=" * 60)
    print()
    print("将清空以下交易数据表：")
    for t in TABLES_TO_TRUNCATE:
        print(f"  - {t}")
    print()
    print("将重置：")
    if RESET_EXCHANGE_ACCOUNTS:
        print("  - dim_exchange_account: balance/futures_balance/futures_available → 0")
    if RESET_BINDING_STATS:
        print("  - dim_strategy_binding: total_profit/total_trades → 0")
    print()
    print("保留不动：")
    print("  - dim_user (用户)")
    print("  - dim_exchange_account (交易所账户，仅重置余额)")
    print("  - dim_strategy (策略)")
    print("  - dim_tenant_strategy (租户策略)")
    print("  - dim_strategy_binding (策略绑定，仅重置统计)")
    print("  - dim_tenant (租户)")
    print("  - dim_quota_plan (配额)")
    print("  - dim_execution_node (执行节点)")
    print("  - fact_point_card_log (点卡流水)")
    print()

    if not skip_confirm:
        answer = input("确认清理？输入 yes 继续: ").strip()
        if answer != "yes":
            print("已取消")
            return

    engine = get_engine()
    with engine.connect() as conn:
        # 禁用外键检查
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

        for table in TABLES_TO_TRUNCATE:
            try:
                # 先检查表是否存在
                result = conn.execute(text(
                    f"SELECT COUNT(*) FROM information_schema.tables "
                    f"WHERE table_schema = DATABASE() AND table_name = :tbl"
                ), {"tbl": table})
                if result.scalar() == 0:
                    print(f"  [skip] {table} (表不存在)")
                    continue

                # 查当前行数
                count = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
                conn.execute(text(f"TRUNCATE TABLE `{table}`"))
                print(f"  [ok] {table} (清除 {count} 条)")
            except Exception as e:
                print(f"  [fail] {table}: {e}")

        # 重置交易所账户余额
        if RESET_EXCHANGE_ACCOUNTS:
            try:
                affected = conn.execute(text(
                    "UPDATE `fact_exchange_account` SET "
                    "balance = 0, futures_balance = 0, futures_available = 0, "
                    "last_sync_at = NULL, last_sync_error = NULL"
                )).rowcount
                print(f"  [ok] fact_exchange_account 余额重置 ({affected} 条)")
            except Exception as e:
                print(f"  [fail] 重置交易所余额: {e}")

        # 重置策略绑定统计
        if RESET_BINDING_STATS:
            try:
                affected = conn.execute(text(
                    "UPDATE `dim_strategy_binding` SET "
                    "total_profit = 0, total_trades = 0"
                )).rowcount
                print(f"  [ok] dim_strategy_binding 统计重置 ({affected} 条)")
            except Exception as e:
                print(f"  [fail] 重置策略绑定统计: {e}")

        # 恢复外键检查
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()

    print()
    print("清理完成！现在可以：")
    print("  1. 在后台「同步管理」页面手动同步余额")
    print("  2. 等待 signal-monitor 自动同步（每 5 分钟）")
    print("  3. 策略信号触发后会自动产生新的交易数据")


if __name__ == "__main__":
    main()
