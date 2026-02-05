"""
OrderTrade Module - 状态机定义

OrderStatus 枚举和 OrderStateMachine 状态流转控制
确保订单状态变更符合业务规则
"""

from enum import Enum
from typing import Set, Dict, Optional


class OrderStatus(str, Enum):
    """订单状态枚举"""
    
    # 初始状态
    PENDING = "PENDING"           # 待处理（本地创建，未提交）
    
    # 提交状态
    SUBMITTED = "SUBMITTED"       # 已提交到交易所
    
    # 活跃状态
    OPEN = "OPEN"                 # 交易所已确认，等待成交
    PARTIAL = "PARTIAL"           # 部分成交
    
    # 终态 - 成功
    FILLED = "FILLED"             # 完全成交
    
    # 终态 - 取消/拒绝
    CANCELLED = "CANCELLED"       # 用户取消
    REJECTED = "REJECTED"         # 被拒绝（交易所或本地校验）
    EXPIRED = "EXPIRED"           # 订单过期
    
    # 终态 - 失败
    FAILED = "FAILED"             # 系统错误
    
    @classmethod
    def terminal_states(cls) -> Set["OrderStatus"]:
        """获取所有终态"""
        return {cls.FILLED, cls.CANCELLED, cls.REJECTED, cls.EXPIRED, cls.FAILED}
    
    @classmethod
    def active_states(cls) -> Set["OrderStatus"]:
        """获取所有活跃状态（可以继续成交或取消）"""
        return {cls.OPEN, cls.PARTIAL}
    
    @classmethod
    def cancellable_states(cls) -> Set["OrderStatus"]:
        """获取可以取消的状态"""
        return {cls.PENDING, cls.SUBMITTED, cls.OPEN, cls.PARTIAL}
    
    def is_terminal(self) -> bool:
        """是否为终态"""
        return self in self.terminal_states()
    
    def is_active(self) -> bool:
        """是否为活跃状态"""
        return self in self.active_states()
    
    def is_cancellable(self) -> bool:
        """是否可以取消"""
        return self in self.cancellable_states()


class OrderStateMachine:
    """
    订单状态机
    
    控制订单状态的合法流转，防止非法状态跳跃
    """
    
    # 状态转换规则：from_status -> set(to_status)
    TRANSITIONS: Dict[OrderStatus, Set[OrderStatus]] = {
        OrderStatus.PENDING: {
            OrderStatus.SUBMITTED,   # 提交到交易所
            OrderStatus.REJECTED,    # 本地校验失败
            OrderStatus.FAILED,      # 系统错误
            OrderStatus.CANCELLED,   # 提交前取消
        },
        OrderStatus.SUBMITTED: {
            OrderStatus.OPEN,        # 交易所确认
            OrderStatus.FILLED,      # 市价单立即成交
            OrderStatus.PARTIAL,     # 部分成交
            OrderStatus.REJECTED,    # 交易所拒绝
            OrderStatus.FAILED,      # 网络错误
            OrderStatus.CANCELLED,   # 提交后立即取消
        },
        OrderStatus.OPEN: {
            OrderStatus.PARTIAL,     # 部分成交
            OrderStatus.FILLED,      # 完全成交
            OrderStatus.CANCELLED,   # 用户取消
            OrderStatus.EXPIRED,     # 订单过期
        },
        OrderStatus.PARTIAL: {
            OrderStatus.PARTIAL,     # 继续部分成交
            OrderStatus.FILLED,      # 完全成交
            OrderStatus.CANCELLED,   # 用户取消（剩余部分）
        },
        # 终态不能转换
        OrderStatus.FILLED: set(),
        OrderStatus.CANCELLED: set(),
        OrderStatus.REJECTED: set(),
        OrderStatus.EXPIRED: set(),
        OrderStatus.FAILED: set(),
    }
    
    @classmethod
    def can_transition(cls, from_status: OrderStatus, to_status: OrderStatus) -> bool:
        """
        检查状态转换是否合法
        
        Args:
            from_status: 当前状态
            to_status: 目标状态
            
        Returns:
            是否可以转换
        """
        if from_status == to_status:
            return True  # 允许相同状态（幂等）
        
        allowed = cls.TRANSITIONS.get(from_status, set())
        return to_status in allowed
    
    @classmethod
    def validate_transition(cls, from_status: OrderStatus, to_status: OrderStatus) -> None:
        """
        验证状态转换，不合法则抛出异常
        
        Args:
            from_status: 当前状态
            to_status: 目标状态
            
        Raises:
            InvalidStateTransitionError: 非法状态转换
        """
        if not cls.can_transition(from_status, to_status):
            from .exceptions import InvalidStateTransitionError
            raise InvalidStateTransitionError(
                f"Invalid state transition: {from_status.value} -> {to_status.value}"
            )
    
    @classmethod
    def get_allowed_transitions(cls, from_status: OrderStatus) -> Set[OrderStatus]:
        """
        获取当前状态可以转换到的所有状态
        
        Args:
            from_status: 当前状态
            
        Returns:
            可转换的状态集合
        """
        return cls.TRANSITIONS.get(from_status, set()).copy()
    
    @classmethod
    def determine_status_after_fill(
        cls, 
        order_quantity: float, 
        filled_quantity: float,
        current_status: OrderStatus
    ) -> OrderStatus:
        """
        根据成交情况确定新状态
        
        Args:
            order_quantity: 订单数量
            filled_quantity: 累计成交数量（包含本次）
            current_status: 当前状态
            
        Returns:
            新状态
        """
        if filled_quantity >= order_quantity:
            return OrderStatus.FILLED
        elif filled_quantity > 0:
            return OrderStatus.PARTIAL
        else:
            return current_status


class FillValidation:
    """
    成交校验工具
    
    确保成交记录符合不变量约束
    """
    
    @staticmethod
    def validate_fill_quantity(
        order_quantity: float,
        existing_filled: float,
        new_fill_quantity: float
    ) -> None:
        """
        校验成交数量不超过订单数量
        
        不变量：成交 ≤ 订单
        
        Args:
            order_quantity: 订单委托数量
            existing_filled: 已成交数量
            new_fill_quantity: 本次成交数量
            
        Raises:
            FillQuantityExceededError: 成交数量超过订单数量
        """
        total_filled = existing_filled + new_fill_quantity
        if total_filled > order_quantity * 1.0001:  # 允许极小误差（浮点精度）
            from .exceptions import FillQuantityExceededError
            raise FillQuantityExceededError(
                f"Fill quantity exceeded: order={order_quantity}, "
                f"existing_filled={existing_filled}, new_fill={new_fill_quantity}, "
                f"total={total_filled}"
            )
    
    @staticmethod
    def validate_fill_time_order(
        existing_max_time: Optional[float],
        new_fill_time: float
    ) -> None:
        """
        校验成交时间有序
        
        不变量：同一订单的成交时间单调递增
        
        Args:
            existing_max_time: 已有成交的最大时间戳
            new_fill_time: 本次成交时间戳
            
        Raises:
            FillTimeOrderError: 成交时间乱序
        """
        if existing_max_time is not None and new_fill_time < existing_max_time:
            from .exceptions import FillTimeOrderError
            raise FillTimeOrderError(
                f"Fill time out of order: existing_max={existing_max_time}, "
                f"new_fill={new_fill_time}"
            )
