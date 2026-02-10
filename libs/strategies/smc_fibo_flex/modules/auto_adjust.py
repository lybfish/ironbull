"""
自适应参数调整模块

实现 Auto Profile、波动率自适应、自动RR调整等
"""

from typing import Dict, List, Optional
from libs.indicators import atr


def calculate_volatility(candles: List[Dict], lookback: int = 100) -> float:
    """
    计算市场波动率（平均百分比波动）
    
    Args:
        candles: K线数据
        lookback: 回看周期
    
    Returns:
        平均波动率（百分比，如 0.5 表示 0.5%）
    """
    if len(candles) < 10:
        return 0.5
    
    sample = candles[-min(lookback, len(candles)):]
    avg_pct = sum(((c["high"] - c["low"]) / max(1e-8, c["close"])) for c in sample) / max(1, len(sample)) * 100.0
    
    return avg_pct


def apply_auto_profile(
    config: Dict,
    candles: List[Dict]
) -> Dict:
    """
    应用 Auto Profile 逻辑
    
    Args:
        config: 配置字典
        candles: K线数据
    
    Returns:
        调整后的配置字典
    """
    auto_profile = config.get("auto_profile", "medium")
    if auto_profile not in ("conservative", "medium", "aggressive"):
        return config
    
    volatility = calculate_volatility(candles)
    adjusted_config = config.copy()
    
    if auto_profile == "conservative":
        # 保守模式：根据波动率调整参数
        if volatility < 0.25:
            adjusted_config["swing"] = 2
            adjusted_config["min_rr"] = 2.0
            adjusted_config["retest_bars"] = 32
        elif volatility < 0.5:
            adjusted_config["swing"] = 3
            adjusted_config["min_rr"] = 2.5
            adjusted_config["retest_bars"] = 24
        elif volatility < 0.9:
            adjusted_config["swing"] = 4
            adjusted_config["min_rr"] = 3.0
            adjusted_config["retest_bars"] = 16
        else:
            adjusted_config["swing"] = 5
            adjusted_config["min_rr"] = 3.5
            adjusted_config["retest_bars"] = 10
    
    elif auto_profile == "aggressive":
        # 激进模式
        if volatility < 0.2:
            adjusted_config["swing"] = 2
            adjusted_config["min_rr"] = 1.2
            adjusted_config["retest_bars"] = 20
        elif volatility < 0.4:
            adjusted_config["swing"] = 3
            adjusted_config["min_rr"] = 1.6
            adjusted_config["retest_bars"] = 14
        elif volatility < 0.8:
            adjusted_config["swing"] = 4
            adjusted_config["min_rr"] = 2.0
            adjusted_config["retest_bars"] = 10
        else:
            adjusted_config["swing"] = 5
            adjusted_config["min_rr"] = 2.5
            adjusted_config["retest_bars"] = 6
    
    else:  # medium
        # 中等模式
        if volatility < 0.15:
            adjusted_config["swing"] = 2
            adjusted_config["min_rr"] = 1.5
            adjusted_config["retest_bars"] = 28
        elif volatility < 0.3:
            adjusted_config["swing"] = 3
            adjusted_config["min_rr"] = 2.0
            adjusted_config["retest_bars"] = 20
        elif volatility < 0.6:
            adjusted_config["swing"] = 4
            adjusted_config["min_rr"] = 2.5
            adjusted_config["retest_bars"] = 12
        else:
            adjusted_config["swing"] = 5
            adjusted_config["min_rr"] = 3.0
            adjusted_config["retest_bars"] = 8
    
    return adjusted_config


def auto_adjust_rr(
    config: Dict,
    candles: List[Dict],
    base_min_rr: float
) -> float:
    """
    根据波动率自动调整 min_rr
    
    Args:
        config: 配置字典
        candles: K线数据
        base_min_rr: 基础最小RR
    
    Returns:
        调整后的 min_rr
    """
    if not config.get("rr_auto_adjust", False):
        return base_min_rr
    
    volatility = calculate_volatility(candles)
    
    # 波动率越高，要求的RR越高
    if volatility < 0.2:
        return base_min_rr * 0.8
    elif volatility < 0.5:
        return base_min_rr
    elif volatility < 1.0:
        return base_min_rr * 1.2
    else:
        return base_min_rr * 1.5


def auto_adjust_sl_buffer(
    config: Dict,
    candles: List[Dict],
    base_sl_buffer_pct: float
) -> float:
    """
    根据波动率自动调整止损缓冲
    
    Args:
        config: 配置字典
        candles: K线数据
        base_sl_buffer_pct: 基础止损缓冲百分比
    
    Returns:
        调整后的止损缓冲百分比
    """
    if not config.get("sl_buffer_auto_adjust", False):
        return base_sl_buffer_pct
    
    volatility = calculate_volatility(candles)
    atr_val = atr(candles, period=config.get("atr_period", 14))
    
    if atr_val is None:
        return base_sl_buffer_pct
    
    # 根据ATR调整止损缓冲
    current_price = candles[-1]["close"]
    atr_pct = atr_val / current_price
    
    # ATR越大，止损缓冲越大
    if atr_pct < 0.01:
        return base_sl_buffer_pct * 0.8
    elif atr_pct < 0.02:
        return base_sl_buffer_pct
    elif atr_pct < 0.05:
        return base_sl_buffer_pct * 1.2
    else:
        return base_sl_buffer_pct * 1.5
