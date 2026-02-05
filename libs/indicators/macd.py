"""
MACD Indicator

移动平均收敛散度。
"""

from typing import List, Optional, Dict
from .ma import ema_series


def macd(
    prices: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Optional[Dict[str, float]]:
    """
    计算 MACD 指标（最新值）
    
    Args:
        prices: 价格列表（按时间正序）
        fast: 快线周期，默认 12
        slow: 慢线周期，默认 26
        signal: 信号线周期，默认 9
    
    Returns:
        {
            'macd': MACD 线值,
            'signal': 信号线值,
            'histogram': 柱状图值
        }
        数据不足返回 None
    """
    if len(prices) < slow:
        return None
    
    # 计算快慢 EMA 序列
    ema_fast = ema_series(prices, fast)
    ema_slow = ema_series(prices, slow)
    
    # 计算 MACD 线
    macd_line: List[Optional[float]] = []
    for i in range(len(prices)):
        if ema_fast[i] is None or ema_slow[i] is None:
            macd_line.append(None)
        else:
            macd_line.append(ema_fast[i] - ema_slow[i])
    
    # 过滤有效值计算信号线
    valid_macd = [v for v in macd_line if v is not None]
    if len(valid_macd) < signal:
        return None
    
    # 计算信号线（MACD 的 EMA）
    signal_series = ema_series(valid_macd, signal)
    
    macd_val = valid_macd[-1]
    signal_val = signal_series[-1]
    
    if signal_val is None:
        return None
    
    histogram = macd_val - signal_val
    
    return {
        'macd': macd_val,
        'signal': signal_val,
        'histogram': histogram
    }
