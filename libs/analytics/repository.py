"""
Analytics Repository - 分析数据访问层

职责：
- 绩效快照的 CRUD
- 交易统计的 CRUD
- 风险指标的 CRUD
- 租户隔离
"""

from datetime import date, datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from libs.core import gen_id
from .models import PerformanceSnapshot, TradeStatistics, RiskMetrics
from .contracts import (
    PerformanceSnapshotDTO,
    TradeStatisticsDTO,
    RiskMetricsDTO,
    PerformanceFilter,
    StatisticsFilter,
    RiskMetricsFilter,
)


class PerformanceSnapshotRepository:
    """绩效快照数据访问"""
    
    def __init__(self, session: Session, tenant_id: int):
        self.session = session
        self.tenant_id = tenant_id
    
    def _to_dto(self, model: PerformanceSnapshot) -> PerformanceSnapshotDTO:
        """模型转 DTO"""
        return PerformanceSnapshotDTO(
            snapshot_id=model.snapshot_id,
            tenant_id=model.tenant_id,
            account_id=model.account_id,
            snapshot_date=model.snapshot_date,
            balance=model.balance,
            position_value=model.position_value,
            total_equity=model.total_equity,
            daily_pnl=model.daily_pnl,
            daily_return=model.daily_return,
            cumulative_pnl=model.cumulative_pnl,
            cumulative_return=model.cumulative_return,
            net_value=model.net_value,
            benchmark_value=model.benchmark_value,
            benchmark_return=model.benchmark_return,
            excess_return=model.excess_return,
            created_at=model.created_at,
        )
    
    def create(
        self,
        account_id: int,
        snapshot_date: date,
        balance: float,
        position_value: float,
        total_equity: float,
        daily_pnl: float = 0.0,
        daily_return: float = 0.0,
        cumulative_pnl: float = 0.0,
        cumulative_return: float = 0.0,
        net_value: float = 1.0,
        benchmark_value: Optional[float] = None,
        benchmark_return: Optional[float] = None,
    ) -> PerformanceSnapshotDTO:
        """创建绩效快照"""
        snapshot = PerformanceSnapshot(
            snapshot_id=gen_id("SNAP-"),
            tenant_id=self.tenant_id,
            account_id=account_id,
            snapshot_date=snapshot_date,
            balance=balance,
            position_value=position_value,
            total_equity=total_equity,
            daily_pnl=daily_pnl,
            daily_return=daily_return,
            cumulative_pnl=cumulative_pnl,
            cumulative_return=cumulative_return,
            net_value=net_value,
            benchmark_value=benchmark_value,
            benchmark_return=benchmark_return,
            excess_return=(daily_return - benchmark_return) if benchmark_return else None,
        )
        self.session.add(snapshot)
        self.session.flush()
        return self._to_dto(snapshot)
    
    def get_by_id(self, snapshot_id: str) -> Optional[PerformanceSnapshotDTO]:
        """根据 ID 获取快照"""
        snapshot = self.session.query(PerformanceSnapshot).filter(
            PerformanceSnapshot.snapshot_id == snapshot_id,
            PerformanceSnapshot.tenant_id == self.tenant_id,
        ).first()
        return self._to_dto(snapshot) if snapshot else None
    
    def get_by_date(
        self,
        account_id: int,
        snapshot_date: date,
    ) -> Optional[PerformanceSnapshotDTO]:
        """根据日期获取快照"""
        snapshot = self.session.query(PerformanceSnapshot).filter(
            PerformanceSnapshot.tenant_id == self.tenant_id,
            PerformanceSnapshot.account_id == account_id,
            PerformanceSnapshot.snapshot_date == snapshot_date,
        ).first()
        return self._to_dto(snapshot) if snapshot else None
    
    def get_latest(self, account_id: int) -> Optional[PerformanceSnapshotDTO]:
        """获取最新快照"""
        snapshot = self.session.query(PerformanceSnapshot).filter(
            PerformanceSnapshot.tenant_id == self.tenant_id,
            PerformanceSnapshot.account_id == account_id,
        ).order_by(desc(PerformanceSnapshot.snapshot_date)).first()
        return self._to_dto(snapshot) if snapshot else None
    
    def list_snapshots(
        self,
        account_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 365,
    ) -> List[PerformanceSnapshotDTO]:
        """查询快照列表"""
        query = self.session.query(PerformanceSnapshot).filter(
            PerformanceSnapshot.tenant_id == self.tenant_id,
            PerformanceSnapshot.account_id == account_id,
        )
        
        if start_date:
            query = query.filter(PerformanceSnapshot.snapshot_date >= start_date)
        if end_date:
            query = query.filter(PerformanceSnapshot.snapshot_date <= end_date)
        
        snapshots = query.order_by(asc(PerformanceSnapshot.snapshot_date)).limit(limit).all()
        return [self._to_dto(s) for s in snapshots]
    
    def update(
        self,
        snapshot_id: str,
        **kwargs,
    ) -> Optional[PerformanceSnapshotDTO]:
        """更新快照"""
        snapshot = self.session.query(PerformanceSnapshot).filter(
            PerformanceSnapshot.snapshot_id == snapshot_id,
            PerformanceSnapshot.tenant_id == self.tenant_id,
        ).first()
        
        if not snapshot:
            return None
        
        for key, value in kwargs.items():
            if hasattr(snapshot, key) and value is not None:
                setattr(snapshot, key, value)
        
        self.session.flush()
        return self._to_dto(snapshot)
    
    def delete(self, snapshot_id: str) -> bool:
        """删除快照"""
        result = self.session.query(PerformanceSnapshot).filter(
            PerformanceSnapshot.snapshot_id == snapshot_id,
            PerformanceSnapshot.tenant_id == self.tenant_id,
        ).delete()
        return result > 0


