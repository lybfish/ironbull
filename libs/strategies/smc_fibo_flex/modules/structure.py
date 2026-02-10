"""
结构检测模块

实现 BOS（Break of Structure）和 CHoCH（Change of Character）检测
"""

from typing import List, Dict, Optional
from ..utils.swing_points import SwingPoint


def detect_bos(
    candles: List[Dict],
    swing_highs: List[SwingPoint],
    swing_lows: List[SwingPoint]
) -> Optional[str]:
    """
    检测结构突破（Break of Structure）
    
    Args:
        candles: K线数据
        swing_highs: 摆动高点列表
        swing_lows: 摆动低点列表
    
    Returns:
        "BUY" / "SELL" / None
    """
    if not swing_highs or not swing_lows:
        return None
    
    current = candles[-1]
    last_swing_high = swing_highs[-1]
    last_swing_low = swing_lows[-1]
    
    # 向上突破摆动高点 = BOS BUY
    if current["high"] > last_swing_high.price:
        return "BUY"
    
    # 向下突破摆动低点 = BOS SELL
    if current["low"] < last_swing_low.price:
        return "SELL"
    
    return None


def detect_choch(
    candles: List[Dict],
    swing_highs: List[SwingPoint],
    swing_lows: List[SwingPoint],
    current_trend: str
) -> Optional[str]:
    """
    检测结构反转（Change of Character）
    
    Args:
        candles: K线数据
        swing_highs: 摆动高点列表
        swing_lows: 摆动低点列表
        current_trend: 当前趋势（"bullish" / "bearish" / "neutral"）
    
    Returns:
        "BUY" / "SELL" / None
    """
    if not swing_highs or not swing_lows:
        return None
    
    current = candles[-1]
    last_swing_high = swing_highs[-1]
    last_swing_low = swing_lows[-1]
    
    # 上升趋势中向下突破 = CHoCH SELL
    if current_trend == "bullish" and current["low"] < last_swing_low.price:
        return "SELL"
    
    # 下降趋势中向上突破 = CHoCH BUY
    if current_trend == "bearish" and current["high"] > last_swing_high.price:
        return "BUY"
    
    return None


def filter_by_structure(
    side: Optional[str],
    structure_mode: str,
    bos: Optional[str],
    choch: Optional[str]
) -> Optional[str]:
    """
    根据 structure 参数过滤方向
    
    Args:
        side: 当前方向
        structure_mode: "bos" / "choch" / "both"
        bos: BOS 检测结果
        choch: CHoCH 检测结果
    
    Returns:
        过滤后的方向或 None
    """
    if structure_mode == "bos":
        return bos
    elif structure_mode == "choch":
        return choch
    else:  # "both"
        return bos or choch


def filter_by_bias(
    side: Optional[str],
    bias_mode: str,
    trend: str
) -> Optional[str]:
    """
    根据 bias 参数过滤方向
    
    Args:
        side: 当前方向
        bias_mode: "with_trend" / "counter" / "both"
        trend: 当前趋势（"bullish" / "bearish" / "neutral"）
    
    Returns:
        过滤后的方向或 None
    """
    if not side:
        return None
    
    if bias_mode == "with_trend":
        if trend == "bullish" and side != "BUY":
            return None
        if trend == "bearish" and side != "SELL":
            return None
    elif bias_mode == "counter":
        if trend == "bullish" and side != "SELL":
            return None
        if trend == "bearish" and side != "BUY":
            return None
    # "both" 模式不过滤
    
    return side
