"""
IronBull Risk Module (v1 Phase 4)

风控规则引擎 - 支持多种风控策略的可扩展框架

组件：
- RiskRule: 风控规则基类
- RiskEngine: 规则引擎（执行规则链）
- 内置规则：仓位控制、限额策略、冷却机制
"""

from .engine import RiskEngine, RiskRule, RiskCheckContext, RiskViolation
from .rules import (
    # 仓位控制
    MaxPositionRule,
    MaxPositionValueRule,
    # 限额策略
    DailyTradeLimitRule,
    WeeklyTradeLimitRule,
    DailyLossLimitRule,
    # 冷却机制
    ConsecutiveLossCooldownRule,
    TradeCooldownRule,
    # 其他
    SymbolWhitelistRule,
    SymbolBlacklistRule,
    MinBalanceRule,
)

__all__ = [
    # 核心
    "RiskEngine",
    "RiskRule",
    "RiskCheckContext",
    "RiskViolation",
    # 仓位控制
    "MaxPositionRule",
    "MaxPositionValueRule",
    # 限额策略
    "DailyTradeLimitRule",
    "WeeklyTradeLimitRule",
    "DailyLossLimitRule",
    # 冷却机制
    "ConsecutiveLossCooldownRule",
    "TradeCooldownRule",
    # 其他
    "SymbolWhitelistRule",
    "SymbolBlacklistRule",
    "MinBalanceRule",
]
