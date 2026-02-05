"""
Core Auth - 认证模块

- api_sign: Merchant API AppKey + Sign 认证
- jwt: 管理后台 JWT 签发与校验
"""

from .api_sign import (
    SIGN_EXPIRE_SECONDS,
    extract_sign_headers,
    compute_sign,
    verify_timestamp,
    verify_sign,
)
from .jwt import encode as jwt_encode, decode as jwt_decode

__all__ = [
    "SIGN_EXPIRE_SECONDS",
    "extract_sign_headers",
    "compute_sign",
    "verify_timestamp",
    "verify_sign",
    "jwt_encode",
    "jwt_decode",
]
