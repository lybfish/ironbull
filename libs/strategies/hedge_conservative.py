"""
Hedge Conservative Strategy

合约对冲保守策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import rsi, bollinger, atr
from .base import StrategyBase


class HedgeConservativeStrategy(StrategyBase):
    """
    合约对冲保守策略
    
    基于布林带建立对冲仓位，智能补仓。
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "hedge_conservative"
        self.name = "合约对冲保守策略"
        
        # 参数
        self.boll_period = self.config.get("boll_period", 20)
        self.boll_std = self.config.get("boll_std", 2.0)
        self.stop_loss_pct = self.config.get("stop_loss_pct", 5.0) / 100
        self.rsi_threshold = self.config.get("rsi_threshold", 50)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析对冲保守信号"""
        
        if len(candles) < self.boll_period + 1:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        boll = bollinger(prices, self.boll_period, self.boll_std)
        rsi_val = rsi(prices, 14)
        atr_val = atr(candles, period=14)
        
        if boll is None or rsi_val is None:
            return None
        
        # 默认无持仓
        if positions is None:
            positions = {"has_long": False, "has_short": False}
        
        has_long = positions.get("has_long", False)
        has_short = positions.get("has_short", False)
        
        band_width = boll["bandwidth"]
        price_position = (current_price - boll["lower"]) / (boll["upper"] - boll["lower"])
        boll_middle = boll["middle"]
        
        # 无持仓 → 建立对冲仓位
        if not has_long and not has_short:
            if band_width > 2.0:
                confidence = 70 if 0.35 < price_position < 0.65 else 60
                position_desc = "中轨附近" if 0.35 < price_position < 0.65 else \
                               ("下轨附近" if price_position < 0.35 else "上轨附近")
                
                return StrategyOutput(
                    symbol=symbol,
                    signal_type="HEDGE",
                    side="BOTH",
                    entry_price=current_price,
                    stop_loss=current_price * (1 - self.stop_loss_pct),
                    take_profit=boll["upper"],
                    confidence=confidence,
                    reason=f"建立对冲仓位：波动率 {band_width:.2f}%，价格在{position_desc}",
                    indicators={
                        "boll_upper": boll["upper"],
                        "boll_middle": boll_middle,
                        "boll_lower": boll["lower"],
                        "band_width": band_width,
                        "rsi": rsi_val,
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
                    confidence=65,
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
                    confidence=65,
                    reason=f"补开多仓恢复对冲，RSI={rsi_val:.1f}",
                    indicators={
                        "rsi": rsi_val,
                        "boll_middle": boll_middle,
                    },
                )
        
        return None
