"""
StrategyOutput Contract

策略输出 - Strategy.analyze() 的返回值。

使用位置：
- libs/strategies/*.py：策略 analyze() 方法返回
- services/strategy-engine：接收策略输出，转换为 Signal
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class StrategyOutput:
    """
    策略输出 - Strategy.analyze() 的返回值
    
    Attributes:
        symbol: 交易对
        side: 交易方向，BUY / SELL / None（HOLD 时为 None）
        signal_type: 信号类型，OPEN / CLOSE / ADD / HOLD
        entry_price: 入场价
        stop_loss: 止损价
        take_profit: 止盈价
        confidence: 置信度 0-100
        reason: 信号原因
        indicators: 指标快照（可选）
        bar_data: K线数据（可选）
    """
    
    symbol: str
    signal_type: str                        # OPEN / CLOSE / ADD / HOLD
    
    side: Optional[str] = None              # BUY / SELL / None（HOLD）
    
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    confidence: Optional[float] = None
    reason: Optional[str] = None
    
    # 策略附加数据（可选）
    indicators: Optional[Dict[str, Any]] = None     # 指标快照
    bar_data: Optional[Dict[str, Any]] = None       # K线数据
