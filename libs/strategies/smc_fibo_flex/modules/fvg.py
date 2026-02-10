"""
FVG (Fair Value Gap) 检测模块

实现 FVG 识别、有效性管理、回填检测等
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class FVG:
    """公平价差（Fair Value Gap）"""
    index: int
    type: str  # "bullish" / "bearish"
    high: float
    low: float
    timestamp: Optional[int] = None
    filled: bool = False  # 是否已回填


def find_fvgs(
    candles: List[Dict],
    fvg_min_pct: float = 0.15,
    lookback: int = 50
) -> List[FVG]:
    """
    识别 FVG
    
    Args:
        candles: K线数据
        fvg_min_pct: 最小缺口百分比（小数，如 0.15 = 15%）
        lookback: 回看范围
    
    Returns:
        FVG 列表
    """
    fvgs = []
    
    if len(candles) < 3:
        return fvgs
    
    lookback_start = max(0, len(candles) - lookback - 2)
    
    for i in range(lookback_start + 2, len(candles)):
        c0 = candles[i - 2]
        c1 = candles[i - 1]
        c2 = candles[i]
        
        # 看涨 FVG：中间K线被跳过，形成向上缺口
        gap_up = c2["low"] - c0["high"]
        if gap_up > 0:
            gap_pct = gap_up / c2["close"]
            if gap_pct >= fvg_min_pct:
                fvgs.append(FVG(
                    index=i - 1,
                    type="bullish",
                    high=c2["low"],
                    low=c0["high"],
                    timestamp=c1.get("timestamp") or c1.get("time"),
                ))
        
        # 看跌 FVG：中间K线被跳过，形成向下缺口
        gap_down = c0["low"] - c2["high"]
        if gap_down > 0:
            gap_pct = gap_down / c2["close"]
            if gap_pct >= fvg_min_pct:
                fvgs.append(FVG(
                    index=i - 1,
                    type="bearish",
                    high=c0["low"],
                    low=c2["high"],
                    timestamp=c1.get("timestamp") or c1.get("time"),
                ))
    
    return fvgs


def check_fvg_fill(
    fvg: FVG,
    candles: List[Dict],
    fvg_fill_mode: str = "touch",
    start_index: int = 0
) -> bool:
    """
    检查 FVG 是否已回填
    
    Args:
        fvg: FVG 对象
        candles: K线数据
        fvg_fill_mode: 回填模式 "touch" / "full" / "partial"
        start_index: 开始检查的索引
    
    Returns:
        是否已回填
    """
    if fvg.filled:
        return True
    
    for i in range(start_index, len(candles)):
        c = candles[i]
        
        if fvg_fill_mode == "touch":
            # 只要价格触及FVG区域即认为回填
            if fvg.low <= c["low"] <= fvg.high or fvg.low <= c["high"] <= fvg.high:
                return True
        elif fvg_fill_mode == "full":
            # 价格完全穿过FVG区域
            if c["low"] <= fvg.low and c["high"] >= fvg.high:
                return True
        elif fvg_fill_mode == "partial":
            # 价格部分回填（超过50%）
            overlap = min(c["high"], fvg.high) - max(c["low"], fvg.low)
            fvg_range = fvg.high - fvg.low
            if overlap > 0 and overlap / fvg_range >= 0.5:
                return True
    
    return False


def find_nearest_fvg(
    fvgs: List[FVG],
    side: str,
    price: float,
    fvg_valid_bars: int = 50,
    current_index: int = 0
) -> Optional[Dict]:
    """
    找到最近的可用 FVG
    
    Args:
        fvgs: FVG 列表
        side: "BUY" / "SELL"
        price: 当前价格
        fvg_valid_bars: 最大有效K线数
        current_index: 当前K线索引
    
    Returns:
        FVG 字典或 None
    """
    target_type = "bullish" if side == "BUY" else "bearish"
    
    candidates = []
    for fvg in fvgs:
        if fvg.type != target_type:
            continue
        
        # 检查是否过期
        if current_index - fvg.index > fvg_valid_bars:
            continue
        
        # 检查是否已回填
        if fvg.filled:
            continue
        
        # 检查价格是否在FVG范围内或附近
        if fvg.low <= price <= fvg.high:
            candidates.append(fvg)
    
    if not candidates:
        return None
    
    # 返回最近的FVG
    nearest = min(candidates, key=lambda fvg: abs(price - (fvg.high + fvg.low) / 2))
    
    return {
        "high": nearest.high,
        "low": nearest.low,
        "index": nearest.index,
    }
