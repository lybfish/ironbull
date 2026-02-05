"""
SMC + Fibonacci Strategy - 以损定仓版本 + 多时间框架过滤

核心逻辑：
- SMC (Smart Money Concepts) 识别订单块和流动性区域
- Fibonacci 回撤位确认入场点（0.382/0.5/0.618）
- 以损定仓：根据固定止损金额计算仓位
- 盈亏比过滤：< min_rr 不开仓
- 多时间框架(MTF)：只在大周期趋势方向一致时开仓
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from libs.contracts import StrategyOutput
from libs.indicators import atr, sma, ema
from libs.indicators.fibo import fibo_levels, price_in_fibo_zone, fibo_extension
from .base import StrategyBase


@dataclass
class OrderBlock:
    """订单块"""
    index: int
    type: str            # bullish / bearish
    high: float
    low: float
    body_high: float
    body_low: float
    strength: float


@dataclass 
class SwingPoint:
    """摆动点"""
    index: int
    price: float
    type: str  # high / low


class SMCFiboStrategy(StrategyBase):
    """
    SMC + 斐波那契回踩策略（以损定仓版 + MTF过滤）
    
    入场条件（做多）：
    1. 大周期趋势看涨（HTF Filter）
    2. 识别上升趋势中的摆动高低点
    3. 价格回踩到斐波那契关键位（0.382/0.5/0.618）
    4. 有看涨订单块支撑
    5. 盈亏比 >= min_rr
    
    入场条件（做空）：
    1. 大周期趋势看跌（HTF Filter）
    2. 识别下降趋势中的摆动高低点
    3. 价格反弹到斐波那契关键位
    4. 有看跌订单块阻力
    5. 盈亏比 >= min_rr
    
    仓位计算：
    - 仓位 = 固定亏损金额 / 止损距离
    - 止损设在订单块外侧
    - 止盈 = 入场 + (止损距离 × 盈亏比)
    
    多时间框架过滤：
    - 使用 htf_multiplier 倍的K线聚合为大周期
    - 例如 1h 图 + htf_multiplier=4 = 模拟 4h 大周期
    - 大周期使用 EMA 判断趋势方向
    
    参数：
    - max_loss: 每单最大亏损（默认 100 USDT）
    - min_rr: 最小盈亏比（默认 1.5）
    - fibo_levels: 关键回撤位（默认 [0.382, 0.5, 0.618]）
    - fibo_tolerance: 回撤位容差（默认 0.5%）
    - lookback: 回看周期（默认 50）
    - htf_multiplier: 大周期倍数（默认 4，即 1h->4h）
    - htf_ema_fast: 大周期快EMA（默认 20）
    - htf_ema_slow: 大周期慢EMA（默认 50）
    - require_htf_filter: 是否要求大周期过滤（默认 True）
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "smc_fibo"
        self.name = "SMC斐波那契回踩策略(MTF)"
        
        # 资金管理参数
        self.max_loss = self.config.get("max_loss", 100)       # 每单最大亏损 USDT
        self.min_rr = self.config.get("min_rr", 1.5)           # 最小盈亏比
        
        # 斐波那契参数
        self.fibo_entry_levels = self.config.get("fibo_levels", [0.382, 0.5, 0.618])
        self.fibo_tolerance = self.config.get("fibo_tolerance", 0.005)  # 0.5%
        
        # SMC 参数
        self.lookback = self.config.get("lookback", 50)
        self.swing_left = self.config.get("swing_left", 5)
        self.swing_right = self.config.get("swing_right", 3)
        self.ob_min_body_ratio = self.config.get("ob_min_body_ratio", 0.5)
        
        # 止损缓冲
        self.sl_buffer_pct = self.config.get("sl_buffer_pct", 0.002)  # 0.2%
        
        # 多时间框架参数
        self.htf_multiplier = self.config.get("htf_multiplier", 4)      # 大周期倍数
        self.htf_ema_fast = self.config.get("htf_ema_fast", 20)         # 大周期快EMA
        self.htf_ema_slow = self.config.get("htf_ema_slow", 50)         # 大周期慢EMA
        self.require_htf_filter = self.config.get("require_htf_filter", True)  # 是否强制大周期过滤
    
    def _aggregate_to_htf(self, candles: List[Dict]) -> List[Dict]:
        """
        将小周期K线聚合为大周期
        
        例如：4根1h K线 -> 1根4h K线
        """
        if len(candles) < self.htf_multiplier:
            return []
        
        htf_candles = []
        n = self.htf_multiplier
        
        # 从后往前聚合，确保最新的K线完整
        for i in range(0, len(candles) - n + 1, n):
            chunk = candles[i:i + n]
            
            htf_candle = {
                "time": chunk[0].get("time"),
                "open": chunk[0]["open"],
                "high": max(c["high"] for c in chunk),
                "low": min(c["low"] for c in chunk),
                "close": chunk[-1]["close"],
                "volume": sum(c.get("volume", 0) for c in chunk),
            }
            htf_candles.append(htf_candle)
        
        return htf_candles
    
    def _get_htf_trend(self, candles: List[Dict]) -> str:
        """
        判断大周期趋势方向
        
        使用 EMA 交叉判断：
        - bullish: 快EMA > 慢EMA（大周期上升趋势）
        - bearish: 快EMA < 慢EMA（大周期下降趋势）
        - neutral: EMA 非常接近（横盘震荡）
        """
        # 聚合到大周期
        htf_candles = self._aggregate_to_htf(candles)
        
        min_candles = self.htf_ema_slow + 5
        if len(htf_candles) < min_candles:
            # 数据不足时，退化为使用原始K线计算
            closes = [c["close"] for c in candles]
            if len(closes) < self.htf_ema_slow * self.htf_multiplier:
                return "neutral"
            ema_fast = ema(closes, self.htf_ema_fast * self.htf_multiplier)
            ema_slow = ema(closes, self.htf_ema_slow * self.htf_multiplier)
        else:
            # 计算大周期EMA
            closes = [c["close"] for c in htf_candles]
            ema_fast = ema(closes, self.htf_ema_fast)
            ema_slow = ema(closes, self.htf_ema_slow)
        
        if ema_fast is None or ema_slow is None:
            return "neutral"
        
        # 计算EMA差距百分比
        ema_diff_pct = (ema_fast - ema_slow) / ema_slow * 100
        
        # 判断趋势（差距超过0.5%才确认趋势）
        if ema_diff_pct > 0.5:
            return "bullish"
        elif ema_diff_pct < -0.5:
            return "bearish"
        
        return "neutral"
    
    def _find_swing_points(self, candles: List[Dict]) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """识别摆动高低点"""
        swing_highs = []
        swing_lows = []
        left = self.swing_left
        right = self.swing_right
        
        for i in range(left, len(candles) - right):
            high = candles[i]["high"]
            low = candles[i]["low"]
            
            # 摆动高点
            is_swing_high = True
            for j in range(i - left, i + right + 1):
                if j != i and candles[j]["high"] >= high:
                    is_swing_high = False
                    break
            if is_swing_high:
                swing_highs.append(SwingPoint(index=i, price=high, type="high"))
            
            # 摆动低点
            is_swing_low = True
            for j in range(i - left, i + right + 1):
                if j != i and candles[j]["low"] <= low:
                    is_swing_low = False
                    break
            if is_swing_low:
                swing_lows.append(SwingPoint(index=i, price=low, type="low"))
        
        return swing_highs, swing_lows
    
    def _find_order_blocks(self, candles: List[Dict]) -> List[OrderBlock]:
        """识别订单块"""
        order_blocks = []
        
        for i in range(2, len(candles) - 1):
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
            if (c0["close"] < c0["open"] and
                c1["close"] > c1["open"] and
                body_ratio1 >= self.ob_min_body_ratio and
                c1["close"] > c0["high"]):
                
                strength = min(100, (c1["close"] - c0["high"]) / c0["high"] * 1000)
                order_blocks.append(OrderBlock(
                    index=i - 1,
                    type="bullish",
                    high=c0["high"],
                    low=c0["low"],
                    body_high=max(c0["open"], c0["close"]),
                    body_low=min(c0["open"], c0["close"]),
                    strength=strength,
                ))
            
            # 看跌订单块
            if (c0["close"] > c0["open"] and
                c1["close"] < c1["open"] and
                body_ratio1 >= self.ob_min_body_ratio and
                c1["close"] < c0["low"]):
                
                strength = min(100, (c0["low"] - c1["close"]) / c0["low"] * 1000)
                order_blocks.append(OrderBlock(
                    index=i - 1,
                    type="bearish",
                    high=c0["high"],
                    low=c0["low"],
                    body_high=max(c0["open"], c0["close"]),
                    body_low=min(c0["open"], c0["close"]),
                    strength=strength,
                ))
        
        return order_blocks
    
    def _get_trend(self, candles: List[Dict], swing_highs: List[SwingPoint], swing_lows: List[SwingPoint]) -> str:
        """判断趋势 - 基于摆动点结构"""
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "neutral"
        
        # 高点和低点都在上升 = 上升趋势
        hh = swing_highs[-1].price > swing_highs[-2].price  # Higher High
        hl = swing_lows[-1].price > swing_lows[-2].price    # Higher Low
        
        # 高点和低点都在下降 = 下降趋势
        lh = swing_highs[-1].price < swing_highs[-2].price  # Lower High
        ll = swing_lows[-1].price < swing_lows[-2].price    # Lower Low
        
        if hh and hl:
            return "bullish"
        elif lh and ll:
            return "bearish"
        
        return "neutral"
    
    def _calc_position_size(self, entry: float, stop_loss: float) -> float:
        """
        以损定仓：根据固定亏损金额计算仓位
        
        仓位 = 最大亏损 / 止损距离
        """
        sl_distance = abs(entry - stop_loss)
        if sl_distance == 0:
            return 0
        
        # 仓位大小（合约数量）
        position_size = self.max_loss / sl_distance
        return round(position_size, 4)
    
    def _calc_rr_ratio(self, entry: float, stop_loss: float, take_profit: float) -> float:
        """计算盈亏比"""
        sl_distance = abs(entry - stop_loss)
        tp_distance = abs(take_profit - entry)
        
        if sl_distance == 0:
            return 0
        
        return tp_distance / sl_distance
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析 SMC + Fibonacci 信号"""
        
        if len(candles) < self.lookback:
            return None
        
        current = candles[-1]
        current_price = current["close"]
        atr_val = atr(candles, period=14)
        
        # 0. 大周期趋势过滤
        htf_trend = self._get_htf_trend(candles)
        
        # 1. 识别摆动点
        swing_highs, swing_lows = self._find_swing_points(candles)
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None
        
        # 2. 判断小周期趋势
        trend = self._get_trend(candles, swing_highs, swing_lows)
        
        if trend == "neutral":
            return None
        
        # 3. 大周期过滤检查
        # 只过滤"逆势"交易，允许顺势和中性
        if self.require_htf_filter:
            # 做多时：大周期不能看跌（允许 bullish 和 neutral）
            if trend == "bullish" and htf_trend == "bearish":
                return None
            # 做空时：大周期不能看涨（允许 bearish 和 neutral）
            if trend == "bearish" and htf_trend == "bullish":
                return None
        
        # 4. 识别订单块
        order_blocks = self._find_order_blocks(candles[-self.lookback:])
        
        # 5. 计算斐波那契
        signal = None
        
        # ========== 做多逻辑（上升趋势回调买入）==========
        if trend == "bullish":
            # 找最近的摆动高低点
            recent_high = swing_highs[-1].price
            recent_low = swing_lows[-1].price
            
            # 确保高点在低点之后（正常的上升波段）
            if swing_highs[-1].index > swing_lows[-1].index:
                # 计算斐波那契回撤位
                fibo_dict = fibo_levels(recent_high, recent_low, self.fibo_entry_levels)
                
                # 检查当前价格是否在斐波那契关键位
                fibo_zone = price_in_fibo_zone(current_price, fibo_dict, self.fibo_tolerance)
                
                if fibo_zone:
                    fibo_level, fibo_price = fibo_zone
                    
                    # 检查是否有看涨订单块支撑
                    supporting_ob = None
                    for ob in reversed(order_blocks):
                        if ob.type == "bullish":
                            # 订单块在当前价格下方且距离合理
                            if ob.body_low <= current_price <= ob.body_high * 1.01:
                                supporting_ob = ob
                                break
                            # 或者订单块接近斐波那契位
                            if abs(ob.body_high - fibo_price) / fibo_price < 0.01:
                                supporting_ob = ob
                                break
                    
                    # 计算止损止盈
                    if supporting_ob:
                        stop_loss = supporting_ob.low * (1 - self.sl_buffer_pct)
                    else:
                        stop_loss = recent_low * (1 - self.sl_buffer_pct)
                    
                    sl_distance = current_price - stop_loss
                    
                    # 用斐波那契扩展位作为止盈目标
                    extension = fibo_extension(recent_high, recent_low, [1.272, 1.618])
                    take_profit = extension.get(1.272, recent_high + sl_distance * self.min_rr)
                    
                    # 检查盈亏比
                    rr_ratio = self._calc_rr_ratio(current_price, stop_loss, take_profit)
                    
                    if rr_ratio >= self.min_rr:
                        # 计算仓位
                        position_size = self._calc_position_size(current_price, stop_loss)
                        
                        # 计算置信度（多因素加权）
                        conf_score = 50  # 基础分
                        
                        # 1. 斐波那契位权重（0.5位最佳，0.618次之，0.382再次）
                        if abs(fibo_level - 0.5) < 0.05:
                            conf_score += 15  # 黄金分割位
                        elif abs(fibo_level - 0.618) < 0.05:
                            conf_score += 12
                        else:
                            conf_score += 8
                        
                        # 2. 订单块支撑（有订单块更可靠）
                        if supporting_ob:
                            ob_strength = min(15, supporting_ob.strength / 5)
                            conf_score += int(ob_strength)
                        
                        # 3. 盈亏比加成（越高越好）
                        rr_bonus = min(10, (rr_ratio - self.min_rr) * 5)
                        conf_score += int(rr_bonus)
                        
                        # 4. HTF 趋势一致性（大小周期同向）
                        if htf_trend == trend:
                            conf_score += 10  # 大小周期一致
                        elif htf_trend == "neutral":
                            conf_score += 5   # 大周期中性
                        # 逆势已被过滤，不会到这里
                        
                        confidence = min(95, max(50, conf_score))
                        
                        signal = StrategyOutput(
                            symbol=symbol,
                            signal_type="OPEN",
                            side="BUY",
                            entry_price=current_price,
                            stop_loss=round(stop_loss, 2),
                            take_profit=round(take_profit, 2),
                            confidence=confidence,
                            reason=f"SMC+Fibo做多: 回踩{fibo_level:.1%}位, " + 
                                   f"盈亏比{rr_ratio:.2f}, 仓位{position_size}",
                            indicators={
                                "htf_trend": htf_trend,  # 大周期趋势
                                "ltf_trend": trend,      # 小周期趋势
                                "fibo_level": fibo_level,
                                "fibo_price": round(fibo_price, 2),
                                "swing_high": round(recent_high, 2),
                                "swing_low": round(recent_low, 2),
                                "order_block": {
                                    "high": supporting_ob.high if supporting_ob else None,
                                    "low": supporting_ob.low if supporting_ob else None,
                                } if supporting_ob else None,
                                "rr_ratio": round(rr_ratio, 2),
                                "position_size": position_size,
                                "max_loss": self.max_loss,
                                "sl_distance": round(sl_distance, 2),
                                "atr": round(atr_val, 2) if atr_val else None,
                            },
                        )
        
        # ========== 做空逻辑（下降趋势反弹卖出）==========
        elif trend == "bearish":
            recent_high = swing_highs[-1].price
            recent_low = swing_lows[-1].price
            
            # 确保低点在高点之后（正常的下降波段）
            if swing_lows[-1].index > swing_highs[-1].index:
                # 下降趋势的斐波那契：从低点往高点算回撤
                fibo_dict = {}
                swing_range = recent_high - recent_low
                for level in self.fibo_entry_levels:
                    fibo_dict[level] = recent_low + swing_range * level
                
                # 检查当前价格是否在斐波那契关键位
                fibo_zone = price_in_fibo_zone(current_price, fibo_dict, self.fibo_tolerance)
                
                if fibo_zone:
                    fibo_level, fibo_price = fibo_zone
                    
                    # 检查是否有看跌订单块阻力
                    resisting_ob = None
                    for ob in reversed(order_blocks):
                        if ob.type == "bearish":
                            if ob.body_low * 0.99 <= current_price <= ob.body_high:
                                resisting_ob = ob
                                break
                            if abs(ob.body_low - fibo_price) / fibo_price < 0.01:
                                resisting_ob = ob
                                break
                    
                    # 计算止损止盈
                    if resisting_ob:
                        stop_loss = resisting_ob.high * (1 + self.sl_buffer_pct)
                    else:
                        stop_loss = recent_high * (1 + self.sl_buffer_pct)
                    
                    sl_distance = stop_loss - current_price
                    
                    # 斐波那契扩展作为止盈
                    take_profit = recent_low - (swing_range * 0.272)
                    
                    # 检查盈亏比
                    rr_ratio = self._calc_rr_ratio(current_price, stop_loss, take_profit)
                    
                    if rr_ratio >= self.min_rr:
                        position_size = self._calc_position_size(current_price, stop_loss)
                        
                        # 计算置信度（多因素加权）
                        conf_score = 50  # 基础分
                        
                        # 1. 斐波那契位权重
                        if abs(fibo_level - 0.5) < 0.05:
                            conf_score += 15
                        elif abs(fibo_level - 0.618) < 0.05:
                            conf_score += 12
                        else:
                            conf_score += 8
                        
                        # 2. 订单块阻力
                        if resisting_ob:
                            ob_strength = min(15, resisting_ob.strength / 5)
                            conf_score += int(ob_strength)
                        
                        # 3. 盈亏比加成
                        rr_bonus = min(10, (rr_ratio - self.min_rr) * 5)
                        conf_score += int(rr_bonus)
                        
                        # 4. HTF 趋势一致性
                        if htf_trend == trend:
                            conf_score += 10
                        elif htf_trend == "neutral":
                            conf_score += 5
                        
                        confidence = min(95, max(50, conf_score))
                        
                        signal = StrategyOutput(
                            symbol=symbol,
                            signal_type="OPEN",
                            side="SELL",
                            entry_price=current_price,
                            stop_loss=round(stop_loss, 2),
                            take_profit=round(take_profit, 2),
                            confidence=confidence,
                            reason=f"SMC+Fibo做空: 反弹{fibo_level:.1%}位, " +
                                   f"盈亏比{rr_ratio:.2f}, 仓位{position_size}",
                            indicators={
                                "htf_trend": htf_trend,  # 大周期趋势
                                "ltf_trend": trend,      # 小周期趋势
                                "fibo_level": fibo_level,
                                "fibo_price": round(fibo_price, 2),
                                "swing_high": round(recent_high, 2),
                                "swing_low": round(recent_low, 2),
                                "order_block": {
                                    "high": resisting_ob.high if resisting_ob else None,
                                    "low": resisting_ob.low if resisting_ob else None,
                                } if resisting_ob else None,
                                "rr_ratio": round(rr_ratio, 2),
                                "position_size": position_size,
                                "max_loss": self.max_loss,
                                "sl_distance": round(sl_distance, 2),
                                "atr": round(atr_val, 2) if atr_val else None,
                            },
                        )
        
        return signal
