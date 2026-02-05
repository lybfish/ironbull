"""
Hedge Strategy

多空双开对冲策略（智能补仓版）。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import rsi, bollinger, atr
from .base import StrategyBase


class HedgeStrategy(StrategyBase):
    """
    多空双开对冲策略
    
    同时开多空仓位，根据持仓状态智能补仓：
    - 无持仓 → 多空双开
    - 只有多仓 + RSI>50 → 补开空仓
    - 只有空仓 + RSI<50 → 补开多仓
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "hedge"
        self.name = "多空双开对冲策略"
        
        # 参数
        self.stop_loss_pct = self.config.get("stop_loss_pct", 5.0) / 100
        self.rsi_threshold = self.config.get("rsi_threshold", 50)
        self.boll_period = self.config.get("boll_period", 20)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析对冲信号"""
        
        if len(candles) < self.boll_period + 1:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        # 计算指标
        rsi_val = rsi(prices, 14)
        boll = bollinger(prices, self.boll_period)
        atr_val = atr(candles, period=14)
        
        if rsi_val is None or boll is None:
            return None
        
        # 默认无持仓
        if positions is None:
            positions = {"has_long": False, "has_short": False}
        
        has_long = positions.get("has_long", False)
        has_short = positions.get("has_short", False)
        
        boll_middle = boll["middle"]
        
        # 无持仓 → 多空双开
        if not has_long and not has_short:
            return StrategyOutput(
                symbol=symbol,
                signal_type="HEDGE",
                side="BOTH",
                entry_price=current_price,
                stop_loss=current_price * (1 - self.stop_loss_pct),
                take_profit=boll["upper"],
                confidence=65,
                reason=f"多空双开对冲，RSI={rsi_val:.1f}",
                indicators={
                    "rsi": rsi_val,
                    "boll_upper": boll["upper"],
                    "boll_middle": boll_middle,
                    "boll_lower": boll["lower"],
                    "atr": atr_val,
                },
            )
        
        # 只有多仓，检查是否应该补空仓
        if has_long and not has_short:
            if rsi_val > self.rsi_threshold or current_price > boll_middle:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="SELL",
                    entry_price=current_price,
                    stop_loss=current_price * (1 + self.stop_loss_pct),
                    take_profit=boll["lower"],
                    confidence=60,
                    reason=f"补开空仓恢复对冲，RSI={rsi_val:.1f}",
                    indicators={
                        "rsi": rsi_val,
                        "boll_middle": boll_middle,
                    },
                )
        
        # 只有空仓，检查是否应该补多仓
        if has_short and not has_long:
            if rsi_val < self.rsi_threshold or current_price < boll_middle:
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="BUY",
                    entry_price=current_price,
                    stop_loss=current_price * (1 - self.stop_loss_pct),
                    take_profit=boll["upper"],
                    confidence=60,
                    reason=f"补开多仓恢复对冲，RSI={rsi_val:.1f}",
                    indicators={
                        "rsi": rsi_val,
                        "boll_middle": boll_middle,
                    },
                )
        
        return None
