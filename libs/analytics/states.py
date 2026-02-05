"""
Analytics States - 分析模块状态和计算逻辑

包含：
- 周期类型枚举
- 指标计算函数
- 验证规则
"""

from enum import Enum
from typing import List, Optional, Tuple
from datetime import date, datetime, timedelta
import math


class PeriodType(str, Enum):
    """统计周期类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ALL = "all"  # 全部时间


class MetricCalculator:
    """
    指标计算器
    
    所有计算都是纯函数，确保可复现
    """
    
    # 年化天数（加密货币 365 天）
    ANNUAL_DAYS = 365
    # 无风险收益率（默认 0%）
    RISK_FREE_RATE = 0.0
    
    @staticmethod
    def calculate_return(
        start_value: float,
        end_value: float,
    ) -> float:
        """
        计算收益率
        
        Returns:
            收益率（百分比）
        """
        if start_value <= 0:
            return 0.0
        return ((end_value - start_value) / start_value) * 100
    
    @staticmethod
    def calculate_daily_returns(equity_series: List[float]) -> List[float]:
        """
        计算日收益率序列
        
        Args:
            equity_series: 每日净值序列
        
        Returns:
            日收益率序列（百分比）
        """
        if len(equity_series) < 2:
            return []
        
        returns = []
        for i in range(1, len(equity_series)):
            if equity_series[i-1] > 0:
                daily_return = ((equity_series[i] - equity_series[i-1]) / equity_series[i-1]) * 100
                returns.append(daily_return)
            else:
                returns.append(0.0)
        return returns
    
    @staticmethod
    def calculate_cumulative_return(returns: List[float]) -> float:
        """
        计算累计收益率
        
        Args:
            returns: 日收益率序列（百分比）
        
        Returns:
            累计收益率（百分比）
        """
        if not returns:
            return 0.0
        
        cumulative = 1.0
        for r in returns:
            cumulative *= (1 + r / 100)
        return (cumulative - 1) * 100
    
    @staticmethod
    def calculate_annualized_return(
        total_return: float,
        days: int,
    ) -> float:
        """
        计算年化收益率
        
        Args:
            total_return: 总收益率（百分比）
            days: 天数
        
        Returns:
            年化收益率（百分比）
        """
        if days <= 0:
            return 0.0
        
        # (1 + r) ^ (365 / days) - 1
        years = days / MetricCalculator.ANNUAL_DAYS
        if years <= 0:
            return 0.0
        
        return ((1 + total_return / 100) ** (1 / years) - 1) * 100
    
    @staticmethod
    def calculate_volatility(returns: List[float]) -> float:
        """
        计算日波动率（标准差）
        
        Args:
            returns: 日收益率序列（百分比）
        
        Returns:
            日波动率（百分比）
        """
        if len(returns) < 2:
            return 0.0
        
        n = len(returns)
        mean = sum(returns) / n
        variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
        return math.sqrt(variance)
    
    @staticmethod
    def calculate_annualized_volatility(daily_volatility: float) -> float:
        """
        计算年化波动率
        
        Args:
            daily_volatility: 日波动率（百分比）
        
        Returns:
            年化波动率（百分比）
        """
        return daily_volatility * math.sqrt(MetricCalculator.ANNUAL_DAYS)
    
    @staticmethod
    def calculate_sharpe_ratio(
        annualized_return: float,
        annualized_volatility: float,
        risk_free_rate: float = 0.0,
    ) -> float:
        """
        计算夏普比率
        
        Sharpe = (Rp - Rf) / σp
        
        Args:
            annualized_return: 年化收益率（百分比）
            annualized_volatility: 年化波动率（百分比）
            risk_free_rate: 无风险收益率（百分比）
        
        Returns:
            夏普比率
        """
        if annualized_volatility <= 0:
            return 0.0
        return (annualized_return - risk_free_rate) / annualized_volatility
    
    @staticmethod
    def calculate_sortino_ratio(
        annualized_return: float,
        downside_volatility: float,
        risk_free_rate: float = 0.0,
    ) -> float:
        """
        计算索提诺比率
        
        Sortino = (Rp - Rf) / σd
        只考虑下行波动率
        
        Args:
            annualized_return: 年化收益率（百分比）
            downside_volatility: 年化下行波动率（百分比）
            risk_free_rate: 无风险收益率（百分比）
        
        Returns:
            索提诺比率
        """
        if downside_volatility <= 0:
            return 0.0
        return (annualized_return - risk_free_rate) / downside_volatility
    
    @staticmethod
    def calculate_downside_volatility(
        returns: List[float],
        target_return: float = 0.0,
    ) -> float:
        """
        计算下行波动率
        
        只计算低于目标收益率的收益的波动率
        
        Args:
            returns: 日收益率序列（百分比）
            target_return: 目标收益率（百分比）
        
        Returns:
            下行波动率（百分比）
        """
        downside_returns = [r for r in returns if r < target_return]
        if len(downside_returns) < 2:
            return 0.0
        
        n = len(downside_returns)
        mean = target_return
        variance = sum((r - mean) ** 2 for r in downside_returns) / (n - 1)
        return math.sqrt(variance)
    
    @staticmethod
    def calculate_max_drawdown(equity_series: List[float]) -> Tuple[float, int, int, int]:
        """
        计算最大回撤
        
        Args:
            equity_series: 净值序列
        
        Returns:
            (最大回撤百分比, 回撤开始索引, 回撤最低点索引, 回撤持续天数)
        """
        if len(equity_series) < 2:
            return (0.0, 0, 0, 0)
        
        max_dd = 0.0
        peak = equity_series[0]
        peak_idx = 0
        dd_start = 0
        dd_end = 0
        
        for i, value in enumerate(equity_series):
            if value > peak:
                peak = value
                peak_idx = i
            
            if peak > 0:
                dd = (peak - value) / peak * 100
                if dd > max_dd:
                    max_dd = dd
                    dd_start = peak_idx
                    dd_end = i
        
        duration = dd_end - dd_start
        return (max_dd, dd_start, dd_end, duration)
    
    @staticmethod
    def calculate_calmar_ratio(
        annualized_return: float,
        max_drawdown: float,
    ) -> float:
        """
        计算卡玛比率
        
        Calmar = 年化收益率 / 最大回撤
        
        Args:
            annualized_return: 年化收益率（百分比）
            max_drawdown: 最大回撤（百分比）
        
        Returns:
            卡玛比率
        """
        if max_drawdown <= 0:
            return 0.0
        return annualized_return / max_drawdown
    
    @staticmethod
    def calculate_var(
        returns: List[float],
        confidence: float = 0.95,
    ) -> float:
        """
        计算 VaR (Value at Risk)
        
        使用历史模拟法
        
        Args:
            returns: 日收益率序列（百分比）
            confidence: 置信度 (0.95 或 0.99)
        
        Returns:
            VaR（百分比，负值表示损失）
        """
        if len(returns) < 10:
            return 0.0
        
        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))
        return sorted_returns[index]
    
    @staticmethod
    def calculate_cvar(
        returns: List[float],
        confidence: float = 0.95,
    ) -> float:
        """
        计算 CVaR (Conditional Value at Risk)
        
        超过 VaR 的平均损失
        
        Args:
            returns: 日收益率序列（百分比）
            confidence: 置信度
        
        Returns:
            CVaR（百分比，负值表示损失）
        """
        if len(returns) < 10:
            return 0.0
        
        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))
        tail_returns = sorted_returns[:index + 1]
        
        if not tail_returns:
            return 0.0
        
        return sum(tail_returns) / len(tail_returns)
    
    @staticmethod
    def calculate_win_rate(
        winning_trades: int,
        total_trades: int,
    ) -> float:
        """
        计算胜率
        
        Args:
            winning_trades: 盈利交易次数
            total_trades: 总交易次数
        
        Returns:
            胜率（百分比）
        """
        if total_trades <= 0:
            return 0.0
        return (winning_trades / total_trades) * 100
    
    @staticmethod
    def calculate_profit_loss_ratio(
        avg_profit: float,
        avg_loss: float,
    ) -> float:
        """
        计算盈亏比
        
        Args:
            avg_profit: 平均盈利
            avg_loss: 平均亏损（绝对值）
        
        Returns:
            盈亏比
        """
        if avg_loss <= 0:
            return 0.0 if avg_profit <= 0 else float('inf')
        return avg_profit / avg_loss
    
    @staticmethod
    def calculate_profit_factor(
        total_profit: float,
        total_loss: float,
    ) -> float:
        """
        计算获利因子
        
        Args:
            total_profit: 总盈利
            total_loss: 总亏损（绝对值）
        
        Returns:
            获利因子
        """
        if total_loss <= 0:
            return 0.0 if total_profit <= 0 else float('inf')
        return total_profit / total_loss
    
    @staticmethod
    def calculate_expectancy(
        win_rate: float,
        avg_profit: float,
        avg_loss: float,
    ) -> float:
        """
        计算期望收益
        
        E = Win% * AvgWin - Loss% * AvgLoss
        
        Args:
            win_rate: 胜率（百分比）
            avg_profit: 平均盈利
            avg_loss: 平均亏损（绝对值）
        
        Returns:
            期望收益
        """
        win_pct = win_rate / 100
        loss_pct = 1 - win_pct
        return win_pct * avg_profit - loss_pct * avg_loss


class AnalyticsValidation:
    """分析指标验证"""
    
    @staticmethod
    def validate_equity_series(equity_series: List[float]) -> bool:
        """验证净值序列"""
        if not equity_series:
            return False
        return all(e >= 0 for e in equity_series)
    
    @staticmethod
    def validate_date_range(start_date: date, end_date: date) -> bool:
        """验证日期范围"""
        return start_date <= end_date
    
    @staticmethod
    def validate_period_type(period_type: str) -> bool:
        """验证周期类型"""
        try:
            PeriodType(period_type)
            return True
        except ValueError:
            return False
