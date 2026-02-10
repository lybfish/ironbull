"""
斐波那契计算模块

实现斐波那契回撤位、扩展位计算，以及价格是否在斐波那契区域的判断
"""

from typing import List, Dict, Optional, Tuple
from libs.indicators.fibo import fibo_levels as lib_fibo_levels, fibo_extension as lib_fibo_extension


def calculate_fibo_levels(
    swing_high: float,
    swing_low: float,
    levels: List[float]
) -> Dict[float, float]:
    """
    计算斐波那契回撤位
    
    Args:
        swing_high: 摆动高点
        swing_low: 摆动低点
        levels: 斐波那契比例列表（如 [0.5, 0.618, 0.705]）
    
    Returns:
        {比例: 价格} 字典
    """
    return lib_fibo_levels(swing_high, swing_low, levels)


def price_in_fibo_zone(
    price: float,
    fibo_dict: Dict[float, float],
    tolerance_pct: float = 0.005
) -> Optional[Tuple[float, float]]:
    """
    检查价格是否在某个斐波那契位附近
    
    Args:
        price: 当前价格
        fibo_dict: 斐波那契位字典 {比例: 价格}
        tolerance_pct: 容差百分比（默认 0.5%）
    
    Returns:
        (比例, 目标价格) 元组，不在任何区域返回 None
    """
    from libs.indicators.fibo import price_in_fibo_zone as lib_price_in_fibo_zone
    return lib_price_in_fibo_zone(price, fibo_dict, tolerance_pct)


def calculate_fibo_extension(
    swing_high: float,
    swing_low: float,
    levels: Optional[List[float]] = None
) -> Dict[float, float]:
    """
    计算斐波那契扩展位
    
    Args:
        swing_high: 摆动高点
        swing_low: 摆动低点
        levels: 扩展比例列表（默认 [1.272, 1.618]）
    
    Returns:
        {比例: 价格} 字典
    """
    if levels is None:
        levels = [1.272, 1.618]
    return lib_fibo_extension(swing_high, swing_low, levels)


def apply_fibo_fallback(
    side: Optional[str],
    trend: str,
    htf_trend: str
) -> Tuple[Optional[str], bool]:
    """
    应用斐波那契 Fallback 机制
    
    当结构没有给出方向时，根据趋势兜底
    
    Args:
        side: 当前方向（可能为 None）
        trend: 小周期趋势
        htf_trend: 大周期趋势
    
    Returns:
        (方向, 是否使用了 fallback) 元组
    """
    if side:
        return side, False
    
    # 优先使用小周期趋势，其次大周期趋势
    if trend == "bullish":
        return "BUY", True
    elif trend == "bearish":
        return "SELL", True
    else:
        if htf_trend == "bullish":
            return "BUY", True
        elif htf_trend == "bearish":
            return "SELL", True
    
    return None, False
