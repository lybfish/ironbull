#!/usr/bin/env python3
"""
迁移 017：dim_strategy_binding 加 capital / leverage / risk_mode 列（幂等）

新增字段：
- capital DECIMAL(20,2)   本金/最大仓位(USDT)
- leverage INT            杠杆倍数（默认20）
- risk_mode INT           风险档位: 1=稳健(1%) 2=均衡(1.5%) 3=激进(2%)

下单金额计算：amount_usdt = capital × risk_pct × leverage
示例: capital=1000, leverage=20, risk_mode=1(稳健) → 1000×1%×20 = 200 USDT

用法：PYTHONPATH=. python3 scripts/run_migration_017.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from libs.core import get_config, get_logger
from libs.core.database import init_database, get_engine

log = get_logger("migration-017")


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

    TABLE = "dim_strategy_binding"

    with engine.connect() as conn:
        # capital
        if not column_exists(conn, TABLE, "capital", db_name):
            conn.execute(text(
                f"ALTER TABLE `{TABLE}` ADD COLUMN capital DECIMAL(20,2) NULL "
                "COMMENT '本金/最大仓位(USDT)' AFTER ratio"
            ))
            log.info("added column: capital")
        else:
            log.info("column capital already exists")

        # leverage
        if not column_exists(conn, TABLE, "leverage", db_name):
            conn.execute(text(
                f"ALTER TABLE `{TABLE}` ADD COLUMN leverage INT NULL DEFAULT 20 "
                "COMMENT '杠杆倍数' AFTER capital"
            ))
            log.info("added column: leverage")
        else:
            log.info("column leverage already exists")

        # risk_mode
        if not column_exists(conn, TABLE, "risk_mode", db_name):
            conn.execute(text(
                f"ALTER TABLE `{TABLE}` ADD COLUMN risk_mode INT NULL DEFAULT 1 "
                "COMMENT '风险档位: 1=稳健(1%%) 2=均衡(1.5%%) 3=激进(2%%)' AFTER leverage"
            ))
            log.info("added column: risk_mode")
        else:
            log.info("column risk_mode already exists")

        conn.commit()
        log.info("migration 017 done")


if __name__ == "__main__":
    run()
