"""
全流程集成测试 — Layer 1 (模型/导入/DB) + Layer 3 (API 端点)

运行：
    PYTHONPATH=. python3 -m pytest tests/test_integration.py -v --tb=short

Layer 1 仅需数据库；Layer 3 需要 data-api (8026) + signal-monitor (8020) 运行。
"""

import os
import sys
import pytest
import importlib

# 保证可导入项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

# ============================================================
#  Layer 1: 模型 / 导入 / 数据库验证（无需启动服务）
# ============================================================


class TestLayer1_DBFields:
    """1.1 数据库字段校验"""

    def test_strategy_new_columns_exist(self, db_session):
        """dim_strategy 表包含所有新增列"""
        from sqlalchemy import text
        rows = db_session.execute(text("DESCRIBE dim_strategy")).fetchall()
        fields = {r[0] for r in rows}
        expected = {
            "symbols", "exchange", "market_type",
            "amount_usdt", "leverage",
            "min_confidence", "cooldown_minutes",
        }
        missing = expected - fields
        assert not missing, f"dim_strategy 缺少字段: {missing}"

    def test_execution_node_table(self, db_session):
        """dim_execution_node 表可查询"""
        from sqlalchemy import text
        rows = db_session.execute(text("DESCRIBE dim_execution_node")).fetchall()
        fields = {r[0] for r in rows}
        assert "node_code" in fields
        assert "base_url" in fields
        assert "last_heartbeat_at" in fields

    def test_exchange_account_has_node_id(self, db_session):
        """fact_exchange_account 包含 execution_node_id"""
        from sqlalchemy import text
        rows = db_session.execute(text("DESCRIBE fact_exchange_account")).fetchall()
        fields = {r[0] for r in rows}
        assert "execution_node_id" in fields


class TestLayer1_Models:
    """1.2 Strategy 模型方法"""

    def test_strategy_get_symbols_with_list(self, db_session):
        from libs.member.models import Strategy
        s = Strategy(code="test", name="test", symbol="BTC/USDT",
                     symbols=["BTCUSDT", "ETHUSDT"])
        assert s.get_symbols() == ["BTCUSDT", "ETHUSDT"]

    def test_strategy_get_symbols_fallback_to_symbol(self, db_session):
        from libs.member.models import Strategy
        s = Strategy(code="test", name="test", symbol="BTC/USDT", symbols=None)
        assert s.get_symbols() == ["BTC/USDT"]

    def test_strategy_get_symbols_empty_list_fallback(self, db_session):
        from libs.member.models import Strategy
        s = Strategy(code="test", name="test", symbol="ETH/USDT", symbols=[])
        assert s.get_symbols() == ["ETH/USDT"]

    def test_strategy_get_config_dict(self, db_session):
        from libs.member.models import Strategy
        s = Strategy(code="test", name="test", symbol="X",
                     config={"atr_mult_sl": 1.5})
        assert s.get_config() == {"atr_mult_sl": 1.5}

    def test_strategy_get_config_none(self, db_session):
        from libs.member.models import Strategy
        s = Strategy(code="test", name="test", symbol="X", config=None)
        assert s.get_config() == {}

    def test_strategy_load_from_db(self, db_session):
        """从数据库加载 market_regime 策略，验证新字段有值"""
        from libs.member.models import Strategy
        s = db_session.query(Strategy).filter(Strategy.code == "market_regime").first()
        if not s:
            pytest.skip("market_regime 策略不存在")
        assert s.market_type in ("spot", "future")
        assert int(s.min_confidence) >= 0
        assert int(s.cooldown_minutes) >= 0
        assert float(s.amount_usdt) > 0
        assert int(s.leverage) >= 1


