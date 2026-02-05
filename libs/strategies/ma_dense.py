"""
MA Dense Strategy

均线密集策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import sma_series, ema_series, atr
from .base import StrategyBase


class MADenseStrategy(StrategyBase):
    """
    均线密集策略
    
    多条均线密集后突破入场。
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "ma_dense"
        self.name = "均线密集交叉策略"
        
        # 参数
        self.ma_periods = self.config.get("ma_periods", [5, 10, 20, 60])
        self.use_ema = self.config.get("ma_type", "SMA") == "EMA"
        self.sl_atr_mult = self.config.get("sl_atr_mult", 1.5)
        self.tp_atr_mult = self.config.get("tp_atr_mult", 3.0)
        self.dense_threshold = self.config.get("dense_threshold", 2.0)  # 密集阈值 %
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析均线密集信号"""
        
        max_period = max(self.ma_periods)
        if len(candles) < max_period + 1:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        atr_val = atr(candles, period=14)
        
        # 计算多条均线
        ma_values = []
        for period in self.ma_periods:
            if self.use_ema:
                ma = ema_series(prices, period)
            else:
                ma = sma_series(prices, period)
            if ma and ma[-1] is not None:
                ma_values.append(ma[-1])
        
        if len(ma_values) < 3:
            return None
        
        # 检测均线密集
        max_ma = max(ma_values)
        min_ma = min(ma_values)
        dense_ratio = ((max_ma - min_ma) / min_ma) * 100
        
        # 均线密集且价格突破
        if dense_ratio < self.dense_threshold:
            if current_price > max_ma:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="BUY",
                    entry_price=current_price,
                    stop_loss=min_ma,
                    take_profit=current_price + (atr_val * self.tp_atr_mult),
                    confidence=75,
                    reason=f"均线密集后向上突破，密集度 {dense_ratio:.2f}%",
                    indicators={
                        "dense_ratio": dense_ratio,
                        "max_ma": max_ma,
                        "min_ma": min_ma,
                        "atr": atr_val,
                    },
                )
            
            if current_price < min_ma:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="SELL",
                    entry_price=current_price,
                    stop_loss=max_ma,
                    take_profit=current_price - (atr_val * self.tp_atr_mult),
                    confidence=75,
                    reason=f"均线密集后向下突破，密集度 {dense_ratio:.2f}%",
                    indicators={
                        "dense_ratio": dense_ratio,
                        "max_ma": max_ma,
                        "min_ma": min_ma,
                        "atr": atr_val,
                    },
                )
        
        return None
