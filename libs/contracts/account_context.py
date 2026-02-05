"""
AccountContext Contract

账户上下文 - 风控计算所需的账户信息。

使用位置：
- services/signal-hub：构建账户上下文
- services/risk-control：接收并用于风控计算
- services/follow-service：获取跟单者账户上下文
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Position:
    """
    持仓信息
    
    Attributes:
        symbol: 交易对
        side: 持仓方向，long / short
        quantity: 持仓数量
        entry_price: 入场均价
        unrealized_pnl: 未实现盈亏
    """
    
    symbol: str
    side: str                               # long / short
    quantity: float
    entry_price: float
    unrealized_pnl: Optional[float] = None


@dataclass
class AccountContext:
    """
    账户上下文 - 风控计算所需的账户信息
    
    Attributes:
        account_id: 账户ID
        member_id: 用户ID
        balance: 总余额
        available: 可用余额
        frozen: 冻结金额
        positions: 当前持仓列表
        max_loss_per_trade: 单笔最大亏损
        max_daily_loss: 每日最大亏损
        cooldown_seconds: 冷却时间（秒）
        symbol_whitelist: 品种白名单
        symbol_blacklist: 品种黑名单
    """
    
    account_id: int
    member_id: int
    
    # 余额
    balance: float                          # 总余额
    available: float                        # 可用余额
    frozen: float = 0.0                     # 冻结金额
    
    # 当前持仓（可选）
    positions: Optional[List[Position]] = None
    
    # 配置
    max_loss_per_trade: Optional[float] = None      # 单笔最大亏损
    max_daily_loss: Optional[float] = None          # 每日最大亏损
    cooldown_seconds: Optional[int] = None          # 冷却时间
    symbol_whitelist: Optional[List[str]] = None    # 品种白名单
    symbol_blacklist: Optional[List[str]] = None    # 品种黑名单
