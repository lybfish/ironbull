"""
Position Module - 异常定义

定义持仓模块特定的异常类型
"""


class PositionError(Exception):
    """持仓模块基础异常"""
    
    def __init__(self, message: str, code: str = "POSITION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class PositionNotFoundError(PositionError):
    """持仓不存在"""
    
    def __init__(
        self,
        tenant_id: int,
        account_id: int,
        symbol: str,
        position_side: str = None,
    ):
        self.tenant_id = tenant_id
        self.account_id = account_id
        self.symbol = symbol
        self.position_side = position_side
        
        side_info = f", side={position_side}" if position_side else ""
        message = f"Position not found: tenant={tenant_id}, account={account_id}, symbol={symbol}{side_info}"
        super().__init__(message, "POSITION_NOT_FOUND")


class InsufficientPositionError(PositionError):
    """持仓数量不足"""
    
    def __init__(
        self,
        symbol: str,
        required: float,
        available: float,
    ):
        self.symbol = symbol
        self.required = required
        self.available = available
        
        message = f"Insufficient position for {symbol}: required={required}, available={available}"
        super().__init__(message, "INSUFFICIENT_POSITION")


class InsufficientAvailableError(PositionError):
    """可用数量不足（考虑冻结）"""
    
    def __init__(
        self,
        symbol: str,
        required: float,
        available: float,
        frozen: float,
    ):
        self.symbol = symbol
        self.required = required
        self.available = available
        self.frozen = frozen
        
        message = (
            f"Insufficient available position for {symbol}: "
            f"required={required}, available={available}, frozen={frozen}"
        )
        super().__init__(message, "INSUFFICIENT_AVAILABLE")


class FreezeExceedsAvailableError(PositionError):
    """冻结数量超过可用数量"""
    
    def __init__(
        self,
        symbol: str,
        freeze_amount: float,
        available: float,
    ):
        self.symbol = symbol
        self.freeze_amount = freeze_amount
        self.available = available
        
        message = (
            f"Freeze amount exceeds available for {symbol}: "
            f"freeze={freeze_amount}, available={available}"
        )
        super().__init__(message, "FREEZE_EXCEEDS_AVAILABLE")


class InvalidFreezeReleaseError(PositionError):
    """无效的冻结释放（释放数量超过冻结数量）"""
    
    def __init__(
        self,
        symbol: str,
        release_amount: float,
        frozen: float,
    ):
        self.symbol = symbol
        self.release_amount = release_amount
        self.frozen = frozen
        
        message = (
            f"Release amount exceeds frozen for {symbol}: "
            f"release={release_amount}, frozen={frozen}"
        )
        super().__init__(message, "INVALID_FREEZE_RELEASE")


class TenantMismatchError(PositionError):
    """租户不匹配"""
    
    def __init__(
        self,
        expected_tenant: int,
        actual_tenant: int,
    ):
        self.expected_tenant = expected_tenant
        self.actual_tenant = actual_tenant
        
        message = f"Tenant mismatch: expected={expected_tenant}, actual={actual_tenant}"
        super().__init__(message, "TENANT_MISMATCH")


class InvalidChangeSourceError(PositionError):
    """无效的变动来源"""
    
    def __init__(
        self,
        change_type: str,
        source_type: str = None,
        source_id: str = None,
    ):
        self.change_type = change_type
        self.source_type = source_type
        self.source_id = source_id
        
        message = f"Invalid change source for {change_type}: source_type={source_type}, source_id={source_id}"
        super().__init__(message, "INVALID_CHANGE_SOURCE")


class PositionAlreadyExistsError(PositionError):
    """持仓已存在"""
    
    def __init__(
        self,
        tenant_id: int,
        account_id: int,
        symbol: str,
        position_side: str = None,
    ):
        self.tenant_id = tenant_id
        self.account_id = account_id
        self.symbol = symbol
        self.position_side = position_side
        
        side_info = f", side={position_side}" if position_side else ""
        message = f"Position already exists: tenant={tenant_id}, account={account_id}, symbol={symbol}{side_info}"
        super().__init__(message, "POSITION_ALREADY_EXISTS")


class CostCalculationError(PositionError):
    """成本计算错误"""
    
    def __init__(
        self,
        symbol: str,
        reason: str,
    ):
        self.symbol = symbol
        self.reason = reason
        
        message = f"Cost calculation error for {symbol}: {reason}"
        super().__init__(message, "COST_CALCULATION_ERROR")


class PositionInvariantViolation(PositionError):
    """持仓不变量违反"""
    
    def __init__(
        self,
        invariant: str,
        details: str = None,
    ):
        self.invariant = invariant
        self.details = details
        
        message = f"Position invariant violated: {invariant}"
        if details:
            message += f" - {details}"
        super().__init__(message, "INVARIANT_VIOLATION")
