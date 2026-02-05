"""
Moving Average Indicators

简单移动平均线（SMA）和指数移动平均线（EMA）。
"""

from typing import List, Optional


def sma(prices: List[float], period: int) -> Optional[float]:
    """
    计算简单移动平均线（最新值）
    
    Args:
        prices: 价格列表（按时间正序）
        period: 周期
    
    Returns:
        SMA 值，数据不足返回 None
    """
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def sma_series(prices: List[float], period: int) -> List[Optional[float]]:
    """
    计算简单移动平均线序列
    
    Args:
        prices: 价格列表
        period: 周期
    
    Returns:
        SMA 序列，前 period-1 个为 None
    """
    result: List[Optional[float]] = []
    for i in range(len(prices)):
        if i < period - 1:
            result.append(None)
        else:
            window = prices[i - period + 1 : i + 1]
            result.append(sum(window) / period)
    return result


def ema(prices: List[float], period: int) -> Optional[float]:
    """
    计算指数移动平均线（最新值）
    
    Args:
        prices: 价格列表
        period: 周期
    
    Returns:
        EMA 值，数据不足返回 None
    """
    if len(prices) < period:
        return None
    
    multiplier = 2 / (period + 1)
    
    # 初始 EMA = 前 period 个的 SMA
    ema_val = sum(prices[:period]) / period
    
    # 递推计算
    for price in prices[period:]:
        ema_val = (price - ema_val) * multiplier + ema_val
    
    return ema_val


def ema_series(prices: List[float], period: int) -> List[Optional[float]]:
    """
    计算指数移动平均线序列
    
    Args:
        prices: 价格列表
        period: 周期
    
    Returns:
        EMA 序列，前 period-1 个为 None
    """
    if len(prices) < period:
        return [None] * len(prices)
    
    result: List[Optional[float]] = [None] * (period - 1)
    
    multiplier = 2 / (period + 1)
    
    # 初始 EMA = 前 period 个的 SMA
    ema_val = sum(prices[:period]) / period
    result.append(ema_val)
    
    # 递推计算
    for price in prices[period:]:
        ema_val = (price - ema_val) * multiplier + ema_val
        result.append(ema_val)
    
    return result
