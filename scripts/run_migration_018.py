#!/usr/bin/env python3
"""
迁移 018：fact_position 加 entry_price / stop_loss / take_profit / strategy_code 列（幂等）

新增字段：
- entry_price DECIMAL(20,8)   入场价格
- stop_loss DECIMAL(20,8)     止损价格（自管模式，不挂交易所单）
- take_profit DECIMAL(20,8)   止盈价格（自管模式，不挂交易所单）
- strategy_code VARCHAR(64)   策略代码（用于平仓后触发冷却回调）

目的：将 SL/TP 存在自己的数据库中，由 position_monitor 监控到价平仓。
     交易所看不到止损位，防止"扫损"。

用法：PYTHONPATH=. python3 scripts/run_migration_018.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from libs.core import get_config, get_logger
from libs.core.database import init_database, get_engine

log = get_logger("migration-018")


def column_exists(conn, table: str, column: str, schema: str) -> bool:
    row = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :tbl AND COLUMN_NAME = :col"
    ), {"schema": schema, "tbl": table, "col": column}).scalar()
    return row > 0


def run():
    config = get_config()
    db_name = config.get_str("db_name", "ironbull")
    init_database()
    engine = get_engine()

    TABLE = "fact_position"

    with engine.connect() as conn:
        # entry_price
        if not column_exists(conn, TABLE, "entry_price", db_name):
            conn.execute(text(
                f"ALTER TABLE `{TABLE}` ADD COLUMN entry_price DECIMAL(20,8) NULL "
                "COMMENT '入场价格' AFTER liquidation_price"
            ))
            log.info("added column: entry_price")
        else:
            log.info("column entry_price already exists")

        # stop_loss
        if not column_exists(conn, TABLE, "stop_loss", db_name):
            conn.execute(text(
                f"ALTER TABLE `{TABLE}` ADD COLUMN stop_loss DECIMAL(20,8) NULL "
                "COMMENT '止损价格（自管模式，不挂交易所单）' AFTER entry_price"
            ))
            log.info("added column: stop_loss")
        else:
            log.info("column stop_loss already exists")

        # take_profit
        if not column_exists(conn, TABLE, "take_profit", db_name):
            conn.execute(text(
                f"ALTER TABLE `{TABLE}` ADD COLUMN take_profit DECIMAL(20,8) NULL "
                "COMMENT '止盈价格（自管模式，不挂交易所单）' AFTER stop_loss"
            ))
            log.info("added column: take_profit")
        else:
            log.info("column take_profit already exists")

        # strategy_code
        if not column_exists(conn, TABLE, "strategy_code", db_name):
            conn.execute(text(
                f"ALTER TABLE `{TABLE}` ADD COLUMN strategy_code VARCHAR(64) NULL "
                "COMMENT '策略代码（用于冷却回调）' AFTER take_profit"
            ))
            log.info("added column: strategy_code")
        else:
            log.info("column strategy_code already exists")

        # 添加索引：加速 position_monitor 查询（status=OPEN + 有 SL/TP）
        try:
            conn.execute(text(
                f"ALTER TABLE `{TABLE}` ADD INDEX idx_position_sl_tp (status, stop_loss, take_profit)"
            ))
            log.info("added index: idx_position_sl_tp")
        except Exception as e:
            if "Duplicate" in str(e):
                log.info("index idx_position_sl_tp already exists")
            else:
                log.warning(f"add index failed: {e}")

        conn.commit()
        log.info("migration 018 done")


if __name__ == "__main__":
    run()
