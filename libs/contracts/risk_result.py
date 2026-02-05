"""
RiskResult Contract

风控结果 - RiskControl 的返回值。

使用位置：
- services/risk-control：风控检查后返回
- services/signal-hub：接收风控结果，决定是否执行
"""

from dataclasses import dataclass
from typing import Optional

from .signal import Signal


@dataclass
class RiskResult:
    """
    风控结果 - RiskControl 的返回值
    
    Attributes:
        passed: 是否通过风控
        signal: 修正后的 Signal（含 quantity/stop/tp）
        reject_reason: 拒绝原因（若 passed=False）
        reject_code: 拒绝代码
        calculated_quantity: 计算的下单数量
        calculated_stop_loss: 计算的止损价
        calculated_take_profit: 计算的止盈价
        potential_loss: 潜在亏损金额
        risk_reward_ratio: 风险回报比
    """
    
    passed: bool                            # 是否通过
    signal: Signal                          # 修正后的 Signal（含 quantity/stop/tp）
    
    reject_reason: Optional[str] = None     # 拒绝原因（若 passed=False）
    reject_code: Optional[str] = None       # 拒绝代码
    
    # 风控计算结果
    calculated_quantity: Optional[float] = None
    calculated_stop_loss: Optional[float] = None
    calculated_take_profit: Optional[float] = None
    potential_loss: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
