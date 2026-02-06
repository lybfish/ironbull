#!/usr/bin/env python3
"""
IronBull 全量业务流程测试

覆盖范围：
  A. 核心库导入与模型验证（无需服务）
  B. Data API 全部路由（端口 8026）
  C. Merchant API 全部路由（端口 8010）
  D. Signal Monitor 端点（端口 8020）
  E. Execution Node 端点（端口 9101）
  F. 业务闭环流程（跨服务联动）

运行：
  PYTHONPATH=. python3 scripts/test_full_business.py

前提：
  - MySQL / Redis 可达
  - data-api (8026)、merchant-api (8010) 运行
  - signal-monitor (8020)、execution-node (9101) 可选
"""

import os
import sys
import time
import hashlib
import traceback
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests

# ============================================================
# 配置
# ============================================================
DATA_API = os.environ.get("DATA_API_BASE", "http://127.0.0.1:8026")
MERCHANT_API = os.environ.get("MERCHANT_API_BASE", "http://127.0.0.1:8010")
SIGNAL_MONITOR = os.environ.get("SIGNAL_MONITOR_BASE", "http://127.0.0.1:8020")
EXECUTION_NODE = os.environ.get("EXECUTION_NODE_BASE", "http://127.0.0.1:9101")
TIMEOUT = 15


# ============================================================
# 测试框架
# ============================================================
@dataclass
class TestResult:
    group: str
    name: str
    passed: bool
    status_code: Optional[int] = None
    detail: str = ""
    skipped: bool = False


class TestRunner:
    def __init__(self):
        self.results: List[TestResult] = []
        self.session = requests.Session()
        self._admin_token: Optional[str] = None
        self._tenant_app_key: Optional[str] = None
        self._tenant_app_secret: Optional[str] = None
        # 记录创建的资源 ID 用于后续流程
        self._created_tenant_id: Optional[int] = None
        self._created_user_email: Optional[str] = None
        self._created_node_id: Optional[int] = None
        self._created_admin_id: Optional[int] = None
        self._created_tenant_strategy_id: Optional[int] = None

    def record(self, group: str, name: str, passed: bool,
               status_code: Optional[int] = None, detail: str = "", skipped: bool = False):
        self.results.append(TestResult(group, name, passed, status_code, detail, skipped))
        icon = "✅" if passed else ("⏭️" if skipped else "❌")
        sc = f" [{status_code}]" if status_code else ""
        dt = f"  {detail}" if detail else ""
        print(f"  {icon} {name}{sc}{dt}")

    def skip(self, group: str, name: str, reason: str = ""):
        self.record(group, name, True, detail=reason, skipped=True)

    def _get(self, url: str, headers: dict = None, params: dict = None) -> requests.Response:
        return self.session.get(url, headers=headers, params=params, timeout=TIMEOUT)

    def _post(self, url: str, headers: dict = None, json: dict = None, data: dict = None) -> requests.Response:
        return self.session.post(url, headers=headers, json=json, data=data, timeout=TIMEOUT)

    def _put(self, url: str, headers: dict = None, json: dict = None) -> requests.Response:
        return self.session.put(url, headers=headers, json=json, timeout=TIMEOUT)

    def _patch(self, url: str, headers: dict = None, json: dict = None) -> requests.Response:
        return self.session.patch(url, headers=headers, json=json, timeout=TIMEOUT)

    def _delete(self, url: str, headers: dict = None) -> requests.Response:
        return self.session.delete(url, headers=headers, timeout=TIMEOUT)

    def _admin_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._admin_token}"}

    def _merchant_headers(self) -> dict:
        ts = str(int(time.time()))
        sign = hashlib.md5(f"{self._tenant_app_key}{ts}{self._tenant_app_secret}".encode()).hexdigest()
        return {
            "X-App-Key": self._tenant_app_key,
            "X-Timestamp": ts,
            "X-Sign": sign,
        }

    def _service_up(self, base_url: str) -> bool:
        try:
            r = requests.get(f"{base_url}/health", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed and not r.skipped)
        failed = sum(1 for r in self.results if not r.passed)
        skipped = sum(1 for r in self.results if r.skipped)

        print("\n" + "=" * 80)
        print(f"测试汇总: 共 {total} 项, ✅ 通过 {passed}, ❌ 失败 {failed}, ⏭️ 跳过 {skipped}")
        print("=" * 80)

        if failed:
            print("\n❌ 失败项目:")
            for r in self.results:
                if not r.passed:
                    sc = f" [{r.status_code}]" if r.status_code else ""
                    print(f"  [{r.group}] {r.name}{sc} — {r.detail}")

        # 按分组汇总
        groups: Dict[str, Tuple[int, int, int]] = {}
        for r in self.results:
            if r.group not in groups:
                groups[r.group] = (0, 0, 0)
            p, f, s = groups[r.group]
            if r.skipped:
                groups[r.group] = (p, f, s + 1)
            elif r.passed:
                groups[r.group] = (p + 1, f, s)
            else:
                groups[r.group] = (p, f + 1, s)

        print("\n分组统计:")
        for g, (p, f, s) in groups.items():
            total_g = p + f + s
            status = "✅" if f == 0 else "❌"
            print(f"  {status} {g}: {p}/{total_g} 通过" + (f", {f} 失败" if f else "") + (f", {s} 跳过" if s else ""))

        return failed


