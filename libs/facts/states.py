"""
统一状态机定义

定义 Signal 和 Execution 的标准状态流转。
所有服务必须使用这些状态枚举，确保状态一致性。
"""

from enum import Enum
from typing import List, Dict, Set


class SignalStatus(str, Enum):
    """
    信号状态
    
    状态流转：
        PENDING → RISK_CHECKING → PASSED → DISPATCHED → EXECUTED
                              ↘ REJECTED
                                        ↘ FAILED
                                        ↘ CANCELLED
    """
    PENDING = "pending"              # 初始状态，等待处理
    RISK_CHECKING = "risk_checking"  # 风控检查中
    PASSED = "passed"                # 风控通过，等待执行
    REJECTED = "rejected"            # 风控拒绝
    DISPATCHED = "dispatched"        # 已分发到节点
    EXECUTING = "executing"          # 执行中
    EXECUTED = "executed"            # 执行成功
    FAILED = "failed"                # 执行失败
    CANCELLED = "cancelled"          # 已取消
    EXPIRED = "expired"              # 已过期


class ExecutionStatus(str, Enum):
    """
    执行任务状态
    
    状态流转：
        PENDING → DISPATCHED → EXECUTING → FILLED
                                        ↘ PARTIAL
                                        ↘ FAILED
                                        ↘ CANCELLED
    """
    PENDING = "pending"        # 等待执行
    DISPATCHED = "dispatched"  # 已分发到节点
    EXECUTING = "executing"    # 执行中
    FILLED = "filled"          # 完全成交
    PARTIAL = "partial"        # 部分成交
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消
    TIMEOUT = "timeout"        # 超时


class TradeStatus(str, Enum):
    """交易记录状态"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AuditAction(str, Enum):
    """
    审计动作类型
    """
    # Signal 相关
    SIGNAL_CREATED = "signal_created"
    SIGNAL_RISK_CHECK_START = "signal_risk_check_start"
    SIGNAL_RISK_PASSED = "signal_risk_passed"
    SIGNAL_RISK_REJECTED = "signal_risk_rejected"
    SIGNAL_DISPATCHED = "signal_dispatched"
    SIGNAL_EXECUTED = "signal_executed"
    SIGNAL_FAILED = "signal_failed"
    SIGNAL_CANCELLED = "signal_cancelled"
    
    # Execution 相关
    EXEC_SUBMITTED = "exec_submitted"
    EXEC_QUEUED = "exec_queued"       # 异步队列入队
    EXEC_DEQUEUED = "exec_dequeued"   # 从队列取出开始处理
    EXEC_DISPATCHED = "exec_dispatched"
    EXEC_STARTED = "exec_started"
    EXEC_FILLED = "exec_filled"
    EXEC_PARTIAL = "exec_partial"
    EXEC_FAILED = "exec_failed"
    EXEC_TIMEOUT = "exec_timeout"
    EXEC_RETRY = "exec_retry"
    EXEC_DLQ = "exec_dlq"             # 进入死信队列
    
    # Trade 相关
    TRADE_CREATED = "trade_created"
    TRADE_UPDATED = "trade_updated"
    
    # 账户相关
    ACCOUNT_FREEZE = "account_freeze"
    ACCOUNT_UNFREEZE = "account_unfreeze"
    LEDGER_ENTRY = "ledger_entry"


# 状态转换规则
SIGNAL_TRANSITIONS: Dict[SignalStatus, Set[SignalStatus]] = {
    SignalStatus.PENDING: {SignalStatus.RISK_CHECKING, SignalStatus.CANCELLED, SignalStatus.EXPIRED},
    SignalStatus.RISK_CHECKING: {SignalStatus.PASSED, SignalStatus.REJECTED},
    SignalStatus.PASSED: {SignalStatus.DISPATCHED, SignalStatus.CANCELLED, SignalStatus.EXPIRED},
    SignalStatus.DISPATCHED: {SignalStatus.EXECUTING, SignalStatus.FAILED, SignalStatus.CANCELLED},
    SignalStatus.EXECUTING: {SignalStatus.EXECUTED, SignalStatus.FAILED},
    SignalStatus.REJECTED: set(),  # 终态
    SignalStatus.EXECUTED: set(),  # 终态
    SignalStatus.FAILED: set(),    # 终态
    SignalStatus.CANCELLED: set(), # 终态
    SignalStatus.EXPIRED: set(),   # 终态
}

EXECUTION_TRANSITIONS: Dict[ExecutionStatus, Set[ExecutionStatus]] = {
    ExecutionStatus.PENDING: {ExecutionStatus.DISPATCHED, ExecutionStatus.CANCELLED},
    ExecutionStatus.DISPATCHED: {ExecutionStatus.EXECUTING, ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT},
    ExecutionStatus.EXECUTING: {ExecutionStatus.FILLED, ExecutionStatus.PARTIAL, ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT},
    ExecutionStatus.PARTIAL: {ExecutionStatus.FILLED, ExecutionStatus.CANCELLED},
    ExecutionStatus.FILLED: set(),     # 终态
    ExecutionStatus.FAILED: set(),     # 终态
    ExecutionStatus.CANCELLED: set(),  # 终态
    ExecutionStatus.TIMEOUT: set(),    # 终态
}


def can_transition(current: SignalStatus, target: SignalStatus) -> bool:
    """检查信号状态是否可以转换"""
    return target in SIGNAL_TRANSITIONS.get(current, set())


def can_exec_transition(current: ExecutionStatus, target: ExecutionStatus) -> bool:
    """检查执行状态是否可以转换"""
    return target in EXECUTION_TRANSITIONS.get(current, set())


def is_terminal_signal_status(status: SignalStatus) -> bool:
    """检查是否为信号终态"""
    return status in {
        SignalStatus.REJECTED,
        SignalStatus.EXECUTED,
        SignalStatus.FAILED,
        SignalStatus.CANCELLED,
        SignalStatus.EXPIRED,
    }


def is_terminal_exec_status(status: ExecutionStatus) -> bool:
    """检查是否为执行终态"""
    return status in {
        ExecutionStatus.FILLED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.TIMEOUT,
    }
