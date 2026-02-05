"""
Breakout Strategy

突破策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from .base import StrategyBase


class BreakoutStrategy(StrategyBase):
    """
    突破策略
    
    价格突破 N 周期内的最高点 → BUY
    价格跌破 N 周期内的最低点 → SELL
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "breakout"
        self.name = "突破策略"
        
        # 回看周期
        self.lookback = self.config.get("lookback", 20)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析突破信号"""
        
        if len(candles) < self.lookback + 1:
            return None
        
        prices = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        
        current_price = prices[-1]
        
        # 计算阻力位和支撑位（不包含当前 K 线）
        resistance = max(highs[-self.lookback - 1:-1])
        support = min(lows[-self.lookback - 1:-1])
        
        # 向上突破阻力位
        if current_price > resistance:
            breakout_pct = ((current_price - resistance) / resistance) * 100
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=resistance,  # 止损在阻力位
                take_profit=current_price + (current_price - resistance),  # 1:1 目标
                confidence=80,
                reason=f"向上突破阻力位 {resistance:.2f}，突破幅度 {breakout_pct:.2f}%",
                indicators={
                    "resistance": resistance,
                    "support": support,
                    "breakout_pct": breakout_pct,
                },
            )
        
        # 向下突破支撑位
        if current_price < support:
            breakout_pct = ((support - current_price) / support) * 100
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=support,  # 止损在支撑位
                take_profit=current_price - (support - current_price),  # 1:1 目标
                confidence=80,
                reason=f"向下突破支撑位 {support:.2f}，突破幅度 {breakout_pct:.2f}%",
                indicators={
                    "resistance": resistance,
                    "support": support,
                    "breakout_pct": breakout_pct,
                },
            )
        
        return None