class TestLayer1_Imports:
    """1.3 核心模块导入"""

    def test_live_trader_constants(self):
        from libs.trading.live_trader import (
            OKX_MARKET_PRICE,
            GATE_MARKET_PRICE,
            GATE_CLOSE_ALL_SIZE,
            DEFAULT_QUOTE,
            DEFAULT_SETTLE,
            MARKET_ORDER_CONFIRM_RETRIES,
            MARKET_ORDER_CONFIRM_INTERVAL,
            OKX_CLOSE_FULL_FRACTION,
            DEFAULT_LEVERAGE_FALLBACK,
        )
        assert OKX_MARKET_PRICE == "-1"
        assert GATE_MARKET_PRICE == "0"
        assert GATE_CLOSE_ALL_SIZE == 0
        assert DEFAULT_QUOTE == "USDT"
        assert DEFAULT_SETTLE == "usdt"
        assert MARKET_ORDER_CONFIRM_RETRIES == 3
        assert MARKET_ORDER_CONFIRM_INTERVAL == 0.5
        assert OKX_CLOSE_FULL_FRACTION == "1"
        assert DEFAULT_LEVERAGE_FALLBACK == 20

    def test_config_get_list(self):
        from libs.core.config import Config
        c = Config.__new__(Config)
        c._data = {"items": ["a", "b"], "csv": "x,y,z", "empty": None}
        assert c.get_list("items") == ["a", "b"]
        assert c.get_list("csv") == ["x", "y", "z"]
        assert c.get_list("empty", ["default"]) == ["default"]
        assert c.get_list("missing", ["fallback"]) == ["fallback"]

    def test_auto_trader_risk_limits(self):
        from libs.trading.auto_trader import RiskLimits
        rl = RiskLimits()
        assert rl.max_trade_amount > 0
        assert rl.max_daily_trades > 0
        assert rl.max_open_positions > 0
        assert rl.max_daily_loss > 0
        assert rl.min_confidence > 0

    def test_signal_contract_fields(self):
        from libs.contracts.signal import Signal
        s = Signal(
            signal_id="test", strategy_code="x",
            symbol="BTC/USDT", canonical_symbol="BTC/USDT",
            side="BUY", signal_type="OPEN",
            amount_usdt=200.0, leverage=20,
        )
        assert s.amount_usdt == 200.0
        assert s.leverage == 20


# ============================================================
#  Layer 3: API 端点测试（需要 data-api / signal-monitor 运行）
# ============================================================

DATA_API = "http://127.0.0.1:8026"
SIGNAL_MONITOR = "http://127.0.0.1:8020"


def _get_admin_token():
    """签发一个管理后台 JWT"""
    from libs.core.auth.jwt import encode
    return encode(admin_id=1, username="admin", exp_hours=1)


def _auth_headers():
    return {"Authorization": f"Bearer {_get_admin_token()}"}


