"""
Mean Reversion Strategy

均值回归策略
价格偏离均值过多时反向交易
"""

from typing import Dict, List, Optional
import statistics

from libs.contracts import StrategyOutput
from libs.indicators import sma, atr
from .base import StrategyBase


class MeanReversionStrategy(StrategyBase):
    """
    均值回归策略
    
    价格低于均值 N 个标准差 → BUY
    价格高于均值 N 个标准差 → SELL
    
    参数：
    - period: 均值周期（默认 20）
    - std_mult: 标准差倍数（默认 2.0）
    - exit_std: 出场标准差（默认 0.5）
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "mean_reversion"
        self.name = "均值回归策略"
        
        self.period = self.config.get("period", 20)
        self.std_mult = self.config.get("std_mult", 2.0)
        self.exit_std = self.config.get("exit_std", 0.5)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        
        if len(candles) < self.period + 1:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        # 计算均值和标准差
        recent_prices = prices[-self.period:]
        mean = statistics.mean(recent_prices)
        std = statistics.stdev(recent_prices) if len(recent_prices) > 1 else 0
        
        if std == 0:
            return None
        
        # 计算 Z-score
        z_score = (current_price - mean) / std
        
        atr_val = atr(candles, 14)
        
        # 价格低于均值 N 个标准差 → 做多（预期回归）
        if z_score < -self.std_mult:
            target = mean - (std * self.exit_std)  # 回归到接近均值
            stop = current_price - (atr_val * 2)
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=stop,
                take_profit=target,
                confidence=70 + min(abs(z_score) * 5, 20),
                reason=f"均值回归: Z-score={z_score:.2f}，价格偏低",
                indicators={
                    "mean": mean,
                    "std": std,
                    "z_score": z_score,
                    "atr": atr_val,
                },
            )
        
        # 价格高于均值 N 个标准差 → 做空（预期回归）
        if z_score > self.std_mult:
            target = mean + (std * self.exit_std)
            stop = current_price + (atr_val * 2)
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=stop,
                take_profit=target,
                confidence=70 + min(abs(z_score) * 5, 20),
                reason=f"均值回归: Z-score={z_score:.2f}，价格偏高",
                indicators={
                    "mean": mean,
                    "std": std,
                    "z_score": z_score,
                    "atr": atr_val,
                },
            )
        
        return None