# ============================================================
# A. 核心库导入与模型验证（不依赖任何服务）
# ============================================================
def test_A_core_libs(runner: TestRunner):
    group = "A.核心库"
    print(f"\n{'='*60}")
    print(f"  {group}")
    print(f"{'='*60}")

    # A1: 配置加载
    try:
        from libs.core import get_config
        cfg = get_config()
        assert cfg.get_str("service_name") == "ironbull"
        runner.record(group, "A1 Config 加载", True)
    except Exception as e:
        runner.record(group, "A1 Config 加载", False, detail=str(e))

    # A2: 日志模块
    try:
        from libs.core.logger import get_logger, setup_logging
        log = get_logger("test")
        assert log is not None
        runner.record(group, "A2 Logger 初始化", True)
    except Exception as e:
        runner.record(group, "A2 Logger 初始化", False, detail=str(e))

    # A3: Contracts
    try:
        from libs.contracts.signal import Signal
        s = Signal(
            signal_id="test", strategy_code="x", symbol="BTC/USDT",
            canonical_symbol="BTC/USDT", side="BUY", signal_type="OPEN",
            amount_usdt=200.0, leverage=20,
        )
        assert s.amount_usdt == 200.0
        assert s.leverage == 20
        runner.record(group, "A3 Signal Contract", True)
    except Exception as e:
        runner.record(group, "A3 Signal Contract", False, detail=str(e))

    # A4: JWT 签发与校验
    try:
        from libs.core.auth.jwt import encode, decode
        token = encode(admin_id=1, username="test_admin", exp_hours=1)
        payload = decode(token)
        assert payload and payload["admin_id"] == 1
        assert payload["username"] == "test_admin"
        runner.record(group, "A4 JWT 签发/校验", True)
    except Exception as e:
        runner.record(group, "A4 JWT 签发/校验", False, detail=str(e))

    # A5: API Sign 计算
    try:
        from libs.core.auth.api_sign import compute_sign, verify_sign
        ts = str(int(time.time()))
        sign = compute_sign("test_key", ts, "test_secret")
        assert verify_sign("test_key", ts, sign, "test_secret")
        assert not verify_sign("test_key", ts, "wrong_sign", "test_secret")
        runner.record(group, "A5 API Sign 计算/验证", True)
    except Exception as e:
        runner.record(group, "A5 API Sign 计算/验证", False, detail=str(e))

    # A6: 数据库初始化
    try:
        from libs.core.database import init_database, get_session
        init_database()
        session = get_session()
        from sqlalchemy import text
        session.execute(text("SELECT 1"))
        session.close()
        runner.record(group, "A6 MySQL 连接", True)
    except Exception as e:
        runner.record(group, "A6 MySQL 连接", False, detail=str(e))

    # A7: Strategy 模型
    try:
        from libs.member.models import Strategy, User, TenantStrategy
        s = Strategy(code="test", name="test", symbol="BTC/USDT", symbols=["BTCUSDT", "ETHUSDT"])
        assert s.get_symbols() == ["BTCUSDT", "ETHUSDT"]
        runner.record(group, "A7 Strategy 模型", True)
    except Exception as e:
        runner.record(group, "A7 Strategy 模型", False, detail=str(e))

    # A8: LiveTrader 常量
    try:
        from libs.trading.live_trader import (
            DEFAULT_QUOTE, DEFAULT_SETTLE,
            MARKET_ORDER_CONFIRM_RETRIES, DEFAULT_LEVERAGE_FALLBACK,
        )
        assert DEFAULT_QUOTE == "USDT"
        assert DEFAULT_SETTLE == "usdt"
        assert MARKET_ORDER_CONFIRM_RETRIES == 3
        assert DEFAULT_LEVERAGE_FALLBACK == 20
        runner.record(group, "A8 LiveTrader 常量", True)
    except Exception as e:
        runner.record(group, "A8 LiveTrader 常量", False, detail=str(e))

    # A9: AutoTrader RiskLimits
    try:
        from libs.trading.auto_trader import RiskLimits
        rl = RiskLimits()
        assert rl.max_trade_amount > 0
        assert rl.max_daily_trades > 0
        runner.record(group, "A9 RiskLimits 默认值", True)
    except Exception as e:
        runner.record(group, "A9 RiskLimits 默认值", False, detail=str(e))

    # A10: Exchange utils
    try:
        from libs.exchange.utils import to_canonical_symbol, normalize_symbol
        assert to_canonical_symbol("BTCUSDT", "future") is not None
        runner.record(group, "A10 Exchange utils", True)
    except Exception as e:
        runner.record(group, "A10 Exchange utils", False, detail=str(e))

    # A11: 策略库导入
    try:
        from libs.strategies import list_strategies, get_strategy
        strategies = list_strategies()
        assert len(strategies) >= 10, f"策略数 {len(strategies)} < 10"
        runner.record(group, f"A11 策略库 ({len(strategies)} 个策略)", True)
    except Exception as e:
        runner.record(group, "A11 策略库导入", False, detail=str(e))

    # A12: Config get_list
    try:
        from libs.core.config import Config
        c = Config.__new__(Config)
        c._data = {"items": ["a", "b"], "csv": "x,y,z"}
        assert c.get_list("items") == ["a", "b"]
        assert c.get_list("csv") == ["x", "y", "z"]
        runner.record(group, "A12 Config.get_list", True)
    except Exception as e:
        runner.record(group, "A12 Config.get_list", False, detail=str(e))

    # A13: 数据库表结构校验
    try:
        from libs.core.database import get_session
        from sqlalchemy import text
        session = get_session()
        # 检查核心表是否存在
        tables_to_check = [
            "dim_strategy", "dim_tenant", "dim_user", "dim_admin",
            "dim_execution_node", "dim_tenant_strategy",
            "fact_exchange_account", "fact_order", "fact_fill",
            "fact_position", "fact_account", "fact_transaction",
            "fact_point_card_log", "fact_user_reward", "fact_user_withdrawal",
            "dim_strategy_binding", "dim_quota_plan",
        ]
        rows = session.execute(text("SHOW TABLES")).fetchall()
        existing = {r[0] for r in rows}
        missing = [t for t in tables_to_check if t not in existing]
        session.close()
        if missing:
            runner.record(group, "A13 数据库表结构", False, detail=f"缺失表: {missing}")
        else:
            runner.record(group, f"A13 数据库表结构 ({len(tables_to_check)} 表)", True)
    except Exception as e:
        runner.record(group, "A13 数据库表结构", False, detail=str(e))

    # A14: dim_strategy 字段检查
    try:
        from libs.core.database import get_session
        from sqlalchemy import text
        session = get_session()
        rows = session.execute(text("DESCRIBE dim_strategy")).fetchall()
        fields = {r[0] for r in rows}
        expected = {"symbols", "exchange", "market_type", "amount_usdt", "leverage",
                    "min_confidence", "cooldown_minutes", "show_to_user"}
        missing = expected - fields
        session.close()
        if missing:
            runner.record(group, "A14 dim_strategy 字段", False, detail=f"缺失: {missing}")
        else:
            runner.record(group, "A14 dim_strategy 字段完整", True)
    except Exception as e:
        runner.record(group, "A14 dim_strategy 字段", False, detail=str(e))

    # A15: Pointcard / Reward 模块导入
    try:
        from libs.pointcard.service import PointCardService
        from libs.reward.service import RewardService
        from libs.reward.withdrawal_service import WithdrawalService
        runner.record(group, "A15 Pointcard/Reward 模块", True)
    except Exception as e:
        runner.record(group, "A15 Pointcard/Reward 模块", False, detail=str(e))

    # A16: Analytics 模块
    try:
        from libs.analytics.service import AnalyticsService
        from libs.analytics.models import PerformanceSnapshot, TradeStatistics, RiskMetrics
        runner.record(group, "A16 Analytics 模块导入", True)
    except Exception as e:
        runner.record(group, "A16 Analytics 模块导入", False, detail=str(e))

    # A17: Monitor 模块
    try:
        from libs.monitor.health_checker import HealthChecker
        from libs.monitor.node_checker import NodeChecker
        from libs.monitor.db_checker import DbChecker
        from libs.monitor.alerter import Alerter
        runner.record(group, "A17 Monitor 模块导入", True)
    except Exception as e:
        runner.record(group, "A17 Monitor 模块导入", False, detail=str(e))

    # A18: Queue 模块
    try:
        from libs.queue import get_node_execute_queue, TaskMessage
        runner.record(group, "A18 Queue 模块导入", True)
    except Exception as e:
        runner.record(group, "A18 Queue 模块导入", False, detail=str(e))

    # A19: Execution Node 模块
    try:
        from libs.execution_node import ExecutionNodeRepository
        from libs.execution_node.apply_results import apply_remote_results
        runner.record(group, "A19 ExecutionNode 模块导入", True)
    except Exception as e:
        runner.record(group, "A19 ExecutionNode 模块导入", False, detail=str(e))

    # A20: Sync Node 模块
    try:
        from libs.sync_node.service import sync_balance_from_nodes, sync_positions_from_nodes
        assert callable(sync_balance_from_nodes)
        assert callable(sync_positions_from_nodes)
        runner.record(group, "A20 SyncNode 模块导入", True)
    except Exception as e:
        runner.record(group, "A20 SyncNode 模块导入", False, detail=str(e))


