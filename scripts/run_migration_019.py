#!/usr/bin/env python3
"""
迁移 019：为订单/成交/持仓表增加 trade_type / close_reason 字段（幂等）

新增字段：
- fact_order.trade_type VARCHAR(16)    交易类型: OPEN/CLOSE/ADD/REDUCE
- fact_order.close_reason VARCHAR(32)  平仓原因: SL/TP/SIGNAL/MANUAL/LIQUIDATION
- fact_fill.trade_type VARCHAR(16)     交易类型（冗余存储，便于查询）
- fact_position.close_reason VARCHAR(32) 平仓原因

目的：让系统能区分开仓/平仓订单，并记录平仓原因，
     支持前端展示、绩效分析按平仓原因统计。

用法：PYTHONPATH=. python3 scripts/run_migration_019.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from libs.core import get_config, get_logger
from libs.core.database import init_database, get_engine

log = get_logger("migration-019")


def column_exists(conn, table: str, column: str, schema: str) -> bool:
    row = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :tbl AND COLUMN_NAME = :col"
    ), {"schema": schema, "tbl": table, "col": column}).scalar()
    return row > 0


def add_column_if_not_exists(conn, table, column, definition, schema, after=None):
    """幂等添加列"""
    if not column_exists(conn, table, column, schema):
        after_clause = f" AFTER {after}" if after else ""
        conn.execute(text(
            f"ALTER TABLE `{table}` ADD COLUMN {column} {definition}{after_clause}"
        ))
        log.info(f"added column: {table}.{column}")
    else:
        log.info(f"column {table}.{column} already exists")


def add_index_if_not_exists(conn, table, index_name, columns):
    """幂等添加索引"""
    try:
        cols = ", ".join(columns)
        conn.execute(text(
            f"ALTER TABLE `{table}` ADD INDEX {index_name} ({cols})"
        ))
        log.info(f"added index: {table}.{index_name}")
    except Exception as e:
        if "Duplicate" in str(e):
            log.info(f"index {table}.{index_name} already exists")
        else:
            log.warning(f"add index {table}.{index_name} failed: {e}")


def run():
    config = get_config()
    db_name = config.get_str("db_name", "ironbull")
    init_database()
    engine = get_engine()

    with engine.connect() as conn:
        # ── fact_order ──
        add_column_if_not_exists(
            conn, "fact_order", "trade_type",
            "VARCHAR(16) NULL DEFAULT 'OPEN' COMMENT '交易类型: OPEN/CLOSE/ADD/REDUCE'",
            db_name, after="order_type",
        )
        add_column_if_not_exists(
            conn, "fact_order", "close_reason",
            "VARCHAR(32) NULL COMMENT '平仓原因: SL/TP/SIGNAL/MANUAL/LIQUIDATION'",
            db_name, after="trade_type",
        )

        # ── fact_fill ──
        add_column_if_not_exists(
            conn, "fact_fill", "trade_type",
            "VARCHAR(16) NULL COMMENT '交易类型: OPEN/CLOSE/ADD/REDUCE（冗余存储）'",
            db_name, after="side",
        )

        # ── fact_position ──
        add_column_if_not_exists(
            conn, "fact_position", "close_reason",
            "VARCHAR(32) NULL COMMENT '平仓原因: SL/TP/SIGNAL/MANUAL/LIQUIDATION'",
            db_name, after="status",
        )

        # ── 索引：加速按 trade_type 查询 ──
        add_index_if_not_exists(
            conn, "fact_order", "idx_order_trade_type", ["trade_type"]
        )
        add_index_if_not_exists(
            conn, "fact_order", "idx_order_close_reason", ["close_reason"]
        )
        add_index_if_not_exists(
            conn, "fact_position", "idx_position_close_reason", ["close_reason"]
        )

        # ── 将现有订单默认标记为 OPEN（仅未设置的）──
        try:
            result = conn.execute(text(
                "UPDATE `fact_order` SET trade_type = 'OPEN' WHERE trade_type IS NULL"
            ))
            log.info(f"updated {result.rowcount} existing orders to trade_type=OPEN")
        except Exception as e:
            log.warning(f"update existing orders failed: {e}")

        conn.commit()
        log.info("migration 019 done")


if __name__ == "__main__":
    run()
