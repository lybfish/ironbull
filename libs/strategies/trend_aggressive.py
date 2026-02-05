"""
Trend Aggressive Strategy

合约趋势激进策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import ema_series, rsi, atr
from .base import StrategyBase


class TrendAggressiveStrategy(StrategyBase):
    """
    合约趋势激进策略
    
    EMA 金叉/死叉 + RSI 确认，激进入场。
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "trend_aggressive"
        self.name = "合约趋势激进策略"
        
        # 参数
        self.ema_fast = self.config.get("ema_fast", 8)
        self.ema_slow = self.config.get("ema_slow", 21)
        self.atr_multiplier = self.config.get("atr_multiplier", 1.5)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析激进趋势信号"""
        
        if len(candles) < self.ema_slow + 2:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        # 计算指标
        ema_fast = ema_series(prices, self.ema_fast)
        ema_slow = ema_series(prices, self.ema_slow)
        rsi_val = rsi(prices, 14)
        atr_val = atr(candles, period=14)
        
        if len(ema_fast) < 2 or len(ema_slow) < 2 or rsi_val is None:
            return None
        
        curr_fast = ema_fast[-1]
        curr_slow = ema_slow[-1]
        prev_fast = ema_fast[-2]
        prev_slow = ema_slow[-2]
        
        # 激进做多：EMA 金叉 + RSI 不超买 + 价格站上快线
        if (prev_fast <= prev_slow and curr_fast > curr_slow and
            rsi_val < 65 and current_price > curr_fast):
            
            trend_strength = ((curr_fast - curr_slow) / curr_slow) * 100
            confidence = min(90, 75 + trend_strength * 5)
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr_val * self.atr_multiplier),
                take_profit=current_price + (atr_val * 3),
                confidence=int(confidence),
                reason=f"激进趋势：EMA金叉+价格站上均线，RSI={rsi_val:.1f}",
                indicators={
                    "ema_fast": curr_fast,
                    "ema_slow": curr_slow,
                    "rsi": rsi_val,
                    "atr": atr_val,
                    "trend_strength": trend_strength,
                },
            )
        
        # 激进做空：EMA 死叉 + RSI 不超卖 + 价格跌破快线
        if (prev_fast >= prev_slow and curr_fast < curr_slow and
            rsi_val > 35 and current_price < curr_fast):
            
            trend_strength = ((curr_slow - curr_fast) / curr_slow) * 100
            confidence = min(90, 75 + trend_strength * 5)
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr_val * self.atr_multiplier),
                take_profit=current_price - (atr_val * 3),
                confidence=int(confidence),
                reason=f"激进趋势：EMA死叉+价格跌破均线，RSI={rsi_val:.1f}",
                indicators={
                    "ema_fast": curr_fast,
                    "ema_slow": curr_slow,
                    "rsi": rsi_val,
                    "atr": atr_val,
                    "trend_strength": trend_strength,
                },
            )
        
        return None
