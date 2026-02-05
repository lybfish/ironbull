"""
Analytics Service - 分析服务层

职责：
- 从 OrderTrade/Position/Ledger 读取数据
- 计算绩效指标、风险指标、交易统计
- 生成净值曲线
- 存储分析结果

遵循蓝图不变量：
1. 指标可复现：给定相同输入，结果完全一致
2. 口径一致：回测与实盘使用相同公式
3. 数据来源明确：来自 OrderTrade/Position/Ledger
4. 无反向写入：只读取上游数据
"""

from datetime import date, datetime, timedelta
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from libs.core import get_logger, gen_id
from libs.order_trade.models import Order, Fill
from libs.position.models import Position, PositionChange
from libs.ledger.models import Account, Transaction, EquitySnapshot

from .models import PerformanceSnapshot, TradeStatistics, RiskMetrics
from .states import PeriodType, MetricCalculator, AnalyticsValidation
from .contracts import (
    PerformanceSnapshotDTO,
    TradeStatisticsDTO,
    RiskMetricsDTO,
    CreateSnapshotDTO,
    CalculateMetricsDTO,
    PerformanceSummary,
    EquityCurve,
    EquityCurvePoint,
)
from .exceptions import (
    AnalyticsError,
    InsufficientDataError,
    InvalidDateRangeError,
    InvalidPeriodTypeError,
    DuplicateSnapshotError,
)
from .repository import (
    PerformanceSnapshotRepository,
    TradeStatisticsRepository,
    RiskMetricsRepository,
)

logger = get_logger("analytics")


