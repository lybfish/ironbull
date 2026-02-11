"""
Order Block 检测模块

实现订单块识别、有效性管理等
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class OrderBlock:
    """订单块"""
    index: int
    type: str  # "bullish" / "bearish"
    high: float
    low: float
    body_high: float
    body_low: float
    timestamp: Optional[int] = None
    tests: int = 0  # 被测试次数


def find_order_blocks(
    candles: List[Dict],
    ob_type: str = "reversal",
    ob_lookback: int = 20,
    ob_min_body_ratio: float = 0.5,
    wick_ob: bool = True
) -> List[OrderBlock]:
    """
    识别订单块
    
    Args:
        candles: K线数据
        ob_type: 订单块类型 "reversal" / "continuation"
        ob_lookback: 回看范围
        ob_min_body_ratio: 最小实体比例
        wick_ob: 是否允许影线订单块
    
    Returns:
        订单块列表
    """
    order_blocks = []
    
    if len(candles) < 2:
        return order_blocks
    
    lookback_start = max(0, len(candles) - ob_lookback - 1)
    
    for i in range(lookback_start + 1, len(candles)):
        c0 = candles[i - 1]
        c1 = candles[i]
        
        body0 = abs(c0["close"] - c0["open"])
        body1 = abs(c1["close"] - c1["open"])
        range0 = c0["high"] - c0["low"]
        range1 = c1["high"] - c1["low"]
        
        if range0 == 0 or range1 == 0:
            continue
        
        body_ratio1 = body1 / range1
        
        # 看涨订单块
        if ob_type == "reversal":
            # 反转型：前一根阴线，后一根阳线突破
            if (c0["close"] < c0["open"] and
                c1["close"] > c1["open"] and
                body_ratio1 >= ob_min_body_ratio and
                c1["close"] > c0["high"]):
                
                strength = min(100, (c1["close"] - c0["high"]) / c0["high"] * 1000)
                order_blocks.append(OrderBlock(
                    index=i - 1,
                    type="bullish",
                    high=c0["high"],
                    low=c0["low"],
                    body_high=max(c0["open"], c0["close"]),
                    body_low=min(c0["open"], c0["close"]),
                    timestamp=c0.get("timestamp") or c0.get("time"),
                ))
        else:
            # 延续型：前一根阳线，后一根阳线继续
            if (c0["close"] > c0["open"] and
                c1["close"] > c1["open"] and
                body_ratio1 >= ob_min_body_ratio and
                c1["close"] > c0["high"]):
                
                order_blocks.append(OrderBlock(
                    index=i - 1,
                    type="bullish",
                    high=c0["high"],
                    low=c0["low"],
                    body_high=max(c0["open"], c0["close"]),
                    body_low=min(c0["open"], c0["close"]),
                    timestamp=c0.get("timestamp") or c0.get("time"),
                ))
        
        # 看跌订单块
        if ob_type == "reversal":
            # 反转型：前一根阳线，后一根阴线突破
            if (c0["close"] > c0["open"] and
                c1["close"] < c1["open"] and
                body_ratio1 >= ob_min_body_ratio and
                c1["close"] < c0["low"]):
                
                strength = min(100, (c0["low"] - c1["close"]) / c0["low"] * 1000)
                order_blocks.append(OrderBlock(
                    index=i - 1,
                    type="bearish",
                    high=c0["high"],
                    low=c0["low"],
                    body_high=max(c0["open"], c0["close"]),
                    body_low=min(c0["open"], c0["close"]),
                    timestamp=c0.get("timestamp") or c0.get("time"),
                ))
        else:
            # 延续型：前一根阴线，后一根阴线继续
            if (c0["close"] < c0["open"] and
                c1["close"] < c1["open"] and
                body_ratio1 >= ob_min_body_ratio and
                c1["close"] < c0["low"]):
                
                order_blocks.append(OrderBlock(
                    index=i - 1,
                    type="bearish",
                    high=c0["high"],
                    low=c0["low"],
                    body_high=max(c0["open"], c0["close"]),
                    body_low=min(c0["open"], c0["close"]),
                    timestamp=c0.get("timestamp") or c0.get("time"),
                ))
    
    return order_blocks


@dataclass
class BreakerBlock:
    """Breaker Block (被突破的 OB → 供需反转)"""
    index: int
    type: str  # "bullish" (原 bearish OB 被向上突破) / "bearish" (原 bullish OB 被向下突破)
    high: float
    low: float
    body_high: float
    body_low: float
    original_type: str  # 原始 OB 类型
    break_index: int  # 被突破的 K 线索引
    timestamp: Optional[int] = None
    tests: int = 0


def find_breaker_blocks(
    candles: List[Dict],
    ob_lookback: int = 50,
    ob_min_body_ratio: float = 0.5,
) -> List[BreakerBlock]:
    """
    识别 Breaker Block (供需反转区)
    
    原理：
    - 一个 Bullish OB 被价格向下突破 → 变成 Bearish Breaker (阻力位)
    - 一个 Bearish OB 被价格向上突破 → 变成 Bullish Breaker (支撑位)
    
    对应文档中的"供需反转：突破后原供区转为需区，类似支撑阻力转换"
    
    Args:
        candles: K线数据
        ob_lookback: 回看范围
        ob_min_body_ratio: 最小实体比例
    
    Returns:
        BreakerBlock 列表
    """
    breakers = []
    
    if len(candles) < 3:
        return breakers
    
    lookback_start = max(0, len(candles) - ob_lookback - 1)
    
    # 第一步：找出所有 OB (用 reversal 类型)
    raw_obs = []
    for i in range(lookback_start + 1, len(candles) - 1):
        c0 = candles[i - 1]
        c1 = candles[i]
        
        body1 = abs(c1["close"] - c1["open"])
        range1 = c1["high"] - c1["low"]
        
        if range1 == 0:
            continue
        
        body_ratio1 = body1 / range1
        if body_ratio1 < ob_min_body_ratio:
            continue
        
        # Bullish OB: 阴线 + 阳线突破
        if (c0["close"] < c0["open"] and
            c1["close"] > c1["open"] and
            c1["close"] > c0["high"]):
            raw_obs.append({
                "index": i - 1,
                "type": "bullish",
                "high": c0["high"],
                "low": c0["low"],
                "body_high": max(c0["open"], c0["close"]),
                "body_low": min(c0["open"], c0["close"]),
                "ts": c0.get("timestamp") or c0.get("time"),
            })
        
        # Bearish OB: 阳线 + 阴线突破
        if (c0["close"] > c0["open"] and
            c1["close"] < c1["open"] and
            c1["close"] < c0["low"]):
            raw_obs.append({
                "index": i - 1,
                "type": "bearish",
                "high": c0["high"],
                "low": c0["low"],
                "body_high": max(c0["open"], c0["close"]),
                "body_low": min(c0["open"], c0["close"]),
                "ts": c0.get("timestamp") or c0.get("time"),
            })
    
    # 第二步：检查哪些 OB 被后续价格突破 → 变成 Breaker
    for ob in raw_obs:
        ob_idx = ob["index"]
        
        # 从 OB 之后的第 2 根 K 线开始检查（第 1 根是形成 OB 的突破 K 线本身）
        for j in range(ob_idx + 2, len(candles)):
            c = candles[j]
            
            if ob["type"] == "bullish":
                # Bullish OB 被向下突破 → Bearish Breaker (阻力)
                # 条件：收盘价跌破 OB 低点
                if c["close"] < ob["low"]:
                    breakers.append(BreakerBlock(
                        index=ob_idx,
                        type="bearish",  # 反转后的类型
                        high=ob["high"],
                        low=ob["low"],
                        body_high=ob["body_high"],
                        body_low=ob["body_low"],
                        original_type="bullish",
                        break_index=j,
                        timestamp=ob["ts"],
                    ))
                    break  # 只取第一次突破
            
            elif ob["type"] == "bearish":
                # Bearish OB 被向上突破 → Bullish Breaker (支撑)
                # 条件：收盘价涨破 OB 高点
                if c["close"] > ob["high"]:
                    breakers.append(BreakerBlock(
                        index=ob_idx,
                        type="bullish",  # 反转后的类型
                        high=ob["high"],
                        low=ob["low"],
                        body_high=ob["body_high"],
                        body_low=ob["body_low"],
                        original_type="bearish",
                        break_index=j,
                        timestamp=ob["ts"],
                    ))
                    break  # 只取第一次突破
    
    return breakers


def find_nearest_order_block(
    order_blocks: List[OrderBlock],
    side: str,
    price: float,
    ob_max_tests: int = 3,
    ob_valid_bars: int = 100,
    current_index: int = 0
) -> Optional[Dict]:
    """
    找到最近的可用订单块
    
    Args:
        order_blocks: 订单块列表
        side: "BUY" / "SELL"
        price: 当前价格
        ob_max_tests: 最大测试次数
        ob_valid_bars: 最大有效K线数
        current_index: 当前K线索引
    
    Returns:
        订单块字典或 None
    """
    target_type = "bullish" if side == "BUY" else "bearish"
    
    candidates = []
    for ob in order_blocks:
        if ob.type != target_type:
            continue
        
        # 检查是否过期
        if current_index - ob.index > ob_valid_bars:
            continue
        
        # 检查是否被测试太多次
        if ob.tests >= ob_max_tests:
            continue
        
        # 检查价格是否在订单块范围内
        if side == "BUY":
            if ob.low <= price <= ob.high:
                candidates.append(ob)
        else:
            if ob.low <= price <= ob.high:
                candidates.append(ob)
    
    if not candidates:
        return None
    
    # 返回最近的订单块
    nearest = min(candidates, key=lambda ob: abs(price - (ob.high + ob.low) / 2))
    
    return {
        "high": nearest.high,
        "low": nearest.low,
        "body_high": nearest.body_high,
        "body_low": nearest.body_low,
        "index": nearest.index,
    }
