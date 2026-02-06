#!/usr/bin/env python3
"""
执行迁移 014、015（使用项目 config 的数据库连接）。
用法：在项目根目录执行 PYTHONPATH=. python3 scripts/run_migrations_014_015.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from libs.core.database import get_database_url, init_database

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "migrations")


def run_sql(engine, sql: str, desc: str):
    """执行一条或若干条 SQL（按分号拆分，忽略空行和注释）"""
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if not stmt or stmt.startswith("--"):
            continue
        try:
            with engine.connect() as conn:
                conn.execute(text(stmt))
                conn.commit()
            print(f"  OK: {desc}")
        except Exception as e:
            msg = str(e).lower()
            # 014: 列已存在则跳过
            if "duplicate column" in msg or "show_to_user" in msg and "already" in msg:
                print(f"  跳过(已存在): {desc}")
                continue
            if "1054" in msg and "show_to_user" in msg:
                raise
            # 其它错误直接抛
            print(f"  失败: {e}")
            raise


def main():
    print("使用项目 config 连接数据库...")
    init_database(echo=False)
    from libs.core.database import _engine
    if _engine is None:
        print("无法获取 engine，请检查 config 与数据库")
        return 1

    # 014：逐列添加，避免「列已存在」导致整句失败
    print("\n执行 014_strategy_show_to_user.sql ...")
    alters_014 = [
        ("ALTER TABLE `dim_strategy` ADD COLUMN `show_to_user` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '是否对用户/商户展示 0否 1是' AFTER `status`", "show_to_user"),
        ("ALTER TABLE `dim_strategy` ADD COLUMN `user_display_name` VARCHAR(100) NULL COMMENT '对用户展示的名称，空则用 name' AFTER `show_to_user`", "user_display_name"),
        ("ALTER TABLE `dim_strategy` ADD COLUMN `user_description` VARCHAR(500) NULL COMMENT '对用户展示的描述，空则用 description' AFTER `user_display_name`", "user_description"),
    ]
    for stmt, name in alters_014:
        try:
            with _engine.connect() as conn:
                conn.execute(text(stmt))
                conn.commit()
            print(f"  OK: 添加列 {name}")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print(f"  跳过(已存在): {name}")
            else:
                raise

    # 015
    path_015 = os.path.join(MIGRATIONS_DIR, "015_tenant_strategy_instance.sql")
    if not os.path.isfile(path_015):
        print(f"未找到 {path_015}")
        return 1
    print("\n执行 015_tenant_strategy_instance.sql ...")
    with open(path_015, "r", encoding="utf-8") as f:
        sql_015 = f.read()
    # 去掉注释行，按 ; 拆分执行
    lines = [line for line in sql_015.split("\n") if line.strip() and not line.strip().startswith("--")]
    full = " ".join(lines)
    for stmt in full.split(";"):
        stmt = stmt.strip()
        if not stmt:
            continue
        try:
            with _engine.connect() as conn:
                conn.execute(text(stmt))
                conn.commit()
            print(f"  OK: CREATE TABLE dim_tenant_strategy")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  跳过(表已存在): dim_tenant_strategy")
            else:
                raise

    print("\n迁移完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
