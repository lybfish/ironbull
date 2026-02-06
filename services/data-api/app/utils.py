"""
Data API - 公共工具函数
"""

from datetime import date, datetime
from typing import Optional


def parse_datetime(s: Optional[str]) -> Optional[datetime]:
    """解析 ISO datetime 字符串，失败返回 None"""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def parse_date(s: Optional[str]) -> Optional[date]:
    """解析 ISO date 字符串 (YYYY-MM-DD)，失败返回 None"""
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None
