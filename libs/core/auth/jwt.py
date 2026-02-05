"""
JWT 签发与校验（管理后台 / data-api 登录态）
"""

import time
from typing import Optional, Dict, Any

from libs.core import get_config

try:
    import jwt as pyjwt
except ImportError:
    pyjwt = None  # type: ignore

ALG = "HS256"
DEFAULT_EXP_HOURS = 24


def _get_secret() -> str:
    config = get_config()
    secret = config.get_str("jwt_secret", "")
    if not secret:
        secret = config.get_str("JWT_SECRET", "")
    if not secret:
        # 开发默认（生产必须配置 jwt_secret）
        secret = "ironbull-admin-dev-secret-change-in-production"
    return secret


def encode(tenant_id: int, user_id: int, exp_hours: int = DEFAULT_EXP_HOURS) -> str:
    """签发 JWT，payload 含 tenant_id、user_id、exp。"""
    if not pyjwt:
        raise RuntimeError("PyJWT not installed")
    now = int(time.time())
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "iat": now,
        "exp": now + exp_hours * 3600,
    }
    return pyjwt.encode(payload, _get_secret(), algorithm=ALG)  # type: ignore


def decode(token: str) -> Optional[Dict[str, Any]]:
    """校验并解析 JWT，返回 payload 或 None。"""
    if not pyjwt:
        return None
    try:
        payload = pyjwt.decode(token, _get_secret(), algorithms=[ALG])
        return payload  # type: ignore
    except Exception:
        return None
