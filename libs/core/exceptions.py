"""
Exceptions - 基础异常定义

职责：
- 定义通用异常基类
- 提供错误分类（可重试 / 不可重试）
- 支持错误码

不负责：
- 业务异常定义（由各 service 继承扩展）
"""

from typing import Optional, Dict, Any


class AppError(Exception):
    """
    统一应用异常

    Attributes:
        code: 错误代码
        message: 错误信息
        detail: 详细信息
    """
    
    code: str = "INTERNAL_ERROR"
    message: str = "An internal error occurred"
    detail: Optional[Dict[str, Any]] = None
    
    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None
    ):
        self.message = message or self.__class__.message
        self.code = code or self.__class__.code
        self.detail = detail or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 API 响应）"""
        return {
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
        }


class IronBullError(AppError):
    """
    兼容旧命名，等价于 AppError
    """


class ConfigError(AppError):
    """配置错误"""
    code = "CONFIG_ERROR"
    message = "Configuration error"


class ValidationError(AppError):
    """验证错误"""
    code = "VALIDATION_ERROR"
    message = "Validation failed"


class TimeoutError(AppError):
    """超时错误"""
    code = "TIMEOUT_ERROR"
    message = "Operation timed out"


class RetryableError(AppError):
    """可重试错误"""
    code = "RETRYABLE_ERROR"
    message = "Operation failed but can be retried"


class NotFoundError(AppError):
    """资源未找到"""
    code = "NOT_FOUND"
    message = "Resource not found"


class ConflictError(AppError):
    """冲突错误"""
    code = "CONFLICT"
    message = "Resource conflict"


class AuthenticationError(AppError):
    """认证错误"""
    code = "AUTHENTICATION_ERROR"
    message = "Authentication failed"


class PermissionError(AppError):
    """权限错误"""
    code = "PERMISSION_DENIED"
    message = "Permission denied"