class AnalyticsService:
    """
    分析服务
    
    提供绩效分析、风险分析、交易统计等功能
    """
    
    def __init__(
        self,
        session: Session,
        tenant_id: int,
        account_id: int,
    ):
        self.session = session
        self.tenant_id = tenant_id
        self.account_id = account_id
        
        # 初始化仓库
        self.snapshot_repo = PerformanceSnapshotRepository(session, tenant_id)
        self.stats_repo = TradeStatisticsRepository(session, tenant_id)
        self.risk_repo = RiskMetricsRepository(session, tenant_id)
        
        self.calculator = MetricCalculator()
    
    # ========== 绩效快照 ==========
    
    def create_daily_snapshot(
        self,
        snapshot_date: date,
        balance: float,
        position_value: float,
        benchmark_value: Optional[float] = None,
    ) -> PerformanceSnapshotDTO:
        """
        创建每日绩效快照
        
        从 Ledger 和 Position 数据计算当日绩效
        """
        total_equity = balance + position_value
        
        # 获取前一天快照
        prev_snapshot = self._get_previous_snapshot(snapshot_date)
        
        if prev_snapshot:
            prev_equity = prev_snapshot.total_equity
            prev_net_value = prev_snapshot.net_value
            prev_cumulative_pnl = prev_snapshot.cumulative_pnl
        else:
            # 第一天
            prev_equity = total_equity
            prev_net_value = 1.0
            prev_cumulative_pnl = 0.0
        
        # 计算当日盈亏和收益率
        daily_pnl = total_equity - prev_equity
        daily_return = self.calculator.calculate_return(prev_equity, total_equity)
        
        # 计算累计
        cumulative_pnl = prev_cumulative_pnl + daily_pnl
        
        # 计算净值
        net_value = prev_net_value * (1 + daily_return / 100)
        
        # 计算累计收益率
        first_snapshot = self._get_first_snapshot()
        if first_snapshot:
            initial_equity = first_snapshot.total_equity
            cumulative_return = self.calculator.calculate_return(initial_equity, total_equity)
        else:
            cumulative_return = 0.0
        
        # 基准收益
        benchmark_return = None
        if benchmark_value and prev_snapshot and prev_snapshot.benchmark_value:
            benchmark_return = self.calculator.calculate_return(
                prev_snapshot.benchmark_value,
                benchmark_value
            )
        
        # 创建快照
        return self.snapshot_repo.create(
            account_id=self.account_id,
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
        )
    
    def _get_previous_snapshot(self, current_date: date) -> Optional[PerformanceSnapshotDTO]:
        """获取前一天的快照"""
        snapshots = self.snapshot_repo.list_snapshots(
            account_id=self.account_id,
            end_date=current_date - timedelta(days=1),
            limit=1,
        )
        # 获取最后一条（最接近 current_date 的）
        if snapshots:
            return self.snapshot_repo.get_latest(self.account_id)
        return None
    
    def _get_first_snapshot(self) -> Optional[PerformanceSnapshotDTO]:
        """获取第一个快照"""
        snapshots = self.snapshot_repo.list_snapshots(
            account_id=self.account_id,
            limit=1,
        )
        return snapshots[0] if snapshots else None
    
    def get_equity_curve(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> EquityCurve:
        """
        获取净值曲线
        
        返回指定日期范围内的每日净值数据
        """
        snapshots = self.snapshot_repo.list_snapshots(
            account_id=self.account_id,
            start_date=start_date,
            end_date=end_date,
            limit=3650,  # 最多 10 年
        )
        
        if not snapshots:
            return EquityCurve(
                tenant_id=self.tenant_id,
                account_id=self.account_id,
                start_date=start_date or date.today(),
                end_date=end_date or date.today(),
                points=[],
            )
        
        # 计算回撤
        equity_series = [s.total_equity for s in snapshots]
        max_dd, _, _, _ = self.calculator.calculate_max_drawdown(equity_series)
        
        # 构建曲线点
        points = []
        peak_equity = equity_series[0]
        
        for snapshot in snapshots:
            if snapshot.total_equity > peak_equity:
                peak_equity = snapshot.total_equity
            
            current_dd = 0.0
            if peak_equity > 0:
                current_dd = (peak_equity - snapshot.total_equity) / peak_equity * 100
            
            points.append(EquityCurvePoint(
                date=snapshot.snapshot_date,
                equity=snapshot.total_equity,
                net_value=snapshot.net_value,
                daily_return=snapshot.daily_return,
                cumulative_return=snapshot.cumulative_return,
                drawdown=current_dd,
            ))
        
        return EquityCurve(
            tenant_id=self.tenant_id,
            account_id=self.account_id,
            start_date=snapshots[0].snapshot_date,
            end_date=snapshots[-1].snapshot_date,
            points=points,
            initial_equity=snapshots[0].total_equity,
            final_equity=snapshots[-1].total_equity,
            total_return=snapshots[-1].cumulative_return,
            max_drawdown=max_dd,
        )
    
    # ========== 风险指标 ==========
    
    def calculate_risk_metrics(
        self,
        start_date: date,
        end_date: date,
        period_type: str = "all",
        strategy_code: Optional[str] = None,
    ) -> RiskMetricsDTO:
        """
        计算并保存风险指标
        
        基于绩效快照计算各类风险指标
        """
        # 验证日期范围
        if start_date > end_date:
            raise InvalidDateRangeError(start_date, end_date)
        
        # 获取快照数据
        snapshots = self.snapshot_repo.list_snapshots(
            account_id=self.account_id,
            start_date=start_date,
            end_date=end_date,
            limit=3650,
        )
        
        if len(snapshots) < 2:
            raise InsufficientDataError(
                f"Need at least 2 snapshots for risk calculation, got {len(snapshots)}"
            )
        
        # 提取净值序列
        equity_series = [s.total_equity for s in snapshots]
        
        # 计算日收益率
        daily_returns = self.calculator.calculate_daily_returns(equity_series)
        
        if len(daily_returns) < 1:
            raise InsufficientDataError("Need at least 1 daily return for calculation")
        
        # 计算天数
        days = (end_date - start_date).days
        if days <= 0:
            days = 1
        
        # 总收益率
        total_return = self.calculator.calculate_return(
            equity_series[0],
            equity_series[-1]
        )
        
        # 年化收益率
        annualized_return = self.calculator.calculate_annualized_return(total_return, days)
        
        # 波动率
        daily_volatility = self.calculator.calculate_volatility(daily_returns)
        annualized_volatility = self.calculator.calculate_annualized_volatility(daily_volatility)
        
        # 下行波动率
        downside_vol = self.calculator.calculate_downside_volatility(daily_returns)
        annualized_downside_vol = self.calculator.calculate_annualized_volatility(downside_vol)
        
        # 夏普比率
        sharpe_ratio = self.calculator.calculate_sharpe_ratio(
            annualized_return,
            annualized_volatility
        )
        
        # 索提诺比率
        sortino_ratio = self.calculator.calculate_sortino_ratio(
            annualized_return,
            annualized_downside_vol
        )
        
        # 最大回撤
        max_dd, dd_start, dd_end, dd_duration = self.calculator.calculate_max_drawdown(equity_series)
        
        # 卡玛比率
        calmar_ratio = self.calculator.calculate_calmar_ratio(annualized_return, max_dd)
        
        # 当前回撤
        peak = max(equity_series)
        current_dd = (peak - equity_series[-1]) / peak * 100 if peak > 0 else 0
        
        # VaR
        var_95 = self.calculator.calculate_var(daily_returns, 0.95)
        var_99 = self.calculator.calculate_var(daily_returns, 0.99)
        cvar_95 = self.calculator.calculate_cvar(daily_returns, 0.95)
        
        # 保存指标
        return self.risk_repo.upsert(
            account_id=self.account_id,
            period_type=period_type,
            period_start=start_date,
            period_end=end_date,
            strategy_code=strategy_code,
            total_return=round(total_return, 4),
            annualized_return=round(annualized_return, 4),
            daily_volatility=round(daily_volatility, 4),
            annualized_volatility=round(annualized_volatility, 4),
            sharpe_ratio=round(sharpe_ratio, 4),
            sortino_ratio=round(sortino_ratio, 4),
            calmar_ratio=round(calmar_ratio, 4),
            max_drawdown=round(max_dd, 4),
            max_drawdown_duration=dd_duration,
            current_drawdown=round(current_dd, 4),
            var_95=round(var_95, 4) if var_95 else None,
            var_99=round(var_99, 4) if var_99 else None,
            cvar_95=round(cvar_95, 4) if cvar_95 else None,
        )
    
    def get_latest_risk_metrics(
        self,
        strategy_code: Optional[str] = None,
    ) -> Optional[RiskMetricsDTO]:
        """获取最新风险指标"""
        return self.risk_repo.get_latest(
            account_id=self.account_id,
            strategy_code=strategy_code,
        )
    
    # ========== 交易统计 ==========
    
    def calculate_trade_statistics(
        self,
        start_date: date,
        end_date: date,
        period_type: str = "all",
        strategy_code: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> TradeStatisticsDTO:
        """
        计算并保存交易统计
        
        从 OrderTrade 数据计算交易指标
        """
        # 验证日期范围
        if start_date > end_date:
            raise InvalidDateRangeError(start_date, end_date)
        
        # 查询已完成的订单
        query = self.session.query(Order).filter(
            Order.tenant_id == self.tenant_id,
            Order.account_id == self.account_id,
            Order.status == "FILLED",
            Order.created_at >= datetime.combine(start_date, datetime.min.time()),
            Order.created_at <= datetime.combine(end_date, datetime.max.time()),
        )
        
        if strategy_code:
            # 如果有 strategy_code 字段可以过滤
            pass
        if symbol:
            query = query.filter(Order.symbol == symbol)
        
        orders = query.all()
        
        if not orders:
            # 没有交易，返回空统计
            return self.stats_repo.upsert(
                account_id=self.account_id,
                period_type=period_type,
                period_start=start_date,
                period_end=end_date,
                strategy_code=strategy_code,
                symbol=symbol,
                total_trades=0,
            )
        
        # 计算统计
        total_trades = len(orders)
        winning_trades = 0
        losing_trades = 0
        break_even_trades = 0
        
        total_profit = 0.0
        total_loss = 0.0
        profits = []
        losses = []
        
        total_volume = 0.0
        total_fee = 0.0
        
        holding_periods = []
        
        # 用于计算连续胜负
        results = []  # 1 = win, -1 = loss, 0 = break even
        
        for order in orders:
            # 获取该订单的成交
            fills = self.session.query(Fill).filter(
                Fill.order_id == order.order_id,
            ).all()
            
            if not fills:
                continue
            
            # 计算订单盈亏（简化：使用 realized_pnl 如果有）
            pnl = float(order.realized_pnl or 0)
            
            # 如果没有 realized_pnl，尝试从成交计算
            if pnl == 0 and hasattr(order, 'filled_price') and order.filled_price:
                # 这里简化处理，实际需要配对开仓/平仓订单
                pass
            
            if pnl > 0:
                winning_trades += 1
                total_profit += pnl
                profits.append(pnl)
                results.append(1)
            elif pnl < 0:
                losing_trades += 1
                total_loss += abs(pnl)
                losses.append(abs(pnl))
                results.append(-1)
            else:
                break_even_trades += 1
                results.append(0)
            
            # 交易量和手续费
            total_volume += float(order.filled_quantity or 0) * float(order.filled_price or 0)
            total_fee += float(order.total_fee or 0)
            
            # 持仓时间（需要配对订单，这里简化）
            # holding_periods.append(...)
        
        # 胜率
        win_rate = self.calculator.calculate_win_rate(winning_trades, total_trades)
        
        # 平均盈亏
        avg_profit = sum(profits) / len(profits) if profits else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        max_profit = max(profits) if profits else 0
        max_loss = max(losses) if losses else 0
        
        # 净利润
        net_profit = total_profit - total_loss
        
        # 盈亏比
        profit_loss_ratio = self.calculator.calculate_profit_loss_ratio(avg_profit, avg_loss)
        profit_factor = self.calculator.calculate_profit_factor(total_profit, total_loss)
        
        # 连续胜负
        max_consecutive_wins = self._max_consecutive(results, 1)
        max_consecutive_losses = self._max_consecutive(results, -1)
        
        # 保存统计
        return self.stats_repo.upsert(
            account_id=self.account_id,
            period_type=period_type,
            period_start=start_date,
            period_end=end_date,
            strategy_code=strategy_code,
            symbol=symbol,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            break_even_trades=break_even_trades,
            win_rate=round(win_rate, 2),
            total_profit=round(total_profit, 4),
            total_loss=round(total_loss, 4),
            net_profit=round(net_profit, 4),
            avg_profit=round(avg_profit, 4),
            avg_loss=round(avg_loss, 4),
            max_profit=round(max_profit, 4),
            max_loss=round(max_loss, 4),
            profit_loss_ratio=round(profit_loss_ratio, 4),
            profit_factor=round(profit_factor, 4),
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            total_volume=round(total_volume, 4),
            total_fee=round(total_fee, 4),
        )
    
    def _max_consecutive(self, results: List[int], target: int) -> int:
        """计算最大连续次数"""
        max_count = 0
        current_count = 0
        
        for r in results:
            if r == target:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        
        return max_count
    
    # ========== 汇总 ==========
    
    def get_performance_summary(self) -> PerformanceSummary:
        """
        获取绩效汇总
        
        返回当前账户的关键绩效指标
        """
        summary = PerformanceSummary(
            tenant_id=self.tenant_id,
            account_id=self.account_id,
        )
        
        # 获取最新快照
        latest = self.snapshot_repo.get_latest(self.account_id)
        if latest:
            summary.current_equity = latest.total_equity
            summary.current_net_value = latest.net_value
            summary.total_return = latest.cumulative_return
            summary.daily_pnl = latest.daily_pnl
            summary.daily_return = latest.daily_return
        
        # 获取最新风险指标
        risk = self.risk_repo.get_latest(self.account_id)
        if risk:
            summary.annualized_return = risk.annualized_return
            summary.max_drawdown = risk.max_drawdown
            summary.sharpe_ratio = risk.sharpe_ratio
        
        # 获取最新交易统计
        stats_list = self.stats_repo.list_statistics(
            account_id=self.account_id,
            period_type="all",
            limit=1,
        )
        if stats_list:
            stats = stats_list[0]
            summary.total_trades = stats.total_trades
            summary.win_rate = stats.win_rate
            summary.profit_factor = stats.profit_factor
        
        return summary
    
    # ========== 从上游数据同步 ==========
    
    def sync_from_ledger(
        self,
        target_date: Optional[date] = None,
    ) -> Optional[PerformanceSnapshotDTO]:
        """
        从 Ledger 同步数据创建快照
        
        读取 Ledger 的 EquitySnapshot 或 Account，创建绩效快照
        """
        target = target_date or date.today()
        
        # 查询账户
        account = self.session.query(Account).filter(
            Account.tenant_id == self.tenant_id,
            Account.account_id == self.account_id,
        ).first()
        
        if not account:
            logger.warning(
                "Account not found for analytics sync",
                tenant_id=self.tenant_id,
                account_id=self.account_id,
            )
            return None
        
        # 查询持仓市值（从 Position）
        from libs.position.models import Position as PositionModel
        
        positions = self.session.query(PositionModel).filter(
            PositionModel.tenant_id == self.tenant_id,
            PositionModel.account_id == self.account_id,
            PositionModel.status == "OPEN",
        ).all()
        
        # 简化：使用 total_cost 作为持仓价值
        # 实际应该使用最新市价 * 数量
        position_value = sum(float(p.total_cost or 0) for p in positions)
        
        # 创建快照
        return self.create_daily_snapshot(
            snapshot_date=target,
            balance=float(account.balance or 0),
            position_value=position_value,
        )
