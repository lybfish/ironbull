"""
HFT (High-Frequency Trading) Strategy

高频激进策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import rsi, ema_series
from .base import StrategyBase


class HFTStrategy(StrategyBase):
    """
    高频激进策略
    
    快速捕捉微小价格波动。
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "hft"
        self.name = "高频激进策略"
        
        # 参数
        self.profit_target = self.config.get("profit_target", 0.15)  # 止盈 %
        self.stop_loss = self.config.get("stop_loss", 0.1)  # 止损 %
        self.rsi_period = self.config.get("rsi_period", 7)
        self.ema_period = self.config.get("ema_period", 5)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析高频信号"""
        
        if len(candles) < 15:
            return None
        
        prices = [c["close"] for c in candles]
        volumes = [c.get("volume", 1000) for c in candles]
        current_price = prices[-1]
        
        rsi_val = rsi(prices, self.rsi_period)
        ema = ema_series(prices, self.ema_period)
        
        if rsi_val is None or not ema or len(ema) < 2:
            return None
        
        # 价格动量
        price_change = (prices[-1] - prices[-2]) / prices[-2] * 100 if len(prices) >= 2 else 0
        
        # 量能确认
        avg_volume = sum(volumes[-10:]) / 10 if len(volumes) >= 10 else volumes[-1]
        volume_spike = volumes[-1] > avg_volume * 1.5
        
        # 快速做多：RSI 超卖回升 + 价格站上 EMA + 动量向上
        if rsi_val < 35 and current_price > ema[-1] and price_change > 0:
            confidence = 65
            if volume_spike:
                confidence += 10
            if rsi_val < 25:
                confidence += 10
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=current_price * (1 - self.stop_loss / 100),
                take_profit=current_price * (1 + self.profit_target / 100),
                confidence=confidence,
                reason=f"高频买入：RSI={rsi_val:.1f}，价格动量={price_change:.3f}%",
                indicators={
                    "rsi": rsi_val,
                    "ema": ema[-1],
                    "price_change": price_change,
                    "volume_spike": volume_spike,
                },
            )
        
        # 快速做空：RSI 超买回落 + 价格跌破 EMA + 动量向下
        if rsi_val > 65 and current_price < ema[-1] and price_change < 0:
            confidence = 65
            if volume_spike:
                confidence += 10
            if rsi_val > 75:
                confidence += 10
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=current_price * (1 + self.stop_loss / 100),
                take_profit=current_price * (1 - self.profit_target / 100),
                confidence=confidence,
                reason=f"高频卖出：RSI={rsi_val:.1f}，价格动量={price_change:.3f}%",
                indicators={
                    "rsi": rsi_val,
                    "ema": ema[-1],
                    "price_change": price_change,
                    "volume_spike": volume_spike,
                },
            )
        
        return None
