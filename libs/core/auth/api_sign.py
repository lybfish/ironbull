"""
AppKey + Sign 认证

Merchant API 认证方式：
- Header: X-App-Key, X-Timestamp, X-Sign
- Sign = md5(app_key + timestamp + app_secret)
- 时间戳 5 分钟有效
"""

import hashlib
import time
from typing import Tuple, Optional

SIGN_EXPIRE_SECONDS = 300  # 5 分钟


def extract_sign_headers(
    x_app_key: Optional[str],
    x_timestamp: Optional[str],
    x_sign: Optional[str],
) -> Tuple[str, str, str]:
    """
    从请求头提取认证参数，缺失时抛出 ValueError。
    """
    if not x_app_key or not x_timestamp or not x_sign:
        raise ValueError("缺少认证参数")
    return (x_app_key.strip(), x_timestamp.strip(), x_sign.strip())


def verify_timestamp(timestamp_str: str) -> None:
    """
    验证时间戳是否在有效期内，无效则抛出 ValueError。
    """
    try:
        ts = int(timestamp_str)
    except ValueError:
        raise ValueError("时间戳格式错误")
    now = int(time.time())
    if abs(now - ts) > SIGN_EXPIRE_SECONDS:
        raise ValueError("请求已过期")


def compute_sign(app_key: str, timestamp: str, app_secret: str) -> str:
    """
    计算签名: md5(app_key + timestamp + app_secret)
    """
    raw = f"{app_key}{timestamp}{app_secret}"
    return hashlib.md5(raw.encode()).hexdigest().lower()


def verify_sign(app_key: str, timestamp: str, sign: str, app_secret: str) -> bool:
    """
    验证签名是否与 app_secret 计算结果一致。
    """
    expected = compute_sign(app_key, timestamp, app_secret)
    return sign.lower() == expected
