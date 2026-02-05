"""
NodeResult Contract

节点结果 - Node 返回给 Dispatcher。

使用位置：
- nodes/crypto-node：执行后返回
- nodes/mt5-node：执行后返回
- services/execution-dispatcher：接收节点结果
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class NodeResult:
    """
    节点结果 - Node 返回给 Dispatcher
    
    Attributes:
        task_id: 任务ID
        success: 是否成功
        exchange_order_id: 交易所订单ID
        filled_price: 成交价
        filled_quantity: 成交量
        fee: 手续费
        fee_currency: 手续费币种
        error_code: 错误代码
        error_message: 错误信息
        executed_at: 执行完成时间（Unix 时间戳）
        execution_ms: 执行耗时（毫秒）
    """
    
    task_id: str
    
    success: bool
    
    # 成功时
    exchange_order_id: Optional[str] = None
    filled_price: Optional[float] = None
    filled_quantity: Optional[float] = None
    fee: Optional[float] = None
    fee_currency: Optional[str] = None
    
    # 失败时
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # 时间
    executed_at: int = 0
    execution_ms: int = 0                   # 执行耗时
