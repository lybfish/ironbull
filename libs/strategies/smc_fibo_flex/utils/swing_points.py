"""
摆动点识别工具

支持 swing 参数和 auto 模式
"""

from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass


@dataclass
class SwingPoint:
    """摆动点"""
    index: int
    price: float
    type: str  # "high" or "low"
    timestamp: Optional[int] = None


def _calculate_auto_swing(candles: List[Dict], lookback: int = 100) -> int:
    """
    根据市场波动率自动计算 swing 值
    
    Args:
        candles: K线数据
        lookback: 回看周期
    
    Returns:
        推荐的 swing 值
    """
    if len(candles) < 10:
        return 3
    
    sample = candles[-min(lookback, len(candles)):]
    avg_pct = sum(((c["high"] - c["low"]) / max(1e-8, c["close"])) for c in sample) / max(1, len(sample)) * 100.0
    
    if avg_pct < 0.15:
        return 2
    elif avg_pct < 0.3:
        return 3
    elif avg_pct < 0.6:
        return 4
    elif avg_pct < 1.0:
        return 5
    else:
        return 6


def find_swing_points(
    candles: List[Dict],
    swing: Union[int, str] = 3,
    realtime_mode: bool = False
) -> Tuple[List[SwingPoint], List[SwingPoint]]:
    """
    识别摆动高低点
    
    Args:
        candles: K线数据
        swing: 摆动点灵敏度（整数或 "auto"）
        realtime_mode: 是否为实时模式（实时模式下只检查左侧）
    
    Returns:
        (swing_highs, swing_lows) 元组
    """
    if len(candles) < 2:
        return [], []
    
    # 处理 auto 模式
    if swing == "auto" or (isinstance(swing, str) and swing.lower() == "auto"):
        swing_value = _calculate_auto_swing(candles)
    else:
        swing_value = max(1, int(swing))
    
    swing_highs = []
    swing_lows = []
    
    if realtime_mode:
        # 实时模式：只检查左侧
        for i in range(swing_value, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            
            # 检查是否是摆动高点
            is_swing_high = all(high >= candles[j]["high"] for j in range(i - swing_value, i + 1))
            if is_swing_high:
                swing_highs.append(SwingPoint(
                    index=i,
                    price=high,
                    type="high",
                    timestamp=candles[i].get("timestamp") or candles[i].get("time")
                ))
            
            # 检查是否是摆动低点
            is_swing_low = all(low <= candles[j]["low"] for j in range(i - swing_value, i + 1))
            if is_swing_low:
                swing_lows.append(SwingPoint(
                    index=i,
                    price=low,
                    type="low",
                    timestamp=candles[i].get("timestamp") or candles[i].get("time")
                ))
    else:
        # 回测模式：检查左右两侧
        for i in range(swing_value, len(candles) - swing_value):
            high = candles[i]["high"]
            low = candles[i]["low"]
            
            # 检查是否是摆动高点
            is_swing_high = all(high >= candles[j]["high"] for j in range(i - swing_value, i + swing_value + 1))
            if is_swing_high:
                swing_highs.append(SwingPoint(
                    index=i,
                    price=high,
                    type="high",
                    timestamp=candles[i].get("timestamp") or candles[i].get("time")
                ))
            
            # 检查是否是摆动低点
            is_swing_low = all(low <= candles[j]["low"] for j in range(i - swing_value, i + swing_value + 1))
            if is_swing_low:
                swing_lows.append(SwingPoint(
                    index=i,
                    price=low,
                    type="low",
                    timestamp=candles[i].get("timestamp") or candles[i].get("time")
                ))
    
    return swing_highs, swing_lows
