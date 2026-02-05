"""
Trend Add Strategy

趋势加仓策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import ema_series, rsi, atr
from .base import StrategyBase


class TrendAddStrategy(StrategyBase):
    """
    趋势加仓策略
    
    在趋势确立后，回调时逐步加仓。
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "trend_add"
        self.name = "趋势加仓策略"
        
        # 参数
        self.ema_period = self.config.get("ema_period", 20)
        self.pullback_pct = self.config.get("pullback_pct", 1.0)  # 回调幅度 %
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析趋势加仓信号"""
        
        if len(candles) < self.ema_period + 10:
            return None
        
        prices = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        current_price = prices[-1]
        
        ema = ema_series(prices, self.ema_period)
        rsi_val = rsi(prices, 14)
        atr_val = atr(candles, period=14)
        
        if not ema or len(ema) < 5 or rsi_val is None:
            return None
        
        # 判断趋势方向
        ema_slope = (ema[-1] - ema[-5]) / ema[-5] * 100
        
        # 上升趋势中回调加仓
        if ema_slope > 0.5 and current_price > ema[-1]:
            recent_high = max(highs[-10:])
            pullback = (recent_high - current_price) / recent_high * 100
            
            # 回调到一定幅度且 RSI 未超买
            if self.pullback_pct <= pullback <= self.pullback_pct * 2 and rsi_val < 65:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="ADD",
                    side="BUY",
                    entry_price=current_price,
                    stop_loss=ema[-1] * 0.98,
                    take_profit=recent_high * 1.02,
                    confidence=75,
                    reason=f"上升趋势回调 {pullback:.2f}%，加仓做多",
                    indicators={
                        "ema": ema[-1],
                        "ema_slope": ema_slope,
                        "recent_high": recent_high,
                        "pullback": pullback,
                        "rsi": rsi_val,
                    },
                )
        
        # 下降趋势中反弹加仓
        if ema_slope < -0.5 and current_price < ema[-1]:
            recent_low = min(lows[-10:])
            bounce = (current_price - recent_low) / recent_low * 100
            
            # 反弹到一定幅度且 RSI 未超卖
            if self.pullback_pct <= bounce <= self.pullback_pct * 2 and rsi_val > 35:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="ADD",
                    side="SELL",
                    entry_price=current_price,
                    stop_loss=ema[-1] * 1.02,
                    take_profit=recent_low * 0.98,
                    confidence=75,
                    reason=f"下降趋势反弹 {bounce:.2f}%，加仓做空",
                    indicators={
                        "ema": ema[-1],
                        "ema_slope": ema_slope,
                        "recent_low": recent_low,
                        "bounce": bounce,
                        "rsi": rsi_val,
                    },
                )
        
        return None
