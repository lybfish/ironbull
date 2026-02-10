"""
回踩确认形态模块

实现所有回踩确认形态：Pin Bar、吞没、晨星、暮星、金K、Inside Bar、Wick Rejection等
支持形态权重和综合评分
"""

from typing import Dict, List, Optional, Tuple


def detect_rejection(
    candle: Dict,
    prev: Optional[Dict],
    prev2: Optional[Dict],
    side: str,
    zone_low: float,
    zone_high: float,
    config: Dict
) -> Dict:
    """
    检测回踩拒绝K线形态
    
    Args:
        candle: 当前K线
        prev: 前一根K线
        prev2: 前两根K线
        side: 交易方向 "BUY" / "SELL"
        zone_low: 回踩区间下沿
        zone_high: 回踩区间上沿
        config: 配置字典（包含所有形态开关和参数）
    
    Returns:
        包含所有形态检测结果的字典，以及综合评分
    """
    o = candle["open"]
    c = candle["close"]
    h = candle["high"]
    l = candle["low"]
    body = max(1e-8, abs(c - o))
    upper = h - max(o, c)
    lower = min(o, c) - l
    range_candle = h - l
    
    results = {
        "close_reject": False,
        "pinbar": False,
        "engulf": False,
        "morning_star": False,
        "evening_star": False,
        "golden_k": False,
        "inside_bar": False,
        "wick_reject": False,
        "fakey": False,
        "tweezer": False,
        "hammer": False,
        "shooting_star": False,
        "harami": False,
        "belt_hold": False,
    }
    
    # 1. Close Reject：收盘价拒绝区间
    if config.get("enable_close_reject", True):
        if side == "BUY":
            results["close_reject"] = c > zone_high and c > o
        else:
            results["close_reject"] = c < zone_low and c < o
    
    # 2. Pin Bar
    if config.get("enable_pinbar", True):
        pinbar_ratio = config.get("pinbar_ratio", 1.5)
        if side == "BUY":
            results["pinbar"] = lower >= pinbar_ratio * body and lower >= upper * 1.2
        else:
            results["pinbar"] = upper >= pinbar_ratio * body and upper >= lower * 1.2
    
    # 3. Engulfing（吞没形态）
    if config.get("enable_engulfing", True) and prev:
        po, pc = prev["open"], prev["close"]
        if side == "BUY":
            results["engulf"] = c > o and pc < po and c >= po and o <= pc
        else:
            results["engulf"] = c < o and pc > po and o >= pc and c <= po
    
    # 4. Morning Star / Evening Star
    if (config.get("enable_morning_star", True) or config.get("enable_evening_star", True)) and prev and prev2:
        c1o, c1c = prev2["open"], prev2["close"]
        c2o, c2c = prev["open"], prev["close"]
        body1 = abs(c1c - c1o)
        body2 = abs(c2c - c2o)
        
        if side == "BUY" and config.get("enable_morning_star", True):
            if c1c < c1o and body1 > 0 and body2 < body1 * 0.5:
                if c > o and body > 0 and c >= (c1o + c1c) / 2.0:
                    results["morning_star"] = True
        elif side == "SELL" and config.get("enable_evening_star", True):
            if c1c > c1o and body1 > 0 and body2 < body1 * 0.5:
                if c < o and body > 0 and c <= (c1o + c1c) / 2.0:
                    results["evening_star"] = True
    
    # 5. 金K（Golden K）
    if config.get("enable_golden_k", False) and side == "BUY":
        # 关键支撑位上出现长下影金K，实体收在区间上半部分
        lower_ratio = lower / max(1e-8, range_candle)
        body_in_upper_half = (c + o) / 2.0 > (zone_low + zone_high) / 2.0
        results["golden_k"] = lower_ratio >= 0.4 and body_in_upper_half and c > o
    
    # 6. Inside Bar
    if config.get("enable_inside_bar", False) and prev:
        prev_h, prev_l = prev["high"], prev["low"]
        results["inside_bar"] = h < prev_h and l > prev_l
    
    # 7. Wick Rejection
    if config.get("enable_wick_reject", False):
        wick_min_ratio = config.get("wick_min_ratio", 1.5)
        if side == "BUY":
            results["wick_reject"] = lower >= wick_min_ratio * body and lower >= range_candle * 0.3
        else:
            results["wick_reject"] = upper >= wick_min_ratio * body and upper >= range_candle * 0.3
    
    # 8. Fakey / False Break
    if config.get("enable_fakey", False) and prev:
        prev_h, prev_l = prev["high"], prev["low"]
        if side == "BUY":
            # 先假突破再快速反向收回区间
            fake_break = prev["high"] > zone_high
            reverse = c < zone_high and c > zone_low
            results["fakey"] = fake_break and reverse
        else:
            fake_break = prev["low"] < zone_low
            reverse = c > zone_low and c < zone_high
            results["fakey"] = fake_break and reverse
    
    # 9. Tweezer Top/Bottom
    if config.get("enable_tweezer", False) and prev:
        prev_h, prev_l = prev["high"], prev["low"]
        if side == "BUY":
            # 双针底
            results["tweezer"] = abs(l - prev_l) / max(1e-8, (l + prev_l) / 2) < 0.002 and lower >= body * 1.5
        else:
            # 双针顶
            results["tweezer"] = abs(h - prev_h) / max(1e-8, (h + prev_h) / 2) < 0.002 and upper >= body * 1.5
    
    # 10. Hammer / Hanging Man
    if config.get("enable_hammer", False):
        if side == "BUY":
            # 锤子线
            results["hammer"] = lower >= body * 2.0 and upper <= body * 0.5
        else:
            # 上吊线
            results["hammer"] = lower >= body * 2.0 and upper <= body * 0.5
    
    # 11. Shooting Star
    if config.get("enable_shooting_star", False) and side == "SELL":
        results["shooting_star"] = upper >= body * 2.0 and lower <= body * 0.5
    
    # 12. Harami
    if config.get("enable_harami", False) and prev:
        prev_h, prev_l = prev["high"], prev["low"]
        prev_body = abs(prev["close"] - prev["open"])
        if prev_body > 0:
            results["harami"] = h < prev_h and l > prev_l and body < prev_body * 0.5
    
    # 13. Belt Hold
    if config.get("enable_belt_hold", False):
        if side == "BUY":
            results["belt_hold"] = c > o and abs(o - l) < range_candle * 0.1 and abs(c - h) < range_candle * 0.1
        else:
            results["belt_hold"] = c < o and abs(o - h) < range_candle * 0.1 and abs(c - l) < range_candle * 0.1
    
    # 计算综合评分
    pattern_weights = config.get("pattern_weights", {})
    pattern_min_score = config.get("pattern_min_score", 1.0)
    
    score = 0.0
    detected_patterns = []
    
    for pattern_name, detected in results.items():
        if detected and pattern_name != "close_reject":
            weight = pattern_weights.get(pattern_name, 1.0)
            score += weight
            detected_patterns.append(pattern_name)
    
    results["score"] = score
    results["patterns"] = detected_patterns
    results["meets_min_score"] = score >= pattern_min_score
    
    return results
