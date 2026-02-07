#!/usr/bin/env python3
"""
迁移 020：dim_strategy 和 dim_tenant_strategy 加 capital / risk_mode 列（幂等）

统一仓位参数模式：capital × risk_pct × leverage = amount_usdt
与 dim_strategy_binding 保持一致。

用法：PYTHONPATH=. python3 scripts/run_migration_020.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from libs.core import get_config, get_logger
from libs.core.database import init_database, get_engine

log = get_logger("migration-020")

RISK_PCT_MAP = {1: 0.01, 2: 0.015, 3: 0.02}


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
        # ── dim_strategy ──
        TABLE = "dim_strategy"

        if not column_exists(conn, TABLE, "capital", db_name):
            conn.execute(text(
                f"ALTER TABLE `{TABLE}` ADD COLUMN capital DECIMAL(20,2) NULL "
                "COMMENT '默认本金(USDT)，用于计算 amount_usdt' AFTER leverage"
            ))
            log.info(f"added column: {TABLE}.capital")
        else:
            log.info(f"column {TABLE}.capital already exists")

        if not column_exists(conn, TABLE, "risk_mode", db_name):
            conn.execute(text(
                f"ALTER TABLE `{TABLE}` ADD COLUMN risk_mode INT NULL DEFAULT 1 "
                "COMMENT '风险档位: 1=稳健(1%%) 2=均衡(1.5%%) 3=激进(2%%)' AFTER capital"
            ))
            log.info(f"added column: {TABLE}.risk_mode")
        else:
            log.info(f"column {TABLE}.risk_mode already exists")

        # 反向填充: 如果已有 amount_usdt 和 leverage，反推 capital
        # capital = amount_usdt / (risk_pct × leverage)
        # 默认 risk_mode=1(1%)，所以 capital = amount_usdt / (0.01 × leverage)
        updated = conn.execute(text(
            f"UPDATE `{TABLE}` SET "
            "capital = ROUND(amount_usdt / (0.01 * GREATEST(leverage, 1)), 2), "
            "risk_mode = 1 "
            "WHERE capital IS NULL AND amount_usdt > 0 AND leverage > 0"
        )).rowcount
        if updated:
            log.info(f"backfilled {updated} strategies with capital from amount_usdt")

        # ── dim_tenant_strategy ──
        TABLE2 = "dim_tenant_strategy"

        if not column_exists(conn, TABLE2, "capital", db_name):
            conn.execute(text(
                f"ALTER TABLE `{TABLE2}` ADD COLUMN capital DECIMAL(20,2) NULL "
                "COMMENT '本金覆盖(USDT)，空则用主策略' AFTER leverage"
            ))
            log.info(f"added column: {TABLE2}.capital")
        else:
            log.info(f"column {TABLE2}.capital already exists")

        if not column_exists(conn, TABLE2, "risk_mode", db_name):
            conn.execute(text(
                f"ALTER TABLE `{TABLE2}` ADD COLUMN risk_mode INT NULL "
                "COMMENT '风险档位覆盖: 1=稳健 2=均衡 3=激进，空则用主策略' AFTER capital"
            ))
            log.info(f"added column: {TABLE2}.risk_mode")
        else:
            log.info(f"column {TABLE2}.risk_mode already exists")

        # 反向填充租户策略
        updated2 = conn.execute(text(
            f"UPDATE `{TABLE2}` SET "
            "capital = ROUND(amount_usdt / (0.01 * GREATEST(leverage, 1)), 2), "
            "risk_mode = 1 "
            "WHERE capital IS NULL AND amount_usdt IS NOT NULL AND amount_usdt > 0 "
            "AND leverage IS NOT NULL AND leverage > 0"
        )).rowcount
        if updated2:
            log.info(f"backfilled {updated2} tenant strategies with capital")

        conn.commit()
        log.info("migration 020 done")


if __name__ == "__main__":
    run()
