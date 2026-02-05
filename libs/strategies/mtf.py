"""
MTF (Multi-Timeframe) Strategy

多时间框架共振策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import ema_series, rsi, macd
from .base import StrategyBase


class MTFStrategy(StrategyBase):
    """
    多时间框架共振策略
    
    通过短期、中期、长期指标同时确认趋势。
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "mtf"
        self.name = "多时间框架共振策略"
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析多时间框架共振信号"""
        
        if len(candles) < 60:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        # 短期指标
        ema_short = ema_series(prices, 10)
        rsi_short = rsi(prices, 7)
        
        # 中期指标
        ema_mid = ema_series(prices, 20)
        rsi_mid = rsi(prices, 14)
        
        # 长期指标
        ema_long = ema_series(prices, 50)
        macd_data = macd(prices, 12, 26, 9)
        
        if (not ema_short or not ema_mid or not ema_long or
            rsi_short is None or rsi_mid is None or macd_data is None):
            return None
        
        # 判断各级别趋势
        short_bullish = current_price > ema_short[-1] and rsi_short > 50
        mid_bullish = current_price > ema_mid[-1] and rsi_mid > 50
        long_bullish = current_price > ema_long[-1] and macd_data["histogram"] > 0
        
        short_bearish = current_price < ema_short[-1] and rsi_short < 50
        mid_bearish = current_price < ema_mid[-1] and rsi_mid < 50
        long_bearish = current_price < ema_long[-1] and macd_data["histogram"] < 0
        
        # 三级共振做多
        if short_bullish and mid_bullish and long_bullish:
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=min(ema_short[-1], ema_mid[-1]) * 0.99,
                take_profit=current_price * 1.03,
                confidence=85,
                reason="多时间框架共振做多：短/中/长期全部看多",
                indicators={
                    "ema_short": ema_short[-1],
                    "ema_mid": ema_mid[-1],
                    "ema_long": ema_long[-1],
                    "rsi_short": rsi_short,
                    "rsi_mid": rsi_mid,
                    "macd_histogram": macd_data["histogram"],
                },
            )
        
        # 三级共振做空
        if short_bearish and mid_bearish and long_bearish:
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=max(ema_short[-1], ema_mid[-1]) * 1.01,
                take_profit=current_price * 0.97,
                confidence=85,
                reason="多时间框架共振做空：短/中/长期全部看空",
                indicators={
                    "ema_short": ema_short[-1],
                    "ema_mid": ema_mid[-1],
                    "ema_long": ema_long[-1],
                    "rsi_short": rsi_short,
                    "rsi_mid": rsi_mid,
                    "macd_histogram": macd_data["histogram"],
                },
            )
        
        return None
