"""
Arbitrage Strategy

套利保守策略。
"""

from typing import Dict, List, Optional
import math

from libs.contracts import StrategyOutput
from .base import StrategyBase


class ArbitrageStrategy(StrategyBase):
    """
    套利保守策略
    
    基于价差的均值回归套利。
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "arbitrage"
        self.name = "套利保守策略"
        
        # 参数
        spread = self.config.get("spread_threshold", 0.5)
        self.spread_threshold = spread * 100 if spread < 0.1 else spread
        self.lookback = self.config.get("lookback", 20)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析套利信号"""
        
        if len(candles) < self.lookback:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        # 计算历史价格均值和标准差
        recent_prices = prices[-self.lookback:]
        avg_price = sum(recent_prices) / len(recent_prices)
        variance = sum((p - avg_price) ** 2 for p in recent_prices) / len(recent_prices)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0001
        
        # 价差和 Z 分数
        spread = ((current_price - avg_price) / avg_price) * 100
        z_score = (current_price - avg_price) / std_dev
        
        # 价格显著低于均值 - 买入套利
        if spread < -self.spread_threshold and z_score < -1.5:
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=current_price * 0.98,
                take_profit=avg_price,
                confidence=min(85, 65 + abs(z_score) * 10),
                reason=f"套利机会：价格低于均值 {abs(spread):.2f}%，Z分数={z_score:.2f}",
                indicators={
                    "spread": spread,
                    "z_score": z_score,
                    "avg_price": avg_price,
                    "std_dev": std_dev,
                },
            )
        
        # 价格显著高于均值 - 卖出套利
        if spread > self.spread_threshold and z_score > 1.5:
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=current_price * 1.02,
                take_profit=avg_price,
                confidence=min(85, 65 + abs(z_score) * 10),
                reason=f"套利机会：价格高于均值 {spread:.2f}%，Z分数={z_score:.2f}",
                indicators={
                    "spread": spread,
                    "z_score": z_score,
                    "avg_price": avg_price,
                    "std_dev": std_dev,
                },
            )
        
        return None
