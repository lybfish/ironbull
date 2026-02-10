"""
AMD 理论模块

实现 AMD 阶段识别（Accumulation/Manipulation/Distribution）
"""

from typing import List, Dict, Optional, Tuple


def detect_amd_phase(
    candles: List[Dict],
    lookback: int = 20
) -> str:
    """
    检测当前AMD阶段
    
    Args:
        candles: K线数据
        lookback: 回看周期
    
    Returns:
        "accumulation" / "manipulation" / "distribution" / "unknown"
    """
    if len(candles) < lookback:
        return "unknown"
    
    sample = candles[-lookback:]
    
    # 计算价格区间和成交量
    highs = [c["high"] for c in sample]
    lows = [c["low"] for c in sample]
    closes = [c["close"] for c in sample]
    volumes = [c.get("volume", 0) for c in sample]
    
    price_range = max(highs) - min(lows)
    avg_volume = sum(volumes) / len(volumes) if volumes else 0
    
    # 简单规则：根据价格波动和成交量判断
    # Accumulation: 低波动，成交量逐渐增加
    # Manipulation: 突然波动（假突破）
    # Distribution: 高波动，成交量减少
    
    volatility = price_range / max(1e-8, sum(closes) / len(closes))
    volume_trend = (volumes[-1] - volumes[0]) / max(1e-8, volumes[0]) if volumes[0] > 0 else 0
    
    if volatility < 0.02 and volume_trend > 0.1:
        return "accumulation"
    elif volatility > 0.05:
        return "manipulation"
    elif volatility > 0.03 and volume_trend < -0.1:
        return "distribution"
    
    return "unknown"


def check_amd_entry(
    amd_entry_mode: str,
    amd_phase_filter: List[str],
    current_phase: str
) -> bool:
    """
    检查是否允许在当前AMD阶段入场
    
    Args:
        amd_entry_mode: AMD入场模式 "off" / "basic" / "advanced"
        amd_phase_filter: 允许的AMD阶段列表
        current_phase: 当前AMD阶段
    
    Returns:
        是否允许入场
    """
    if amd_entry_mode == "off":
        return True
    
    if not amd_phase_filter:
        return True
    
    return current_phase in amd_phase_filter
