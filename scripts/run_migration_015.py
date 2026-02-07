#!/usr/bin/env python3
"""
迁移 015：创建 dim_signal_cooldown 信号冷却持久化表（幂等，可重复执行）

用法：PYTHONPATH=. python3 scripts/run_migration_015.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from libs.core import get_config, get_logger
from libs.core.database import init_database, get_engine

log = get_logger("migration-015")


def table_exists(conn, table: str, schema: str) -> bool:
    result = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = :schema AND table_name = :table"
    ), {"schema": schema, "table": table})
    return result.scalar() > 0


DDL = """
CREATE TABLE dim_signal_cooldown (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_code VARCHAR(64) NOT NULL COMMENT '策略代码',
    symbol VARCHAR(32) NOT NULL COMMENT '交易对 (BTC/USDT)',
    cooldown_until DATETIME NOT NULL COMMENT '冷却到期时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_cooldown_key (strategy_code, symbol),
    INDEX idx_cooldown_until (cooldown_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='信号冷却持久化表（防止重启丢失冷却状态）';
"""


def run():
    config = get_config()
    init_database()
    engine = get_engine()

    db_url = config.get_str("database_url", "")
    schema = "ironbull"
    if "/" in db_url:
        last_part = db_url.rsplit("/", 1)[-1]
        schema = last_part.split("?")[0] if "?" in last_part else last_part

    with engine.begin() as conn:
        if table_exists(conn, "dim_signal_cooldown", schema):
            log.info("dim_signal_cooldown 已存在，跳过")
            return
        log.info("创建 dim_signal_cooldown ...")
        conn.execute(text(DDL))
        log.info("dim_signal_cooldown 创建成功")


if __name__ == "__main__":
    run()
