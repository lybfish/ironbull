"""
MACD Strategy

MACD 金叉死叉策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import macd, atr
from .base import StrategyBase


class MACDStrategy(StrategyBase):
    """
    MACD 策略
    
    MACD 金叉（柱状图转正）→ BUY
    MACD 死叉（柱状图转负）→ SELL
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "macd"
        self.name = "MACD策略"
        
        # MACD 参数
        self.fast = self.config.get("macd_fast", 12)
        self.slow = self.config.get("macd_slow", 26)
        self.signal = self.config.get("macd_signal", 9)
        
        # 止盈止损倍数
        self.sl_atr_mult = self.config.get("sl_atr_mult", 2.0)
        self.tp_atr_mult = self.config.get("tp_atr_mult", 3.0)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析 MACD 信号"""
        
        if len(candles) < self.slow + self.signal:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        # 计算指标
        macd_data = macd(prices, self.fast, self.slow, self.signal)
        atr_val = atr(candles, period=14)
        
        if macd_data is None:
            return None
        
        macd_line = macd_data["macd"]
        signal_line = macd_data["signal"]
        histogram = macd_data["histogram"]
        
        # MACD 金叉 - 买入
        if macd_line > signal_line and histogram > 0:
            confidence = min(85, 65 + abs(histogram) * 5)
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr_val * self.sl_atr_mult),
                take_profit=current_price + (atr_val * self.tp_atr_mult),
                confidence=confidence,
                reason=f"MACD金叉，柱状图转正({histogram:.4f})",
                indicators={
                    "macd": macd_line,
                    "signal": signal_line,
                    "histogram": histogram,
                    "atr": atr_val,
                },
            )
        
        # MACD 死叉 - 做空
        if macd_line < signal_line and histogram < 0:
            confidence = min(85, 65 + abs(histogram) * 5)
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr_val * self.sl_atr_mult),
                take_profit=current_price - (atr_val * self.tp_atr_mult),
                confidence=confidence,
                reason=f"MACD死叉，柱状图转负({histogram:.4f})",
                indicators={
                    "macd": macd_line,
                    "signal": signal_line,
                    "histogram": histogram,
                    "atr": atr_val,
                },
            )
        
        return None
