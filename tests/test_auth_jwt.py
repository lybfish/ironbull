"""
JWT 签发与校验 — 纯逻辑测试（不需要 DB）

覆盖：
- encode 返回非空字符串
- decode 正确解析 admin_id / username / exp
- decode 对篡改 token 返回 None
- decode 对过期 token 返回 None
- _get_secret 开发环境返回默认值 + warning
- _get_secret 生产环境未配置抛 RuntimeError
"""

import os
import sys
import time
import warnings

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.core.auth.jwt import encode, decode, _get_secret, _DEV_SECRET


def test_encode_returns_nonempty_string():
    """encode 应返回非空字符串"""
    token = encode(admin_id=42, username="testadmin")
    assert isinstance(token, str)
    assert len(token) > 20  # JWT 至少几十个字符


def test_decode_returns_correct_payload():
    """decode 应正确解析 admin_id / username"""
    token = encode(admin_id=7, username="alice", exp_hours=1)
    payload = decode(token)
    assert payload is not None
    assert payload["admin_id"] == 7
    assert payload["username"] == "alice"
    assert "exp" in payload
    assert "iat" in payload


def test_decode_rejects_tampered_token():
    """篡改 token 后 decode 应返回 None"""
    token = encode(admin_id=1, username="admin")
    # 在签名部分中间插入字符，确保破坏签名
    parts = token.split(".")
    sig = parts[2]
    tampered_sig = sig[:4] + ("X" if sig[4] != "X" else "Y") + sig[5:]
    tampered = parts[0] + "." + parts[1] + "." + tampered_sig
    assert decode(tampered) is None


def test_decode_rejects_expired_token():
    """过期 token 应返回 None"""
    import jwt as pyjwt
    # 手动构造一个已过期的 token
    secret = _get_secret()
    payload = {
        "admin_id": 1,
        "username": "admin",
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600,  # 1 小时前过期
    }
    expired_token = pyjwt.encode(payload, secret, algorithm="HS256")
    assert decode(expired_token) is None


def test_get_secret_dev_returns_default_with_warning():
    """开发环境未配置 jwt_secret 时返回默认值并发出 warning"""
    # 确保不是 production
    old_env = os.environ.pop("IRONBULL_ENV", None)
    try:
        # 清除 Config 单例缓存中的 jwt_secret（如果有的话）
        from libs.core.config import Config
        orig = Config._instance
        Config._instance = None
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                secret = _get_secret()
                assert secret == _DEV_SECRET
                # 应该有一条 warning
                assert any("jwt_secret" in str(x.message) for x in w)
        finally:
            Config._instance = orig
    finally:
        if old_env is not None:
            os.environ["IRONBULL_ENV"] = old_env


def test_get_secret_production_raises_without_config():
    """生产环境未配置 jwt_secret 时应抛出 RuntimeError"""
    old_env = os.environ.get("IRONBULL_ENV")
    os.environ["IRONBULL_ENV"] = "production"
    from libs.core.config import Config
    orig = Config._instance
    Config._instance = None
    try:
        with pytest.raises(RuntimeError, match="jwt_secret"):
            _get_secret()
    finally:
        Config._instance = orig
        if old_env is not None:
            os.environ["IRONBULL_ENV"] = old_env
        else:
            os.environ.pop("IRONBULL_ENV", None)
