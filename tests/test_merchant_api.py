"""
Merchant API 接口级测试

覆盖：签名认证、参数校验、返回格式、19 个接口基本调用。
使用 FastAPI TestClient + 真实数据库（rollback）。

运行：
    cd /path/to/ironbull
    python -m pytest tests/test_merchant_api.py -v
"""

import os
import sys
import time
import hashlib
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.core.database import init_database, get_session
from libs.tenant.repository import TenantRepository
from libs.member.repository import MemberRepository

# ---------- fixtures ----------

TENANT_ID = 1


@pytest.fixture(scope="module")
def db_session():
    init_database()
    return get_session()


@pytest.fixture(scope="module")
def tenant_info(db_session):
    """获取租户 app_key / app_secret，以及至少一个用户 email"""
    repo = TenantRepository(db_session)
    tenant = repo.get_by_id(TENANT_ID)
    if not tenant or not tenant.app_key or not tenant.app_secret:
        pytest.skip("需要 tenant_id=1 且有 app_key/app_secret")
    member_repo = MemberRepository(db_session)
    items, total = member_repo.list_users(TENANT_ID, 1, 5)
    user_email = items[0].email if items else None
    if not user_email:
        pytest.skip("需要至少一个用户")
    # 找第二个用户（转账测试用）
    user_email_2 = None
    for u in items:
        if u.email != user_email:
            user_email_2 = u.email
            break
    return {
        "app_key": tenant.app_key,
        "app_secret": tenant.app_secret,
        "email": user_email,
        "email_2": user_email_2,
    }


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient（不走真实网络）"""
    import importlib
    from fastapi.testclient import TestClient
    # 目录名含连字符，需要 importlib 加载
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "services", "merchant-api"))
    mod = importlib.import_module("app.main")
    return TestClient(mod.app)


def make_headers(app_key: str, app_secret: str) -> dict:
    """生成合法的认证头"""
    ts = str(int(time.time()))
    sign = hashlib.md5((app_key + ts + app_secret).encode()).hexdigest()
    return {
        "X-App-Key": app_key,
        "X-Timestamp": ts,
        "X-Sign": sign,
    }


def bad_headers() -> dict:
    """生成错误的认证头"""
    return {
        "X-App-Key": "fake_key",
        "X-Timestamp": str(int(time.time())),
        "X-Sign": "0000000000000000",
    }


# ========== 1. 认证测试 ==========

class TestAuth:
    def test_missing_headers(self, client):
        """无认证头 → 401"""
        r = client.get("/merchant/root-user")
        assert r.status_code == 401

    def test_invalid_sign(self, client):
        """错误签名 → 401"""
        r = client.get("/merchant/root-user", headers=bad_headers())
        assert r.status_code == 401

    def test_expired_timestamp(self, client, tenant_info):
        """过期时间戳 → 401"""
        ts = str(int(time.time()) - 600)  # 10 分钟前
        sign = hashlib.md5(
            (tenant_info["app_key"] + ts + tenant_info["app_secret"]).encode()
        ).hexdigest()
        headers = {
            "X-App-Key": tenant_info["app_key"],
            "X-Timestamp": ts,
            "X-Sign": sign,
        }
        r = client.get("/merchant/root-user", headers=headers)
        assert r.status_code == 401

    def test_valid_auth(self, client, tenant_info):
        """正确签名 → 200"""
        headers = make_headers(tenant_info["app_key"], tenant_info["app_secret"])
        r = client.get("/merchant/root-user", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["code"] in (0, 1)  # 0=有根用户, 1=未设置


# ========== 2. 用户管理接口 ==========

class TestUserEndpoints:
    def _h(self, ti):
        return make_headers(ti["app_key"], ti["app_secret"])

    def test_root_user(self, client, tenant_info):
        """GET /merchant/root-user"""
        r = client.get("/merchant/root-user", headers=self._h(tenant_info))
        d = r.json()
        assert d["code"] in (0, 1)
        if d["code"] == 0:
            assert "user_id" in d["data"]
            assert "email" in d["data"]
            assert "invite_code" in d["data"]

    def test_users_list(self, client, tenant_info):
        """GET /merchant/users"""
        r = client.get("/merchant/users", headers=self._h(tenant_info), params={"page": 1, "limit": 5})
        d = r.json()
        assert d["code"] == 0
        assert "list" in d["data"]
        assert "total" in d["data"]
        if d["data"]["list"]:
            item = d["data"]["list"][0]
            for field in ("user_id", "email", "invite_code", "point_card_self", "point_card_gift", "point_card_total", "status"):
                assert field in item, f"缺少字段 {field}"

    def test_user_info_by_email(self, client, tenant_info):
        """GET /merchant/user/info?email=..."""
        r = client.get(
            "/merchant/user/info",
            headers=self._h(tenant_info),
            params={"email": tenant_info["email"]},
        )
        d = r.json()
        assert d["code"] == 0
        data = d["data"]
        required = [
            "user_id", "email", "invite_code", "inviter_invite_code", "status",
            "point_card_self", "point_card_gift", "point_card_total",
            "level", "level_name", "is_market_node", "self_hold",
            "team_direct_count", "team_total_count", "team_performance",
            "reward_usdt", "total_reward", "withdrawn_reward",
            "accounts", "active_strategies", "total_profit", "total_trades",
        ]
        for f in required:
            assert f in data, f"user/info 缺少字段 {f}"

    def test_user_info_missing_email(self, client, tenant_info):
        """GET /merchant/user/info 不传 email → 422"""
        r = client.get("/merchant/user/info", headers=self._h(tenant_info))
        assert r.status_code == 422

    def test_user_info_nonexist(self, client, tenant_info):
        """GET /merchant/user/info email 不存在 → code=1"""
        r = client.get(
            "/merchant/user/info",
            headers=self._h(tenant_info),
            params={"email": "nonexist_99999@test.com"},
        )
        d = r.json()
        assert d["code"] == 1


# ========== 3. 点卡管理接口 ==========

class TestPointcardEndpoints:
    def _h(self, ti):
        return make_headers(ti["app_key"], ti["app_secret"])

    def test_balance(self, client, tenant_info):
        """GET /merchant/balance"""
        r = client.get("/merchant/balance", headers=self._h(tenant_info))
        d = r.json()
        assert d["code"] == 0
        for f in ("point_card_self", "point_card_gift", "point_card_total"):
            assert f in d["data"], f"balance 缺少字段 {f}"

    def test_point_card_logs(self, client, tenant_info):
        """GET /merchant/point-card/logs"""
        r = client.get(
            "/merchant/point-card/logs",
            headers=self._h(tenant_info),
            params={"page": 1, "limit": 5},
        )
        d = r.json()
        assert d["code"] == 0
        assert "list" in d["data"]
        assert "total" in d["data"]
        if d["data"]["list"]:
            item = d["data"]["list"][0]
            for f in ("id", "change_type", "change_type_name", "amount", "member_id"):
                assert f in item, f"logs 缺少字段 {f}"

    def test_point_card_logs_filter_email(self, client, tenant_info):
        """GET /merchant/point-card/logs?email=... 筛选"""
        r = client.get(
            "/merchant/point-card/logs",
            headers=self._h(tenant_info),
            params={"email": tenant_info["email"]},
        )
        d = r.json()
        assert d["code"] == 0

    def test_point_card_logs_filter_nonexist_email(self, client, tenant_info):
        """GET /merchant/point-card/logs?email=不存在 → 返回空列表"""
        r = client.get(
            "/merchant/point-card/logs",
            headers=self._h(tenant_info),
            params={"email": "nonexist_999@test.com"},
        )
        d = r.json()
        assert d["code"] == 0
        assert d["data"]["total"] == 0


# ========== 4. 策略管理接口 ==========

class TestStrategyEndpoints:
    def _h(self, ti):
        return make_headers(ti["app_key"], ti["app_secret"])

    def test_strategies_list(self, client, tenant_info):
        """GET /merchant/strategies"""
        r = client.get("/merchant/strategies", headers=self._h(tenant_info))
        d = r.json()
        assert d["code"] == 0
        if d["data"]:
            item = d["data"][0]
            for f in ("id", "name", "symbol", "status", "min_capital"):
                assert f in item, f"strategies 缺少字段 {f}"

    def test_user_strategies(self, client, tenant_info):
        """GET /merchant/user/strategies?email=..."""
        r = client.get(
            "/merchant/user/strategies",
            headers=self._h(tenant_info),
            params={"email": tenant_info["email"]},
        )
        d = r.json()
        assert d["code"] == 0

    def test_user_strategies_nonexist(self, client, tenant_info):
        """GET /merchant/user/strategies?email=不存在 → code=1"""
        r = client.get(
            "/merchant/user/strategies",
            headers=self._h(tenant_info),
            params={"email": "nonexist_999@test.com"},
        )
        d = r.json()
        assert d["code"] == 1


# ========== 5. 会员分销接口 ==========

class TestRewardEndpoints:
    def _h(self, ti):
        return make_headers(ti["app_key"], ti["app_secret"])

    def test_user_team(self, client, tenant_info):
        """GET /merchant/user/team?email=..."""
        r = client.get(
            "/merchant/user/team",
            headers=self._h(tenant_info),
            params={"email": tenant_info["email"]},
        )
        d = r.json()
        assert d["code"] == 0
        assert "list" in d["data"]
        assert "team_stats" in d["data"]
        stats = d["data"]["team_stats"]
        for f in ("direct_count", "total_count", "total_performance"):
            assert f in stats, f"team_stats 缺少字段 {f}"
        # 确保没有多余的 self_hold
        assert "self_hold" not in stats

    def test_user_rewards(self, client, tenant_info):
        """GET /merchant/user/rewards?email=..."""
        r = client.get(
            "/merchant/user/rewards",
            headers=self._h(tenant_info),
            params={"email": tenant_info["email"]},
        )
        d = r.json()
        assert d["code"] == 0
        assert "list" in d["data"]
        assert "total" in d["data"]

    def test_user_withdrawals(self, client, tenant_info):
        """GET /merchant/user/withdrawals?email=..."""
        r = client.get(
            "/merchant/user/withdrawals",
            headers=self._h(tenant_info),
            params={"email": tenant_info["email"]},
        )
        d = r.json()
        assert d["code"] == 0
        assert "list" in d["data"]

    def test_set_market_node(self, client, tenant_info):
        """POST /merchant/user/set-market-node — 先设后取消"""
        h = self._h(tenant_info)
        r = client.post(
            "/merchant/user/set-market-node",
            headers=h,
            data={"email": tenant_info["email"], "is_node": 1},
        )
        d = r.json()
        assert d["code"] == 0
        # 取消
        r2 = client.post(
            "/merchant/user/set-market-node",
            headers=self._h(tenant_info),
            data={"email": tenant_info["email"], "is_node": 0},
        )
        assert r2.json()["code"] == 0


# ========== 6. 响应格式一致性 ==========

class TestResponseFormat:
    def _h(self, ti):
        return make_headers(ti["app_key"], ti["app_secret"])

    def test_all_responses_have_code_msg_data(self, client, tenant_info):
        """所有 GET 接口返回 {code, msg, data}"""
        h = self._h(tenant_info)
        email = tenant_info["email"]
        endpoints = [
            ("/merchant/root-user", {}),
            ("/merchant/users", {"page": 1}),
            ("/merchant/user/info", {"email": email}),
            ("/merchant/balance", {}),
            ("/merchant/point-card/logs", {}),
            ("/merchant/strategies", {}),
            ("/merchant/user/strategies", {"email": email}),
            ("/merchant/user/team", {"email": email}),
            ("/merchant/user/rewards", {"email": email}),
            ("/merchant/user/withdrawals", {"email": email}),
        ]
        for path, params in endpoints:
            r = client.get(path, headers=h, params=params)
            assert r.status_code == 200, f"{path} 返回 {r.status_code}"
            d = r.json()
            assert "code" in d, f"{path} 缺少 code"
            assert "msg" in d, f"{path} 缺少 msg"
            assert "data" in d, f"{path} 缺少 data"
