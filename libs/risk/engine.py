"""
Risk Engine - 风控规则引擎

支持规则链执行，可配置是否遇到失败就停止
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from libs.contracts import Signal, AccountContext
from libs.core import get_logger

logger = get_logger("risk-engine")


@dataclass
class RiskCheckContext:
    """
    风控检查上下文
    
    包含信号、账户信息，以及可选的历史数据
    """
    signal: Signal
    account: AccountContext
    
    # 历史数据（用于限额/冷却检查）
    recent_trades: List[Dict] = field(default_factory=list)  # 最近交易记录
    recent_losses: List[float] = field(default_factory=list)  # 最近亏损列表
    last_trade_time: Optional[datetime] = None  # 最后交易时间
    
    # 统计数据
    daily_trade_count: int = 0      # 今日交易次数
    weekly_trade_count: int = 0     # 本周交易次数
    daily_loss: float = 0.0         # 今日亏损
    consecutive_losses: int = 0     # 连续亏损次数
    
    # 额外配置
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskViolation:
    """风控违规记录"""
    rule_name: str           # 规则名称
    code: str                # 错误码
    message: str             # 错误描述
    severity: str = "error"  # 严重程度: warning, error, critical
    detail: Dict[str, Any] = field(default_factory=dict)


class RiskRule(ABC):
    """
    风控规则基类
    
    所有具体规则都需要继承此类并实现 check 方法
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    @property
    @abstractmethod
    def name(self) -> str:
        """规则名称"""
        pass
    
    @property
    @abstractmethod
    def code(self) -> str:
        """规则错误码"""
        pass
    
    @abstractmethod
    def check(self, ctx: RiskCheckContext) -> Optional[RiskViolation]:
        """
        执行规则检查
        
        Args:
            ctx: 风控检查上下文
        
        Returns:
            None 如果通过，RiskViolation 如果违规
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(enabled={self.enabled})"


class RiskEngine:
    """
    风控规则引擎
    
    执行规则链，收集所有违规或遇到第一个就停止
    
    使用方式：
        engine = RiskEngine()
        engine.add_rule(MaxPositionRule(max_positions=10))
        engine.add_rule(DailyTradeLimitRule(max_trades=50))
        
        violations = engine.check(ctx)
        if violations:
            print("风控未通过:", violations)
    """
    
    def __init__(self, fail_fast: bool = True):
        """
        Args:
            fail_fast: 遇到第一个违规就停止（默认 True）
        """
        self.rules: List[RiskRule] = []
        self.fail_fast = fail_fast
    
    def add_rule(self, rule: RiskRule) -> "RiskEngine":
        """添加规则"""
        self.rules.append(rule)
        return self
    
    def add_rules(self, rules: List[RiskRule]) -> "RiskEngine":
        """批量添加规则"""
        self.rules.extend(rules)
        return self
    
    def remove_rule(self, rule_name: str) -> bool:
        """移除规则"""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                self.rules.pop(i)
                return True
        return False
    
    def check(self, ctx: RiskCheckContext) -> List[RiskViolation]:
        """
        执行所有规则检查
        
        Args:
            ctx: 风控检查上下文
        
        Returns:
            违规列表（空表示全部通过）
        """
        violations: List[RiskViolation] = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                violation = rule.check(ctx)
                if violation:
                    violations.append(violation)
                    logger.warning(
                        "risk rule violated",
                        rule=rule.name,
                        code=violation.code,
                        message=violation.message,
                        signal_id=ctx.signal.signal_id,
                        account_id=ctx.account.account_id,
                    )
                    
                    if self.fail_fast:
                        break
            except Exception as e:
                logger.error(
                    "risk rule check failed",
                    rule=rule.name,
                    error=str(e),
                )
                # 规则执行异常视为通过（不阻塞交易）
                continue
        
        return violations
    
    def is_passed(self, ctx: RiskCheckContext) -> bool:
        """检查是否通过（简化版）"""
        return len(self.check(ctx)) == 0
    
    def list_rules(self) -> List[Dict[str, Any]]:
        """列出所有规则"""
        return [
            {
                "name": rule.name,
                "code": rule.code,
                "enabled": rule.enabled,
                "class": rule.__class__.__name__,
            }
            for rule in self.rules
        ]


def create_default_engine(config: Optional[Dict] = None) -> RiskEngine:
    """
    创建默认风控引擎
    
    Args:
        config: 可选配置覆盖
    
    Returns:
        配置好的 RiskEngine
    """
    from .rules import (
        MaxPositionRule,
        DailyTradeLimitRule,
        DailyLossLimitRule,
        ConsecutiveLossCooldownRule,
        MinBalanceRule,
    )
    
    cfg = config or {}
    
    engine = RiskEngine(fail_fast=cfg.get("fail_fast", True))
    
    # 默认规则
    engine.add_rule(MinBalanceRule(
        min_balance=cfg.get("min_balance", 100.0)
    ))
    engine.add_rule(MaxPositionRule(
        max_positions=cfg.get("max_positions", 10)
    ))
    engine.add_rule(DailyTradeLimitRule(
        max_trades=cfg.get("daily_trade_limit", 100)
    ))
    engine.add_rule(DailyLossLimitRule(
        max_loss=cfg.get("daily_loss_limit", 1000.0)
    ))
    engine.add_rule(ConsecutiveLossCooldownRule(
        max_consecutive=cfg.get("max_consecutive_losses", 5),
        cooldown_minutes=cfg.get("loss_cooldown_minutes", 30)
    ))
    
    return engine
