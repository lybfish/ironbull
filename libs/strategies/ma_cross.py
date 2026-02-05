"""
MA Cross Strategy

均线金叉死叉策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import sma_series, ema_series, atr
from .base import StrategyBase


class MACrossStrategy(StrategyBase):
    """
    均线金叉死叉策略
    
    金叉（快线上穿慢线）→ BUY
    死叉（快线下穿慢线）→ SELL
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "ma_cross"
        self.name = "均线金叉策略"
        
        # 策略参数
        self.fast_period = self.config.get("fast_ma", 5)
        self.slow_period = self.config.get("slow_ma", 20)
        self.use_ema = self.config.get("use_ema", False)
        self.atr_sl_mult = self.config.get("atr_sl_mult", 2.0)
        self.atr_tp_mult = self.config.get("atr_tp_mult", 4.0)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析均线金叉死叉信号"""
        
        if len(candles) < self.slow_period + 2:
            return None
        
        # 提取收盘价
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        # 计算均线
        if self.use_ema:
            fast_ma = ema_series(prices, self.fast_period)
            slow_ma = ema_series(prices, self.slow_period)
        else:
            fast_ma = sma_series(prices, self.fast_period)
            slow_ma = sma_series(prices, self.slow_period)
        
        # 检查数据有效性
        if fast_ma[-1] is None or fast_ma[-2] is None:
            return None
        if slow_ma[-1] is None or slow_ma[-2] is None:
            return None
        
        curr_fast = fast_ma[-1]
        curr_slow = slow_ma[-1]
        prev_fast = fast_ma[-2]
        prev_slow = slow_ma[-2]
        
        # 计算 ATR 用于止盈止损
        atr_val = atr(candles, period=14)
        
        # 金叉检测：快线从下方穿越慢线
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            divergence = ((curr_fast - curr_slow) / curr_slow) * 100
            confidence = min(90, 70 + abs(divergence) * 10)
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr_val * self.atr_sl_mult),
                take_profit=current_price + (atr_val * self.atr_tp_mult),
                confidence=confidence,
                reason=f"均线金叉: MA{self.fast_period}({curr_fast:.2f}) 上穿 MA{self.slow_period}({curr_slow:.2f})",
                indicators={
                    "fast_ma": curr_fast,
                    "slow_ma": curr_slow,
                    "divergence": divergence,
                    "atr": atr_val,
                },
            )
        
        # 死叉检测：快线从上方穿越慢线
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            divergence = ((curr_slow - curr_fast) / curr_slow) * 100
            confidence = min(90, 70 + abs(divergence) * 10)
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr_val * self.atr_sl_mult),
                take_profit=current_price - (atr_val * self.atr_tp_mult),
                confidence=confidence,
                reason=f"均线死叉: MA{self.fast_period}({curr_fast:.2f}) 下穿 MA{self.slow_period}({curr_slow:.2f})",
                indicators={
                    "fast_ma": curr_fast,
                    "slow_ma": curr_slow,
                    "divergence": divergence,
                    "atr": atr_val,
                },
            )
        
        # 无信号
        return None
