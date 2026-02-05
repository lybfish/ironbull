"""
RSI Indicator

相对强弱指数。
"""

from typing import List, Optional


def rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    计算 RSI 指标（最新值）
    
    Args:
        prices: 价格列表（按时间正序）
        period: 周期，默认 14
    
    Returns:
        RSI 值 (0-100)，数据不足返回 None
    """
    if len(prices) < period + 1:
        return None
    
    # 计算价格变化
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    
    # 分离涨跌
    gains = [max(0, c) for c in changes]
    losses = [max(0, -c) for c in changes]
    
    # 计算平均涨跌（使用最近 period 个）
    recent_gains = gains[-period:]
    recent_losses = losses[-period:]
    
    avg_gain = sum(recent_gains) / period
    avg_loss = sum(recent_losses) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi_val = 100 - (100 / (1 + rs))
    
    return rsi_val


def rsi_series(prices: List[float], period: int = 14) -> List[Optional[float]]:
    """
    计算 RSI 序列
    
    Args:
        prices: 价格列表
        period: 周期，默认 14
    
    Returns:
        RSI 序列，前 period 个为 None
    """
    if len(prices) < period + 1:
        return [None] * len(prices)
    
    result: List[Optional[float]] = [None] * period
    
    # 计算价格变化
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    
    # 分离涨跌
    gains = [max(0, c) for c in changes]
    losses = [max(0, -c) for c in changes]
    
    # 初始平均
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # 第一个 RSI
    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100 - (100 / (1 + rs)))
    
    # 递推计算（Wilder's smoothing）
    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - (100 / (1 + rs)))
    
    return result
