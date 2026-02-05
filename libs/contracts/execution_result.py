"""
ExecutionResult Contract

执行结果 - Dispatcher 返回给调用方。

使用位置：
- services/execution-dispatcher：返回执行结果
- services/signal-hub：接收执行结果，更新信号状态
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    """
    执行结果 - Dispatcher 返回给调用方
    
    Attributes:
        task_id: 任务ID
        signal_id: 关联的信号ID
        success: 是否成功
        order_id: 系统内订单ID
        exchange_order_id: 交易所订单ID
        filled_price: 成交价
        filled_quantity: 成交量
        error_code: 错误代码
        error_message: 错误信息
        executed_at: 执行完成时间（Unix 时间戳）
    """
    
    task_id: str
    signal_id: str
    
    success: bool
    
    # 成功时
    order_id: Optional[str] = None              # 系统内订单ID
    exchange_order_id: Optional[str] = None     # 交易所订单ID
    filled_price: Optional[float] = None        # 成交价
    filled_quantity: Optional[float] = None     # 成交量
    
    # 失败时
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # 时间
    executed_at: Optional[int] = None
