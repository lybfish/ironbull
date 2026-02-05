"""
Swing Trading Strategy

波段交易策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import sma_series, atr
from .base import StrategyBase


class SwingStrategy(StrategyBase):
    """
    波段交易策略
    
    价格突破/跌破均线时入场，持有较长时间。
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "swing"
        self.name = "波段交易策略"
        
        # 参数
        self.ma_period = self.config.get("ma_period", 20)
        self.swing_target = self.config.get("swing_target", 5.0)  # 目标盈利 %
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析波段信号"""
        
        if len(candles) < self.ma_period + 2:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        prev_price = prices[-2]
        
        # 计算均线
        ma = sma_series(prices, self.ma_period)
        atr_val = atr(candles, period=14)
        
        if len(ma) < 2 or ma[-1] is None or ma[-2] is None:
            return None
        
        ma_value = ma[-1]
        prev_ma = ma[-2]
        
        # 价格突破均线向上
        if prev_price <= prev_ma and current_price > ma_value:
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr_val * 2),
                take_profit=current_price * (1 + self.swing_target / 100),
                confidence=75,
                reason=f"价格突破 MA{self.ma_period}，波段买入",
                indicators={
                    "ma": ma_value,
                    "atr": atr_val,
                },
            )
        
        # 价格跌破均线向下
        if prev_price >= prev_ma and current_price < ma_value:
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr_val * 2),
                take_profit=current_price * (1 - self.swing_target / 100),
                confidence=75,
                reason=f"价格跌破 MA{self.ma_period}，波段卖出",
                indicators={
                    "ma": ma_value,
                    "atr": atr_val,
                },
            )
        
        return None
