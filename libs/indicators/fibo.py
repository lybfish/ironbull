"""
Fibonacci Retracement

斐波那契回撤位计算。
"""

from typing import List, Optional, Dict, Tuple


# 默认斐波那契比例
DEFAULT_FIBO_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786]


def fibo_levels(
    swing_high: float,
    swing_low: float,
    levels: Optional[List[float]] = None
) -> Dict[float, float]:
    """
    计算斐波那契回撤位
    
    Args:
        swing_high: Swing 高点
        swing_low: Swing 低点
        levels: 斐波那契比例列表，默认 [0.236, 0.382, 0.5, 0.618, 0.786]
    
    Returns:
        {比例: 价格} 字典，如 {0.382: 1850.5, 0.5: 1825.0, ...}
    """
    if levels is None:
        levels = DEFAULT_FIBO_LEVELS
    
    swing_range = swing_high - swing_low
    
    result: Dict[float, float] = {}
    for level in levels:
        # 从高点回撤
        result[level] = swing_high - (swing_range * level)
    
    return result


def price_in_fibo_zone(
    price: float,
    fibo_dict: Dict[float, float],
    tolerance_pct: float = 0.002
) -> Optional[Tuple[float, float]]:
    """
    检查价格是否在某个斐波那契位附近
    
    Args:
        price: 当前价格
        fibo_dict: 斐波那契位字典 {比例: 价格}
        tolerance_pct: 容差百分比，默认 0.2%
    
    Returns:
        (比例, 目标价格) 元组，不在任何区域返回 None
    """
    for level, level_price in sorted(fibo_dict.items(), reverse=True):
        if level_price == 0:
            continue
        distance_pct = abs(price - level_price) / level_price
        if distance_pct <= tolerance_pct:
            return (level, level_price)
    
    return None


def fibo_extension(
    swing_high: float,
    swing_low: float,
    levels: Optional[List[float]] = None
) -> Dict[float, float]:
    """
    计算斐波那契扩展位
    
    Args:
        swing_high: Swing 高点
        swing_low: Swing 低点
        levels: 扩展比例列表，默认 [1.0, 1.272, 1.618, 2.0, 2.618]
    
    Returns:
        {比例: 价格} 字典
    """
    if levels is None:
        levels = [1.0, 1.272, 1.618, 2.0, 2.618]
    
    swing_range = swing_high - swing_low
    
    result: Dict[float, float] = {}
    for level in levels:
        # 从低点向上扩展
        result[level] = swing_low + (swing_range * level)
    
    return result
