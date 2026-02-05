"""
RSI + Bollinger Bands Strategy

RSI 超买超卖 + 布林带边界策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import rsi, bollinger
from .base import StrategyBase


class RSIBollStrategy(StrategyBase):
    """
    RSI + 布林带震荡策略
    
    超卖 + 触及布林下轨 → BUY
    超买 + 触及布林上轨 → SELL
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "rsi_boll"
        self.name = "RSI布林带震荡策略"
        
        # RSI 参数
        self.rsi_period = self.config.get("rsi_period", 14)
        self.rsi_overbought = self.config.get("rsi_overbought", 70)
        self.rsi_oversold = self.config.get("rsi_oversold", 30)
        
        # 布林带参数
        self.boll_period = self.config.get("boll_period", 20)
        self.boll_std = self.config.get("boll_std", 2.0)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析 RSI + 布林带信号"""
        
        if len(candles) < max(self.rsi_period + 1, self.boll_period):
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        # 计算指标
        rsi_val = rsi(prices, self.rsi_period)
        boll = bollinger(prices, self.boll_period, self.boll_std)
        
        if rsi_val is None or boll is None:
            return None
        
        # 超卖 + 触及布林下轨 → 做多
        if rsi_val < self.rsi_oversold and current_price <= boll["lower"] * 1.01:
            confidence = 60
            if rsi_val < 20:
                confidence += 20
            elif rsi_val < 25:
                confidence += 15
            elif rsi_val < 30:
                confidence += 10
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=boll["lower"] * 0.98,
                take_profit=boll["middle"],
                confidence=confidence,
                reason=f"RSI超卖({rsi_val:.1f}) + 触及布林下轨",
                indicators={
                    "rsi": rsi_val,
                    "boll_lower": boll["lower"],
                    "boll_middle": boll["middle"],
                    "boll_upper": boll["upper"],
                },
            )
        
        # 超买 + 触及布林上轨 → 做空
        if rsi_val > self.rsi_overbought and current_price >= boll["upper"] * 0.99:
            confidence = 60
            if rsi_val > 80:
                confidence += 20
            elif rsi_val > 75:
                confidence += 15
            elif rsi_val > 70:
                confidence += 10
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=boll["upper"] * 1.02,
                take_profit=boll["middle"],
                confidence=confidence,
                reason=f"RSI超买({rsi_val:.1f}) + 触及布林上轨",
                indicators={
                    "rsi": rsi_val,
                    "boll_lower": boll["lower"],
                    "boll_middle": boll["middle"],
                    "boll_upper": boll["upper"],
                },
            )
        
        return None
