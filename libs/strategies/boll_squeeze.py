"""
Bollinger Squeeze Strategy

布林带压缩策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import bollinger, atr
from .base import StrategyBase


class BollSqueezeStrategy(StrategyBase):
    """
    布林带压缩策略
    
    布林带宽度收窄到阈值以下时，预期即将突破。
    价格在中轨上方 → 预期向上突破 → BUY
    价格在中轨下方 → 预期向下突破 → SELL
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "boll_squeeze"
        self.name = "布林压缩策略"
        
        # 压缩阈值（带宽百分比）
        self.squeeze_threshold = self.config.get("squeeze_threshold", 2.0)
        
        # 布林带参数
        self.boll_period = self.config.get("boll_period", 20)
        self.boll_std = self.config.get("boll_std", 2.0)
        
        # 止盈止损倍数
        self.sl_atr_mult = self.config.get("sl_atr_mult", 1.5)
        self.tp_atr_mult = self.config.get("tp_atr_mult", 3.0)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析布林压缩信号"""
        
        if len(candles) < self.boll_period:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        # 计算指标
        boll = bollinger(prices, self.boll_period, self.boll_std)
        atr_val = atr(candles, period=14)
        
        if boll is None:
            return None
        
        # 计算带宽百分比
        boll_width = boll["bandwidth"]
        
        # 布林带压缩
        if boll_width < self.squeeze_threshold:
            # 价格在中轨上方 → 预期向上突破
            if current_price > boll["middle"]:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="BUY",
                    entry_price=current_price,
                    stop_loss=boll["middle"],
                    take_profit=boll["upper"] + (atr_val * self.tp_atr_mult),
                    confidence=70,
                    reason=f"布林带压缩({boll_width:.2f}%)，价格在中轨上方，预期向上突破",
                    indicators={
                        "boll_width": boll_width,
                        "boll_middle": boll["middle"],
                        "boll_upper": boll["upper"],
                        "atr": atr_val,
                    },
                )
            
            # 价格在中轨下方 → 预期向下突破
            if current_price < boll["middle"]:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="SELL",
                    entry_price=current_price,
                    stop_loss=boll["middle"],
                    take_profit=boll["lower"] - (atr_val * self.tp_atr_mult),
                    confidence=70,
                    reason=f"布林带压缩({boll_width:.2f}%)，价格在中轨下方，预期向下突破",
                    indicators={
                        "boll_width": boll_width,
                        "boll_middle": boll["middle"],
                        "boll_lower": boll["lower"],
                        "atr": atr_val,
                    },
                )
        
        return None
