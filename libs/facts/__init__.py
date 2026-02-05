"""
IronBull Facts Layer (v1)

事实层数据模型 - 不可变的业务事实记录

模型：
- Trade: 交易记录（下单执行结果）
- Ledger: 账本流水（资金变动）
- FreezeRecord: 冻结记录（保证金/风控冻结）
- SignalEvent: 信号状态事件（链路追踪）
- AuditLog: 审计日志（完整操作记录）

状态机：
- SignalStatus: 信号状态枚举
- ExecutionStatus: 执行状态枚举
- AuditAction: 审计动作类型
"""

from .models import (
    Trade,
    Ledger,
    FreezeRecord,
    SignalEvent,
    AuditLog,
)
from .states import (
    SignalStatus,
    ExecutionStatus,
    TradeStatus,
    AuditAction,
    can_transition,
    can_exec_transition,
    is_terminal_signal_status,
    is_terminal_exec_status,
)
from .repository import FactsRepository

__all__ = [
    # Models
    "Trade",
    "Ledger",
    "FreezeRecord",
    "SignalEvent",
    "AuditLog",
    # States
    "SignalStatus",
    "ExecutionStatus",
    "TradeStatus",
    "AuditAction",
    "can_transition",
    "can_exec_transition",
    "is_terminal_signal_status",
    "is_terminal_exec_status",
    # Repository
    "FactsRepository",
]
