"""
Volume Indicators

成交量相关指标。
"""

from typing import List, Optional, Dict


def obv(
    closes: List[float],
    volumes: List[float]
) -> Optional[float]:
    """
    计算 OBV（On-Balance Volume）最新值
    
    Args:
        closes: 收盘价列表
        volumes: 成交量列表
    
    Returns:
        OBV 值，数据不足返回 None
    """
    if len(closes) < 2 or len(volumes) < 2:
        return None
    
    if len(closes) != len(volumes):
        return None
    
    obv_val = 0.0
    
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv_val += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv_val -= volumes[i]
        # 价格不变则 OBV 不变
    
    return obv_val


def obv_series(
    closes: List[float],
    volumes: List[float]
) -> List[Optional[float]]:
    """
    计算 OBV 序列
    
    Args:
        closes: 收盘价列表
        volumes: 成交量列表
    
    Returns:
        OBV 序列
    """
    if len(closes) < 2 or len(volumes) < 2:
        return [None] * len(closes)
    
    if len(closes) != len(volumes):
        return [None] * len(closes)
    
    result: List[Optional[float]] = [0.0]  # 第一个 OBV = 0
    obv_val = 0.0
    
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv_val += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv_val -= volumes[i]
        result.append(obv_val)
    
    return result


def vwap(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[float]
) -> Optional[float]:
    """
    计算 VWAP（Volume Weighted Average Price）
    
    Args:
        highs: 最高价列表
        lows: 最低价列表
        closes: 收盘价列表
        volumes: 成交量列表
    
    Returns:
        VWAP 值，数据不足返回 None
    """
    n = len(closes)
    if n == 0 or len(highs) != n or len(lows) != n or len(volumes) != n:
        return None
    
    total_volume = sum(volumes)
    if total_volume == 0:
        return None
    
    # 典型价格 = (H + L + C) / 3
    cumulative_tp_vol = 0.0
    for i in range(n):
        typical_price = (highs[i] + lows[i] + closes[i]) / 3
        cumulative_tp_vol += typical_price * volumes[i]
    
    return cumulative_tp_vol / total_volume


def volume_ma(
    volumes: List[float],
    period: int = 20
) -> Optional[float]:
    """
    计算成交量移动平均
    
    Args:
        volumes: 成交量列表
        period: 周期，默认 20
    
    Returns:
        成交量 MA，数据不足返回 None
    """
    if len(volumes) < period:
        return None
    return sum(volumes[-period:]) / period


def volume_ratio(
    volumes: List[float],
    period: int = 20
) -> Optional[float]:
    """
    计算量比（当前成交量 / 平均成交量）
    
    Args:
        volumes: 成交量列表
        period: 周期，默认 20
    
    Returns:
        量比，数据不足返回 None
    """
    if len(volumes) < period:
        return None
    
    avg_vol = sum(volumes[-period - 1:-1]) / period
    if avg_vol == 0:
        return None
    
    return volumes[-1] / avg_vol
