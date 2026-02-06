"""
AppKey + Sign 认证 — 纯逻辑测试（不需要 DB）

覆盖：
- compute_sign 结果一致性
- verify_sign 正确签名 / 错误签名
- extract_sign_headers 缺少参数抛 ValueError
- verify_timestamp 超时抛 ValueError
"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.core.auth.api_sign import (
    compute_sign,
    verify_sign,
    extract_sign_headers,
    verify_timestamp,
)


def test_compute_sign_deterministic():
    """相同输入应产出相同签名"""
    s1 = compute_sign("key1", "1700000000", "secret1")
    s2 = compute_sign("key1", "1700000000", "secret1")
    assert s1 == s2
    assert len(s1) == 32  # md5 hex
    # 不同输入应不同
    s3 = compute_sign("key2", "1700000000", "secret1")
    assert s1 != s3


def test_verify_sign_correct():
    """正确签名应验证通过"""
    ts = str(int(time.time()))
    sign = compute_sign("mykey", ts, "mysecret")
    assert verify_sign("mykey", ts, sign, "mysecret") is True


def test_verify_sign_wrong():
    """错误签名应验证失败"""
    ts = str(int(time.time()))
    assert verify_sign("mykey", ts, "wrong_sign_value", "mysecret") is False


def test_extract_sign_headers_missing():
    """缺少任意一个 header 应抛 ValueError"""
    with pytest.raises(ValueError, match="缺少认证参数"):
        extract_sign_headers(None, "123", "abc")
    with pytest.raises(ValueError, match="缺少认证参数"):
        extract_sign_headers("key", None, "abc")
    with pytest.raises(ValueError, match="缺少认证参数"):
        extract_sign_headers("key", "123", None)
    with pytest.raises(ValueError, match="缺少认证参数"):
        extract_sign_headers("", "123", "abc")


def test_verify_timestamp_expired():
    """过期时间戳应抛 ValueError"""
    old_ts = str(int(time.time()) - 600)  # 10 分钟前，超过 5 分钟限制
    with pytest.raises(ValueError, match="过期"):
        verify_timestamp(old_ts)
    # 正常时间戳不应抛异常
    verify_timestamp(str(int(time.time())))
