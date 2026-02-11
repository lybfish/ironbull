"""
趋势判断工具

基于摆动点结构、EMA等判断趋势
"""

from typing import List, Dict, Tuple, Optional
from libs.indicators import ema
from .swing_points import SwingPoint


def detect_trend(
    candles: List[Dict],
    swing_highs: List[SwingPoint],
    swing_lows: List[SwingPoint]
) -> str:
    """
    基于摆动点结构判断趋势
    
    Args:
        candles: K线数据
        swing_highs: 摆动高点列表
        swing_lows: 摆动低点列表
    
    Returns:
        "bullish" / "bearish" / "neutral"
    """
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "neutral"
    
    # 检查最近两个摆动高点
    last_high = swing_highs[-1].price
    prev_high = swing_highs[-2].price if len(swing_highs) >= 2 else last_high
    
    # 检查最近两个摆动低点
    last_low = swing_lows[-1].price
    prev_low = swing_lows[-2].price if len(swing_lows) >= 2 else last_low
    
    # Higher High + Higher Low = 上升趋势
    if last_high > prev_high and last_low > prev_low:
        return "bullish"
    
    # Lower High + Lower Low = 下降趋势
    if last_high < prev_high and last_low < prev_low:
        return "bearish"
    
    return "neutral"


def get_htf_trend(
    candles: List[Dict],
    htf_multiplier: int = 4,
    ema_fast: int = 20,
    ema_slow: int = 50
) -> str:
    """
    使用大周期EMA判断趋势
    
    Args:
        candles: K线数据
        htf_multiplier: 大周期倍数（例如 4 = 1h -> 4h）
        ema_fast: 快EMA周期
        ema_slow: 慢EMA周期
    
    Returns:
        "bullish" / "bearish" / "neutral"
    """
    required = htf_multiplier * ema_slow
    if len(candles) < required:
        return "neutral"
    
    # 性能优化：只取 EMA 需要的最后一段数据来聚合，不处理全量历史
    # EMA(slow) 需要 ema_slow 根 HTF K线 = ema_slow * htf_multiplier 根原始K线
    # 多留 2 倍余量给 EMA 预热
    trim_len = min(len(candles), required * 2)
    trimmed = candles[-trim_len:] if trim_len < len(candles) else candles
    
    # 聚合到大周期
    htf_candles = _aggregate_candles(trimmed, htf_multiplier)
    
    if len(htf_candles) < ema_slow:
        return "neutral"
    
    closes = [c["close"] for c in htf_candles]
    ema_fast_val = ema(closes, ema_fast)
    ema_slow_val = ema(closes, ema_slow)
    
    if ema_fast_val is None or ema_slow_val is None:
        return "neutral"
    
    # 计算EMA差距百分比
    ema_diff_pct = (ema_fast_val - ema_slow_val) / ema_slow_val * 100
    
    # 判断趋势（差距超过0.5%才确认趋势）
    if ema_diff_pct > 0.5:
        return "bullish"
    elif ema_diff_pct < -0.5:
        return "bearish"
    
    return "neutral"


def get_htf_structure_trend(
    candles: List[Dict],
    htf_multiplier: int = 4,
    swing_count: int = 3
) -> str:
    """
    基于大周期 K 线结构（Swing High/Low）判断趋势
    
    核心思想：
    - 聚合出 HTF K线
    - 在 HTF 上识别摆动高低点
    - Higher High + Higher Low = bullish
    - Lower High + Lower Low = bearish
    
    相比 EMA 方式，这种方法更符合 SMC/PA 体系：
    "大周期定方向 → 看 K 线结构，而非看均线金叉死叉"
    
    Args:
        candles: 小周期 K 线数据
        htf_multiplier: 大周期倍数 (如 4 表示 1H→4H)
        swing_count: HTF 摆动点灵敏度 (默认 3，即需要左右各 3 根 HTF K线确认)
    
    Returns:
        "bullish" / "bearish" / "neutral"
    """
    # 至少需要足够的 K 线来生成 HTF 摆动点
    min_htf_bars = (swing_count * 2 + 1) * 3  # 需要至少 3 组完整的摆动结构
    min_candles = min_htf_bars * htf_multiplier
    
    if len(candles) < min_candles:
        return "neutral"
    
    # 聚合到大周期
    htf_candles = _aggregate_candles(candles, htf_multiplier)
    
    if len(htf_candles) < min_htf_bars:
        return "neutral"
    
    # 在 HTF K线上识别摆动点
    htf_swing_highs = []
    htf_swing_lows = []
    
    for i in range(swing_count, len(htf_candles) - swing_count):
        high = htf_candles[i]["high"]
        low = htf_candles[i]["low"]
        
        # 摆动高点: 左右 swing_count 根 K 线的 high 都 <= 当前
        is_high = all(
            high >= htf_candles[j]["high"]
            for j in range(i - swing_count, i + swing_count + 1)
        )
        if is_high:
            htf_swing_highs.append({"index": i, "price": high})
        
        # 摆动低点: 左右 swing_count 根 K 线的 low 都 >= 当前
        is_low = all(
            low <= htf_candles[j]["low"]
            for j in range(i - swing_count, i + swing_count + 1)
        )
        if is_low:
            htf_swing_lows.append({"index": i, "price": low})
    
    if len(htf_swing_highs) < 2 or len(htf_swing_lows) < 2:
        return "neutral"
    
    # 取最近两个摆动高点和低点
    h1 = htf_swing_highs[-2]["price"]
    h2 = htf_swing_highs[-1]["price"]
    l1 = htf_swing_lows[-2]["price"]
    l2 = htf_swing_lows[-1]["price"]
    
    # Higher High + Higher Low = bullish
    if h2 > h1 and l2 > l1:
        return "bullish"
    
    # Lower High + Lower Low = bearish
    if h2 < h1 and l2 < l1:
        return "bearish"
    
    return "neutral"


def _aggregate_candles(candles: List[Dict], multiplier: int) -> List[Dict]:
    """
    将小周期K线聚合为大周期
    
    Args:
        candles: 小周期K线
        multiplier: 聚合倍数
    
    Returns:
        大周期K线列表
    """
    n = multiplier
    total = len(candles)
    if total < n:
        return []
    
    htf_candles = []
    # 直接循环，避免每轮创建 chunk 切片
    for i in range(0, total - n + 1, n):
        hi = candles[i]["high"]
        lo = candles[i]["low"]
        for k in range(i + 1, i + n):
            h = candles[k]["high"]
            l = candles[k]["low"]
            if h > hi:
                hi = h
            if l < lo:
                lo = l
        htf_candles.append({
            "open": candles[i]["open"],
            "high": hi,
            "low": lo,
            "close": candles[i + n - 1]["close"],
        })
    
    return htf_candles
