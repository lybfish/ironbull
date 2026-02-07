#!/usr/bin/env python3
"""
只清空：订单表、成交记录表、持仓表、持仓变动表、信号事件表。
其它表（资金账户、流水、审计等）不动。

用法: PYTHONPATH=. python3 scripts/clear_orders_fills_positions_signals.py [--yes]
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from libs.core.database import get_engine

# 仅清这 5 张表（按依赖顺序：先子表后父表）
TABLES = [
    "fact_fill",             # 成交记录
    "fact_order",            # 订单
    "fact_position_change",  # 持仓变动
    "fact_position",         # 持仓
    "fact_signal_event",     # 信号事件
]


def main():
    skip_confirm = "--yes" in sys.argv
    print("将清空：订单、成交、持仓、持仓变动、信号事件 共 5 张表")
    for t in TABLES:
        print(f"  - {t}")
    if not skip_confirm:
        answer = input("确认？输入 yes 继续: ").strip()
        if answer != "yes":
            print("已取消")
            return

    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in TABLES:
            try:
                r = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = :t"
                ), {"t": table})
                if r.scalar() == 0:
                    print(f"  [skip] {table} (表不存在)")
                    continue
                count = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
                conn.execute(text(f"TRUNCATE TABLE `{table}`"))
                print(f"  [ok] {table} (清除 {count} 条)")
            except Exception as e:
                print(f"  [fail] {table}: {e}")
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()
    print("完成。")


if __name__ == "__main__":
    main()
