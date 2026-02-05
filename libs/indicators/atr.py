"""
ATR Indicator

平均真实波幅（Average True Range）。
"""

from typing import List, Optional, Dict


def true_range(
    high: float,
    low: float,
    prev_close: float
) -> float:
    """
    计算真实波幅（True Range）
    
    Args:
        high: 当前最高价
        low: 当前最低价
        prev_close: 前一根 K 线收盘价
    
    Returns:
        真实波幅值
    """
    return max(
        high - low,
        abs(high - prev_close),
        abs(low - prev_close)
    )


def atr(
    candles: List[Dict],
    period: int = 14,
    min_pct: float = 0.01
) -> float:
    """
    计算 ATR 指标（带最小值保护）
    
    Args:
        candles: K线数据列表，每个元素需包含 high/low/close
        period: 周期，默认 14
        min_pct: 最小值百分比（相对于当前价格），默认 1%
    
    Returns:
        ATR 值，数据不足时返回当前价格的 min_pct
    """
    if not candles:
        return 0.0
    
    current_price = candles[-1].get('close', 0)
    default_atr = current_price * min_pct
    
    if len(candles) < period + 1:
        return default_atr
    
    # 计算所有 TR
    trs: List[float] = []
    for i in range(1, len(candles)):
        high = candles[i].get('high', 0)
        low = candles[i].get('low', 0)
        prev_close = candles[i - 1].get('close', 0)
        tr = true_range(high, low, prev_close)
        trs.append(tr)
    
    # 取最近 period 个 TR 的平均
    recent_trs = trs[-period:]
    if not recent_trs:
        return default_atr
    
    atr_val = sum(recent_trs) / len(recent_trs)
    
    # 确保 ATR 不小于最小值
    return max(atr_val, default_atr)
