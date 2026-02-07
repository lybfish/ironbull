"""
Analytics Models - 分析数据模型

数据表：
- fact_performance_snapshot: 绩效快照（定期记录净值、收益率）
- fact_trade_statistics: 交易统计（按策略/标的/时间段汇总）
- fact_risk_metrics: 风险指标（波动率、VaR、最大回撤等）
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Date,
    Text, Index, UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy.dialects.mysql import BIGINT

from libs.core.database import Base


class PerformanceSnapshot(Base):
    """
    绩效快照表
    
    定期记录账户的净值、收益率等绩效数据
    用于绘制净值曲线、计算区间收益等
    """
    __tablename__ = "fact_performance_snapshot"
    
    # 主键
    snapshot_id = Column(String(36), primary_key=True, comment="快照ID")
    
    # 租户和账户
    tenant_id = Column(Integer, nullable=False, index=True, comment="租户ID")
    account_id = Column(Integer, nullable=False, index=True, comment="账户ID")
    
    # 快照日期
    snapshot_date = Column(Date, nullable=False, comment="快照日期")
    
    # 资金数据
    balance = Column(Float, nullable=False, default=0, comment="账户余额")
    position_value = Column(Float, nullable=False, default=0, comment="持仓市值")
    total_equity = Column(Float, nullable=False, default=0, comment="总权益(余额+持仓)")
    
    # 收益数据
    daily_pnl = Column(Float, nullable=False, default=0, comment="当日盈亏")
    daily_return = Column(Float, nullable=False, default=0, comment="当日收益率(%)")
    cumulative_pnl = Column(Float, nullable=False, default=0, comment="累计盈亏")
    cumulative_return = Column(Float, nullable=False, default=0, comment="累计收益率(%)")
    
    # 基准数据（可选）
    benchmark_value = Column(Float, nullable=True, comment="基准净值")
    benchmark_return = Column(Float, nullable=True, comment="基准当日收益率(%)")
    excess_return = Column(Float, nullable=True, comment="超额收益率(%)")
    
    # 净值（归一化）
    net_value = Column(Float, nullable=False, default=1.0, comment="净值(初始1.0)")
    
    # 元数据
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'account_id', 'snapshot_date', name='uk_performance_daily'),
        Index('idx_performance_tenant_date', 'tenant_id', 'snapshot_date'),
        {'comment': '绩效快照表（每日记录净值和收益率）'}
    )


class TradeStatistics(Base):
    """
    交易统计表
    
    按策略/标的/时间段汇总交易指标
    """
    __tablename__ = "fact_trade_statistics"
    
    # 主键
    stat_id = Column(String(36), primary_key=True, comment="统计ID")
    
    # 租户和账户
    tenant_id = Column(Integer, nullable=False, index=True, comment="租户ID")
    account_id = Column(Integer, nullable=False, index=True, comment="账户ID")
    
    # 统计维度
    period_type = Column(String(20), nullable=False, comment="周期类型(daily/weekly/monthly/yearly/all)")
    period_start = Column(Date, nullable=False, comment="周期开始日期")
    period_end = Column(Date, nullable=False, comment="周期结束日期")
    
    # 可选维度
    strategy_code = Column(String(50), nullable=True, index=True, comment="策略代码(可选)")
    symbol = Column(String(50), nullable=True, index=True, comment="交易对(可选)")
    
    # 交易次数统计
    total_trades = Column(Integer, nullable=False, default=0, comment="总交易次数")
    winning_trades = Column(Integer, nullable=False, default=0, comment="盈利交易次数")
    losing_trades = Column(Integer, nullable=False, default=0, comment="亏损交易次数")
    break_even_trades = Column(Integer, nullable=False, default=0, comment="持平交易次数")
    
    # 胜率
    win_rate = Column(Float, nullable=False, default=0, comment="胜率(%)")
    
    # 盈亏统计
    total_profit = Column(Float, nullable=False, default=0, comment="总盈利")
    total_loss = Column(Float, nullable=False, default=0, comment="总亏损(绝对值)")
    net_profit = Column(Float, nullable=False, default=0, comment="净利润")
    
    # 单笔统计
    avg_profit = Column(Float, nullable=False, default=0, comment="平均盈利")
    avg_loss = Column(Float, nullable=False, default=0, comment="平均亏损(绝对值)")
    max_profit = Column(Float, nullable=False, default=0, comment="最大单笔盈利")
    max_loss = Column(Float, nullable=False, default=0, comment="最大单笔亏损")
    
    # 盈亏比
    profit_loss_ratio = Column(Float, nullable=False, default=0, comment="盈亏比(平均盈利/平均亏损)")
    profit_factor = Column(Float, nullable=False, default=0, comment="获利因子(总盈利/总亏损)")
    
    # 持仓时间
    avg_holding_period = Column(Float, nullable=False, default=0, comment="平均持仓时间(小时)")
    max_holding_period = Column(Float, nullable=False, default=0, comment="最长持仓时间(小时)")
    
    # 连续统计
    max_consecutive_wins = Column(Integer, nullable=False, default=0, comment="最大连胜次数")
    max_consecutive_losses = Column(Integer, nullable=False, default=0, comment="最大连亏次数")
    
    # 交易量
    total_volume = Column(Float, nullable=False, default=0, comment="总交易量(USDT)")
    total_fee = Column(Float, nullable=False, default=0, comment="总手续费")
    
    # 元数据
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        UniqueConstraint(
            'tenant_id', 'account_id', 'period_type', 'period_start', 
            'strategy_code', 'symbol', 
            name='uk_trade_stats_period'
        ),
        Index('idx_trade_stats_period', 'tenant_id', 'period_type', 'period_start'),
        {'comment': '交易统计表（按周期汇总）'}
    )


class RiskMetrics(Base):
    """
    风险指标表
    
    记录账户/策略的风险指标
    """
    __tablename__ = "fact_risk_metrics"
    
    # 主键
    metric_id = Column(String(36), primary_key=True, comment="指标ID")
    
    # 租户和账户
    tenant_id = Column(Integer, nullable=False, index=True, comment="租户ID")
    account_id = Column(Integer, nullable=False, index=True, comment="账户ID")
    
    # 统计周期
    period_type = Column(String(20), nullable=False, comment="周期类型(daily/weekly/monthly/yearly/all)")
    period_start = Column(Date, nullable=False, comment="周期开始日期")
    period_end = Column(Date, nullable=False, comment="周期结束日期")
    
    # 可选维度
    strategy_code = Column(String(50), nullable=True, index=True, comment="策略代码(可选)")
    
    # 收益指标
    total_return = Column(Float, nullable=False, default=0, comment="总收益率(%)")
    annualized_return = Column(Float, nullable=False, default=0, comment="年化收益率(%)")
    
    # 波动率
    daily_volatility = Column(Float, nullable=False, default=0, comment="日波动率(%)")
    annualized_volatility = Column(Float, nullable=False, default=0, comment="年化波动率(%)")
    
    # 风险调整收益
    sharpe_ratio = Column(Float, nullable=False, default=0, comment="夏普比率")
    sortino_ratio = Column(Float, nullable=False, default=0, comment="索提诺比率")
    calmar_ratio = Column(Float, nullable=False, default=0, comment="卡玛比率")
    
    # 回撤指标
    max_drawdown = Column(Float, nullable=False, default=0, comment="最大回撤(%)")
    max_drawdown_duration = Column(Integer, nullable=False, default=0, comment="最大回撤持续天数")
    current_drawdown = Column(Float, nullable=False, default=0, comment="当前回撤(%)")
    
    # VaR
    var_95 = Column(Float, nullable=True, comment="95% VaR")
    var_99 = Column(Float, nullable=True, comment="99% VaR")
    cvar_95 = Column(Float, nullable=True, comment="95% CVaR(条件VaR)")
    
    # Beta（相对基准）
    beta = Column(Float, nullable=True, comment="Beta系数")
    alpha = Column(Float, nullable=True, comment="Alpha(超额收益)")
    
    # 信息比率
    information_ratio = Column(Float, nullable=True, comment="信息比率")
    tracking_error = Column(Float, nullable=True, comment="跟踪误差")
    
    # 元数据
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        UniqueConstraint(
            'tenant_id', 'account_id', 'period_type', 'period_start', 'strategy_code',
            name='uk_risk_metrics_period'
        ),
        Index('idx_risk_metrics_period', 'tenant_id', 'period_type', 'period_start'),
        {'comment': '风险指标表（按周期记录）'}
    )
