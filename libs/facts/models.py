"""
Facts Layer - 数据模型定义

所有表都是事实表（Fact Table），记录不可变的业务事实。
遵循 append-only 原则，不做 UPDATE/DELETE。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    Text,
    DateTime,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.mysql import DECIMAL

from libs.core.database import Base


class Trade(Base):
    """
    交易记录表 - 记录每次下单执行的结果
    
    一个 signal_id 可能对应多条 Trade（开仓、加仓、平仓等）
    """
    __tablename__ = "fact_trade"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 关联ID
    signal_id = Column(String(64), nullable=False, index=True, comment="信号ID")
    task_id = Column(String(64), nullable=False, index=True, comment="执行任务ID")
    account_id = Column(Integer, nullable=False, index=True, comment="账户ID")
    user_id = Column(Integer, nullable=False, index=True, comment="用户ID")
    
    # 交易标的
    symbol = Column(String(32), nullable=False, comment="交易对")
    canonical_symbol = Column(String(32), nullable=True, comment="标准化交易对")
    exchange = Column(String(32), nullable=True, comment="交易所")
    
    # 交易方向与类型
    side = Column(String(8), nullable=False, comment="BUY/SELL")
    trade_type = Column(String(16), nullable=False, comment="OPEN/CLOSE/ADD/REDUCE")
    order_type = Column(String(16), default="MARKET", comment="MARKET/LIMIT")
    
    # 价格与数量
    entry_price = Column(DECIMAL(20, 8), nullable=True, comment="入场价")
    filled_price = Column(DECIMAL(20, 8), nullable=True, comment="成交均价")
    quantity = Column(DECIMAL(20, 8), nullable=False, comment="委托数量")
    filled_quantity = Column(DECIMAL(20, 8), nullable=True, comment="成交数量")
    
    # 止损止盈
    stop_loss = Column(DECIMAL(20, 8), nullable=True, comment="止损价")
    take_profit = Column(DECIMAL(20, 8), nullable=True, comment="止盈价")
    
    # 成本与手续费
    fee = Column(DECIMAL(20, 8), default=0, comment="手续费")
    fee_currency = Column(String(16), nullable=True, comment="手续费币种")
    
    # 订单ID
    order_id = Column(String(64), nullable=True, comment="系统订单ID")
    exchange_order_id = Column(String(128), nullable=True, comment="交易所订单ID")
    
    # 执行状态
    status = Column(String(16), nullable=False, default="pending", comment="pending/filled/partial/failed/cancelled")
    error_code = Column(String(32), nullable=True, comment="错误码")
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    # 关联策略
    strategy_code = Column(String(64), nullable=True, comment="策略代码")
    timeframe = Column(String(8), nullable=True, comment="时间周期")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    executed_at = Column(DateTime, nullable=True, comment="执行完成时间")
    
    # 追踪
    request_id = Column(String(64), nullable=True, index=True, comment="请求追踪ID")
    
    __table_args__ = (
        Index("idx_trade_signal_task", "signal_id", "task_id"),
        Index("idx_trade_account_time", "account_id", "created_at"),
        Index("idx_trade_symbol_time", "symbol", "created_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )


class Ledger(Base):
    """
    账本流水表 - 记录资金变动
    
    每笔资金变动都是一条 Ledger 记录（append-only）
    """
    __tablename__ = "fact_ledger"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 关联ID
    account_id = Column(Integer, nullable=False, index=True, comment="账户ID")
    user_id = Column(Integer, nullable=False, index=True, comment="用户ID")
    trade_id = Column(BigInteger, nullable=True, index=True, comment="关联交易ID")
    signal_id = Column(String(64), nullable=True, index=True, comment="关联信号ID")
    
    # 流水类型
    ledger_type = Column(String(32), nullable=False, comment="TRADE_FEE/TRADE_PNL/FREEZE/UNFREEZE/DEPOSIT/WITHDRAW")
    
    # 金额
    currency = Column(String(16), nullable=False, default="USDT", comment="币种")
    amount = Column(DECIMAL(20, 8), nullable=False, comment="变动金额（正为入，负为出）")
    balance_before = Column(DECIMAL(20, 8), nullable=True, comment="变动前余额")
    balance_after = Column(DECIMAL(20, 8), nullable=True, comment="变动后余额")
    
    # 描述
    description = Column(String(256), nullable=True, comment="流水描述")
    
    # 时间
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    
    # 追踪
    request_id = Column(String(64), nullable=True, index=True, comment="请求追踪ID")
    
    __table_args__ = (
        Index("idx_ledger_account_time", "account_id", "created_at"),
        Index("idx_ledger_type_time", "ledger_type", "created_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )


class FreezeRecord(Base):
    """
    冻结记录表 - 记录保证金/风控冻结
    """
    __tablename__ = "fact_freeze"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 关联ID
    account_id = Column(Integer, nullable=False, index=True, comment="账户ID")
    user_id = Column(Integer, nullable=False, index=True, comment="用户ID")
    signal_id = Column(String(64), nullable=True, index=True, comment="关联信号ID")
    task_id = Column(String(64), nullable=True, index=True, comment="关联任务ID")
    
    # 冻结类型
    freeze_type = Column(String(32), nullable=False, comment="MARGIN/RISK_CONTROL/MANUAL")
    
    # 金额
    currency = Column(String(16), nullable=False, default="USDT", comment="币种")
    amount = Column(DECIMAL(20, 8), nullable=False, comment="冻结金额")
    
    # 状态
    status = Column(String(16), nullable=False, default="frozen", comment="frozen/released")
    
    # 时间
    frozen_at = Column(DateTime, default=datetime.now, nullable=False)
    released_at = Column(DateTime, nullable=True, comment="解冻时间")
    
    # 描述
    reason = Column(String(256), nullable=True, comment="冻结原因")
    
    # 追踪
    request_id = Column(String(64), nullable=True, index=True, comment="请求追踪ID")
    
    __table_args__ = (
        Index("idx_freeze_account_status", "account_id", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )


class SignalEvent(Base):
    """
    信号状态事件表 - 记录信号在整个链路中的状态变更
    
    用于完整追踪：Signal → Risk → Execution → Trade
    """
    __tablename__ = "fact_signal_event"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 信号ID（核心索引）
    signal_id = Column(String(64), nullable=False, index=True, comment="信号ID")
    
    # 关联ID
    task_id = Column(String(64), nullable=True, comment="执行任务ID")
    account_id = Column(Integer, nullable=True, index=True, comment="账户ID")
    
    # 事件类型与状态
    event_type = Column(String(32), nullable=False, comment="CREATED/RISK_CHECK/RISK_PASSED/RISK_REJECTED/DISPATCHED/EXECUTED/FAILED")
    status = Column(String(16), nullable=False, comment="pending/passed/rejected/executing/executed/failed")
    
    # 来源服务
    source_service = Column(String(32), nullable=False, comment="signal-hub/risk-control/execution-dispatcher/crypto-node")
    
    # 事件详情
    detail = Column(Text, nullable=True, comment="事件详情（JSON）")
    error_code = Column(String(32), nullable=True, comment="错误码")
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    # 时间
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    
    # 追踪
    request_id = Column(String(64), nullable=True, index=True, comment="请求追踪ID")
    
    __table_args__ = (
        Index("idx_signal_event_signal_time", "signal_id", "created_at"),
        Index("idx_signal_event_type_time", "event_type", "created_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )


class AuditLog(Base):
    """
    审计日志表 - 记录所有关键操作和状态变更
    
    用于：
    - 完整追踪任意 signal_id/task_id 的所有操作
    - 失败原因追踪和问题排查
    - 合规审计
    """
    __tablename__ = "fact_audit_log"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 关联ID（三选一或多选）
    signal_id = Column(String(64), nullable=True, index=True, comment="信号ID")
    task_id = Column(String(64), nullable=True, index=True, comment="执行任务ID")
    account_id = Column(Integer, nullable=True, index=True, comment="账户ID")
    user_id = Column(Integer, nullable=True, index=True, comment="用户ID")
    
    # 审计动作
    action = Column(String(64), nullable=False, index=True, comment="动作类型")
    
    # 状态变更
    status_before = Column(String(32), nullable=True, comment="变更前状态")
    status_after = Column(String(32), nullable=True, comment="变更后状态")
    
    # 来源
    source_service = Column(String(32), nullable=False, comment="来源服务")
    source_ip = Column(String(64), nullable=True, comment="来源IP")
    
    # 详情
    detail = Column(Text, nullable=True, comment="操作详情（JSON）")
    
    # 错误信息（失败时）
    success = Column(Integer, default=1, comment="是否成功 1=成功 0=失败")
    error_code = Column(String(32), nullable=True, comment="错误码")
    error_message = Column(Text, nullable=True, comment="错误信息")
    retry_count = Column(Integer, default=0, comment="重试次数")
    
    # 时间
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    duration_ms = Column(Integer, nullable=True, comment="操作耗时(毫秒)")
    
    # 追踪
    request_id = Column(String(64), nullable=True, index=True, comment="请求追踪ID")
    trace_id = Column(String(64), nullable=True, comment="链路追踪ID")
    
    __table_args__ = (
        Index("idx_audit_signal_time", "signal_id", "created_at"),
        Index("idx_audit_task_time", "task_id", "created_at"),
        Index("idx_audit_action_time", "action", "created_at"),
        Index("idx_audit_account_time", "account_id", "created_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
