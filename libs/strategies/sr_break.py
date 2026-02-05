"""
Support/Resistance Break Strategy

支撑阻力突破策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import atr
from .base import StrategyBase


class SRBreakStrategy(StrategyBase):
    """
    支撑阻力突破策略
    
    识别关键支撑阻力位并在突破时入场。
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "sr_break"
        self.name = "支撑阻力突破策略"
        
        # 参数
        self.lookback = self.config.get("lookback", 50)
    
    def _find_resistance(self, highs: List[float]) -> List[float]:
        """找出阻力位（局部高点）"""
        resistance = []
        for i in range(2, len(highs) - 2):
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                resistance.append(highs[i])
        return sorted(resistance, reverse=True)
    
    def _find_support(self, lows: List[float]) -> List[float]:
        """找出支撑位（局部低点）"""
        support = []
        for i in range(2, len(lows) - 2):
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                support.append(lows[i])
        return sorted(support, reverse=True)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析支撑阻力突破信号"""
        
        if len(candles) < self.lookback:
            return None
        
        prices = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        
        current_price = prices[-1]
        prev_price = prices[-2]
        atr_val = atr(candles, period=14)
        
        # 找出关键支撑阻力位
        resistance_levels = self._find_resistance(highs[-self.lookback:])
        support_levels = self._find_support(lows[-self.lookback:])
        
        # 检查是否突破阻力
        for resistance in resistance_levels[:3]:
            if current_price > resistance and prev_price <= resistance:
                breakout_strength = (current_price - resistance) / resistance * 100
                
                if breakout_strength > 0.1:
                    return StrategyOutput(
                        symbol=symbol,
                        signal_type="OPEN",
                        side="BUY",
                        entry_price=current_price,
                        stop_loss=resistance * 0.99,
                        take_profit=current_price + (current_price - resistance) * 2,
                        confidence=min(85, 70 + breakout_strength * 10),
                        reason=f"突破阻力位 {resistance:.2f}，突破幅度 {breakout_strength:.2f}%",
                        indicators={
                            "resistance": resistance,
                            "breakout_strength": breakout_strength,
                            "atr": atr_val,
                        },
                    )
        
        # 检查是否跌破支撑
        for support in support_levels[:3]:
            if current_price < support and prev_price >= support:
                breakdown_strength = (support - current_price) / support * 100
                
                if breakdown_strength > 0.1:
                    return StrategyOutput(
                        symbol=symbol,
                        signal_type="OPEN",
                        side="SELL",
                        entry_price=current_price,
                        stop_loss=support * 1.01,
                        take_profit=current_price - (support - current_price) * 2,
                        confidence=min(85, 70 + breakdown_strength * 10),
                        reason=f"跌破支撑位 {support:.2f}，跌破幅度 {breakdown_strength:.2f}%",
                        indicators={
                            "support": support,
                            "breakdown_strength": breakdown_strength,
                            "atr": atr_val,
                        },
                    )
        
        return None