class TradeStatisticsRepository:
    """交易统计数据访问"""
    
    def __init__(self, session: Session, tenant_id: int):
        self.session = session
        self.tenant_id = tenant_id
    
    def _to_dto(self, model: TradeStatistics) -> TradeStatisticsDTO:
        """模型转 DTO"""
        return TradeStatisticsDTO(
            stat_id=model.stat_id,
            tenant_id=model.tenant_id,
            account_id=model.account_id,
            period_type=model.period_type,
            period_start=model.period_start,
            period_end=model.period_end,
            strategy_code=model.strategy_code,
            symbol=model.symbol,
            total_trades=model.total_trades,
            winning_trades=model.winning_trades,
            losing_trades=model.losing_trades,
            break_even_trades=model.break_even_trades,
            win_rate=model.win_rate,
            total_profit=model.total_profit,
            total_loss=model.total_loss,
            net_profit=model.net_profit,
            avg_profit=model.avg_profit,
            avg_loss=model.avg_loss,
            max_profit=model.max_profit,
            max_loss=model.max_loss,
            profit_loss_ratio=model.profit_loss_ratio,
            profit_factor=model.profit_factor,
            avg_holding_period=model.avg_holding_period,
            max_holding_period=model.max_holding_period,
            max_consecutive_wins=model.max_consecutive_wins,
            max_consecutive_losses=model.max_consecutive_losses,
            total_volume=model.total_volume,
            total_fee=model.total_fee,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    def create(
        self,
        account_id: int,
        period_type: str,
        period_start: date,
        period_end: date,
        strategy_code: Optional[str] = None,
        symbol: Optional[str] = None,
        **kwargs,
    ) -> TradeStatisticsDTO:
        """创建交易统计"""
        stat = TradeStatistics(
            stat_id=gen_id("STAT-"),
            tenant_id=self.tenant_id,
            account_id=account_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            strategy_code=strategy_code,
            symbol=symbol,
            **kwargs,
        )
        self.session.add(stat)
        self.session.flush()
        return self._to_dto(stat)
    
    def get_by_id(self, stat_id: str) -> Optional[TradeStatisticsDTO]:
        """根据 ID 获取统计"""
        stat = self.session.query(TradeStatistics).filter(
            TradeStatistics.stat_id == stat_id,
            TradeStatistics.tenant_id == self.tenant_id,
        ).first()
        return self._to_dto(stat) if stat else None
    
    def get_by_period(
        self,
        account_id: int,
        period_type: str,
        period_start: date,
        strategy_code: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> Optional[TradeStatisticsDTO]:
        """根据周期获取统计"""
        query = self.session.query(TradeStatistics).filter(
            TradeStatistics.tenant_id == self.tenant_id,
            TradeStatistics.account_id == account_id,
            TradeStatistics.period_type == period_type,
            TradeStatistics.period_start == period_start,
        )
        
        if strategy_code:
            query = query.filter(TradeStatistics.strategy_code == strategy_code)
        else:
            query = query.filter(TradeStatistics.strategy_code.is_(None))
        
        if symbol:
            query = query.filter(TradeStatistics.symbol == symbol)
        else:
            query = query.filter(TradeStatistics.symbol.is_(None))
        
        stat = query.first()
        return self._to_dto(stat) if stat else None
    
    def list_statistics(
        self,
        account_id: int,
        period_type: Optional[str] = None,
        strategy_code: Optional[str] = None,
        symbol: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
    ) -> List[TradeStatisticsDTO]:
        """查询统计列表"""
        query = self.session.query(TradeStatistics).filter(
            TradeStatistics.tenant_id == self.tenant_id,
            TradeStatistics.account_id == account_id,
        )
        
        if period_type:
            query = query.filter(TradeStatistics.period_type == period_type)
        if strategy_code:
            query = query.filter(TradeStatistics.strategy_code == strategy_code)
        if symbol:
            query = query.filter(TradeStatistics.symbol == symbol)
        if start_date:
            query = query.filter(TradeStatistics.period_start >= start_date)
        if end_date:
            query = query.filter(TradeStatistics.period_end <= end_date)
        
        stats = query.order_by(desc(TradeStatistics.period_start)).limit(limit).all()
        return [self._to_dto(s) for s in stats]
    
    def upsert(
        self,
        account_id: int,
        period_type: str,
        period_start: date,
        period_end: date,
        strategy_code: Optional[str] = None,
        symbol: Optional[str] = None,
        **kwargs,
    ) -> TradeStatisticsDTO:
        """更新或创建统计"""
        existing = self.get_by_period(
            account_id=account_id,
            period_type=period_type,
            period_start=period_start,
            strategy_code=strategy_code,
            symbol=symbol,
        )
        
        if existing:
            # 更新
            stat = self.session.query(TradeStatistics).filter(
                TradeStatistics.stat_id == existing.stat_id,
            ).first()
            
            stat.period_end = period_end
            for key, value in kwargs.items():
                if hasattr(stat, key) and value is not None:
                    setattr(stat, key, value)
            stat.updated_at = datetime.utcnow()
            
            self.session.flush()
            return self._to_dto(stat)
        else:
            # 创建
            return self.create(
                account_id=account_id,
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                strategy_code=strategy_code,
                symbol=symbol,
                **kwargs,
            )


class RiskMetricsRepository:
    """风险指标数据访问"""
    
    def __init__(self, session: Session, tenant_id: int):
        self.session = session
        self.tenant_id = tenant_id
    
    def _to_dto(self, model: RiskMetrics) -> RiskMetricsDTO:
        """模型转 DTO"""
        return RiskMetricsDTO(
            metric_id=model.metric_id,
            tenant_id=model.tenant_id,
            account_id=model.account_id,
            period_type=model.period_type,
            period_start=model.period_start,
            period_end=model.period_end,
            strategy_code=model.strategy_code,
            total_return=model.total_return,
            annualized_return=model.annualized_return,
            daily_volatility=model.daily_volatility,
            annualized_volatility=model.annualized_volatility,
            sharpe_ratio=model.sharpe_ratio,
            sortino_ratio=model.sortino_ratio,
            calmar_ratio=model.calmar_ratio,
            max_drawdown=model.max_drawdown,
            max_drawdown_duration=model.max_drawdown_duration,
            current_drawdown=model.current_drawdown,
            var_95=model.var_95,
            var_99=model.var_99,
            cvar_95=model.cvar_95,
            beta=model.beta,
            alpha=model.alpha,
            information_ratio=model.information_ratio,
            tracking_error=model.tracking_error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    def create(
        self,
        account_id: int,
        period_type: str,
        period_start: date,
        period_end: date,
        strategy_code: Optional[str] = None,
        **kwargs,
    ) -> RiskMetricsDTO:
        """创建风险指标"""
        metric = RiskMetrics(
            metric_id=gen_id("RISK-"),
            tenant_id=self.tenant_id,
            account_id=account_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            strategy_code=strategy_code,
            **kwargs,
        )
        self.session.add(metric)
        self.session.flush()
        return self._to_dto(metric)
    
    def get_by_id(self, metric_id: str) -> Optional[RiskMetricsDTO]:
        """根据 ID 获取指标"""
        metric = self.session.query(RiskMetrics).filter(
            RiskMetrics.metric_id == metric_id,
            RiskMetrics.tenant_id == self.tenant_id,
        ).first()
        return self._to_dto(metric) if metric else None
    
    def get_by_period(
        self,
        account_id: int,
        period_type: str,
        period_start: date,
        strategy_code: Optional[str] = None,
    ) -> Optional[RiskMetricsDTO]:
        """根据周期获取指标"""
        query = self.session.query(RiskMetrics).filter(
            RiskMetrics.tenant_id == self.tenant_id,
            RiskMetrics.account_id == account_id,
            RiskMetrics.period_type == period_type,
            RiskMetrics.period_start == period_start,
        )
        
        if strategy_code:
            query = query.filter(RiskMetrics.strategy_code == strategy_code)
        else:
            query = query.filter(RiskMetrics.strategy_code.is_(None))
        
        metric = query.first()
        return self._to_dto(metric) if metric else None
    
    def get_latest(
        self,
        account_id: int,
        strategy_code: Optional[str] = None,
    ) -> Optional[RiskMetricsDTO]:
        """获取最新风险指标"""
        query = self.session.query(RiskMetrics).filter(
            RiskMetrics.tenant_id == self.tenant_id,
            RiskMetrics.account_id == account_id,
        )
        
        if strategy_code:
            query = query.filter(RiskMetrics.strategy_code == strategy_code)
        
        metric = query.order_by(desc(RiskMetrics.period_end)).first()
        return self._to_dto(metric) if metric else None
    
    def list_metrics(
        self,
        account_id: int,
        period_type: Optional[str] = None,
        strategy_code: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
    ) -> List[RiskMetricsDTO]:
        """查询指标列表"""
        query = self.session.query(RiskMetrics).filter(
            RiskMetrics.tenant_id == self.tenant_id,
            RiskMetrics.account_id == account_id,
        )
        
        if period_type:
            query = query.filter(RiskMetrics.period_type == period_type)
        if strategy_code:
            query = query.filter(RiskMetrics.strategy_code == strategy_code)
        if start_date:
            query = query.filter(RiskMetrics.period_start >= start_date)
        if end_date:
            query = query.filter(RiskMetrics.period_end <= end_date)
        
        metrics = query.order_by(desc(RiskMetrics.period_start)).limit(limit).all()
        return [self._to_dto(m) for m in metrics]
    
    def upsert(
        self,
        account_id: int,
        period_type: str,
        period_start: date,
        period_end: date,
        strategy_code: Optional[str] = None,
        **kwargs,
    ) -> RiskMetricsDTO:
        """更新或创建指标"""
        existing = self.get_by_period(
            account_id=account_id,
            period_type=period_type,
            period_start=period_start,
            strategy_code=strategy_code,
        )
        
        if existing:
            # 更新
            metric = self.session.query(RiskMetrics).filter(
                RiskMetrics.metric_id == existing.metric_id,
            ).first()
            
            metric.period_end = period_end
            for key, value in kwargs.items():
                if hasattr(metric, key) and value is not None:
                    setattr(metric, key, value)
            metric.updated_at = datetime.utcnow()
            
            self.session.flush()
            return self._to_dto(metric)
        else:
            # 创建
            return self.create(
                account_id=account_id,
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                strategy_code=strategy_code,
                **kwargs,
            )
