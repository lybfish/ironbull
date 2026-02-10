"""
时区/新闻过滤模块

实现时区过滤、新闻过滤占位接口等
"""

from typing import List, Dict, Optional
from datetime import datetime


def in_session(timestamp: int, session: str) -> bool:
    """
    检查时间戳是否在指定交易时段内
    
    Args:
        timestamp: Unix时间戳（秒）
        session: 时段名称 "asia" / "london" / "ny" / "all"
    
    Returns:
        是否在时段内
    """
    if session == "all":
        return True
    
    # 转换为UTC+8（假设服务器时间）
    t = (timestamp + 8 * 3600) % 86400
    hour = t // 3600
    
    if session == "asia":
        return 0 <= hour < 8
    elif session == "london":
        return 15 <= hour < 23
    elif session == "ny":
        return hour >= 20 or hour < 4
    
    return True


def check_session_filter(
    timestamp: int,
    enable_session_filter: bool,
    allowed_sessions: List[str]
) -> bool:
    """
    检查是否允许在当前时段交易
    
    Args:
        timestamp: Unix时间戳
        enable_session_filter: 是否启用时区过滤
        allowed_sessions: 允许的交易时段列表
    
    Returns:
        是否允许交易
    """
    if not enable_session_filter:
        return True
    
    for session in allowed_sessions:
        if in_session(timestamp, session):
            return True
    
    return False


def check_news_filter(
    timestamp: int,
    enable_news_filter: bool,
    news_impact_levels: List[str],
    news_blackout_minutes: int = 30
) -> bool:
    """
    检查是否在新闻黑名单时间窗内（占位接口）
    
    Args:
        timestamp: Unix时间戳
        enable_news_filter: 是否启用新闻过滤
        news_impact_levels: 过滤的新闻级别
        news_blackout_minutes: 新闻前后禁止开仓的分钟数
    
    Returns:
        是否允许交易（True=允许，False=禁止）
    """
    if not enable_news_filter:
        return True
    
    # TODO: 实现新闻日历接口对接
    # 目前返回True（允许交易）
    return True


def get_session_risk_factor(
    timestamp: int,
    session_risk_factor: Dict[str, float]
) -> float:
    """
    获取当前时段的风险系数
    
    Args:
        timestamp: Unix时间戳
        session_risk_factor: 时段风险系数字典
    
    Returns:
        风险系数（默认1.0）
    """
    if not session_risk_factor:
        return 1.0
    
    # 确定当前时段
    t = (timestamp + 8 * 3600) % 86400
    hour = t // 3600
    
    if 0 <= hour < 8:
        return session_risk_factor.get("asia", 1.0)
    elif 15 <= hour < 23:
        return session_risk_factor.get("london", 1.0)
    elif hour >= 20 or hour < 4:
        return session_risk_factor.get("ny", 1.0)
    
    return 1.0
