"""
JWT 签发与校验（管理后台 / data-api 登录态）

配置项：
  jwt_secret  — 必须在生产环境中通过环境变量 IRONBULL_JWT_SECRET 注入。
                开发环境未配置时使用内置默认值并输出警告。
"""

import os
import time
import warnings
from typing import Optional, Dict, Any

from libs.core import get_config

try:
    import jwt as pyjwt
except ImportError:
    pyjwt = None  # type: ignore

ALG = "HS256"
DEFAULT_EXP_HOURS = 24

_DEV_SECRET = "ironbull-admin-dev-secret-DO-NOT-USE-IN-PROD"


def _get_secret() -> str:
    config = get_config()
    secret = config.get_str("jwt_secret", "").strip()
    if secret:
        return secret
    # 未配置 jwt_secret
    env = os.environ.get("IRONBULL_ENV", "dev").lower()
    if env in ("prod", "production"):
        raise RuntimeError(
            "jwt_secret 未配置！生产环境必须设置 IRONBULL_JWT_SECRET 环境变量"
        )
    warnings.warn(
        "jwt_secret 未配置，使用开发默认值。生产环境请设置 IRONBULL_JWT_SECRET",
        stacklevel=2,
    )
    return _DEV_SECRET


def encode(admin_id: int, username: str, exp_hours: int = DEFAULT_EXP_HOURS) -> str:
    """签发 JWT，payload 含 admin_id、username、exp。仅用于管理后台登录。"""
    if not pyjwt:
        raise RuntimeError("PyJWT not installed")
    now = int(time.time())
    payload = {
        "admin_id": admin_id,
        "username": username,
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
