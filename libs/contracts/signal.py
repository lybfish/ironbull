"""
Signal Contract

信号对象 - 模块间传递的核心数据结构。

使用位置：
- StrategyEngine → SignalHub：创建信号
- SignalHub → RiskControl：风控校验
- RiskControl → ExecutionDispatcher：执行提交
- SignalHub → FollowService：跟单广播
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Signal:
    """
    信号对象 - 模块间传递的核心数据结构
    
    Attributes:
        signal_id: 信号唯一ID
        strategy_code: 来源策略代码
        symbol: 交易对（原始，如 BTCUSDT）
        canonical_symbol: 交易对（归一化，如 BTC/USDT）
        side: 交易方向，BUY / SELL
        signal_type: 信号类型，OPEN / CLOSE / ADD / HOLD
        entry_price: 入场价（市价单为 None）
        stop_loss: 止损价
        take_profit: 止盈价
        quantity: 下单数量（风控计算后填充）
        confidence: 置信度 0-100
        reason: 信号原因
        timeframe: 时间周期（如 15m, 1h, 4h）
        timestamp: 信号时间（Unix 时间戳，秒）
        status: 信号状态
    """
    
    # 身份标识
    signal_id: str
    strategy_code: str
    
    # 交易意图
    symbol: str
    canonical_symbol: str
    side: str                               # BUY / SELL
    signal_type: str                        # OPEN / CLOSE / ADD / HOLD
    
    # 价格参数
    entry_price: Optional[float] = None     # 入场价（市价单为 None）
    stop_loss: Optional[float] = None       # 止损价
    take_profit: Optional[float] = None     # 止盈价
    
    # 数量（风控计算后填充）
    quantity: Optional[float] = None        # 下单数量
    
    # 仓位配置（策略层定义，随信号传递到执行层）
    amount_usdt: Optional[float] = None     # 单仓下单金额（USDT），策略配置
    leverage: Optional[int] = None          # 杠杆倍数，策略配置
    
    # 元信息
    confidence: Optional[float] = None      # 置信度 0-100
    reason: Optional[str] = None            # 信号原因
    timeframe: str = ""                     # 时间周期
    timestamp: int = 0                      # 信号时间（Unix）
    
    # 状态
    status: str = "pending"                 # pending / passed / rejected / executed / cancelled
