"""
Reversal Hedge Strategy

极值反转对冲策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import rsi, bollinger, atr
from .base import StrategyBase


class ReversalHedgeStrategy(StrategyBase):
    """
    极值反转对冲策略
    
    在极端行情下建立对冲仓位，等待反转。
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "reversal_hedge"
        self.name = "极值反转对冲策略"
        
        # 参数
        self.rsi_extreme_low = self.config.get("rsi_extreme_low", 20)
        self.rsi_extreme_high = 100 - self.rsi_extreme_low
        self.boll_std = self.config.get("boll_std", 2.5)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析极值反转对冲信号"""
        
        if len(candles) < 21:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        rsi_val = rsi(prices, 14)
        boll = bollinger(prices, 20, self.boll_std)
        atr_val = atr(candles, period=14)
        
        if rsi_val is None or boll is None:
            return None
        
        # 极度超卖 - 对冲偏向多头
        if rsi_val < self.rsi_extreme_low and current_price < boll["lower"]:
            extreme_level = (self.rsi_extreme_low - rsi_val) / self.rsi_extreme_low
            confidence = min(85, 70 + extreme_level * 30)
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="HEDGE",
                side="BUY",
                entry_price=current_price,
                stop_loss=current_price * 0.95,
                take_profit=boll["middle"],
                confidence=int(confidence),
                reason=f"极度超卖(RSI={rsi_val:.1f})，建立偏多对冲仓位",
                indicators={
                    "rsi": rsi_val,
                    "boll_lower": boll["lower"],
                    "boll_middle": boll["middle"],
                    "extreme_level": extreme_level,
                },
            )
        
        # 极度超买 - 对冲偏向空头
        if rsi_val > self.rsi_extreme_high and current_price > boll["upper"]:
            extreme_level = (rsi_val - self.rsi_extreme_high) / (100 - self.rsi_extreme_high)
            confidence = min(85, 70 + extreme_level * 30)
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="HEDGE",
                side="SELL",
                entry_price=current_price,
                stop_loss=current_price * 1.05,
                take_profit=boll["middle"],
                confidence=int(confidence),
                reason=f"极度超买(RSI={rsi_val:.1f})，建立偏空对冲仓位",
                indicators={
                    "rsi": rsi_val,
                    "boll_upper": boll["upper"],
                    "boll_middle": boll["middle"],
                    "extreme_level": extreme_level,
                },
            )
        
        # 从极值回归中轨 - 平仓信号
        if 40 < rsi_val < 60 and abs(current_price - boll["middle"]) / boll["middle"] < 0.01:
            return StrategyOutput(
                symbol=symbol,
                signal_type="CLOSE",
                side="BOTH",
                entry_price=current_price,
                stop_loss=None,
                take_profit=None,
                confidence=70,
                reason=f"价格回归中轨，RSI={rsi_val:.1f}，平仓对冲",
                indicators={
                    "rsi": rsi_val,
                    "boll_middle": boll["middle"],
                },
            )
        
        return None
