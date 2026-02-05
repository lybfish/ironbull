"""
RSI Strategy

纯 RSI 超买超卖策略
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import rsi, atr
from .base import StrategyBase


class RSIStrategy(StrategyBase):
    """
    RSI 超买超卖策略
    
    RSI 超卖 (< 30) → BUY
    RSI 超买 (> 70) → SELL
    
    参数：
    - rsi_period: RSI 周期（默认 14）
    - rsi_overbought: 超买阈值（默认 70）
    - rsi_oversold: 超卖阈值（默认 30）
    - sl_atr_mult: 止损 ATR 倍数（默认 2.0）
    - tp_atr_mult: 止盈 ATR 倍数（默认 3.0）
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "rsi"
        self.name = "RSI超买超卖策略"
        
        # RSI 参数
        self.rsi_period = self.config.get("rsi_period", 14)
        self.rsi_overbought = self.config.get("rsi_overbought", 70)
        self.rsi_oversold = self.config.get("rsi_oversold", 30)
        
        # 止盈止损
        self.sl_atr_mult = self.config.get("sl_atr_mult", 2.0)
        self.tp_atr_mult = self.config.get("tp_atr_mult", 3.0)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析 RSI 信号"""
        
        if len(candles) < self.rsi_period + 1:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        # 计算 RSI
        rsi_val = rsi(prices, self.rsi_period)
        atr_val = atr(candles, period=14)
        
        if rsi_val is None:
            return None
        
        # 计算前一根 K 线的 RSI（用于判断交叉）
        prev_rsi = rsi(prices[:-1], self.rsi_period)
        
        # RSI 从超卖区上穿 → 做多
        if prev_rsi and prev_rsi < self.rsi_oversold and rsi_val >= self.rsi_oversold:
            confidence = 70
            if prev_rsi < 20:
                confidence += 15
            elif prev_rsi < 25:
                confidence += 10
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr_val * self.sl_atr_mult),
                take_profit=current_price + (atr_val * self.tp_atr_mult),
                confidence=confidence,
                reason=f"RSI从超卖区上穿 ({prev_rsi:.1f} -> {rsi_val:.1f})",
                indicators={
                    "rsi": rsi_val,
                    "prev_rsi": prev_rsi,
                    "atr": atr_val,
                },
            )
        
        # RSI 从超买区下穿 → 做空
        if prev_rsi and prev_rsi > self.rsi_overbought and rsi_val <= self.rsi_overbought:
            confidence = 70
            if prev_rsi > 80:
                confidence += 15
            elif prev_rsi > 75:
                confidence += 10
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr_val * self.sl_atr_mult),
                take_profit=current_price - (atr_val * self.tp_atr_mult),
                confidence=confidence,
                reason=f"RSI从超买区下穿 ({prev_rsi:.1f} -> {rsi_val:.1f})",
                indicators={
                    "rsi": rsi_val,
                    "prev_rsi": prev_rsi,
                    "atr": atr_val,
                },
            )
        
        # 强超卖（直接入场）
        if rsi_val < 20:
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr_val * self.sl_atr_mult),
                take_profit=current_price + (atr_val * self.tp_atr_mult),
                confidence=80,
                reason=f"RSI强超卖 ({rsi_val:.1f})",
                indicators={"rsi": rsi_val, "atr": atr_val},
            )
        
        # 强超买（直接入场）
        if rsi_val > 80:
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr_val * self.sl_atr_mult),
                take_profit=current_price - (atr_val * self.tp_atr_mult),
                confidence=80,
                reason=f"RSI强超买 ({rsi_val:.1f})",
                indicators={"rsi": rsi_val, "atr": atr_val},
            )
        
        return None
