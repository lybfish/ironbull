"""
Momentum Strategy

动量追踪策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import atr
from .base import StrategyBase


class MomentumStrategy(StrategyBase):
    """
    动量追踪策略
    
    价格相对于 N 周期前的涨幅超过阈值 → 追涨/追跌
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "momentum"
        self.name = "动量追踪策略"
        
        # 动量参数
        self.period = self.config.get("momentum_period", 14)
        self.threshold = self.config.get("momentum_threshold", 5)  # 百分比
        
        # 止盈止损倍数
        self.sl_atr_mult = self.config.get("sl_atr_mult", 1.5)
        self.tp_atr_mult = self.config.get("tp_atr_mult", 4.0)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析动量信号"""
        
        if len(candles) < self.period + 1:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        old_price = prices[-self.period - 1]
        
        # 计算动量（百分比）
        momentum = ((current_price - old_price) / old_price) * 100
        
        # 计算 ATR
        atr_val = atr(candles, period=14)
        
        # 强势上涨动量 → 做多
        if momentum > self.threshold:
            confidence = min(90, 70 + abs(momentum))
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr_val * self.sl_atr_mult),
                take_profit=current_price + (atr_val * self.tp_atr_mult),
                confidence=confidence,
                reason=f"强势上涨动量 {momentum:.2f}%",
                indicators={
                    "momentum": momentum,
                    "period": self.period,
                    "atr": atr_val,
                },
            )
        
        # 强势下跌动量 → 做空
        if momentum < -self.threshold:
            confidence = min(90, 70 + abs(momentum))
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr_val * self.sl_atr_mult),
                take_profit=current_price - (atr_val * self.tp_atr_mult),
                confidence=confidence,
                reason=f"强势下跌动量 {momentum:.2f}%",
                indicators={
                    "momentum": momentum,
                    "period": self.period,
                    "atr": atr_val,
                },
            )
        
        return None
