"""
Analytics Module - 分析模块

提供绩效分析、风险分析、交易统计等功能

核心组件：
- AnalyticsService: 分析服务
- MetricCalculator: 指标计算器

数据模型：
- PerformanceSnapshot: 绩效快照（每日净值、收益率）
- TradeStatistics: 交易统计（胜率、盈亏比）
- RiskMetrics: 风险指标（夏普、回撤、VaR）

使用示例：
    from libs.analytics import AnalyticsService
    
    service = AnalyticsService(
        session=db_session,
        tenant_id=1,
        account_id=1,
    )
    
    # 创建每日快照
    snapshot = service.create_daily_snapshot(
        snapshot_date=date.today(),
        balance=10000,
        position_value=5000,
    )
    
    # 计算风险指标
    metrics = service.calculate_risk_metrics(
        start_date=date(2024, 1, 1),
        end_date=date.today(),
    )
    
    # 获取净值曲线
    curve = service.get_equity_curve()
    
    # 获取绩效汇总
    summary = service.get_performance_summary()
"""

# Models
from .models import (
    PerformanceSnapshot,
    TradeStatistics,
    RiskMetrics,
)

# States
from .states import (
    PeriodType,
    MetricCalculator,
    AnalyticsValidation,
)

# Contracts (DTOs)
from .contracts import (
    # Output DTOs
    PerformanceSnapshotDTO,
    TradeStatisticsDTO,
    RiskMetricsDTO,
    # Input DTOs
    CreateSnapshotDTO,
    CalculateMetricsDTO,
    # Filters
    PerformanceFilter,
    StatisticsFilter,
    RiskMetricsFilter,
    # Summary
    PerformanceSummary,
    EquityCurve,
    EquityCurvePoint,
)

# Exceptions
from .exceptions import (
    AnalyticsError,
    SnapshotNotFoundError,
    StatisticsNotFoundError,
    MetricsNotFoundError,
    InsufficientDataError,
    InvalidDateRangeError,
    InvalidPeriodTypeError,
    TenantMismatchError,
    CalculationError,
    DuplicateSnapshotError,
)

# Repository
from .repository import (
    PerformanceSnapshotRepository,
    TradeStatisticsRepository,
    RiskMetricsRepository,
)

# Service
from .service import AnalyticsService

__all__ = [
    # Models
    "PerformanceSnapshot",
    "TradeStatistics",
    "RiskMetrics",
    # States
    "PeriodType",
    "MetricCalculator",
    "AnalyticsValidation",
    # DTOs
    "PerformanceSnapshotDTO",
    "TradeStatisticsDTO",
    "RiskMetricsDTO",
    "CreateSnapshotDTO",
    "CalculateMetricsDTO",
    "PerformanceFilter",
    "StatisticsFilter",
    "RiskMetricsFilter",
    "PerformanceSummary",
    "EquityCurve",
    "EquityCurvePoint",
    # Exceptions
    "AnalyticsError",
    "SnapshotNotFoundError",
    "StatisticsNotFoundError",
    "MetricsNotFoundError",
    "InsufficientDataError",
    "InvalidDateRangeError",
    "InvalidPeriodTypeError",
    "TenantMismatchError",
    "CalculationError",
    "DuplicateSnapshotError",
    # Repository
    "PerformanceSnapshotRepository",
    "TradeStatisticsRepository",
    "RiskMetricsRepository",
    # Service
    "AnalyticsService",
]
