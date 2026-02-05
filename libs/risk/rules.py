"""
Risk Rules - 风控规则实现

包含：
1. 仓位控制规则
2. 限额策略规则
3. 冷却机制规则
4. 其他通用规则
"""

from typing import Optional, List
from datetime import datetime, timedelta

from .engine import RiskRule, RiskCheckContext, RiskViolation


# ========== 仓位控制规则 ==========

class MaxPositionRule(RiskRule):
    """
    最大持仓数量限制
    
    限制账户同时持有的仓位数量
    """
    
    def __init__(self, max_positions: int = 10, enabled: bool = True):
        super().__init__(enabled)
        self.max_positions = max_positions
    
    @property
    def name(self) -> str:
        return "max_position"
    
    @property
    def code(self) -> str:
        return "RISK_MAX_POSITION"
    
    def check(self, ctx: RiskCheckContext) -> Optional[RiskViolation]:
        positions = ctx.account.positions or []
        current_count = len(positions)
        
        if current_count >= self.max_positions:
            return RiskViolation(
                rule_name=self.name,
                code=self.code,
                message=f"持仓数量已达上限 ({current_count}/{self.max_positions})",
                detail={
                    "current_positions": current_count,
                    "max_positions": self.max_positions,
                },
            )
        return None


class MaxPositionValueRule(RiskRule):
    """
    最大持仓价值限制
    
    限制单个仓位的最大价值（数量 * 价格）
    """
    
    def __init__(self, max_value: float = 10000.0, enabled: bool = True):
        super().__init__(enabled)
        self.max_value = max_value
    
    @property
    def name(self) -> str:
        return "max_position_value"
    
    @property
    def code(self) -> str:
        return "RISK_MAX_POSITION_VALUE"
    
    def check(self, ctx: RiskCheckContext) -> Optional[RiskViolation]:
        signal = ctx.signal
        quantity = signal.quantity or 0
        price = signal.entry_price or 0
        
        if quantity <= 0 or price <= 0:
            return None
        
        position_value = quantity * price
        
        if position_value > self.max_value:
            return RiskViolation(
                rule_name=self.name,
                code=self.code,
                message=f"仓位价值超限 ({position_value:.2f} > {self.max_value:.2f})",
                detail={
                    "position_value": position_value,
                    "max_value": self.max_value,
                    "quantity": quantity,
                    "price": price,
                },
            )
        return None


# ========== 限额策略规则 ==========

class DailyTradeLimitRule(RiskRule):
    """
    每日交易次数限制
    """
    
    def __init__(self, max_trades: int = 100, enabled: bool = True):
        super().__init__(enabled)
        self.max_trades = max_trades
    
    @property
    def name(self) -> str:
        return "daily_trade_limit"
    
    @property
    def code(self) -> str:
        return "RISK_DAILY_TRADE_LIMIT"
    
    def check(self, ctx: RiskCheckContext) -> Optional[RiskViolation]:
        if ctx.daily_trade_count >= self.max_trades:
            return RiskViolation(
                rule_name=self.name,
                code=self.code,
                message=f"今日交易次数已达上限 ({ctx.daily_trade_count}/{self.max_trades})",
                detail={
                    "daily_trade_count": ctx.daily_trade_count,
                    "max_trades": self.max_trades,
                },
            )
        return None


class WeeklyTradeLimitRule(RiskRule):
    """
    每周交易次数限制
    """
    
    def __init__(self, max_trades: int = 500, enabled: bool = True):
        super().__init__(enabled)
        self.max_trades = max_trades
    
    @property
    def name(self) -> str:
        return "weekly_trade_limit"
    
    @property
    def code(self) -> str:
        return "RISK_WEEKLY_TRADE_LIMIT"
    
    def check(self, ctx: RiskCheckContext) -> Optional[RiskViolation]:
        if ctx.weekly_trade_count >= self.max_trades:
            return RiskViolation(
                rule_name=self.name,
                code=self.code,
                message=f"本周交易次数已达上限 ({ctx.weekly_trade_count}/{self.max_trades})",
                detail={
                    "weekly_trade_count": ctx.weekly_trade_count,
                    "max_trades": self.max_trades,
                },
            )
        return None


class DailyLossLimitRule(RiskRule):
    """
    每日亏损限制
    
    当日亏损达到限额时停止交易
    """
    
    def __init__(self, max_loss: float = 1000.0, enabled: bool = True):
        super().__init__(enabled)
        self.max_loss = max_loss
    
    @property
    def name(self) -> str:
        return "daily_loss_limit"
    
    @property
    def code(self) -> str:
        return "RISK_DAILY_LOSS_LIMIT"
    
    def check(self, ctx: RiskCheckContext) -> Optional[RiskViolation]:
        if ctx.daily_loss >= self.max_loss:
            return RiskViolation(
                rule_name=self.name,
                code=self.code,
                message=f"今日亏损已达上限 ({ctx.daily_loss:.2f} >= {self.max_loss:.2f})",
                severity="critical",
                detail={
                    "daily_loss": ctx.daily_loss,
                    "max_loss": self.max_loss,
                },
            )
        return None


# ========== 冷却机制规则 ==========

