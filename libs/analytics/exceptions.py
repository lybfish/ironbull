"""
Analytics Exceptions - 分析模块异常定义
"""


class AnalyticsError(Exception):
    """分析模块基础异常"""
    def __init__(self, message: str, code: str = "ANALYTICS_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class SnapshotNotFoundError(AnalyticsError):
    """快照不存在"""
    def __init__(self, snapshot_id: str):
        super().__init__(
            f"Performance snapshot not found: {snapshot_id}",
            "SNAPSHOT_NOT_FOUND"
        )
        self.snapshot_id = snapshot_id


class StatisticsNotFoundError(AnalyticsError):
    """统计不存在"""
    def __init__(self, stat_id: str):
        super().__init__(
            f"Trade statistics not found: {stat_id}",
            "STATISTICS_NOT_FOUND"
        )
        self.stat_id = stat_id


class MetricsNotFoundError(AnalyticsError):
    """指标不存在"""
    def __init__(self, metric_id: str):
        super().__init__(
            f"Risk metrics not found: {metric_id}",
            "METRICS_NOT_FOUND"
        )
        self.metric_id = metric_id


class InsufficientDataError(AnalyticsError):
    """数据不足"""
    def __init__(self, message: str = "Insufficient data for calculation"):
        super().__init__(message, "INSUFFICIENT_DATA")


class InvalidDateRangeError(AnalyticsError):
    """日期范围无效"""
    def __init__(self, start_date, end_date):
        super().__init__(
            f"Invalid date range: {start_date} to {end_date}",
            "INVALID_DATE_RANGE"
        )
        self.start_date = start_date
        self.end_date = end_date


class InvalidPeriodTypeError(AnalyticsError):
    """周期类型无效"""
    def __init__(self, period_type: str):
        super().__init__(
            f"Invalid period type: {period_type}",
            "INVALID_PERIOD_TYPE"
        )
        self.period_type = period_type


class TenantMismatchError(AnalyticsError):
    """租户不匹配"""
    def __init__(self, expected: int, actual: int):
        super().__init__(
            f"Tenant mismatch: expected {expected}, got {actual}",
            "TENANT_MISMATCH"
        )
        self.expected = expected
        self.actual = actual


class CalculationError(AnalyticsError):
    """计算错误"""
    def __init__(self, message: str):
        super().__init__(message, "CALCULATION_ERROR")


class DuplicateSnapshotError(AnalyticsError):
    """快照重复"""
    def __init__(self, tenant_id: int, account_id: int, snapshot_date):
        super().__init__(
            f"Snapshot already exists for tenant={tenant_id}, account={account_id}, date={snapshot_date}",
            "DUPLICATE_SNAPSHOT"
        )
        self.tenant_id = tenant_id
        self.account_id = account_id
        self.snapshot_date = snapshot_date
