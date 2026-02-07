#!/usr/bin/env python3
"""
迁移 016：fact_account 加 unrealized_pnl / equity / margin_ratio 列（幂等）

用法：PYTHONPATH=. python3 scripts/run_migration_016.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from libs.core import get_config, get_logger
from libs.core.database import init_database, get_engine

log = get_logger("migration-016")


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

    with engine.connect() as conn:
        # unrealized_pnl
        if not column_exists(conn, "fact_account", "unrealized_pnl", db_name):
            conn.execute(text(
                "ALTER TABLE fact_account ADD COLUMN unrealized_pnl DECIMAL(20,8) NOT NULL DEFAULT 0 "
                "COMMENT '未实现盈亏（从交易所同步）' AFTER margin_used"
            ))
            log.info("added column: fact_account.unrealized_pnl")
        else:
            log.info("column fact_account.unrealized_pnl already exists")

        # equity
        if not column_exists(conn, "fact_account", "equity", db_name):
            conn.execute(text(
                "ALTER TABLE fact_account ADD COLUMN equity DECIMAL(20,8) NOT NULL DEFAULT 0 "
                "COMMENT '权益（余额+未实现盈亏）' AFTER unrealized_pnl"
            ))
            log.info("added column: fact_account.equity")
        else:
            log.info("column fact_account.equity already exists")

        # margin_ratio
        if not column_exists(conn, "fact_account", "margin_ratio", db_name):
            conn.execute(text(
                "ALTER TABLE fact_account ADD COLUMN margin_ratio DECIMAL(10,4) DEFAULT 0 "
                "COMMENT '保证金使用率' AFTER equity"
            ))
            log.info("added column: fact_account.margin_ratio")
        else:
            log.info("column fact_account.margin_ratio already exists")

        # synced_balance：记录上次交易所同步余额（不受 settle_trade 影响）
        if not column_exists(conn, "fact_account", "synced_balance", db_name):
            conn.execute(text(
                "ALTER TABLE fact_account ADD COLUMN synced_balance DECIMAL(20,8) NOT NULL DEFAULT 0 "
                "COMMENT '上次交易所同步余额' AFTER realized_pnl"
            ))
            # 初始化：将当前 balance 复制到 synced_balance，避免首次同步误判
            conn.execute(text(
                "UPDATE fact_account SET synced_balance = balance WHERE synced_balance = 0 AND balance > 0"
            ))
            log.info("added column: fact_account.synced_balance (initialized from balance)")
        else:
            log.info("column fact_account.synced_balance already exists")

        # 扩展 description 相关字段为 TEXT（原 VARCHAR(500) 不够长描述文本）
        _desc_columns = [
            ("dim_strategy", "description"),
            ("dim_strategy", "user_description"),
            ("dim_tenant_strategy", "display_description"),
        ]
        for tbl, col in _desc_columns:
            if column_exists(conn, tbl, col, db_name):
                # 查当前列类型
                row = conn.execute(text(
                    "SELECT DATA_TYPE FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :tbl AND COLUMN_NAME = :col"
                ), {"schema": db_name, "tbl": tbl, "col": col}).scalar()
                if row and row.lower() != "text":
                    conn.execute(text(f"ALTER TABLE `{tbl}` MODIFY COLUMN `{col}` TEXT"))
                    log.info(f"altered {tbl}.{col} from {row} to TEXT")
                else:
                    log.info(f"{tbl}.{col} already TEXT")

        conn.commit()
        log.info("migration 016 done")


if __name__ == "__main__":
    run()
