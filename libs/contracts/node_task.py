"""
NodeTask Contract

节点任务 - Dispatcher 发送给 Node 的任务。

使用位置：
- services/execution-dispatcher：构建并发送给节点
- nodes/crypto-node：接收并执行
- nodes/mt5-node：接收并执行
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class NodeTask:
    """
    节点任务 - Dispatcher 发送给 Node 的任务
    
    Attributes:
        task_id: 任务ID
        symbol: 交易对
        side: 交易方向，BUY / SELL
        order_type: 订单类型，MARKET / LIMIT
        quantity: 下单数量
        price: 限价单价格
        stop_loss: 止损价
        take_profit: 止盈价
        api_key: API Key
        api_secret: API Secret
        passphrase: API Passphrase（OKX 需要）
        exchange: 交易所，binance / okx / gate / bybit
        timeout_ms: 超时时间（毫秒）
    """
    
    task_id: str
    
    # 订单参数
    symbol: str
    side: str                               # BUY / SELL
    order_type: str                         # MARKET / LIMIT
    quantity: float
    price: Optional[float] = None
    
    # 附加订单（可选）
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # 凭证
    api_key: str = ""
    api_secret: str = ""
    passphrase: Optional[str] = None        # OKX 需要
    
    # 执行参数
    exchange: str = ""                      # binance / okx / gate / bybit
    timeout_ms: int = 30000
