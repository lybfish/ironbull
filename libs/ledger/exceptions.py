"""
Ledger Module - 异常定义

定义账务模块特定的异常类型
"""


class LedgerError(Exception):
    """账务模块基础异常"""
    
    def __init__(self, message: str, code: str = "LEDGER_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class AccountNotFoundError(LedgerError):
    """账户不存在"""
    
    def __init__(
        self,
        tenant_id: int,
        account_id: int = None,
        currency: str = None,
    ):
        self.tenant_id = tenant_id
        self.account_id = account_id
        self.currency = currency
        
        details = f"tenant={tenant_id}"
        if account_id:
            details += f", account={account_id}"
        if currency:
            details += f", currency={currency}"
        
        message = f"Account not found: {details}"
        super().__init__(message, "ACCOUNT_NOT_FOUND")


class InsufficientBalanceError(LedgerError):
    """余额不足"""
    
    def __init__(
        self,
        required: float,
        available: float,
        currency: str = "USDT",
    ):
        self.required = required
        self.available = available
        self.currency = currency
        
        message = f"Insufficient balance: required={required} {currency}, available={available} {currency}"
        super().__init__(message, "INSUFFICIENT_BALANCE")


class InsufficientAvailableError(LedgerError):
    """可用余额不足（考虑冻结）"""
    
    def __init__(
        self,
        required: float,
        available: float,
        frozen: float,
        currency: str = "USDT",
    ):
        self.required = required
        self.available = available
        self.frozen = frozen
        self.currency = currency
        
        message = (
            f"Insufficient available balance: "
            f"required={required} {currency}, available={available} {currency}, frozen={frozen} {currency}"
        )
        super().__init__(message, "INSUFFICIENT_AVAILABLE")


class FreezeExceedsAvailableError(LedgerError):
    """冻结金额超过可用余额"""
    
    def __init__(
        self,
        freeze_amount: float,
        available: float,
        currency: str = "USDT",
    ):
        self.freeze_amount = freeze_amount
        self.available = available
        self.currency = currency
        
        message = (
            f"Freeze amount exceeds available: "
            f"freeze={freeze_amount} {currency}, available={available} {currency}"
        )
        super().__init__(message, "FREEZE_EXCEEDS_AVAILABLE")


class InvalidUnfreezeError(LedgerError):
    """无效的解冻操作"""
    
    def __init__(
        self,
        unfreeze_amount: float,
        frozen: float,
        currency: str = "USDT",
    ):
        self.unfreeze_amount = unfreeze_amount
        self.frozen = frozen
        self.currency = currency
        
        message = (
            f"Unfreeze amount exceeds frozen: "
            f"unfreeze={unfreeze_amount} {currency}, frozen={frozen} {currency}"
        )
        super().__init__(message, "INVALID_UNFREEZE")


class DuplicateTransactionError(LedgerError):
    """重复交易（幂等检查）"""
    
    def __init__(
        self,
        source_type: str,
        source_id: str,
    ):
        self.source_type = source_type
        self.source_id = source_id
        
        message = f"Duplicate transaction: {source_type}/{source_id}"
        super().__init__(message, "DUPLICATE_TRANSACTION")


class TenantMismatchError(LedgerError):
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


class InvalidTransactionError(LedgerError):
    """无效交易"""
    
    def __init__(
        self,
        reason: str,
    ):
        self.reason = reason
        message = f"Invalid transaction: {reason}"
        super().__init__(message, "INVALID_TRANSACTION")


class AccountAlreadyExistsError(LedgerError):
    """账户已存在"""
    
    def __init__(
        self,
        tenant_id: int,
        account_id: int,
        currency: str,
    ):
        self.tenant_id = tenant_id
        self.account_id = account_id
        self.currency = currency
        
        message = f"Account already exists: tenant={tenant_id}, account={account_id}, currency={currency}"
        super().__init__(message, "ACCOUNT_ALREADY_EXISTS")


class LedgerInvariantViolation(LedgerError):
    """账务不变量违反"""
    
    def __init__(
        self,
        invariant: str,
        details: str = None,
    ):
        self.invariant = invariant
        self.details = details
        
        message = f"Ledger invariant violated: {invariant}"
        if details:
            message += f" - {details}"
        super().__init__(message, "INVARIANT_VIOLATION")
