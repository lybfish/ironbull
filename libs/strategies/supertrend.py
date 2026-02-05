"""
SuperTrend Strategy

超级趋势策略
基于 ATR 的趋势跟踪指标
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import atr
from .base import StrategyBase


def calculate_supertrend(candles: List[Dict], period: int = 10, multiplier: float = 3.0):
    """计算 SuperTrend 指标"""
    if len(candles) < period + 1:
        return None, None
    
    # 计算 ATR
    atr_val = atr(candles, period)
    if atr_val is None:
        return None, None
    
    # 计算基础线
    hl2 = (candles[-1]["high"] + candles[-1]["low"]) / 2
    
    # 上下轨
    basic_upper = hl2 + (multiplier * atr_val)
    basic_lower = hl2 - (multiplier * atr_val)
    
    # 简化版：直接用当前价格判断趋势
    close = candles[-1]["close"]
    prev_close = candles[-2]["close"]
    
    # 趋势判断
    if close > basic_lower and prev_close > candles[-2]["low"]:
        trend = 1  # 上升趋势
        supertrend = basic_lower
    else:
        trend = -1  # 下降趋势
        supertrend = basic_upper
    
    return supertrend, trend


class SuperTrendStrategy(StrategyBase):
    """
    SuperTrend 策略
    
    趋势转为上升 → BUY
    趋势转为下降 → SELL
    
    参数：
    - period: ATR 周期（默认 10）
    - multiplier: ATR 倍数（默认 3.0）
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "supertrend"
        self.name = "SuperTrend策略"
        
        self.period = self.config.get("period", 10)
        self.multiplier = self.config.get("multiplier", 3.0)
        
        self._prev_trend = 0
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        
        if len(candles) < self.period + 2:
            return None
        
        current_price = candles[-1]["close"]
        
        # 当前 SuperTrend
        st, trend = calculate_supertrend(candles, self.period, self.multiplier)
        
        # 前一根 K 线的 SuperTrend
        st_prev, trend_prev = calculate_supertrend(candles[:-1], self.period, self.multiplier)
        
        if st is None or st_prev is None:
            return None
        
        atr_val = atr(candles, self.period)
        
        # 趋势转为上升
        if trend_prev == -1 and trend == 1:
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=st,
                take_profit=current_price + (atr_val * 4),
                confidence=80,
                reason=f"SuperTrend 转为上升趋势",
                indicators={
                    "supertrend": st,
                    "trend": trend,
                    "atr": atr_val,
                },
            )
        
        # 趋势转为下降
        if trend_prev == 1 and trend == -1:
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=st,
                take_profit=current_price - (atr_val * 4),
                confidence=80,
                reason=f"SuperTrend 转为下降趋势",
                indicators={
                    "supertrend": st,
                    "trend": trend,
                    "atr": atr_val,
                },
            )
        
        return None
