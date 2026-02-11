"""
风险管理模块

实现以损定仓、止损止盈计算、最小RR过滤等
"""

from typing import Dict, Optional, Tuple


def calculate_position_size(
    entry_price: float,
    stop_loss: float,
    max_loss: float
) -> float:
    """
    以损定仓：根据固定亏损金额计算仓位
    
    Args:
        entry_price: 入场价
        stop_loss: 止损价
        max_loss: 最大亏损金额（USDT）
    
    Returns:
        仓位大小
    """
    sl_distance = abs(entry_price - stop_loss)
    if sl_distance == 0:
        return 0.0
    
    position_size = max_loss / sl_distance
    return round(position_size, 4)


def calculate_stop_loss(
    side: str,
    entry_price: float,
    order_block: Optional[Dict] = None,
    swing_high: Optional[float] = None,
    swing_low: Optional[float] = None,
    stop_source: str = "auto",
    stop_buffer_pct: float = 0.05,
    atr_value: float = 0.0,
    atr_multiplier: float = 0.5
) -> float:
    """
    根据 stop_source 计算止损价
    
    止损缓冲模式:
      1. 固定百分比: stop_buffer_pct > 0, atr_value == 0
         SL = swing_low × (1 - pct)
      2. ATR动态:    atr_value > 0
         SL = swing_low - ATR × multiplier
         (忽略 stop_buffer_pct)
    
    Args:
        side: "BUY" / "SELL"
        entry_price: 入场价
        order_block: 订单块字典（包含 high/low）
        swing_high: 摆动高点
        swing_low: 摆动低点
        stop_source: "auto" / "ob" / "swing" / "structure"
        stop_buffer_pct: 止损缓冲百分比（0.05 表示 0.05%）
        atr_value: ATR值（>0 时启用ATR缓冲模式）
        atr_multiplier: ATR乘数（默认0.5，即半个ATR作为缓冲）
    
    Returns:
        止损价
    """
    # 选择缓冲模式
    use_atr = atr_value > 0
    
    if use_atr:
        # ATR模式: 缓冲距离 = ATR × multiplier（绝对值）
        atr_buffer = atr_value * atr_multiplier
    else:
        # 固定百分比模式
        # 与 old1 对齐：stopBufferPct=0.05 表示 0.05%，需要 /100 转换为小数
        buffer = stop_buffer_pct / 100.0 if stop_buffer_pct >= 0.01 else stop_buffer_pct
    
    if stop_source == "ob" and order_block:
        base = order_block.get("low", 0) if side == "BUY" else order_block.get("high", 0)
        if use_atr:
            return (base - atr_buffer) if side == "BUY" else (base + atr_buffer)
        else:
            return base * (1 - buffer) if side == "BUY" else base * (1 + buffer)
    
    if stop_source == "swing" or stop_source == "auto":
        if side == "BUY" and swing_low:
            return (swing_low - atr_buffer) if use_atr else swing_low * (1 - buffer)
        elif side == "SELL" and swing_high:
            return (swing_high + atr_buffer) if use_atr else swing_high * (1 + buffer)
    
    # Fallback：使用入场价
    if use_atr:
        return (entry_price - atr_buffer) if side == "BUY" else (entry_price + atr_buffer)
    else:
        return entry_price * (1 - buffer) if side == "BUY" else entry_price * (1 + buffer)


def calculate_take_profit(
    side: str,
    entry_price: float,
    stop_loss: float,
    tp_mode: str,
    swing_high: Optional[float] = None,
    swing_low: Optional[float] = None,
    rr: float = 2.0,
    fibo_extension: Optional[Dict[float, float]] = None
) -> float:
    """
    根据 tp_mode 计算止盈价
    
    Args:
        side: "BUY" / "SELL"
        entry_price: 入场价
        stop_loss: 止损价
        tp_mode: "swing" / "rr" / "fibo"
        swing_high: 摆动高点（用于 swing 模式）
        swing_low: 摆动低点（用于 swing 模式）
        rr: 风险回报比（用于 rr 模式）
        fibo_extension: 斐波那契扩展位字典（用于 fibo 模式）
    
    Returns:
        止盈价
    """
    sl_distance = abs(entry_price - stop_loss)
    
    if tp_mode == "swing":
        if side == "BUY" and swing_high:
            return swing_high
        elif side == "SELL" and swing_low:
            return swing_low
        # Fallback to RR
        if side == "BUY":
            return entry_price + sl_distance * rr
        else:
            return entry_price - sl_distance * rr
    
    elif tp_mode == "rr":
        if side == "BUY":
            return entry_price + sl_distance * rr
        else:
            return entry_price - sl_distance * rr
    
    elif tp_mode == "fibo" and fibo_extension:
        # 优先使用 1.272 扩展位
        if 1.272 in fibo_extension:
            tp = fibo_extension[1.272]
            # 确保止盈在正确方向
            if side == "BUY" and tp > entry_price:
                return tp
            elif side == "SELL" and tp < entry_price:
                return tp
        # Fallback to RR
        if side == "BUY":
            return entry_price + sl_distance * rr
        else:
            return entry_price - sl_distance * rr
    
    # 默认使用 RR
    if side == "BUY":
        return entry_price + sl_distance * rr
    else:
        return entry_price - sl_distance * rr


def calculate_rr_ratio(
    entry_price: float,
    stop_loss: float,
    take_profit: float
) -> float:
    """
    计算盈亏比
    
    Args:
        entry_price: 入场价
        stop_loss: 止损价
        take_profit: 止盈价
    
    Returns:
        盈亏比
    """
    sl_distance = abs(entry_price - stop_loss)
    tp_distance = abs(take_profit - entry_price)
    
    if sl_distance == 0:
        return 0.0
    
    return tp_distance / sl_distance


def ensure_min_rr(
    side: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    min_rr: float
) -> Tuple[float, float]:
    """
    确保止盈满足最小盈亏比要求
    
    如果初始止盈的盈亏比不够，自动调整止盈价格以满足 min_rr 要求
    
    Args:
        side: "BUY" / "SELL"
        entry_price: 入场价
        stop_loss: 止损价
        take_profit: 初始止盈价
        min_rr: 最小盈亏比
    
    Returns:
        (调整后的止盈价, 实际盈亏比) 元组
    """
    rr_ratio = calculate_rr_ratio(entry_price, stop_loss, take_profit)
    
    # 如果已经满足最小盈亏比，直接返回
    if rr_ratio >= min_rr:
        return take_profit, rr_ratio
    
    # 否则，调整止盈以满足最小盈亏比
    sl_distance = abs(entry_price - stop_loss)
    target_rr = max(min_rr * 1.2, min_rr + 0.3)
    
    # 尝试调整止盈（最多5次）
    for _ in range(5):
        if side == "BUY":
            adjusted_tp = entry_price + target_rr * sl_distance
        else:
            adjusted_tp = entry_price - target_rr * sl_distance
        
        rr_ratio = calculate_rr_ratio(entry_price, stop_loss, adjusted_tp)
        if rr_ratio >= min_rr:
            return adjusted_tp, rr_ratio
        
        # 如果还不够，增加目标盈亏比
        target_rr *= 1.35
    
    # 如果5次调整后仍不满足，返回调整后的止盈（至少尝试了）
    return adjusted_tp, rr_ratio
