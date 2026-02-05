"""
Reversal Strategy

反转策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import rsi, atr
from .base import StrategyBase


class ReversalStrategy(StrategyBase):
    """
    反转策略
    
    在 RSI 极值区域预期反转入场。
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "reversal"
        self.name = "反转策略"
        
        # 参数
        self.rsi_extreme = self.config.get("rsi_extreme", 20)  # 极值阈值
        self.sl_atr_mult = self.config.get("sl_atr_mult", 2.0)
        self.tp_atr_mult = self.config.get("tp_atr_mult", 4.0)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析反转信号"""
        
        if len(candles) < 15:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        rsi_val = rsi(prices, 14)
        atr_val = atr(candles, period=14)
        
        if rsi_val is None:
            return None
        
        # 极度超卖 → 做多
        if rsi_val < self.rsi_extreme:
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr_val * self.sl_atr_mult),
                take_profit=current_price + (atr_val * self.tp_atr_mult),
                confidence=80,
                reason=f"RSI极度超卖({rsi_val:.1f})，预期反转",
                indicators={
                    "rsi": rsi_val,
                    "atr": atr_val,
                },
            )
        
        # 极度超买 → 做空
        if rsi_val > (100 - self.rsi_extreme):
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr_val * self.sl_atr_mult),
                take_profit=current_price - (atr_val * self.tp_atr_mult),
                confidence=80,
                reason=f"RSI极度超买({rsi_val:.1f})，预期反转",
                indicators={
                    "rsi": rsi_val,
                    "atr": atr_val,
                },
            )
        
        return None
