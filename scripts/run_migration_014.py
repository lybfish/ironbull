#!/usr/bin/env python3
"""
迁移 014：创建 dim_market_info 市场信息镜像表（幂等，可重复执行）

用法：PYTHONPATH=. python3 scripts/run_migration_014.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from libs.core import get_config, get_logger
from libs.core.database import init_database, get_engine

log = get_logger("migration-014")


def table_exists(conn, table: str, schema: str) -> bool:
    r = conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_name = :tbl LIMIT 1"
        ),
        {"schema": schema, "tbl": table},
    )
    return r.scalar() is not None


def main():
    config = get_config()
    schema = config.get_str("db_name", "ironbull")
    init_database()
    engine = get_engine()

    with engine.connect() as conn:
        if table_exists(conn, "dim_market_info", schema):
            log.info("dim_market_info 表已存在，跳过创建")
        else:
            log.info("创建 dim_market_info 表...")
            conn.execute(text("""
                CREATE TABLE dim_market_info (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    canonical_symbol VARCHAR(32) NOT NULL COMMENT '规范交易对 (BTC/USDT)',
                    exchange VARCHAR(32) NOT NULL COMMENT '交易所 (binance/gate/okx)',
                    market_type VARCHAR(16) NOT NULL DEFAULT 'swap' COMMENT '市场类型 (spot/swap/future)',
                    ccxt_symbol VARCHAR(64) DEFAULT NULL COMMENT 'ccxt 格式 (BTC/USDT:USDT)',
                    exchange_symbol VARCHAR(64) DEFAULT NULL COMMENT '交易所原生格式 (BTCUSDT / BTC_USDT)',
                    contract_size DECIMAL(20,10) DEFAULT 1 COMMENT '合约面值 (Gate BTC=0.0001)',
                    contract_currency VARCHAR(16) DEFAULT NULL COMMENT '合约面值币种 (BTC)',
                    price_precision INT DEFAULT NULL COMMENT '价格精度位数',
                    amount_precision INT DEFAULT NULL COMMENT '数量精度位数',
                    cost_precision INT DEFAULT NULL COMMENT '金额精度位数',
                    min_quantity DECIMAL(20,10) DEFAULT NULL COMMENT '最小下单数量',
                    max_quantity DECIMAL(20,10) DEFAULT NULL COMMENT '最大下单数量',
                    min_cost DECIMAL(20,8) DEFAULT NULL COMMENT '最小下单金额 (USDT)',
                    min_price DECIMAL(20,10) DEFAULT NULL COMMENT '最小价格',
                    max_price DECIMAL(20,2) DEFAULT NULL COMMENT '最大价格',
                    tick_size DECIMAL(20,10) DEFAULT NULL COMMENT '价格最小变动',
                    step_size DECIMAL(20,10) DEFAULT NULL COMMENT '数量最小变动',
                    base_currency VARCHAR(16) DEFAULT NULL COMMENT '基础币种 (BTC)',
                    quote_currency VARCHAR(16) DEFAULT NULL COMMENT '计价币种 (USDT)',
                    settle_currency VARCHAR(16) DEFAULT NULL COMMENT '结算币种 (USDT)',
                    is_active INT NOT NULL DEFAULT 1 COMMENT '是否活跃',
                    synced_at DATETIME DEFAULT NULL COMMENT '最后同步时间',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_market_key (canonical_symbol, exchange, market_type),
                    INDEX idx_market_exchange (exchange),
                    INDEX idx_market_symbol (canonical_symbol)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='市场信息镜像表（统一各交易所交易对参数）';
            """))
            conn.commit()
            log.info("dim_market_info 表创建成功")

    print("014_create_dim_market_info: done (idempotent)")


if __name__ == "__main__":
    main()
