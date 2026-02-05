"""
Analytics Contracts - 分析模块数据传输对象

DTOs for:
- 绩效快照
- 交易统计
- 风险指标
- 查询过滤
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal


@dataclass
class PerformanceSnapshotDTO:
    """绩效快照 DTO"""
    snapshot_id: str
    tenant_id: int
    account_id: int
    snapshot_date: date
    
    # 资金
    balance: float
    position_value: float
    total_equity: float
    
    # 收益
    daily_pnl: float
    daily_return: float
    cumulative_pnl: float
    cumulative_return: float
    net_value: float
    
    # 基准（可选）
    benchmark_value: Optional[float] = None
    benchmark_return: Optional[float] = None
    excess_return: Optional[float] = None
    
    created_at: Optional[datetime] = None


@dataclass
class TradeStatisticsDTO:
    """交易统计 DTO"""
    stat_id: str
    tenant_id: int
    account_id: int
    
    # 周期
    period_type: str
    period_start: date
    period_end: date
    
    # 维度
    strategy_code: Optional[str] = None
    symbol: Optional[str] = None
    
    # 交易次数
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    break_even_trades: int = 0
    
    # 胜率
    win_rate: float = 0.0
    
    # 盈亏
    total_profit: float = 0.0
    total_loss: float = 0.0
    net_profit: float = 0.0
    
    # 单笔
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    
    # 比率
    profit_loss_ratio: float = 0.0
    profit_factor: float = 0.0
    
    # 持仓时间
    avg_holding_period: float = 0.0
    max_holding_period: float = 0.0
    
    # 连续
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    # 交易量
    total_volume: float = 0.0
    total_fee: float = 0.0
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class RiskMetricsDTO:
    """风险指标 DTO"""
    metric_id: str
    tenant_id: int
    account_id: int
    
    # 周期
    period_type: str
    period_start: date
    period_end: date
    
    # 维度
    strategy_code: Optional[str] = None
    
    # 收益
    total_return: float = 0.0
    annualized_return: float = 0.0
    
    # 波动率
    daily_volatility: float = 0.0
    annualized_volatility: float = 0.0
    
    # 风险调整收益
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # 回撤
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    current_drawdown: float = 0.0
    
    # VaR
    var_95: Optional[float] = None
    var_99: Optional[float] = None
    cvar_95: Optional[float] = None
    
    # Beta/Alpha
    beta: Optional[float] = None
    alpha: Optional[float] = None
    
    # 信息比率
    information_ratio: Optional[float] = None
    tracking_error: Optional[float] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ========== 输入 DTOs ==========

@dataclass
class CreateSnapshotDTO:
    """创建绩效快照 DTO"""
    tenant_id: int
    account_id: int
    snapshot_date: date
    
    balance: float
    position_value: float
    total_equity: float
    
    daily_pnl: float = 0.0
    daily_return: float = 0.0
    cumulative_pnl: float = 0.0
    cumulative_return: float = 0.0
    net_value: float = 1.0
    
    benchmark_value: Optional[float] = None
    benchmark_return: Optional[float] = None


@dataclass
class CalculateMetricsDTO:
    """计算指标请求 DTO"""
    tenant_id: int
    account_id: int
    start_date: date
    end_date: date
    period_type: str = "all"
    strategy_code: Optional[str] = None


# ========== 查询过滤 ==========

@dataclass
class PerformanceFilter:
    """绩效快照查询过滤"""
    tenant_id: int
    account_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    limit: int = 365


@dataclass
class StatisticsFilter:
    """交易统计查询过滤"""
    tenant_id: int
    account_id: Optional[int] = None
    period_type: Optional[str] = None
    strategy_code: Optional[str] = None
    symbol: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    limit: int = 100


@dataclass
class RiskMetricsFilter:
    """风险指标查询过滤"""
    tenant_id: int
    account_id: Optional[int] = None
    period_type: Optional[str] = None
    strategy_code: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    limit: int = 100


# ========== 汇总 DTOs ==========

@dataclass
class PerformanceSummary:
    """绩效汇总"""
    tenant_id: int
    account_id: int
    
    # 当前状态
    current_equity: float = 0.0
    current_net_value: float = 1.0
    
    # 收益
    total_return: float = 0.0
    annualized_return: float = 0.0
    
    # 今日
    daily_pnl: float = 0.0
    daily_return: float = 0.0
    
    # 本月
    monthly_return: float = 0.0
    
    # 本年
    yearly_return: float = 0.0
    
    # 风险
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    
    # 交易
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0


@dataclass
class EquityCurvePoint:
    """净值曲线点"""
    date: date
    equity: float
    net_value: float
    daily_return: float
    cumulative_return: float
    drawdown: float = 0.0


@dataclass
class EquityCurve:
    """净值曲线"""
    tenant_id: int
    account_id: int
    start_date: date
    end_date: date
    points: List[EquityCurvePoint] = field(default_factory=list)
    
    # 汇总
    initial_equity: float = 0.0
    final_equity: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
