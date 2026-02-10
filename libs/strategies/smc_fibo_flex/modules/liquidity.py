"""
流动性检测模块

实现内外流动性识别、流动性扫除检测、假突破检测等
"""

from typing import List, Dict, Optional, Tuple
from ..utils.swing_points import SwingPoint


def detect_liquidity_sweep(
    candles: List[Dict],
    swing_highs: List[SwingPoint],
    swing_lows: List[SwingPoint],
    side: str,
    sweep_len: int = 5,
    allow_internal: bool = True,
    allow_external: bool = True,
    htf_swing_highs: Optional[List] = None,
    htf_swing_lows: Optional[List] = None
) -> Optional[Dict]:
    """
    检测流动性扫除（Liquidity Sweep）
    
    Args:
        candles: K线数据
        swing_highs: 摆动高点列表
        swing_lows: 摆动低点列表
        side: "BUY" / "SELL"
        sweep_len: 扫流动性时参考的swing长度
        allow_internal: 是否允许内部流动性
        allow_external: 是否允许外部流动性
        htf_swing_highs: HTF摆动高点（外部流动性）
        htf_swing_lows: HTF摆动低点（外部流动性）
    
    Returns:
        流动性扫除信息字典或 None
    """
    if not candles:
        return None
    
    current = candles[-1]
    
    # 内部流动性扫除
    if allow_internal:
        if side == "BUY" and swing_lows:
            # 做多：扫低点后反转
            recent_low = swing_lows[-1]
            if current["low"] < recent_low.price and current["close"] > recent_low.price:
                # 检查是否在sweep_len范围内
                if len(candles) - recent_low.index <= sweep_len:
                    return {
                        "type": "internal",
                        "price": current["low"],
                        "swing_price": recent_low.price,
                        "index": len(candles) - 1,
                    }
        
        elif side == "SELL" and swing_highs:
            # 做空：扫高点后反转
            recent_high = swing_highs[-1]
            if current["high"] > recent_high.price and current["close"] < recent_high.price:
                if len(candles) - recent_high.index <= sweep_len:
                    return {
                        "type": "internal",
                        "price": current["high"],
                        "swing_price": recent_high.price,
                        "index": len(candles) - 1,
                    }
    
    # 外部流动性扫除
    if allow_external and htf_swing_highs and htf_swing_lows:
        if side == "BUY" and htf_swing_lows:
            last_htf_low = htf_swing_lows[-1]
            if current["low"] < last_htf_low.get("price", 0) and current["close"] > last_htf_low.get("price", 0):
                return {
                    "type": "external",
                    "price": current["low"],
                    "swing_price": last_htf_low.get("price", 0),
                    "index": len(candles) - 1,
                }
        
        elif side == "SELL" and htf_swing_highs:
            last_htf_high = htf_swing_highs[-1]
            if current["high"] > last_htf_high.get("price", 0) and current["close"] < last_htf_high.get("price", 0):
                return {
                    "type": "external",
                    "price": current["high"],
                    "swing_price": last_htf_high.get("price", 0),
                    "index": len(candles) - 1,
                }
    
    return None


def detect_fake_break(
    candles: List[Dict],
    swing_highs: List[SwingPoint],
    swing_lows: List[SwingPoint],
    fake_break_min_ratio: float = 0.3,
    fake_break_max_bars: int = 5
) -> Optional[Dict]:
    """
    检测假突破
    
    Args:
        candles: K线数据
        swing_highs: 摆动高点列表
        swing_lows: 摆动低点列表
        fake_break_min_ratio: 假突破最小超出比例
        fake_break_max_bars: 假突破后允许在多少根K线内迅速收回
    
    Returns:
        假突破信息字典或 None
    """
    if not swing_highs or not swing_lows:
        return None
    
    if len(candles) < fake_break_max_bars + 1:
        return None
    
    last_high = swing_highs[-1]
    last_low = swing_lows[-1]
    range_price = last_high.price - last_low.price
    
    # 检查向上假突破
    for i in range(max(0, len(candles) - fake_break_max_bars - 1), len(candles) - 1):
        c = candles[i]
        if c["high"] > last_high.price:
            # 超出比例
            break_ratio = (c["high"] - last_high.price) / max(1e-8, range_price)
            if break_ratio >= fake_break_min_ratio:
                # 检查后续是否迅速收回
                for j in range(i + 1, min(i + fake_break_max_bars + 1, len(candles))):
                    if candles[j]["close"] < last_high.price:
                        return {
                            "type": "fake_break_up",
                            "break_price": c["high"],
                            "recover_price": candles[j]["close"],
                            "break_index": i,
                            "recover_index": j,
                        }
    
    # 检查向下假突破
    for i in range(max(0, len(candles) - fake_break_max_bars - 1), len(candles) - 1):
        c = candles[i]
        if c["low"] < last_low.price:
            break_ratio = (last_low.price - c["low"]) / max(1e-8, range_price)
            if break_ratio >= fake_break_min_ratio:
                for j in range(i + 1, min(i + fake_break_max_bars + 1, len(candles))):
                    if candles[j]["close"] > last_low.price:
                        return {
                            "type": "fake_break_down",
                            "break_price": c["low"],
                            "recover_price": candles[j]["close"],
                            "break_index": i,
                            "recover_index": j,
                        }
    
    return None
