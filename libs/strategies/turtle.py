"""
Turtle Trading Strategy

海龟交易法则 - 经典趋势跟踪策略
基于唐奇安通道突破
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from libs.indicators import atr
from .base import StrategyBase


def donchian_channel(candles: List[Dict], period: int) -> Optional[Dict]:
    """计算唐奇安通道"""
    if len(candles) < period:
        return None
    
    recent = candles[-period:]
    upper = max(c["high"] for c in recent)
    lower = min(c["low"] for c in recent)
    middle = (upper + lower) / 2
    
    return {"upper": upper, "lower": lower, "middle": middle}


class TurtleStrategy(StrategyBase):
    """
    海龟交易策略
    
    价格突破 N 日最高价 → BUY
    价格跌破 N 日最低价 → SELL
    
    止损使用 ATR 倍数
    
    参数：
    - entry_period: 入场通道周期（默认 20）
    - exit_period: 出场通道周期（默认 10）
    - atr_period: ATR 周期（默认 20）
    - risk_unit: 风险单位 ATR 倍数（默认 2）
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "turtle"
        self.name = "海龟交易策略"
        
        self.entry_period = self.config.get("entry_period", 20)
        self.exit_period = self.config.get("exit_period", 10)
        self.atr_period = self.config.get("atr_period", 20)
        self.risk_unit = self.config.get("risk_unit", 2)
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        
        if len(candles) < max(self.entry_period, self.atr_period) + 1:
            return None
        
        current_price = candles[-1]["close"]
        current_high = candles[-1]["high"]
        current_low = candles[-1]["low"]
        
        # 计算入场通道（不包含当前 K 线）
        entry_channel = donchian_channel(candles[:-1], self.entry_period)
        atr_val = atr(candles, self.atr_period)
        
        if entry_channel is None:
            return None
        
        # 价格突破 N 日最高 → 做多
        if current_high > entry_channel["upper"]:
            stop_loss = current_price - (atr_val * self.risk_unit)
            take_profit = current_price + (atr_val * self.risk_unit * 2)
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="BUY",
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=80,
                reason=f"海龟突破: 价格 {current_high:.2f} > {self.entry_period}日高点 {entry_channel['upper']:.2f}",
                indicators={
                    "entry_upper": entry_channel["upper"],
                    "entry_lower": entry_channel["lower"],
                    "atr": atr_val,
                },
            )
        
        # 价格跌破 N 日最低 → 做空
        if current_low < entry_channel["lower"]:
            stop_loss = current_price + (atr_val * self.risk_unit)
            take_profit = current_price - (atr_val * self.risk_unit * 2)
            
            return StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side="SELL",
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=80,
                reason=f"海龟突破: 价格 {current_low:.2f} < {self.entry_period}日低点 {entry_channel['lower']:.2f}",
                indicators={
                    "entry_upper": entry_channel["upper"],
                    "entry_lower": entry_channel["lower"],
                    "atr": atr_val,
                },
            )
        
        return None
