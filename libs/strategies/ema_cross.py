"""
EMA Cross Strategy

指数移动平均线交叉策略
比 SMA 对价格变化更敏感
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import ema, atr
from .base import StrategyBase


class EMACrossStrategy(StrategyBase):
    """
    EMA 交叉策略
    
    快线上穿慢线 → BUY
    快线下穿慢线 → SELL
    
    参数：
    - fast_ema: 快线周期（默认 9）
    - slow_ema: 慢线周期（默认 21）
    - signal_ema: 信号线周期（默认 5，用于过滤）
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "ema_cross"
        self.name = "EMA交叉策略"
        
        self.fast_ema = self.config.get("fast_ema", 9)
        self.slow_ema = self.config.get("slow_ema", 21)
        self.signal_ema = self.config.get("signal_ema", 5)
        
        self.sl_atr_mult = self.config.get("sl_atr_mult", 2.0)
        self.tp_atr_mult = self.config.get("tp_atr_mult", 3.0)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        
        if len(candles) < self.slow_ema + 2:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        # 计算 EMA
        fast = ema(prices, self.fast_ema)
        slow = ema(prices, self.slow_ema)
        signal = ema(prices, self.signal_ema)
        
        # 前一根 K 线的 EMA
        fast_prev = ema(prices[:-1], self.fast_ema)
        slow_prev = ema(prices[:-1], self.slow_ema)
        
        atr_val = atr(candles, 14)
        
        if None in [fast, slow, fast_prev, slow_prev]:
            return None
        
        # 金叉：快线从下方穿过慢线
        if fast_prev <= slow_prev and fast > slow:
            # 信号线确认
            if signal and current_price > signal:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="BUY",
                    entry_price=current_price,
                    stop_loss=current_price - (atr_val * self.sl_atr_mult),
                    take_profit=current_price + (atr_val * self.tp_atr_mult),
                    confidence=75,
                    reason=f"EMA金叉 ({self.fast_ema}/{self.slow_ema})",
                    indicators={
                        "fast_ema": fast,
                        "slow_ema": slow,
                        "signal_ema": signal,
                        "atr": atr_val,
                    },
                )
        
        # 死叉：快线从上方穿过慢线
        if fast_prev >= slow_prev and fast < slow:
            if signal and current_price < signal:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="SELL",
                    entry_price=current_price,
                    stop_loss=current_price + (atr_val * self.sl_atr_mult),
                    take_profit=current_price - (atr_val * self.tp_atr_mult),
                    confidence=75,
                    reason=f"EMA死叉 ({self.fast_ema}/{self.slow_ema})",
                    indicators={
                        "fast_ema": fast,
                        "slow_ema": slow,
                        "signal_ema": signal,
                        "atr": atr_val,
                    },
                )
        
        return None
