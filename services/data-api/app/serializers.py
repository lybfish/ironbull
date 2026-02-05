"""
Data API - DTO 转 JSON 可序列化 dict
"""

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any, List


def _serialize_value(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if hasattr(v, "value"):  # Enum
        return v.value
    if is_dataclass(v) and not isinstance(v, type):
        return dto_to_dict(v)
    if isinstance(v, list):
        return [_serialize_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _serialize_value(x) for k, x in v.items()}
    return v


def dto_to_dict(dto: Any) -> dict:
    """将 DTO（dataclass）转为 JSON 可序列化 dict"""
    if dto is None:
        return None
    if hasattr(dto, "to_dict"):
        out = dto.to_dict()
        return {k: _serialize_value(v) for k, v in out.items()}
    if is_dataclass(dto):
        return {k: _serialize_value(getattr(dto, k)) for k in getattr(dto.__class__, "__dataclass_fields__", {}).keys()}
    return dto
