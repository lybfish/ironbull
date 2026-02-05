#!/usr/bin/env python3
"""
初始化 Facts Layer 数据库表

使用方式：
    PYTHONPATH=. python scripts/init_facts_db.py

环境变量：
    IRONBULL_DB_HOST: MySQL 主机
    IRONBULL_DB_PORT: MySQL 端口
    IRONBULL_DB_USER: 用户名
    IRONBULL_DB_PASSWORD: 密码
    IRONBULL_DB_NAME: 数据库名
"""

import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.core import get_config, init_database, create_tables, check_connection, get_logger

logger = get_logger("init-facts-db")


def main():
    print("=" * 60)
    print("IronBull v1 Facts Layer - Database Initialization")
    print("=" * 60)
    
    config = get_config()
    
    print(f"\nDatabase Configuration:")
    print(f"  Host: {config.get_str('db_host', '127.0.0.1')}")
    print(f"  Port: {config.get_int('db_port', 3306)}")
    print(f"  User: {config.get_str('db_user', 'root')}")
    print(f"  Database: {config.get_str('db_name', 'ironbull')}")
    
    print("\n[1] Initializing database connection...")
    try:
        init_database(echo=False)
        print("  ✅ Connection pool initialized")
    except Exception as e:
        print(f"  ❌ Failed to initialize: {e}")
        return 1
    
    print("\n[2] Testing database connection...")
    if check_connection():
        print("  ✅ Connection successful")
    else:
        print("  ❌ Connection failed")
        print("\n请确保 MySQL 正在运行，并且已创建数据库:")
        print(f"    CREATE DATABASE IF NOT EXISTS {config.get_str('db_name', 'ironbull')};")
        return 1
    
    print("\n[3] Creating tables...")
    try:
        # 导入模型以注册到 Base.metadata
        from libs.facts.models import Trade, Ledger, FreezeRecord, SignalEvent
        create_tables()
        print("  ✅ Tables created:")
        print("      - fact_trade")
        print("      - fact_ledger")
        print("      - fact_freeze")
        print("      - fact_signal_event")
    except Exception as e:
        print(f"  ❌ Failed to create tables: {e}")
        return 1
    
    print("\n" + "=" * 60)
    print("✅ Facts Layer initialization complete!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