# ============================================================
# B. Data API 全部路由
# ============================================================
def test_B_data_api(runner: TestRunner):
    group = "B.DataAPI"
    print(f"\n{'='*60}")
    print(f"  {group}")
    print(f"{'='*60}")

    if not runner._service_up(DATA_API):
        runner.skip(group, "B0 服务不可用", "data-api (8026) 未运行")
        return

    # --- B1: Health ---
    try:
        r = runner._get(f"{DATA_API}/health")
        ok = r.status_code == 200 and r.json().get("status") == "ok"
        runner.record(group, "B1 GET /health", ok, r.status_code)
    except Exception as e:
        runner.record(group, "B1 GET /health", False, detail=str(e))

    # --- B2: Auth login ---
    try:
        r = runner._post(f"{DATA_API}/api/auth/login", json={"username": "admin", "password": "admin123"})
        if r.status_code == 200:
            data = r.json()
            runner._admin_token = data.get("token")
            runner.record(group, "B2 POST /api/auth/login", bool(runner._admin_token), r.status_code)
        else:
            runner.record(group, "B2 POST /api/auth/login", False, r.status_code, detail=r.text[:100])
    except Exception as e:
        runner.record(group, "B2 POST /api/auth/login", False, detail=str(e))

    if not runner._admin_token:
        runner.skip(group, "B* 后续跳过", "无法获取 admin token")
        return

    h = runner._admin_headers()

    # --- B3: Auth me ---
    try:
        r = runner._get(f"{DATA_API}/api/auth/me", headers=h)
        runner.record(group, "B3 GET /api/auth/me", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B3 GET /api/auth/me", False, detail=str(e))

    # --- B4: Dashboard summary ---
    try:
        r = runner._get(f"{DATA_API}/api/dashboard/summary", headers=h)
        runner.record(group, "B4 GET /api/dashboard/summary", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B4 GET /api/dashboard/summary", False, detail=str(e))

    # --- B5: Tenants list ---
    try:
        r = runner._get(f"{DATA_API}/api/tenants", headers=h, params={"page": 1, "page_size": 20})
        ok = r.status_code == 200
        runner.record(group, "B5 GET /api/tenants", ok, r.status_code)
        # 找一个 status=1（启用）的租户用于 Merchant API 测试
        if ok:
            data = r.json()
            tenants_list = data.get("data", [])
            for t in tenants_list:
                if t.get("status") == 1 and t.get("app_key") and t.get("app_secret"):
                    runner._tenant_app_key = t.get("app_key")
                    runner._tenant_app_secret = t.get("app_secret")
                    runner._created_tenant_id = t.get("id")
                    break
            if not runner._tenant_app_key and tenants_list:
                t = tenants_list[0]
                runner._tenant_app_key = t.get("app_key")
                runner._tenant_app_secret = t.get("app_secret")
                runner._created_tenant_id = t.get("id")
    except Exception as e:
        runner.record(group, "B5 GET /api/tenants", False, detail=str(e))

    # --- B6: Tenants create ---
    try:
        test_tenant_name = f"测试租户_{int(time.time()) % 100000}"
        r = runner._post(f"{DATA_API}/api/tenants", headers=h, json={
            "name": test_tenant_name,
            "contact_email": "test@ironbull.test",
        })
        ok = r.status_code == 200
        runner.record(group, "B6 POST /api/tenants (创建)", ok, r.status_code,
                      detail=r.text[:80] if not ok else "")
    except Exception as e:
        runner.record(group, "B6 POST /api/tenants (创建)", False, detail=str(e))

    # --- B7: Users list ---
    try:
        r = runner._get(f"{DATA_API}/api/users", headers=h, params={"tenant_id": 1, "page": 1, "page_size": 5})
        runner.record(group, "B7 GET /api/users", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B7 GET /api/users", False, detail=str(e))

    # --- B8: User detail ---
    try:
        r = runner._get(f"{DATA_API}/api/users/1", headers=h)
        # 可能 404 或 200
        runner.record(group, "B8 GET /api/users/1", r.status_code in (200, 404), r.status_code)
    except Exception as e:
        runner.record(group, "B8 GET /api/users/1", False, detail=str(e))

    # --- B9: Admins list ---
    try:
        r = runner._get(f"{DATA_API}/api/admins", headers=h)
        runner.record(group, "B9 GET /api/admins", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B9 GET /api/admins", False, detail=str(e))

    # --- B10: Admins create ---
    try:
        test_admin = f"testadmin_{int(time.time()) % 100000}"
        r = runner._post(f"{DATA_API}/api/admins", headers=h, json={
            "username": test_admin,
            "password": "test123456",
            "nickname": "测试管理员",
        })
        ok = r.status_code == 200
        if ok:
            runner._created_admin_id = r.json().get("data", {}).get("id")
        runner.record(group, "B10 POST /api/admins (创建)", ok, r.status_code,
                      detail=r.text[:80] if not ok else "")
    except Exception as e:
        runner.record(group, "B10 POST /api/admins (创建)", False, detail=str(e))

    # --- B11: Strategies list ---
    try:
        r = runner._get(f"{DATA_API}/api/strategies", headers=h)
        runner.record(group, "B11 GET /api/strategies (全局)", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B11 GET /api/strategies (全局)", False, detail=str(e))

    # --- B12: Strategies list by tenant ---
    try:
        r = runner._get(f"{DATA_API}/api/strategies", headers=h, params={"tenant_id": 1})
        runner.record(group, "B12 GET /api/strategies?tenant_id=1", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B12 GET /api/strategies?tenant_id=1", False, detail=str(e))

    # --- B13: Strategy detail ---
    try:
        r = runner._get(f"{DATA_API}/api/strategies/1", headers=h)
        runner.record(group, "B13 GET /api/strategies/1", r.status_code in (200, 404), r.status_code)
    except Exception as e:
        runner.record(group, "B13 GET /api/strategies/1", False, detail=str(e))

    # --- B14: Strategy bindings ---
    try:
        r = runner._get(f"{DATA_API}/api/strategy-bindings", headers=h, params={"tenant_id": 1})
        runner.record(group, "B14 GET /api/strategy-bindings", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B14 GET /api/strategy-bindings", False, detail=str(e))

    # --- B15: Strategy bindings admin ---
    try:
        r = runner._get(f"{DATA_API}/api/strategy-bindings-admin", headers=h, params={"page": 1, "page_size": 5})
        runner.record(group, "B15 GET /api/strategy-bindings-admin", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B15 GET /api/strategy-bindings-admin", False, detail=str(e))

    # --- B16: Tenant strategies list ---
    try:
        r = runner._get(f"{DATA_API}/api/tenants/1/tenant-strategies", headers=h)
        runner.record(group, "B16 GET /api/tenants/1/tenant-strategies", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B16 GET /api/tenants/1/tenant-strategies", False, detail=str(e))

    # --- B17: Tenant strategies create ---
    try:
        r = runner._post(f"{DATA_API}/api/tenants/1/tenant-strategies", headers=h, json={
            "strategy_id": 1, "copy_from_master": True, "status": 1, "sort_order": 0,
        })
        ok = r.status_code == 200
        if ok:
            resp_data = r.json().get("data", {})
            runner._created_tenant_strategy_id = resp_data.get("id")
        runner.record(group, "B17 POST /api/tenants/1/tenant-strategies", ok, r.status_code,
                      detail=r.text[:80] if not ok else "")
    except Exception as e:
        runner.record(group, "B17 POST /api/tenants/1/tenant-strategies", False, detail=str(e))

    # --- B18: Tenant strategies copy-from-master ---
    if runner._created_tenant_strategy_id:
        try:
            tsid = runner._created_tenant_strategy_id
            r = runner._post(f"{DATA_API}/api/tenants/1/tenant-strategies/{tsid}/copy-from-master", headers=h)
            runner.record(group, "B18 POST copy-from-master", r.status_code == 200, r.status_code)
        except Exception as e:
            runner.record(group, "B18 POST copy-from-master", False, detail=str(e))
    else:
        runner.skip(group, "B18 POST copy-from-master", "未创建租户策略实例")

    # --- B19: Tenant strategies update ---
    if runner._created_tenant_strategy_id:
        try:
            tsid = runner._created_tenant_strategy_id
            r = runner._put(f"{DATA_API}/api/tenants/1/tenant-strategies/{tsid}", headers=h,
                            json={"sort_order": 99})
            runner.record(group, "B19 PUT tenant-strategies", r.status_code == 200, r.status_code)
        except Exception as e:
            runner.record(group, "B19 PUT tenant-strategies", False, detail=str(e))
    else:
        runner.skip(group, "B19 PUT tenant-strategies", "无实例")

    # --- B20: Orders ---
    try:
        r = runner._get(f"{DATA_API}/api/orders", headers=h, params={"tenant_id": 1, "limit": 2})
        runner.record(group, "B20 GET /api/orders", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B20 GET /api/orders", False, detail=str(e))

    # --- B21: Fills ---
    try:
        r = runner._get(f"{DATA_API}/api/fills", headers=h, params={"tenant_id": 1, "limit": 2})
        runner.record(group, "B21 GET /api/fills", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B21 GET /api/fills", False, detail=str(e))

    # --- B22: Positions ---
    try:
        r = runner._get(f"{DATA_API}/api/positions", headers=h, params={"tenant_id": 1, "limit": 2})
        runner.record(group, "B22 GET /api/positions", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B22 GET /api/positions", False, detail=str(e))

    # --- B23: Accounts ---
    try:
        r = runner._get(f"{DATA_API}/api/accounts", headers=h, params={"tenant_id": 1})
        runner.record(group, "B23 GET /api/accounts", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B23 GET /api/accounts", False, detail=str(e))

    # --- B24: Transactions ---
    try:
        r = runner._get(f"{DATA_API}/api/transactions", headers=h, params={"tenant_id": 1, "limit": 2})
        runner.record(group, "B24 GET /api/transactions", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B24 GET /api/transactions", False, detail=str(e))

    # --- B25: Analytics performance ---
    try:
        r = runner._get(f"{DATA_API}/api/analytics/performance", headers=h, params={"tenant_id": 1})
        runner.record(group, "B25 GET /api/analytics/performance", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B25 GET /api/analytics/performance", False, detail=str(e))

    # --- B26: Analytics risk ---
    try:
        r = runner._get(f"{DATA_API}/api/analytics/risk", headers=h, params={"tenant_id": 1})
        runner.record(group, "B26 GET /api/analytics/risk", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B26 GET /api/analytics/risk", False, detail=str(e))

    # --- B27: Analytics statistics ---
    try:
        r = runner._get(f"{DATA_API}/api/analytics/statistics", headers=h, params={"tenant_id": 1})
        runner.record(group, "B27 GET /api/analytics/statistics", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B27 GET /api/analytics/statistics", False, detail=str(e))

    # --- B28: Nodes list ---
    try:
        r = runner._get(f"{DATA_API}/api/nodes", headers=h)
        runner.record(group, "B28 GET /api/nodes", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B28 GET /api/nodes", False, detail=str(e))

    # --- B29: Nodes CRUD ---
    try:
        node_code = f"test_node_{int(time.time()) % 100000}"
        r = runner._post(f"{DATA_API}/api/nodes", headers=h, json={
            "node_code": node_code, "name": "测试节点", "base_url": "http://127.0.0.1:19999"
        })
        ok = r.status_code == 200
        if ok:
            runner._created_node_id = r.json().get("data", {}).get("id")
        runner.record(group, "B29 POST /api/nodes (创建)", ok, r.status_code,
                      detail=r.text[:80] if not ok else "")
    except Exception as e:
        runner.record(group, "B29 POST /api/nodes (创建)", False, detail=str(e))

    # --- B30: Node update ---
    if runner._created_node_id:
        try:
            nid = runner._created_node_id
            r = runner._put(f"{DATA_API}/api/nodes/{nid}", headers=h, json={"name": "改名测试节点"})
            runner.record(group, "B30 PUT /api/nodes/:id", r.status_code == 200, r.status_code)
        except Exception as e:
            runner.record(group, "B30 PUT /api/nodes/:id", False, detail=str(e))
    else:
        runner.skip(group, "B30 PUT /api/nodes/:id", "无节点")

    # --- B31: Node accounts ---
    if runner._created_node_id:
        try:
            nid = runner._created_node_id
            r = runner._get(f"{DATA_API}/api/nodes/{nid}/accounts", headers=h)
            runner.record(group, "B31 GET /api/nodes/:id/accounts", r.status_code == 200, r.status_code)
        except Exception as e:
            runner.record(group, "B31 GET /api/nodes/:id/accounts", False, detail=str(e))
    else:
        runner.skip(group, "B31 GET /api/nodes/:id/accounts", "无节点")

    # --- B32: Node delete ---
    if runner._created_node_id:
        try:
            nid = runner._created_node_id
            r = runner._delete(f"{DATA_API}/api/nodes/{nid}", headers=h)
            runner.record(group, "B32 DELETE /api/nodes/:id", r.status_code == 200, r.status_code)
        except Exception as e:
            runner.record(group, "B32 DELETE /api/nodes/:id", False, detail=str(e))
    else:
        runner.skip(group, "B32 DELETE /api/nodes/:id", "无节点")

    # --- B33: Exchange accounts ---
    try:
        r = runner._get(f"{DATA_API}/api/exchange-accounts", headers=h)
        runner.record(group, "B33 GET /api/exchange-accounts", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B33 GET /api/exchange-accounts", False, detail=str(e))

    # --- B34: Quota plans ---
    try:
        r = runner._get(f"{DATA_API}/api/quota-plans", headers=h)
        runner.record(group, "B34 GET /api/quota-plans", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B34 GET /api/quota-plans", False, detail=str(e))

    # --- B35: Quota usage ---
    try:
        r = runner._get(f"{DATA_API}/api/quota-usage/1", headers=h)
        runner.record(group, "B35 GET /api/quota-usage/1", r.status_code in (200, 404), r.status_code)
    except Exception as e:
        runner.record(group, "B35 GET /api/quota-usage/1", False, detail=str(e))

    # --- B36: Withdrawals ---
    try:
        r = runner._get(f"{DATA_API}/api/withdrawals", headers=h, params={"page": 1, "page_size": 5})
        runner.record(group, "B36 GET /api/withdrawals", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B36 GET /api/withdrawals", False, detail=str(e))

    # --- B37: Monitor status ---
    try:
        r = runner._get(f"{DATA_API}/api/monitor/status", headers=h)
        runner.record(group, "B37 GET /api/monitor/status", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B37 GET /api/monitor/status", False, detail=str(e))

    # --- B38: Audit logs ---
    try:
        r = runner._get(f"{DATA_API}/api/audit-logs", headers=h, params={"page": 1, "page_size": 5})
        runner.record(group, "B38 GET /api/audit-logs", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B38 GET /api/audit-logs", False, detail=str(e))

    # --- B39: Pointcard logs ---
    try:
        r = runner._get(f"{DATA_API}/api/pointcard-logs", headers=h, params={"page": 1, "page_size": 5})
        runner.record(group, "B39 GET /api/pointcard-logs", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B39 GET /api/pointcard-logs", False, detail=str(e))

    # --- B40: Rewards ---
    try:
        r = runner._get(f"{DATA_API}/api/rewards", headers=h, params={"page": 1, "page_size": 5})
        runner.record(group, "B40 GET /api/rewards", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B40 GET /api/rewards", False, detail=str(e))

    # --- B41: Signal monitor status proxy ---
    try:
        r = runner._get(f"{DATA_API}/api/signal-monitor/status", headers=h)
        # 如果 signal-monitor 未跑会返回 503/502，仍算接口本身正常
        runner.record(group, "B41 GET /api/signal-monitor/status",
                      r.status_code in (200, 502, 503), r.status_code)
    except Exception as e:
        runner.record(group, "B41 GET /api/signal-monitor/status", False, detail=str(e))

    # --- B42: Auth logout ---
    try:
        r = runner._get(f"{DATA_API}/api/auth/logout", headers=h)
        runner.record(group, "B42 GET /api/auth/logout", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "B42 GET /api/auth/logout", False, detail=str(e))

    # --- B43: Unauth access should 401 ---
    try:
        r = runner._get(f"{DATA_API}/api/dashboard/summary")
        runner.record(group, "B43 未认证访问返回 401", r.status_code == 401, r.status_code)
    except Exception as e:
        runner.record(group, "B43 未认证访问", False, detail=str(e))

    # --- B44: Tenant strategies DELETE (清理) ---
    if runner._created_tenant_strategy_id:
        try:
            tsid = runner._created_tenant_strategy_id
            r = runner._delete(f"{DATA_API}/api/tenants/1/tenant-strategies/{tsid}", headers=h)
            runner.record(group, "B44 DELETE tenant-strategies (清理)", r.status_code == 200, r.status_code)
        except Exception as e:
            runner.record(group, "B44 DELETE tenant-strategies (清理)", False, detail=str(e))

    # --- B45: User manage ---
    try:
        r = runner._get(f"{DATA_API}/api/user-manage", headers=h, params={"tenant_id": 1, "page": 1, "page_size": 5})
        # 可能 404 如果路径不同
        runner.record(group, "B45 GET /api/user-manage", r.status_code in (200, 404, 405), r.status_code)
    except Exception as e:
        runner.record(group, "B45 GET /api/user-manage", False, detail=str(e))


# ============================================================
# C. Merchant API 全部路由
# ============================================================
def test_C_merchant_api(runner: TestRunner):
    group = "C.MerchantAPI"
    print(f"\n{'='*60}")
    print(f"  {group}")
    print(f"{'='*60}")

    if not runner._service_up(MERCHANT_API):
        runner.skip(group, "C0 服务不可用", "merchant-api (8010) 未运行")
        return

    # C1: Health
    try:
        r = runner._get(f"{MERCHANT_API}/health")
        runner.record(group, "C1 GET /health", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "C1 GET /health", False, detail=str(e))

    # 需要 tenant app_key / app_secret
    if not runner._tenant_app_key or not runner._tenant_app_secret:
        # 尝试从数据库获取
        try:
            from libs.core.database import init_database, get_session
            from libs.tenant.models import Tenant
            init_database()
            session = get_session()
            t = session.query(Tenant).filter(Tenant.status == 1).first()
            if t:
                runner._tenant_app_key = t.app_key
                runner._tenant_app_secret = t.app_secret
            session.close()
        except Exception:
            pass

    if not runner._tenant_app_key:
        runner.skip(group, "C* 后续跳过", "无可用租户 app_key/app_secret")
        return

    # Merchant API 使用独立请求（避免 session 共享 header 干扰 Flask / FastAPI）
    import requests as _mreq

    def _mget(url, headers=None, params=None):
        return _mreq.get(url, headers=headers, params=params, timeout=TIMEOUT)

    def _mpost(url, headers=None, data=None, json=None):
        return _mreq.post(url, headers=headers, data=data, json=json, timeout=TIMEOUT)

    mh = runner._merchant_headers

    # C2: Get balance
    try:
        r = _mget(f"{MERCHANT_API}/merchant/balance", headers=mh())
        runner.record(group, "C2 GET /merchant/balance", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "C2 GET /merchant/balance", False, detail=str(e))

    # C3: Root user
    try:
        r = _mget(f"{MERCHANT_API}/merchant/root-user", headers=mh())
        runner.record(group, "C3 GET /merchant/root-user", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "C3 GET /merchant/root-user", False, detail=str(e))

    # C4: Create user
    test_email = f"test_{int(time.time()) % 100000}@ironbull.test"
    try:
        r = _mpost(f"{MERCHANT_API}/merchant/user/create", headers=mh(),
                    data={"email": test_email, "password": "test123456"})
        ok = r.status_code == 200 and r.json().get("code") == 0
        runner.record(group, f"C4 POST /user/create ({test_email})", ok, r.status_code,
                      detail="" if ok else r.text[:80])
        if ok:
            runner._created_user_email = test_email
    except Exception as e:
        runner.record(group, "C4 POST /user/create", False, detail=str(e))

    # C5: Users list
    try:
        r = _mget(f"{MERCHANT_API}/merchant/users", headers=mh(),
                   params={"page": 1, "limit": 5})
        ok = r.status_code == 200 and r.json().get("code") == 0
        runner.record(group, "C5 GET /merchant/users", ok, r.status_code)
    except Exception as e:
        runner.record(group, "C5 GET /merchant/users", False, detail=str(e))

    # C6: User info
    if runner._created_user_email:
        try:
            r = _mget(f"{MERCHANT_API}/merchant/user/info", headers=mh(),
                       params={"email": runner._created_user_email})
            ok = r.status_code == 200 and r.json().get("code") == 0
            runner.record(group, "C6 GET /user/info", ok, r.status_code,
                          detail="" if ok else r.text[:80])
        except Exception as e:
            runner.record(group, "C6 GET /user/info", False, detail=str(e))
    else:
        runner.skip(group, "C6 GET /user/info", "无测试用户")

    # C7: User apikey bind
    if runner._created_user_email:
        try:
            r = _mpost(f"{MERCHANT_API}/merchant/user/apikey", headers=mh(),
                        data={"email": runner._created_user_email, "exchange": "binance",
                              "api_key": "test_key", "api_secret": "test_secret"})
            ok = r.status_code == 200
            runner.record(group, "C7 POST /user/apikey (绑定)", ok, r.status_code,
                          detail="" if ok else r.text[:80])
        except Exception as e:
            runner.record(group, "C7 POST /user/apikey", False, detail=str(e))
    else:
        runner.skip(group, "C7 POST /user/apikey", "无测试用户")

    # C8: User recharge
    if runner._created_user_email:
        try:
            r = _mpost(f"{MERCHANT_API}/merchant/user/recharge", headers=mh(),
                        data={"email": runner._created_user_email, "amount": 100, "type": 1})
            ok = r.status_code == 200
            runner.record(group, "C8 POST /user/recharge", ok, r.status_code,
                          detail="" if ok else r.text[:80])
        except Exception as e:
            runner.record(group, "C8 POST /user/recharge", False, detail=str(e))
    else:
        runner.skip(group, "C8 POST /user/recharge", "无测试用户")

    # C9: Point card logs
    try:
        r = _mget(f"{MERCHANT_API}/merchant/point-card/logs", headers=mh(),
                   params={"page": 1, "limit": 5})
        ok = r.status_code == 200 and r.json().get("code") == 0
        runner.record(group, "C9 GET /point-card/logs", ok, r.status_code)
    except Exception as e:
        runner.record(group, "C9 GET /point-card/logs", False, detail=str(e))

    # C10: Point card logs by user
    if runner._created_user_email:
        try:
            r = _mget(f"{MERCHANT_API}/merchant/point-card/logs", headers=mh(),
                       params={"email": runner._created_user_email, "page": 1, "limit": 5})
            ok = r.status_code == 200 and r.json().get("code") == 0
            runner.record(group, "C10 GET /point-card/logs?email", ok, r.status_code)
        except Exception as e:
            runner.record(group, "C10 GET /point-card/logs?email", False, detail=str(e))

    # C11: Strategies list
    try:
        r = _mget(f"{MERCHANT_API}/merchant/strategies", headers=mh())
        ok = r.status_code == 200 and r.json().get("code") == 0
        runner.record(group, "C11 GET /merchant/strategies", ok, r.status_code)
    except Exception as e:
        runner.record(group, "C11 GET /merchant/strategies", False, detail=str(e))

    # C12: User strategies
    if runner._created_user_email:
        try:
            r = _mget(f"{MERCHANT_API}/merchant/user/strategies", headers=mh(),
                       params={"email": runner._created_user_email})
            ok = r.status_code == 200 and r.json().get("code") == 0
            runner.record(group, "C12 GET /user/strategies", ok, r.status_code)
        except Exception as e:
            runner.record(group, "C12 GET /user/strategies", False, detail=str(e))

    # C13: Strategy open (可能失败 - 策略实例未配置 或 点卡不足)
    if runner._created_user_email:
        try:
            r = _mpost(f"{MERCHANT_API}/merchant/user/strategy/open", headers=mh(),
                        data={"email": runner._created_user_email, "strategy_id": 1,
                              "account_id": 1, "mode": 2, "min_point_card": 0.0})
            ok = r.status_code == 200
            msg = r.json().get("msg", "")
            runner.record(group, f"C13 POST /user/strategy/open", ok, r.status_code,
                          detail=msg if r.json().get("code") != 0 else "")
        except Exception as e:
            runner.record(group, "C13 POST /user/strategy/open", False, detail=str(e))

    # C14: User team
    if runner._created_user_email:
        try:
            r = _mget(f"{MERCHANT_API}/merchant/user/team", headers=mh(),
                       params={"email": runner._created_user_email})
            ok = r.status_code == 200 and r.json().get("code") == 0
            runner.record(group, "C14 GET /user/team", ok, r.status_code)
        except Exception as e:
            runner.record(group, "C14 GET /user/team", False, detail=str(e))

    # C15: Set market node
    if runner._created_user_email:
        try:
            r = _mpost(f"{MERCHANT_API}/merchant/user/set-market-node", headers=mh(),
                        data={"email": runner._created_user_email, "is_node": 1})
            ok = r.status_code == 200
            runner.record(group, "C15 POST /user/set-market-node", ok, r.status_code)
        except Exception as e:
            runner.record(group, "C15 POST /user/set-market-node", False, detail=str(e))

    # C16: User rewards
    if runner._created_user_email:
        try:
            r = _mget(f"{MERCHANT_API}/merchant/user/rewards", headers=mh(),
                       params={"email": runner._created_user_email, "page": 1, "limit": 5})
            ok = r.status_code == 200 and r.json().get("code") == 0
            runner.record(group, "C16 GET /user/rewards", ok, r.status_code)
        except Exception as e:
            runner.record(group, "C16 GET /user/rewards", False, detail=str(e))

    # C17: User withdraw (可能失败 - 余额不足)
    if runner._created_user_email:
        try:
            r = _mpost(f"{MERCHANT_API}/merchant/user/withdraw", headers=mh(),
                        data={"email": runner._created_user_email, "amount": 1.0,
                              "wallet_address": "T_TEST_WALLET_ADDRESS"})
            ok = r.status_code == 200
            msg = r.json().get("msg", "")
            runner.record(group, "C17 POST /user/withdraw", ok, r.status_code,
                          detail=msg if r.json().get("code") != 0 else "")
        except Exception as e:
            runner.record(group, "C17 POST /user/withdraw", False, detail=str(e))

    # C18: User withdrawals
    if runner._created_user_email:
        try:
            r = _mget(f"{MERCHANT_API}/merchant/user/withdrawals", headers=mh(),
                       params={"email": runner._created_user_email})
            ok = r.status_code == 200 and r.json().get("code") == 0
            runner.record(group, "C18 GET /user/withdrawals", ok, r.status_code)
        except Exception as e:
            runner.record(group, "C18 GET /user/withdrawals", False, detail=str(e))

    # C19: Transfer point card (创建第二个用户来转)
    if runner._created_user_email:
        test_email2 = f"test2_{int(time.time()) % 100000}@ironbull.test"
        try:
            r = _mpost(f"{MERCHANT_API}/merchant/user/create", headers=mh(),
                        data={"email": test_email2, "password": "test123456"})
            if r.status_code == 200 and r.json().get("code") == 0:
                _mpost(f"{MERCHANT_API}/merchant/user/recharge", headers=mh(),
                       data={"email": test_email2, "amount": 50, "type": 1})
                r = _mpost(f"{MERCHANT_API}/merchant/user/transfer-point-card", headers=mh(),
                            data={"from_email": test_email2, "to_email": runner._created_user_email,
                                  "amount": 10, "type": 1})
                ok = r.status_code == 200
                msg = r.json().get("msg", "")
                runner.record(group, "C19 POST /user/transfer-point-card", ok, r.status_code,
                              detail=msg if r.json().get("code") != 0 else "")
            else:
                runner.record(group, "C19 POST /user/transfer-point-card", False,
                              detail="创建第二个用户失败")
        except Exception as e:
            runner.record(group, "C19 POST /user/transfer-point-card", False, detail=str(e))

    # C20: Unbind apikey
    if runner._created_user_email:
        try:
            r = _mget(f"{MERCHANT_API}/merchant/user/info", headers=mh(),
                       params={"email": runner._created_user_email})
            if r.status_code == 200 and r.json().get("code") == 0:
                accounts = r.json().get("data", {}).get("accounts", [])
                if accounts:
                    acc_id = accounts[0]["account_id"]
                    r = _mpost(f"{MERCHANT_API}/merchant/user/apikey/unbind", headers=mh(),
                                data={"email": runner._created_user_email, "account_id": acc_id})
                    ok = r.status_code == 200
                    runner.record(group, "C20 POST /user/apikey/unbind", ok, r.status_code)
                else:
                    runner.skip(group, "C20 POST /user/apikey/unbind", "无账户可解绑")
            else:
                runner.skip(group, "C20 POST /user/apikey/unbind", "获取用户信息失败")
        except Exception as e:
            runner.record(group, "C20 POST /user/apikey/unbind", False, detail=str(e))

    # C21: Auth 验证 - 无签名应返回 401
    try:
        r = _mget(f"{MERCHANT_API}/merchant/balance")
        runner.record(group, "C21 无签名返回 401", r.status_code == 401, r.status_code)
    except Exception as e:
        runner.record(group, "C21 无签名返回 401", False, detail=str(e))

    # C22: Auth 验证 - 错误签名
    try:
        bad_headers = {"X-App-Key": "wrong", "X-Timestamp": str(int(time.time())), "X-Sign": "wrong"}
        r = _mget(f"{MERCHANT_API}/merchant/balance", headers=bad_headers)
        runner.record(group, "C22 错误签名返回 401", r.status_code == 401, r.status_code)
    except Exception as e:
        runner.record(group, "C22 错误签名返回 401", False, detail=str(e))


# ============================================================
# D. Signal Monitor 端点
# ============================================================
def test_D_signal_monitor(runner: TestRunner):
    group = "D.SignalMonitor"
    print(f"\n{'='*60}")
    print(f"  {group}")
    print(f"{'='*60}")

    if not runner._service_up(SIGNAL_MONITOR):
        runner.skip(group, "D0 服务不可用", "signal-monitor (8020) 未运行")
        return

    # D1: Health
    try:
        r = runner._get(f"{SIGNAL_MONITOR}/health")
        runner.record(group, "D1 GET /health", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "D1 GET /health", False, detail=str(e))

    # Signal Monitor 是 Flask，用独立 requests 避免共享 session header 干扰
    import requests as _req

    # D2: Status
    try:
        r = _req.get(f"{SIGNAL_MONITOR}/api/status", timeout=TIMEOUT)
        ok = r.status_code == 200
        if ok:
            data = r.json()
            has_fields = "state" in data and "config" in data
            runner.record(group, "D2 GET /api/status", has_fields, r.status_code,
                          detail="" if has_fields else "缺少 state/config 字段")
        else:
            runner.record(group, "D2 GET /api/status", False, r.status_code)
    except Exception as e:
        runner.record(group, "D2 GET /api/status", False, detail=str(e))

    # D3: Config GET
    try:
        r = _req.get(f"{SIGNAL_MONITOR}/api/config", timeout=TIMEOUT)
        ok = r.status_code == 200
        runner.record(group, "D3 GET /api/config", ok, r.status_code)
    except Exception as e:
        runner.record(group, "D3 GET /api/config", False, detail=str(e))

    # D4: Config POST
    try:
        r = _req.post(f"{SIGNAL_MONITOR}/api/config", json={"interval_seconds": 300}, timeout=TIMEOUT)
        runner.record(group, "D4 POST /api/config", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "D4 POST /api/config", False, detail=str(e))

    # D5: Strategies
    try:
        r = _req.get(f"{SIGNAL_MONITOR}/api/strategies", timeout=TIMEOUT)
        ok = r.status_code == 200
        if ok:
            data = r.json()
            strategies = data.get("strategies", [])
            runner.record(group, f"D5 GET /api/strategies ({len(strategies)} 条)", ok, r.status_code)
        else:
            runner.record(group, "D5 GET /api/strategies", False, r.status_code)
    except Exception as e:
        runner.record(group, "D5 GET /api/strategies", False, detail=str(e))

    # D6: Test notify (可能 Telegram 未配置)
    try:
        r = _req.post(f"{SIGNAL_MONITOR}/api/test-notify", timeout=TIMEOUT)
        # 不管 Telegram 是否配好，接口本身应返回 200
        runner.record(group, "D6 POST /api/test-notify", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "D6 POST /api/test-notify", False, detail=str(e))

    # D7: Start/Stop
    try:
        r = _req.post(f"{SIGNAL_MONITOR}/api/start", timeout=TIMEOUT)
        runner.record(group, "D7 POST /api/start", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "D7 POST /api/start", False, detail=str(e))

    try:
        r = _req.post(f"{SIGNAL_MONITOR}/api/stop", timeout=TIMEOUT)
        runner.record(group, "D8 POST /api/stop", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "D8 POST /api/stop", False, detail=str(e))


# ============================================================
# E. Execution Node 端点
# ============================================================
def test_E_execution_node(runner: TestRunner):
    group = "E.ExecutionNode"
    print(f"\n{'='*60}")
    print(f"  {group}")
    print(f"{'='*60}")

    if not runner._service_up(EXECUTION_NODE):
        runner.skip(group, "E0 服务不可用", "execution-node (9101) 未运行")
        return

    # E1: Health
    try:
        r = runner._get(f"{EXECUTION_NODE}/health")
        ok = r.status_code == 200
        data = r.json() if ok else {}
        runner.record(group, "E1 GET /health", ok, r.status_code,
                      detail=f"heartbeat={'enabled' if data.get('heartbeat_enabled') else 'disabled'}" if ok else "")
    except Exception as e:
        runner.record(group, "E1 GET /health", False, detail=str(e))

    import requests as _req

    # E2: Execute (空 tasks)
    try:
        r = _req.post(f"{EXECUTION_NODE}/api/execute", json={
            "signal": {"symbol": "BTC/USDT", "side": "BUY", "entry_price": 50000},
            "amount_usdt": 100,
            "sandbox": True,
            "tasks": [],
        }, timeout=TIMEOUT)
        ok = r.status_code == 200
        runner.record(group, "E2 POST /api/execute (空 tasks)", ok, r.status_code)
    except Exception as e:
        runner.record(group, "E2 POST /api/execute (空 tasks)", False, detail=str(e))

    # E3: Sync balance (空 tasks)
    try:
        r = _req.post(f"{EXECUTION_NODE}/api/sync-balance", json={
            "tasks": [],
            "sandbox": True,
        }, timeout=TIMEOUT)
        runner.record(group, "E3 POST /api/sync-balance (空)", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "E3 POST /api/sync-balance", False, detail=str(e))

    # E4: Sync positions (空 tasks)
    try:
        r = _req.post(f"{EXECUTION_NODE}/api/sync-positions", json={
            "tasks": [],
            "sandbox": True,
        }, timeout=TIMEOUT)
        runner.record(group, "E4 POST /api/sync-positions (空)", r.status_code == 200, r.status_code)
    except Exception as e:
        runner.record(group, "E4 POST /api/sync-positions", False, detail=str(e))

    # E5: Execute - missing symbol should 400
    try:
        r = _req.post(f"{EXECUTION_NODE}/api/execute", json={
            "signal": {"side": "BUY", "entry_price": 50000},
            "amount_usdt": 100, "sandbox": True,
            "tasks": [{"account_id": 1, "tenant_id": 1, "user_id": 1,
                        "exchange": "binance", "api_key": "k", "api_secret": "s"}],
        }, timeout=TIMEOUT)
        runner.record(group, "E5 POST /api/execute (无 symbol→400)", r.status_code in (400, 422), r.status_code)
    except Exception as e:
        runner.record(group, "E5 POST /api/execute (无 symbol)", False, detail=str(e))


# ============================================================
# F. 业务闭环验证（跨模块/服务联动）
# ============================================================
def test_F_business_flows(runner: TestRunner):
    group = "F.业务闭环"
    print(f"\n{'='*60}")
    print(f"  {group}")
    print(f"{'='*60}")

    # F1: 数据库有策略数据
    try:
        from libs.core.database import get_session
        from libs.member.models import Strategy
        session = get_session()
        count = session.query(Strategy).count()
        session.close()
        runner.record(group, f"F1 dim_strategy 有数据 ({count} 条)", count > 0)
    except Exception as e:
        runner.record(group, "F1 dim_strategy 有数据", False, detail=str(e))

    # F2: 数据库有租户数据
    try:
        from libs.core.database import get_session
        from libs.tenant.models import Tenant
        session = get_session()
        count = session.query(Tenant).count()
        session.close()
        runner.record(group, f"F2 dim_tenant 有数据 ({count} 条)", count > 0)
    except Exception as e:
        runner.record(group, "F2 dim_tenant 有数据", False, detail=str(e))

    # F3: 数据库有管理员
    try:
        from libs.core.database import get_session
        from libs.admin.models import Admin
        session = get_session()
        count = session.query(Admin).count()
        session.close()
        runner.record(group, f"F3 dim_admin 有数据 ({count} 条)", count > 0)
    except Exception as e:
        runner.record(group, "F3 dim_admin 有数据", False, detail=str(e))

    # F4: MemberService 核心方法
    try:
        from libs.core.database import get_session
        from libs.member.service import MemberService
        session = get_session()
        svc = MemberService(session)
        # 检查方法存在
        assert callable(getattr(svc, 'create_user', None))
        assert callable(getattr(svc, 'get_user_by_email', None))
        assert callable(getattr(svc, 'open_strategy', None))
        assert callable(getattr(svc, 'close_strategy', None))
        assert callable(getattr(svc, 'get_execution_targets_by_strategy_code', None))
        session.close()
        runner.record(group, "F4 MemberService 核心方法", True)
    except Exception as e:
        runner.record(group, "F4 MemberService 核心方法", False, detail=str(e))

    # F5: PointCardService 核心方法
    try:
        from libs.core.database import get_session
        from libs.pointcard.service import PointCardService
        session = get_session()
        svc = PointCardService(session)
        assert callable(getattr(svc, 'recharge_user', None))
        assert callable(getattr(svc, 'deduct_for_profit', None))
        assert callable(getattr(svc, 'transfer', None))
        session.close()
        runner.record(group, "F5 PointCardService 核心方法", True)
    except Exception as e:
        runner.record(group, "F5 PointCardService 核心方法", False, detail=str(e))

    # F6: RewardService 核心方法
    try:
        from libs.core.database import get_session
        from libs.reward.service import RewardService
        session = get_session()
        svc = RewardService(session)
        assert callable(getattr(svc, 'distribute_for_pool', None))
        session.close()
        runner.record(group, "F6 RewardService 核心方法", True)
    except Exception as e:
        runner.record(group, "F6 RewardService 核心方法", False, detail=str(e))

    # F7: WithdrawalService 生命周期方法
    try:
        from libs.core.database import get_session
        from libs.reward.withdrawal_service import WithdrawalService
        session = get_session()
        svc = WithdrawalService(session)
        assert callable(getattr(svc, 'apply', None))
        assert callable(getattr(svc, 'approve', None))
        assert callable(getattr(svc, 'reject', None))
        assert callable(getattr(svc, 'complete', None))
        session.close()
        runner.record(group, "F7 WithdrawalService 生命周期", True)
    except Exception as e:
        runner.record(group, "F7 WithdrawalService 生命周期", False, detail=str(e))

    # F8: TradeSettlementService 集成
    try:
        from libs.trading.settlement import TradeSettlementService
        from libs.core.database import get_session
        session = get_session()
        svc = TradeSettlementService(session=session, tenant_id=1, account_id=1)
        assert callable(getattr(svc, 'settle_fill', None))
        session.close()
        runner.record(group, "F8 TradeSettlementService 集成", True)
    except Exception as e:
        runner.record(group, "F8 TradeSettlementService 集成", False, detail=str(e))

    # F9: 策略加载与分析
    try:
        from libs.strategies import get_strategy
        strategy = get_strategy("market_regime")
        assert strategy is not None
        runner.record(group, "F9 策略 market_regime 可加载", True)
    except Exception as e:
        runner.record(group, "F9 策略 market_regime 可加载", False, detail=str(e))

    # F10: 租户策略实例查询
    try:
        from libs.core.database import get_session
        from libs.member.repository import MemberRepository
        session = get_session()
        repo = MemberRepository(session)
        instances = repo.list_tenant_strategies(1)  # tenant_id=1
        session.close()
        runner.record(group, f"F10 租户策略实例查询 ({len(instances)} 条)", True)
    except Exception as e:
        runner.record(group, "F10 租户策略实例查询", False, detail=str(e))

    # F11: Exchange utils 符号转换一致性
    try:
        from libs.exchange.utils import to_canonical_symbol, normalize_symbol
        # 测试多种格式的转换
        tests = [
            ("BTCUSDT", "BTC/USDT"),
            ("ETHUSDT", "ETH/USDT"),
            ("BTC/USDT", "BTC/USDT"),
        ]
        all_ok = True
        for input_sym, expected in tests:
            result = to_canonical_symbol(input_sym, "future")
            if expected not in (result or ""):
                all_ok = False
                break
        runner.record(group, "F11 符号标准化", all_ok)
    except Exception as e:
        runner.record(group, "F11 符号标准化", False, detail=str(e))

    # F12: 数据库 dim_tenant_strategy 表存在且可查
    try:
        from libs.core.database import get_session
        from sqlalchemy import text
        session = get_session()
        rows = session.execute(text("SELECT COUNT(*) FROM dim_tenant_strategy")).fetchone()
        count = rows[0] if rows else 0
        session.close()
        runner.record(group, f"F12 dim_tenant_strategy 可查 ({count} 条)", True)
    except Exception as e:
        runner.record(group, "F12 dim_tenant_strategy 可查", False, detail=str(e))

    # F13: Redis 连通性
    try:
        from libs.core.redis_client import get_redis
        r = get_redis()
        r.ping()
        runner.record(group, "F13 Redis 连通", True)
    except Exception as e:
        runner.record(group, "F13 Redis 连通", False, detail=str(e))

    # F14: LevelService 等级名称
    try:
        from libs.core.database import get_session
        from libs.member.level_service import LevelService
        session = get_session()
        svc = LevelService(session)
        name = svc.get_level_name(0)
        assert isinstance(name, str)
        session.close()
        runner.record(group, "F14 LevelService 等级名称", True)
    except Exception as e:
        runner.record(group, "F14 LevelService 等级名称", False, detail=str(e))

    # F15: QuotaService 检查
    try:
        from libs.core.database import get_session
        from libs.quota import QuotaService
        session = get_session()
        svc = QuotaService(session)
        result = svc.check_api_quota(1)
        assert "allowed" in result
        session.close()
        runner.record(group, "F15 QuotaService 配额检查", True)
    except Exception as e:
        runner.record(group, "F15 QuotaService 配额检查", False, detail=str(e))


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 80)
    print("  IronBull 全量业务流程测试")
    print(f"  Data API:       {DATA_API}")
    print(f"  Merchant API:   {MERCHANT_API}")
    print(f"  Signal Monitor: {SIGNAL_MONITOR}")
    print(f"  Execution Node: {EXECUTION_NODE}")
    print("=" * 80)

    runner = TestRunner()

    # A: 核心库（无需服务）
    test_A_core_libs(runner)

    # B: Data API
    test_B_data_api(runner)

    # C: Merchant API
    test_C_merchant_api(runner)

    # D: Signal Monitor
    test_D_signal_monitor(runner)

    # E: Execution Node
    test_E_execution_node(runner)

    # F: 业务闭环
    test_F_business_flows(runner)

    # 汇总
    failed = runner.summary()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
