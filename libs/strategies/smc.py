"""
SMC (Smart Money Concepts) Strategy - Enhanced Version

SMC 智能资金策略（增强版）

核心概念：
- Order Block (订单块) - 机构大单成交区域
- Fair Value Gap (FVG) - 公允价值缺口
- Liquidity Sweep (流动性扫除) - 止损猎杀后反转
- Break of Structure (BOS) - 结构突破
- Change of Character (CHoCH) - 趋势性质改变
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from libs.contracts import StrategyOutput
from libs.indicators import atr, sma
from .base import StrategyBase


@dataclass
class OrderBlock:
    """订单块"""
    index: int           # K线索引
    type: str            # bullish / bearish
    high: float
    low: float
    body_high: float     # 实体高点
    body_low: float      # 实体低点
    strength: float      # 强度 (0-100)
    tested: bool = False # 是否已被测试


@dataclass
class FVG:
    """公允价值缺口"""
    index: int
    type: str            # bullish / bearish
    high: float          # 缺口上沿
    low: float           # 缺口下沿
    filled: bool = False


@dataclass
class LiquiditySweep:
    """流动性扫除"""
    index: int
    type: str            # high_sweep / low_sweep
    level: float         # 被扫的价格水平
    reversal: bool       # 是否确认反转


class SMCStrategy(StrategyBase):
    """
    SMC 智能资金策略（增强版）
    
    入场条件（做多）：
    1. 识别到看涨订单块
    2. 价格回踩订单块区域
    3. 可选：有看涨 FVG 支撑
    4. 可选：出现流动性扫除后反转
    
    入场条件（做空）：
    1. 识别到看跌订单块
    2. 价格回踩订单块区域
    3. 可选：有看跌 FVG 阻力
    4. 可选：出现流动性扫除后反转
    
    参数：
    - lookback: 回看周期（默认 50）
    - ob_min_body_ratio: 订单块最小实体比例（默认 0.5）
    - fvg_min_gap: FVG 最小缺口比例（默认 0.001）
    - liquidity_lookback: 流动性区域回看（默认 20）
    - require_fvg: 是否要求 FVG 确认（默认 False）
    - require_sweep: 是否要求流动性扫除（默认 False）
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "smc"
        self.name = "SMC智能资金分析策略"
        
        # 参数
        self.lookback = self.config.get("lookback", 50)
        self.ob_min_body_ratio = self.config.get("ob_min_body_ratio", 0.5)
        self.fvg_min_gap = self.config.get("fvg_min_gap", 0.001)
        self.liquidity_lookback = self.config.get("liquidity_lookback", 20)
        self.require_fvg = self.config.get("require_fvg", False)
        self.require_sweep = self.config.get("require_sweep", False)
        
        # 止损止盈
        self.sl_atr_mult = self.config.get("sl_atr_mult", 1.5)
        self.tp_atr_mult = self.config.get("tp_atr_mult", 3.0)
        
        # 状态
        self._order_blocks: List[OrderBlock] = []
        self._fvgs: List[FVG] = []
        self._sweeps: List[LiquiditySweep] = []
    
    def _find_swing_points(self, candles: List[Dict], left: int = 3, right: int = 3) -> Tuple[List, List]:
        """找出摆动高低点"""
        swing_highs = []
        swing_lows = []
        
        for i in range(left, len(candles) - right):
            high = candles[i]["high"]
            low = candles[i]["low"]
            
            # 检查是否是摆动高点
            is_swing_high = True
            for j in range(i - left, i + right + 1):
                if j != i and candles[j]["high"] >= high:
                    is_swing_high = False
                    break
            if is_swing_high:
                swing_highs.append((i, high))
            
            # 检查是否是摆动低点
            is_swing_low = True
            for j in range(i - left, i + right + 1):
                if j != i and candles[j]["low"] <= low:
                    is_swing_low = False
                    break
            if is_swing_low:
                swing_lows.append((i, low))
        
        return swing_highs, swing_lows
    
    def _find_order_blocks(self, candles: List[Dict]) -> List[OrderBlock]:
        """
        识别订单块
        
        看涨订单块：大阴线后跟大阳线突破（最后一根阴线）
        看跌订单块：大阳线后跟大阴线突破（最后一根阳线）
        """
        order_blocks = []
        
        for i in range(2, len(candles) - 1):
            c0 = candles[i - 1]  # 前一根
            c1 = candles[i]      # 当前
            c2 = candles[i + 1]  # 后一根
            
            # 计算实体大小
            body0 = abs(c0["close"] - c0["open"])
            body1 = abs(c1["close"] - c1["open"])
            range0 = c0["high"] - c0["low"]
            range1 = c1["high"] - c1["low"]
            
            if range0 == 0 or range1 == 0:
                continue
            
            body_ratio0 = body0 / range0
            body_ratio1 = body1 / range1
            
            # 看涨订单块：阴线 + 强劲阳线突破
            if (c0["close"] < c0["open"] and  # 阴线
                c1["close"] > c1["open"] and  # 阳线
                body_ratio1 >= self.ob_min_body_ratio and  # 阳线实体足够大
                c1["close"] > c0["high"]):  # 突破阴线高点
                
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
            
            # 看跌订单块：阳线 + 强劲阴线突破
            if (c0["close"] > c0["open"] and  # 阳线
                c1["close"] < c1["open"] and  # 阴线
                body_ratio1 >= self.ob_min_body_ratio and  # 阴线实体足够大
                c1["close"] < c0["low"]):  # 跌破阳线低点
                
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
    
    def _find_fvg(self, candles: List[Dict]) -> List[FVG]:
        """
        识别公允价值缺口 (Fair Value Gap)
        
        看涨 FVG：第一根K线高点 < 第三根K线低点（中间有缺口）
        看跌 FVG：第一根K线低点 > 第三根K线高点
        """
        fvgs = []
        
        for i in range(2, len(candles)):
            c0 = candles[i - 2]
            c2 = candles[i]
            
            # 看涨 FVG
            if c0["high"] < c2["low"]:
                gap = c2["low"] - c0["high"]
                if gap / c0["high"] >= self.fvg_min_gap:
                    fvgs.append(FVG(
                        index=i - 1,
                        type="bullish",
                        high=c2["low"],
                        low=c0["high"],
                    ))
            
            # 看跌 FVG
            if c0["low"] > c2["high"]:
                gap = c0["low"] - c2["high"]
                if gap / c0["low"] >= self.fvg_min_gap:
                    fvgs.append(FVG(
                        index=i - 1,
                        type="bearish",
                        high=c0["low"],
                        low=c2["high"],
                    ))
        
        return fvgs
    
    def _find_liquidity_sweep(self, candles: List[Dict], swing_highs: List, swing_lows: List) -> List[LiquiditySweep]:
        """
        识别流动性扫除
        
        高点扫除：价格突破近期高点后迅速回落
        低点扫除：价格跌破近期低点后迅速反弹
        """
        sweeps = []
        
        if len(candles) < 3:
            return sweeps
        
        current = candles[-1]
        prev = candles[-2]
        
        # 检查高点扫除（先突破高点，然后收盘回落）
        for idx, level in swing_highs[-5:]:  # 检查最近 5 个高点
            if (prev["high"] > level and  # 前一根突破了高点
                current["close"] < level and  # 当前收盘回落
                current["close"] < prev["close"]):  # 收盘低于前一根
                sweeps.append(LiquiditySweep(
                    index=len(candles) - 1,
                    type="high_sweep",
                    level=level,
                    reversal=True,
                ))
        
        # 检查低点扫除（先跌破低点，然后收盘反弹）
        for idx, level in swing_lows[-5:]:
            if (prev["low"] < level and  # 前一根跌破了低点
                current["close"] > level and  # 当前收盘反弹
                current["close"] > prev["close"]):  # 收盘高于前一根
                sweeps.append(LiquiditySweep(
                    index=len(candles) - 1,
                    type="low_sweep",
                    level=level,
                    reversal=True,
                ))
        
        return sweeps
    
    def _check_ob_retest(self, price: float, ob: OrderBlock, tolerance: float = 0.002) -> bool:
        """检查价格是否回踩订单块"""
        if ob.type == "bullish":
            # 价格进入订单块区域（允许一定容差）
            return ob.body_low * (1 - tolerance) <= price <= ob.body_high * (1 + tolerance)
        else:
            return ob.body_low * (1 - tolerance) <= price <= ob.body_high * (1 + tolerance)
    
    def _get_trend(self, candles: List[Dict]) -> str:
        """判断趋势方向"""
        if len(candles) < 20:
            return "neutral"
        
        prices = [c["close"] for c in candles]
        ma20 = sma(prices, 20)
        ma50 = sma(prices, min(50, len(prices)))
        
        if ma20 and ma50:
            if ma20 > ma50 and prices[-1] > ma20:
                return "bullish"
            elif ma20 < ma50 and prices[-1] < ma20:
                return "bearish"
        
        return "neutral"
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析 SMC 信号"""
        
        if len(candles) < self.lookback:
            return None
        
        current_price = candles[-1]["close"]
        atr_val = atr(candles, period=14)
        
        # 1. 识别摆动点
        swing_highs, swing_lows = self._find_swing_points(candles)
        
        # 2. 识别订单块
        order_blocks = self._find_order_blocks(candles[-self.lookback:])
        
        # 3. 识别 FVG
        fvgs = self._find_fvg(candles[-30:])
        
        # 4. 识别流动性扫除
        sweeps = self._find_liquidity_sweep(candles, swing_highs, swing_lows)
        
        # 5. 判断趋势
        trend = self._get_trend(candles)
        
        # 6. 寻找交易信号
        signal = None
        reason_parts = []
        confidence = 60
        
        # ========== 做多逻辑 ==========
        # 检查是否有未测试的看涨订单块被回踩
        for ob in reversed(order_blocks):
            if ob.type == "bullish" and not ob.tested:
                if self._check_ob_retest(current_price, ob):
                    reason_parts.append(f"价格回踩看涨订单块 ({ob.body_low:.0f}-{ob.body_high:.0f})")
                    confidence += 15
                    
                    # 检查 FVG 支撑
                    has_fvg_support = False
                    for fvg in fvgs:
                        if fvg.type == "bullish" and fvg.low <= current_price <= fvg.high:
                            has_fvg_support = True
                            reason_parts.append("FVG 支撑确认")
                            confidence += 10
                            break
                    
                    # 检查流动性扫除
                    has_sweep = False
                    for sweep in sweeps:
                        if sweep.type == "low_sweep" and sweep.reversal:
                            has_sweep = True
                            reason_parts.append("流动性扫除后反转")
                            confidence += 15
                            break
                    
                    # 检查是否满足额外条件
                    if self.require_fvg and not has_fvg_support:
                        continue
                    if self.require_sweep and not has_sweep:
                        continue
                    
                    # 趋势加分
                    if trend == "bullish":
                        confidence += 10
                        reason_parts.append("趋势看涨")
                    
                    signal = StrategyOutput(
                        symbol=symbol,
                        signal_type="OPEN",
                        side="BUY",
                        entry_price=current_price,
                        stop_loss=ob.low - (atr_val * 0.5),
                        take_profit=current_price + (atr_val * self.tp_atr_mult),
                        confidence=min(95, confidence),
                        reason="SMC做多: " + ", ".join(reason_parts),
                        indicators={
                            "order_block": {"type": ob.type, "high": ob.high, "low": ob.low},
                            "trend": trend,
                            "atr": atr_val,
                            "fvg_count": len([f for f in fvgs if f.type == "bullish"]),
                            "sweep": has_sweep if 'has_sweep' in dir() else False,
                        },
                    )
                    break
        
        if signal:
            return signal
        
        # ========== 做空逻辑 ==========
        for ob in reversed(order_blocks):
            if ob.type == "bearish" and not ob.tested:
                if self._check_ob_retest(current_price, ob):
                    reason_parts = [f"价格回踩看跌订单块 ({ob.body_low:.0f}-{ob.body_high:.0f})"]
                    confidence = 60 + 15
                    
                    # 检查 FVG 阻力
                    has_fvg_resistance = False
                    for fvg in fvgs:
                        if fvg.type == "bearish" and fvg.low <= current_price <= fvg.high:
                            has_fvg_resistance = True
                            reason_parts.append("FVG 阻力确认")
                            confidence += 10
                            break
                    
                    # 检查流动性扫除
                    has_sweep = False
                    for sweep in sweeps:
                        if sweep.type == "high_sweep" and sweep.reversal:
                            has_sweep = True
                            reason_parts.append("流动性扫除后反转")
                            confidence += 15
                            break
                    
                    # 检查是否满足额外条件
                    if self.require_fvg and not has_fvg_resistance:
                        continue
                    if self.require_sweep and not has_sweep:
                        continue
                    
                    # 趋势加分
                    if trend == "bearish":
                        confidence += 10
                        reason_parts.append("趋势看跌")
                    
                    signal = StrategyOutput(
                        symbol=symbol,
                        signal_type="OPEN",
                        side="SELL",
                        entry_price=current_price,
                        stop_loss=ob.high + (atr_val * 0.5),
                        take_profit=current_price - (atr_val * self.tp_atr_mult),
                        confidence=min(95, confidence),
                        reason="SMC做空: " + ", ".join(reason_parts),
                        indicators={
                            "order_block": {"type": ob.type, "high": ob.high, "low": ob.low},
                            "trend": trend,
                            "atr": atr_val,
                            "fvg_count": len([f for f in fvgs if f.type == "bearish"]),
                            "sweep": has_sweep,
                        },
                    )
                    break
        
        return signal
