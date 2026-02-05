"""
Scalping Strategy

剥头皮策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import rsi
from .base import StrategyBase


class ScalpingStrategy(StrategyBase):
    """
    剥头皮策略
    
    快进快出，利用 RSI 超买超卖捕捉小幅波动。
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "scalping"
        self.name = "剥头皮策略"
        
        # 参数
        self.scalp_target = self.config.get("scalp_target", 0.3)  # 止盈 %
        self.stop_loss = self.config.get("stop_loss", 0.2)  # 止损 %
        self.rsi_oversold = self.config.get("rsi_oversold", 30)
        self.rsi_overbought = self.config.get("rsi_overbought", 70)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析剥头皮信号"""
        
        if len(candles) < 15:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        rsi_val = rsi(prices, 14)
        
        if rsi_val is None:
            return None
        
        # 超卖快速买入
        if rsi_val < self.rsi_oversold:
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=current_price * (1 - self.stop_loss / 100),
                take_profit=current_price * (1 + self.scalp_target / 100),
                confidence=70,
                reason=f"RSI超卖({rsi_val:.1f})，快速买入",
                indicators={"rsi": rsi_val},
            )
        
        # 超买快速卖出
        if rsi_val > self.rsi_overbought:
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=current_price * (1 + self.stop_loss / 100),
                take_profit=current_price * (1 - self.scalp_target / 100),
                confidence=70,
                reason=f"RSI超买({rsi_val:.1f})，快速卖出",
                indicators={"rsi": rsi_val},
            )
        
        return None