class ConsecutiveLossCooldownRule(RiskRule):
    """
    连续亏损冷却
    
    连续亏损达到指定次数后，进入冷却期
    """
    
    def __init__(
        self,
        max_consecutive: int = 5,
        cooldown_minutes: int = 30,
        enabled: bool = True
    ):
        super().__init__(enabled)
        self.max_consecutive = max_consecutive
        self.cooldown_minutes = cooldown_minutes
    
    @property
    def name(self) -> str:
        return "consecutive_loss_cooldown"
    
    @property
    def code(self) -> str:
        return "RISK_CONSECUTIVE_LOSS"
    
    def check(self, ctx: RiskCheckContext) -> Optional[RiskViolation]:
        if ctx.consecutive_losses >= self.max_consecutive:
            return RiskViolation(
                rule_name=self.name,
                code=self.code,
                message=f"连续亏损 {ctx.consecutive_losses} 次，需冷却 {self.cooldown_minutes} 分钟",
                severity="warning",
                detail={
                    "consecutive_losses": ctx.consecutive_losses,
                    "max_consecutive": self.max_consecutive,
                    "cooldown_minutes": self.cooldown_minutes,
                },
            )
        return None


class TradeCooldownRule(RiskRule):
    """
    交易冷却
    
    两次交易之间的最小间隔
    """
    
    def __init__(self, cooldown_seconds: int = 60, enabled: bool = True):
        super().__init__(enabled)
        self.cooldown_seconds = cooldown_seconds
    
    @property
    def name(self) -> str:
        return "trade_cooldown"
    
    @property
    def code(self) -> str:
        return "RISK_TRADE_COOLDOWN"
    
    def check(self, ctx: RiskCheckContext) -> Optional[RiskViolation]:
        if not ctx.last_trade_time:
            return None
        
        elapsed = (datetime.utcnow() - ctx.last_trade_time).total_seconds()
        
        if elapsed < self.cooldown_seconds:
            remaining = self.cooldown_seconds - elapsed
            return RiskViolation(
                rule_name=self.name,
                code=self.code,
                message=f"交易冷却中，剩余 {remaining:.0f} 秒",
                severity="warning",
                detail={
                    "elapsed_seconds": elapsed,
                    "cooldown_seconds": self.cooldown_seconds,
                    "remaining_seconds": remaining,
                },
            )
        return None


# ========== 其他通用规则 ==========

class SymbolWhitelistRule(RiskRule):
    """
    交易品种白名单
    
    只允许交易白名单内的品种
    """
    
    def __init__(self, whitelist: List[str], enabled: bool = True):
        super().__init__(enabled)
        self.whitelist = [s.upper() for s in whitelist]
    
    @property
    def name(self) -> str:
        return "symbol_whitelist"
    
    @property
    def code(self) -> str:
        return "RISK_SYMBOL_NOT_ALLOWED"
    
    def check(self, ctx: RiskCheckContext) -> Optional[RiskViolation]:
        if not self.whitelist:
            return None
        
        symbol = ctx.signal.symbol.upper()
        canonical = ctx.signal.canonical_symbol.upper() if ctx.signal.canonical_symbol else symbol
        
        if symbol not in self.whitelist and canonical not in self.whitelist:
            return RiskViolation(
                rule_name=self.name,
                code=self.code,
                message=f"品种 {symbol} 不在白名单内",
                detail={
                    "symbol": symbol,
                    "whitelist": self.whitelist,
                },
            )
        return None


class SymbolBlacklistRule(RiskRule):
    """
    交易品种黑名单
    
    禁止交易黑名单内的品种
    """
    
    def __init__(self, blacklist: List[str], enabled: bool = True):
        super().__init__(enabled)
        self.blacklist = [s.upper() for s in blacklist]
    
    @property
    def name(self) -> str:
        return "symbol_blacklist"
    
    @property
    def code(self) -> str:
        return "RISK_SYMBOL_BLOCKED"
    
    def check(self, ctx: RiskCheckContext) -> Optional[RiskViolation]:
        if not self.blacklist:
            return None
        
        symbol = ctx.signal.symbol.upper()
        canonical = ctx.signal.canonical_symbol.upper() if ctx.signal.canonical_symbol else symbol
        
        if symbol in self.blacklist or canonical in self.blacklist:
            return RiskViolation(
                rule_name=self.name,
                code=self.code,
                message=f"品种 {symbol} 在黑名单内",
                detail={
                    "symbol": symbol,
                    "blacklist": self.blacklist,
                },
            )
        return None


class MinBalanceRule(RiskRule):
    """
    最小余额限制
    
    账户可用余额低于阈值时停止交易
    """
    
    def __init__(self, min_balance: float = 100.0, enabled: bool = True):
        super().__init__(enabled)
        self.min_balance = min_balance
    
    @property
    def name(self) -> str:
        return "min_balance"
    
    @property
    def code(self) -> str:
        return "RISK_INSUFFICIENT_BALANCE"
    
    def check(self, ctx: RiskCheckContext) -> Optional[RiskViolation]:
        available = ctx.account.available
        
        if available < self.min_balance:
            return RiskViolation(
                rule_name=self.name,
                code=self.code,
                message=f"可用余额不足 ({available:.2f} < {self.min_balance:.2f})",
                severity="critical",
                detail={
                    "available": available,
                    "min_balance": self.min_balance,
                },
            )
        return None
