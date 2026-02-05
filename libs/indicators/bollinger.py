"""
Bollinger Bands Indicator

布林带指标。
"""

from typing import List, Optional, Dict
import math


def bollinger(
    prices: List[float],
    period: int = 20,
    std_dev: float = 2.0
) -> Optional[Dict[str, float]]:
    """
    计算布林带指标（最新值）
    
    Args:
        prices: 价格列表（按时间正序）
        period: 周期，默认 20
        std_dev: 标准差倍数，默认 2.0
    
    Returns:
        {
            'middle': 中轨（SMA）,
            'upper': 上轨,
            'lower': 下轨,
            'bandwidth': 带宽百分比,
            'percent_b': %B 值
        }
        数据不足返回 None
    """
    if len(prices) < period:
        return None
    
    # 取最近 period 个价格
    window = prices[-period:]
    
    # 中轨 = SMA
    middle = sum(window) / period
    
    # 标准差
    variance = sum((p - middle) ** 2 for p in window) / period
    std = math.sqrt(variance)
    
    # 上下轨
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    # 带宽百分比
    bandwidth = ((upper - lower) / middle) * 100 if middle != 0 else 0
    
    # %B = (价格 - 下轨) / (上轨 - 下轨)
    current_price = prices[-1]
    band_range = upper - lower
    percent_b = (current_price - lower) / band_range if band_range != 0 else 0.5
    
    return {
        'middle': middle,
        'upper': upper,
        'lower': lower,
        'bandwidth': bandwidth,
        'percent_b': percent_b
    }
