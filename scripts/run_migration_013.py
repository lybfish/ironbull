#!/usr/bin/env python3
"""
执行迁移 013：订单/成交列表性能索引（幂等，可重复执行）

用法：PYTHONPATH=. python3 scripts/run_migration_013.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from libs.core import get_config, get_logger
from libs.core.database import init_database, get_engine

log = get_logger("migration-013")


def index_exists(conn, table: str, index_name: str, schema: str) -> bool:
    r = conn.execute(
        text(
            "SELECT 1 FROM information_schema.statistics "
            "WHERE table_schema = :schema AND table_name = :tbl AND index_name = :idx LIMIT 1"
        ),
        {"schema": schema, "tbl": table, "idx": index_name},
    )
    return r.scalar() is not None


def main():
    config = get_config()
    schema = config.get_str("db_name", "ironbull")
    init_database()
    engine = get_engine()

    with engine.connect() as conn:
        # fact_order
        if index_exists(conn, "fact_order", "idx_order_tenant_account_time", schema):
            log.info("fact_order.idx_order_tenant_account_time already exists, skip")
        else:
            conn.execute(text("ALTER TABLE fact_order ADD INDEX idx_order_tenant_account_time (tenant_id, account_id, created_at)"))
            conn.commit()
            log.info("fact_order: added idx_order_tenant_account_time")

        # fact_fill
        if index_exists(conn, "fact_fill", "idx_fill_tenant_account_time", schema):
            log.info("fact_fill.idx_fill_tenant_account_time already exists, skip")
        else:
            conn.execute(text("ALTER TABLE fact_fill ADD INDEX idx_fill_tenant_account_time (tenant_id, account_id, filled_at)"))
            conn.commit()
            log.info("fact_fill: added idx_fill_tenant_account_time")

    print("013_perf_order_fill_list_indexes: done (idempotent)")


if __name__ == "__main__":
    main()
