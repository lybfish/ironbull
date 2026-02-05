"""
ExecutionTask Contract

执行任务 - Dispatcher 创建，发送给 Node。

使用位置：
- services/execution-dispatcher：创建任务并路由
- services/execution-dispatcher → nodes/*：发送任务
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ExecutionTask:
    """
    执行任务 - Dispatcher 创建，发送给 Node
    
    Attributes:
        task_id: 任务唯一ID
        signal_id: 关联的信号ID
        account_id: 账户ID
        member_id: 用户ID
        platform: 平台类型，crypto / mt5
        exchange: 交易所/Broker，binance / okx / mt5_broker_name
        symbol: 交易对
        side: 交易方向，BUY / SELL
        order_type: 订单类型，MARKET / LIMIT
        quantity: 下单数量
        price: 限价单价格
        stop_loss: 止损价
        take_profit: 止盈价
        credentials: API 凭证（加密传输或节点本地）
        priority: 优先级 1-10
        created_at: 创建时间（Unix 时间戳）
        timeout_ms: 超时时间（毫秒）
    """
    
    task_id: str                            # 任务唯一ID
    
    # 来源
    signal_id: str
    account_id: int
    member_id: int
    
    # 目标
    platform: str                           # crypto / mt5
    exchange: str                           # binance / okx / mt5_broker_name
    
    # 订单参数
    symbol: str
    side: str                               # BUY / SELL
    order_type: str                         # MARKET / LIMIT
    quantity: float
    price: Optional[float] = None           # 限价单价格
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # 凭证（加密传输或节点本地）
    credentials: Optional[Dict[str, Any]] = None    # api_key, api_secret, passphrase
    
    # 元信息
    priority: int = 5                       # 优先级 1-10
    created_at: int = 0                     # 创建时间
    timeout_ms: int = 30000                 # 超时时间（默认 30 秒）
