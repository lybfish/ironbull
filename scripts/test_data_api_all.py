#!/usr/bin/env python3
"""
Data-API 全量接口探测：登录后逐个请求并记录 HTTP 状态码。
用法：PYTHONPATH=项目根 python3 scripts/test_data_api_all.py
要求：
  - data-api 运行在 127.0.0.1:8026
  - 存在管理员 admin / admin123（dim_admin 表）
  - 已执行迁移：014_strategy_show_to_user.sql、015_tenant_strategy_instance.sql
    否则 /api/strategies、/api/tenants/{id}/tenant-strategies 等会 500
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests

BASE = os.environ.get("DATA_API_BASE", "http://127.0.0.1:8026")
TIMEOUT = 10

def main():
    session = requests.Session()
    session.headers.setdefault("Content-Type", "application/json")

    # 1. 登录
    r = session.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"}, timeout=TIMEOUT)
    if r.status_code != 200:
        print(f"登录失败: {r.status_code} {r.text[:200]}")
        print("请确认 dim_admin 表存在且存在用户 admin 密码 admin123")
        return 1
    token = r.json().get("token")
    if not token:
        print("登录响应无 token")
        return 1
    session.headers["Authorization"] = f"Bearer {token}"
    print("登录成功")
    print()

    # 2. 定义所有要测的请求 (method, path, kwargs)
    cases = [
        ("GET", "/health", {}),
        ("GET", "/api/auth/me", {}),
        ("GET", "/api/strategies", {}),
        ("GET", "/api/strategies", {"params": {"tenant_id": 1}}),
        ("GET", "/api/strategies/1", {}),
        ("GET", "/api/strategy-bindings", {"params": {"tenant_id": 1}}),
        ("GET", "/api/strategy-bindings-admin", {"params": {"page": 1, "page_size": 5}}),
        ("GET", "/api/tenants/1/tenant-strategies", {}),
        ("GET", "/api/tenants", {"params": {"page": 1, "page_size": 5}}),
        ("GET", "/api/users", {"params": {"tenant_id": 1, "page": 1, "page_size": 5}}),
        ("GET", "/api/accounts", {"params": {"tenant_id": 1}}),
        ("GET", "/api/orders", {"params": {"tenant_id": 1, "limit": 2}}),
        ("GET", "/api/fills", {"params": {"tenant_id": 1, "limit": 2}}),
        ("GET", "/api/positions", {"params": {"tenant_id": 1, "limit": 2}}),
        ("GET", "/api/transactions", {"params": {"tenant_id": 1, "limit": 2}}),
        ("GET", "/api/analytics/performance", {"params": {"tenant_id": 1}}),
        ("GET", "/api/analytics/risk", {"params": {"tenant_id": 1}}),
        ("GET", "/api/analytics/statistics", {"params": {"tenant_id": 1}}),
        ("GET", "/api/dashboard/summary", {}),
        ("GET", "/api/admins", {}),
        ("GET", "/api/nodes", {}),
        ("GET", "/api/exchange-accounts", {}),
        ("GET", "/api/quota-plans", {}),
        ("GET", "/api/quota-usage/1", {}),
        ("GET", "/api/withdrawals", {"params": {"page": 1, "page_size": 5}}),
        ("GET", "/api/audit-logs", {"params": {"page": 1, "page_size": 5}}),
        ("GET", "/api/monitor/status", {}),
        ("GET", "/api/pointcard-logs", {"params": {"page": 1, "page_size": 5}}),
        ("GET", "/api/rewards", {"params": {"page": 1, "page_size": 5}}),
        # POST 租户策略实例
        ("POST", "/api/tenants/1/tenant-strategies", {"json": {"strategy_id": 1, "copy_from_master": True, "status": 1, "sort_order": 0}}),
        ("GET", "/api/tenants/1/tenant-strategies", {}),
        ("PUT", "/api/tenants/1/tenant-strategies/1", {"json": {"sort_order": 1}}),
        ("POST", "/api/tenants/1/tenant-strategies/1/copy-from-master", {}),
        ("DELETE", "/api/tenants/1/tenant-strategies/99999", {}),
        # 用户详情（可能 404）
        ("GET", "/api/users/1", {}),
    ]

    print(f"{'METHOD':<6} {'PATH':<55} {'CODE':<5} NOTE")
    print("-" * 85)
    fail = []
    for method, path, kwargs in cases:
        # 只保留 path 部分，query 用 params 传
        path_only = path.split("?")[0]
        url = f"{BASE}{path_only}" if path_only.startswith("/") else f"{BASE}/{path_only}"
        try:
            if method == "GET":
                r = session.get(url, timeout=TIMEOUT, **kwargs)
            elif method == "POST":
                r = session.post(url, timeout=TIMEOUT, **kwargs)
            elif method == "PUT":
                r = session.put(url, timeout=TIMEOUT, **kwargs)
            elif method == "PATCH":
                r = session.patch(url, timeout=TIMEOUT, **kwargs)
            elif method == "DELETE":
                r = session.delete(url, timeout=TIMEOUT, **kwargs)
            else:
                r = None
            if r is None:
                code = "?"
                note = "skip"
            else:
                code = r.status_code
                note = ""
                if code >= 500:
                    note = "ERROR"
                    fail.append((method, path, code))
                elif code == 404 and "99999" in path:
                    note = "ok(no such id)"
        except Exception as e:
            code = "ERR"
            note = str(e)[:30]
            fail.append((method, path, note))
        path_show = path[:52] + ".." if len(path) > 54 else path
        print(f"{method:<6} {path_show:<55} {code!s:<5} {note}")
    print("-" * 85)
    if fail:
        print(f"\n需排查: {len(fail)} 个")
        for m, p, c in fail:
            print(f"  {m} {p} -> {c}")
        print("\n若为 500：请先执行 migrations/014_strategy_show_to_user.sql 与 015_tenant_strategy_instance.sql")
        return 1
    print("\n全部通过（2xx/4xx 为预期）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
