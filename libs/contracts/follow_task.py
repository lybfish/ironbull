"""
FollowTask Contract

跟单任务 - FollowService 生成。

使用位置：
- services/follow-service：创建跟单任务
- services/follow-service → services/execution-dispatcher：提交执行
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FollowTask:
    """
    跟单任务 - FollowService 生成
    
    Attributes:
        task_id: 任务ID
        signal_id: 来源信号ID
        leader_id: Leader ID
        relation_id: 跟单关系ID
        follower_id: 跟单者ID
        follower_account_id: 跟单者账户ID
        follow_mode: 跟单模式，ratio / fixed_amount / fixed_quantity
        follow_value: 跟单值（比例 / 金额 / 数量）
        symbol: 交易对
        side: 交易方向
        quantity: 计算后的下单数量
        status: 任务状态
    """
    
    task_id: str
    
    # 来源
    signal_id: str
    leader_id: int
    relation_id: int
    
    # 跟单者
    follower_id: int
    follower_account_id: int
    
    # 跟单参数
    follow_mode: str                        # ratio / fixed_amount / fixed_quantity
    follow_value: float                     # 比例 / 金额 / 数量
    
    # 计算后的订单参数
    symbol: str = ""
    side: str = ""
    quantity: float = 0.0
    
    # 状态
    status: str = "queued"                  # queued / executing / success / failed / skipped


@dataclass
class FollowTaskResult:
    """
    跟单任务结果 - 查询跟单执行结果
    
    Attributes:
        task_id: 任务ID
        follower_id: 跟单者ID
        status: 任务状态
        order_id: 订单ID（成功时）
        error: 错误信息（失败时）
    """
    
    task_id: str
    follower_id: int
    status: str                             # success / failed / skipped
    order_id: Optional[str] = None
    error: Optional[str] = None