def _service_available(url: str) -> bool:
    try:
        r = httpx.get(f"{url}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


# 自动跳过未启动的服务
_data_api_up = pytest.mark.skipif(
    not _service_available(DATA_API),
    reason="data-api 未运行 (8026)",
)
_signal_monitor_up = pytest.mark.skipif(
    not _service_available(SIGNAL_MONITOR),
    reason="signal-monitor 未运行 (8020)",
)


@_data_api_up
class TestLayer3_NodesCRUD:
    """3.1 执行节点 CRUD"""

    _created_node_id = None

    @staticmethod
    def _unique_code():
        import time
        return f"pytest-node-{int(time.time() * 1000) % 100000}"

    def test_01_create_node(self):
        headers = _auth_headers()
        code = self._unique_code()
        TestLayer3_NodesCRUD._test_node_code = code

        r = httpx.post(
            f"{DATA_API}/api/nodes",
            json={"node_code": code, "name": "Pytest测试节点", "base_url": "http://127.0.0.1:19101"},
            headers=headers,
            timeout=10,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] is True
        TestLayer3_NodesCRUD._created_node_id = data["data"]["id"]

    def test_02_list_nodes(self):
        r = httpx.get(
            f"{DATA_API}/api/nodes?include_disabled=true",
            headers=_auth_headers(),
            timeout=10,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total"] >= 1
        # 确认有 account_count 字段
        node = data["data"][0]
        assert "account_count" in node

    def test_03_update_node(self):
        nid = TestLayer3_NodesCRUD._created_node_id
        assert nid, "节点未创建"
        r = httpx.put(
            f"{DATA_API}/api/nodes/{nid}",
            json={"name": "Pytest测试节点-改名"},
            headers=_auth_headers(),
            timeout=10,
        )
        assert r.status_code == 200, r.text
        assert r.json()["data"]["name"] == "Pytest测试节点-改名"

    def test_04_list_node_accounts(self):
        nid = TestLayer3_NodesCRUD._created_node_id
        assert nid, "节点未创建"
        r = httpx.get(
            f"{DATA_API}/api/nodes/{nid}/accounts",
            headers=_auth_headers(),
            timeout=10,
        )
        assert r.status_code == 200, r.text
        assert r.json()["total"] == 0  # 新节点应无绑定

    def test_05_delete_node(self):
        nid = TestLayer3_NodesCRUD._created_node_id
        assert nid, "节点未创建"
        r = httpx.delete(
            f"{DATA_API}/api/nodes/{nid}",
            headers=_auth_headers(),
            timeout=10,
        )
        assert r.status_code == 200, r.text
        assert "已禁用" in r.json()["message"]


@_data_api_up
class TestLayer3_AccountAssign:
    """3.2 账户分配节点"""

    def test_01_list_unassigned(self):
        r = httpx.get(
            f"{DATA_API}/api/exchange-accounts?unassigned=true",
            headers=_auth_headers(),
            timeout=10,
        )
        assert r.status_code == 200, r.text

    def test_02_assign_and_recover(self):
        """创建临时节点 → 分配账户 → 验证 → 回收"""
        import time
        headers = _auth_headers()
        code = f"pytest-assign-{int(time.time() * 1000) % 100000}"

        # 创建临时节点
        r = httpx.post(
            f"{DATA_API}/api/nodes",
            json={"node_code": code, "name": "临时", "base_url": "http://127.0.0.1:19102"},
            headers=headers, timeout=10,
        )
        assert r.status_code == 200, r.text
        node_id = r.json()["data"]["id"]

        # 找一个账户
        r = httpx.get(f"{DATA_API}/api/exchange-accounts", headers=headers, timeout=10)
        accounts = r.json().get("data", [])
        if not accounts:
            pytest.skip("无交易所账户可测试")
        acc_id = accounts[0]["id"]

        # 分配
        r = httpx.put(
            f"{DATA_API}/api/exchange-accounts/{acc_id}/assign-node",
            json={"execution_node_id": node_id},
            headers=headers, timeout=10,
        )
        assert r.status_code == 200, r.text
        assert r.json()["data"]["execution_node_id"] == node_id

        # 验证筛选
        r = httpx.get(
            f"{DATA_API}/api/exchange-accounts?execution_node_id={node_id}",
            headers=headers, timeout=10,
        )
        assert r.json()["total"] >= 1

        # 回收到本机
        r = httpx.put(
            f"{DATA_API}/api/exchange-accounts/{acc_id}/assign-node",
            json={"execution_node_id": None},
            headers=headers, timeout=10,
        )
        assert r.status_code == 200, r.text
        assert r.json()["data"]["execution_node_id"] is None

        # 清理：删除临时节点
        httpx.delete(f"{DATA_API}/api/nodes/{node_id}", headers=headers, timeout=10)


@_data_api_up
class TestLayer3_StrategyFields:
    """3.3 策略列表新字段"""

    def test_strategy_list_has_new_fields(self):
        r = httpx.get(
            f"{DATA_API}/api/strategies?tenant_id=1",
            headers=_auth_headers(),
            timeout=10,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total"] >= 1
        s = data["data"][0]
        for field in ("symbols", "exchange", "market_type", "amount_usdt",
                      "leverage", "min_confidence", "cooldown_minutes", "config"):
            assert field in s, f"策略缺少字段: {field}"


@_signal_monitor_up
class TestLayer3_SignalMonitor:
    """3.4 signal-monitor 端点"""

    def test_status_no_error(self):
        r = httpx.get(f"{SIGNAL_MONITOR}/api/status", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "state" in data
        assert "config" in data
        # 验证用的是新变量，不再报 monitor_config 错误
        cfg = data["config"]
        assert "interval_seconds" in cfg
        assert "notify_enabled" in cfg

    def test_config_get(self):
        r = httpx.get(f"{SIGNAL_MONITOR}/api/config", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "strategies" in data.get("config", {})

    def test_config_post(self):
        r = httpx.post(
            f"{SIGNAL_MONITOR}/api/config",
            json={"interval_seconds": 300},
            timeout=10,
        )
        assert r.status_code == 200, r.text

    def test_strategies_from_db(self):
        r = httpx.get(f"{SIGNAL_MONITOR}/api/strategies", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("success") is True
        strategies = data.get("strategies", [])
        assert len(strategies) >= 1
        # 验证返回了新字段
        s = strategies[0]
        assert "symbols" in s or "code" in s
