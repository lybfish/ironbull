"""
Ledger Module - 数据模型定义

Account（账户）、Transaction（流水）、EquitySnapshot（权益快照）表
Transaction 为 append-only，确保流水可追溯
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    DateTime,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DECIMAL

from libs.core.database import Base


class Account(Base):
    """
    账户表 - 记录资金账户状态
    
    唯一键：(tenant_id, account_id, currency)
    支持多币种账户
    """
    __tablename__ = "fact_account"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 账户标识
    ledger_account_id = Column(String(64), nullable=False, unique=True, index=True, comment="账本账户ID")
    
    # 租户与账户
    tenant_id = Column(Integer, nullable=False, index=True, comment="租户ID")
    account_id = Column(Integer, nullable=False, index=True, comment="交易账户ID")
    
    # 币种
    currency = Column(String(16), nullable=False, default="USDT", comment="币种")
    
    # 余额
    balance = Column(DECIMAL(20, 8), nullable=False, default=0, comment="总余额")
    available = Column(DECIMAL(20, 8), nullable=False, default=0, comment="可用余额")
    frozen = Column(DECIMAL(20, 8), nullable=False, default=0, comment="冻结金额")
    
    # 盈亏统计
    total_deposit = Column(DECIMAL(20, 8), nullable=False, default=0, comment="累计入金")
    total_withdraw = Column(DECIMAL(20, 8), nullable=False, default=0, comment="累计出金")
    total_fee = Column(DECIMAL(20, 8), nullable=False, default=0, comment="累计手续费")
    realized_pnl = Column(DECIMAL(20, 8), nullable=False, default=0, comment="累计已实现盈亏")
    
    # 同步专用：记录上次交易所同步的余额，用于检测入金出金（不受 settle_trade 影响）
    synced_balance = Column(DECIMAL(20, 8), nullable=False, default=0, comment="上次交易所同步余额")
    
    # 合约专用
    margin_used = Column(DECIMAL(20, 8), nullable=False, default=0, comment="已用保证金")
    unrealized_pnl = Column(DECIMAL(20, 8), nullable=False, default=0, comment="未实现盈亏（从交易所同步）")
    equity = Column(DECIMAL(20, 8), nullable=False, default=0, comment="权益（余额+未实现盈亏）")
    margin_ratio = Column(DECIMAL(10, 4), nullable=True, default=0, comment="保证金使用率")
    
    # 状态
    status = Column(String(16), nullable=False, default="ACTIVE", comment="状态: ACTIVE/FROZEN/CLOSED")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now,
                        nullable=False, comment="最后更新时间")
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "account_id", "currency", name="uq_account_key"),
        Index("idx_account_tenant_account", "tenant_id", "account_id"),
        Index("idx_account_status", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
    
    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "id": self.id,
            "ledger_account_id": self.ledger_account_id,
            "tenant_id": self.tenant_id,
            "account_id": self.account_id,
            "currency": self.currency,
            "balance": float(self.balance) if self.balance else 0,
            "available": float(self.available) if self.available else 0,
            "frozen": float(self.frozen) if self.frozen else 0,
            "total_deposit": float(self.total_deposit) if self.total_deposit else 0,
            "total_withdraw": float(self.total_withdraw) if self.total_withdraw else 0,
            "total_fee": float(self.total_fee) if self.total_fee else 0,
            "realized_pnl": float(self.realized_pnl) if self.realized_pnl else 0,
            "margin_used": float(self.margin_used) if self.margin_used else 0,
            "unrealized_pnl": float(self.unrealized_pnl) if self.unrealized_pnl else 0,
            "equity": float(self.equity) if self.equity else 0,
            "margin_ratio": float(self.margin_ratio) if self.margin_ratio else 0,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Transaction(Base):
    """
    交易流水表 - 记录每笔资金变动
    
    严格遵循 append-only 原则，不做 UPDATE/DELETE
    每笔流水必须有来源（成交、入金、费用等）
    """
    __tablename__ = "fact_transaction"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 流水标识
    transaction_id = Column(String(64), nullable=False, unique=True, index=True, comment="流水ID")
    
    # 关联账户
    ledger_account_id = Column(String(64), nullable=False, index=True, comment="账本账户ID")
    
    # 租户与账户（冗余存储便于查询）
    tenant_id = Column(Integer, nullable=False, index=True, comment="租户ID")
    account_id = Column(Integer, nullable=False, index=True, comment="交易账户ID")
    
    # 币种
    currency = Column(String(16), nullable=False, default="USDT", comment="币种")
    
    # 交易类型
    transaction_type = Column(String(32), nullable=False, comment="交易类型")
    
    # 金额
    amount = Column(DECIMAL(20, 8), nullable=False, comment="变动金额（可正可负）")
    fee = Column(DECIMAL(20, 8), nullable=False, default=0, comment="手续费")
    
    # 变动后余额（快照）
    balance_after = Column(DECIMAL(20, 8), nullable=False, comment="变动后总余额")
    available_after = Column(DECIMAL(20, 8), nullable=False, comment="变动后可用")
    frozen_after = Column(DECIMAL(20, 8), nullable=False, comment="变动后冻结")
    
    # 来源关联（不变量：流水可追溯）
    source_type = Column(String(32), nullable=False, comment="来源类型: FILL/ORDER/DEPOSIT/WITHDRAW/ADJUSTMENT")
    source_id = Column(String(64), nullable=True, index=True, comment="来源ID")
    
    # 关联标的（交易时）
    symbol = Column(String(32), nullable=True, comment="交易对（交易相关流水）")
    
    # 状态
    status = Column(String(16), nullable=False, default="COMPLETED", comment="状态")
    
    # 时间戳
    transaction_at = Column(DateTime, nullable=False, comment="交易时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="记录创建时间")
    
    # 备注
    remark = Column(Text, nullable=True, comment="备注")
    
    __table_args__ = (
        Index("idx_tx_account", "ledger_account_id"),
        Index("idx_tx_tenant_account", "tenant_id", "account_id"),
        Index("idx_tx_type", "transaction_type"),
        Index("idx_tx_source", "source_type", "source_id"),
        Index("idx_tx_time", "transaction_at"),
        Index("idx_tx_symbol", "symbol"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
    
    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "ledger_account_id": self.ledger_account_id,
            "tenant_id": self.tenant_id,
            "account_id": self.account_id,
            "currency": self.currency,
            "transaction_type": self.transaction_type,
            "amount": float(self.amount) if self.amount else 0,
            "fee": float(self.fee) if self.fee else 0,
            "balance_after": float(self.balance_after) if self.balance_after else 0,
            "available_after": float(self.available_after) if self.available_after else 0,
            "frozen_after": float(self.frozen_after) if self.frozen_after else 0,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "symbol": self.symbol,
            "status": self.status,
            "transaction_at": self.transaction_at.isoformat() if self.transaction_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "remark": self.remark,
        }


class EquitySnapshot(Base):
    """
    权益快照表 - 定时记录账户权益状态
    
    用于净值曲线、收益率计算
    """
    __tablename__ = "fact_equity_snapshot"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 快照标识
    snapshot_id = Column(String(64), nullable=False, unique=True, index=True, comment="快照ID")
    
    # 关联账户
    ledger_account_id = Column(String(64), nullable=False, index=True, comment="账本账户ID")
    
    # 租户与账户
    tenant_id = Column(Integer, nullable=False, index=True, comment="租户ID")
    account_id = Column(Integer, nullable=False, index=True, comment="交易账户ID")
    
    # 币种
    currency = Column(String(16), nullable=False, default="USDT", comment="币种")
    
    # 权益数据
    balance = Column(DECIMAL(20, 8), nullable=False, comment="现金余额")
    unrealized_pnl = Column(DECIMAL(20, 8), nullable=False, default=0, comment="未实现盈亏")
    equity = Column(DECIMAL(20, 8), nullable=False, comment="总权益 = 余额 + 未实现盈亏")
    
    # 持仓市值
    position_value = Column(DECIMAL(20, 8), nullable=False, default=0, comment="持仓市值")
    
    # 保证金（合约）
    margin_used = Column(DECIMAL(20, 8), nullable=False, default=0, comment="已用保证金")
    margin_ratio = Column(DECIMAL(10, 4), nullable=True, comment="保证金率")
    
    # 净值与收益率
    net_value = Column(DECIMAL(20, 8), nullable=True, comment="单位净值")
    daily_return = Column(DECIMAL(10, 6), nullable=True, comment="日收益率")
    cumulative_return = Column(DECIMAL(10, 6), nullable=True, comment="累计收益率")
    
    # 快照时间
    snapshot_at = Column(DateTime, nullable=False, comment="快照时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    
    __table_args__ = (
        Index("idx_snapshot_account", "ledger_account_id"),
        Index("idx_snapshot_tenant_account", "tenant_id", "account_id"),
        Index("idx_snapshot_time", "snapshot_at"),
        UniqueConstraint("ledger_account_id", "snapshot_at", name="uq_snapshot_account_time"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
    
    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "id": self.id,
            "snapshot_id": self.snapshot_id,
            "ledger_account_id": self.ledger_account_id,
            "tenant_id": self.tenant_id,
            "account_id": self.account_id,
            "currency": self.currency,
            "balance": float(self.balance) if self.balance else 0,
            "unrealized_pnl": float(self.unrealized_pnl) if self.unrealized_pnl else 0,
            "equity": float(self.equity) if self.equity else 0,
            "position_value": float(self.position_value) if self.position_value else 0,
            "margin_used": float(self.margin_used) if self.margin_used else 0,
            "margin_ratio": float(self.margin_ratio) if self.margin_ratio else None,
            "net_value": float(self.net_value) if self.net_value else None,
            "daily_return": float(self.daily_return) if self.daily_return else None,
            "cumulative_return": float(self.cumulative_return) if self.cumulative_return else None,
            "snapshot_at": self.snapshot_at.isoformat() if self.snapshot_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
