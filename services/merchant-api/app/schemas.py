"""
Merchant API - 统一响应格式（与 old3 一致）
"""

from typing import Any, Optional


def ok(data: Any = None, msg: str = "success") -> dict:
    return {"code": 0, "msg": msg, "data": data}


def fail(msg: str = "失败", code: int = 1) -> dict:
    return {"code": code, "msg": msg, "data": None}
