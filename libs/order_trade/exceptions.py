"""
OrderTrade Module - 异常定义

定义 OrderTrade 模块的所有异常类型
"""


class OrderTradeError(Exception):
    """OrderTrade 模块基础异常"""
    
    def __init__(self, message: str, code: str = "ORDER_TRADE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# ============ Order 相关异常 ============

class OrderNotFoundError(OrderTradeError):
    """订单不存在"""
    
    def __init__(self, order_id: str):
        super().__init__(
            message=f"Order not found: {order_id}",
            code="ORDER_NOT_FOUND"
        )
        self.order_id = order_id


class OrderAlreadyExistsError(OrderTradeError):
    """订单已存在（重复创建）"""
    
    def __init__(self, order_id: str):
        super().__init__(
            message=f"Order already exists: {order_id}",
            code="ORDER_ALREADY_EXISTS"
        )
        self.order_id = order_id


class InvalidStateTransitionError(OrderTradeError):
    """非法状态转换"""
    
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="INVALID_STATE_TRANSITION"
        )


class OrderNotCancellableError(OrderTradeError):
    """订单不可取消"""
    
    def __init__(self, order_id: str, status: str):
        super().__init__(
            message=f"Order {order_id} cannot be cancelled in status: {status}",
            code="ORDER_NOT_CANCELLABLE"
        )
        self.order_id = order_id
        self.status = status


class OrderInTerminalStateError(OrderTradeError):
    """订单已在终态，不可修改"""
    
    def __init__(self, order_id: str, status: str):
        super().__init__(
            message=f"Order {order_id} is in terminal state: {status}",
            code="ORDER_IN_TERMINAL_STATE"
        )
        self.order_id = order_id
        self.status = status


# ============ Fill 相关异常 ============

class FillNotFoundError(OrderTradeError):
    """成交记录不存在"""
    
    def __init__(self, fill_id: str):
        super().__init__(
            message=f"Fill not found: {fill_id}",
            code="FILL_NOT_FOUND"
        )
        self.fill_id = fill_id


class FillAlreadyExistsError(OrderTradeError):
    """成交记录已存在（幂等性检查）"""
    
    def __init__(self, fill_id: str):
        super().__init__(
            message=f"Fill already exists: {fill_id}",
            code="FILL_ALREADY_EXISTS"
        )
        self.fill_id = fill_id


class FillQuantityExceededError(OrderTradeError):
    """成交数量超过订单数量"""
    
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="FILL_QUANTITY_EXCEEDED"
        )


class FillTimeOrderError(OrderTradeError):
    """成交时间乱序"""
    
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="FILL_TIME_ORDER_ERROR"
        )


class FillOrderMismatchError(OrderTradeError):
    """成交与订单不匹配"""
    
    def __init__(self, fill_id: str, order_id: str, reason: str):
        super().__init__(
            message=f"Fill {fill_id} does not match order {order_id}: {reason}",
            code="FILL_ORDER_MISMATCH"
        )
        self.fill_id = fill_id
        self.order_id = order_id
        self.reason = reason


# ============ 租户/权限相关异常 ============

class TenantMismatchError(OrderTradeError):
    """租户不匹配（跨租户访问）"""
    
    def __init__(self, resource_type: str, resource_id: str, expected_tenant: int, actual_tenant: int):
        super().__init__(
            message=f"{resource_type} {resource_id} belongs to tenant {actual_tenant}, "
                    f"not {expected_tenant}",
            code="TENANT_MISMATCH"
        )
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.expected_tenant = expected_tenant
        self.actual_tenant = actual_tenant


# ============ 验证相关异常 ============

class ValidationError(OrderTradeError):
    """数据验证错误"""
    
    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation error on {field}: {message}",
            code="VALIDATION_ERROR"
        )
        self.field = field


class InvariantViolationError(OrderTradeError):
    """不变量约束违反"""
    
    def __init__(self, invariant: str, message: str):
        super().__init__(
            message=f"Invariant violation [{invariant}]: {message}",
            code="INVARIANT_VIOLATION"
        )
        self.invariant = invariant
