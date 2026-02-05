"""
Keltner Channel Strategy

凯尔特纳通道策略
基于 EMA 和 ATR 的通道突破
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import ema, atr
from .base import StrategyBase


class KeltnerStrategy(StrategyBase):
    """
    凯尔特纳通道策略
    
    价格突破上轨 → BUY（趋势跟踪）
    价格突破下轨 → SELL（趋势跟踪）
    
    或者反向使用（均值回归模式）
    
    参数：
    - ema_period: EMA 周期（默认 20）
    - atr_period: ATR 周期（默认 10）
    - atr_mult: ATR 倍数（默认 2.0）
    - mode: 模式 trend(趋势) / reversion(回归)
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "keltner"
        self.name = "凯尔特纳通道策略"
        
        self.ema_period = self.config.get("ema_period", 20)
        self.atr_period = self.config.get("atr_period", 10)
        self.atr_mult = self.config.get("atr_mult", 2.0)
        self.mode = self.config.get("mode", "trend")
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        
        if len(candles) < max(self.ema_period, self.atr_period) + 1:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        # 计算通道
        middle = ema(prices, self.ema_period)
        atr_val = atr(candles, self.atr_period)
        
        if middle is None or atr_val is None:
            return None
        
        upper = middle + (atr_val * self.atr_mult)
        lower = middle - (atr_val * self.atr_mult)
        
        if self.mode == "trend":
            # 趋势模式：突破追涨杀跌
            if current_price > upper:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="BUY",
                    entry_price=current_price,
                    stop_loss=middle,
                    take_profit=current_price + (atr_val * 3),
                    confidence=75,
                    reason=f"凯尔特纳突破上轨: {current_price:.2f} > {upper:.2f}",
                    indicators={
                        "upper": upper,
                        "middle": middle,
                        "lower": lower,
                        "atr": atr_val,
                    },
                )
            
            if current_price < lower:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="SELL",
                    entry_price=current_price,
                    stop_loss=middle,
                    take_profit=current_price - (atr_val * 3),
                    confidence=75,
                    reason=f"凯尔特纳突破下轨: {current_price:.2f} < {lower:.2f}",
                    indicators={
                        "upper": upper,
                        "middle": middle,
                        "lower": lower,
                        "atr": atr_val,
                    },
                )
        else:
            # 回归模式：触及边界反转
            if current_price <= lower * 1.01:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="BUY",
                    entry_price=current_price,
                    stop_loss=lower - (atr_val * 0.5),
                    take_profit=middle,
                    confidence=70,
                    reason=f"凯尔特纳触及下轨反弹",
                    indicators={
                        "upper": upper,
                        "middle": middle,
                        "lower": lower,
                    },
                )
            
            if current_price >= upper * 0.99:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="SELL",
                    entry_price=current_price,
                    stop_loss=upper + (atr_val * 0.5),
                    take_profit=middle,
                    confidence=70,
                    reason=f"凯尔特纳触及上轨回落",
                    indicators={
                        "upper": upper,
                        "middle": middle,
                        "lower": lower,
                    },
                )
        
        return None
