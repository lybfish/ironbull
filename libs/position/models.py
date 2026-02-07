"""
Position Module - 数据模型定义

Position（持仓）和 PositionChange（持仓变动）表
遵循"变动有来源"原则，PositionChange 为 append-only
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


class Position(Base):
    """
    持仓表 - 记录当前持仓状态
    
    唯一键：(tenant_id, account_id, symbol, exchange, position_side)
    支持现货和合约（双向持仓）
    """
    __tablename__ = "fact_position"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 持仓标识
    position_id = Column(String(64), nullable=False, unique=True, index=True, comment="持仓ID")
    
    # 租户与账户
    tenant_id = Column(Integer, nullable=False, index=True, comment="租户ID")
    account_id = Column(Integer, nullable=False, index=True, comment="账户ID")
    
    # 标的信息
    symbol = Column(String(32), nullable=False, index=True, comment="交易对")
    exchange = Column(String(32), nullable=False, comment="交易所")
    market_type = Column(String(16), nullable=False, default="spot", comment="spot/future")
    
    # 持仓方向（合约用）
    position_side = Column(String(16), nullable=False, default="NONE", comment="LONG/SHORT/NONE")
    
    # 持仓数量
    quantity = Column(DECIMAL(20, 8), nullable=False, default=0, comment="总持仓数量")
    available = Column(DECIMAL(20, 8), nullable=False, default=0, comment="可用数量")
    frozen = Column(DECIMAL(20, 8), nullable=False, default=0, comment="冻结数量")
    
    # 成本与盈亏
    avg_cost = Column(DECIMAL(20, 8), nullable=False, default=0, comment="平均成本价")
    total_cost = Column(DECIMAL(20, 8), nullable=False, default=0, comment="总成本")
    realized_pnl = Column(DECIMAL(20, 8), nullable=False, default=0, comment="已实现盈亏")
    unrealized_pnl = Column(DECIMAL(20, 8), nullable=True, comment="未实现盈亏（从交易所同步）")
    
    # 合约专用
    leverage = Column(Integer, nullable=True, comment="杠杆倍数")
    margin = Column(DECIMAL(20, 8), nullable=True, comment="保证金")
    liquidation_price = Column(DECIMAL(20, 8), nullable=True, comment="强平价格")
    
    # 状态
    status = Column(String(16), nullable=False, default="OPEN", comment="OPEN/CLOSED/LIQUIDATED")
    
    # 时间戳
    opened_at = Column(DateTime, nullable=True, comment="开仓时间")
    closed_at = Column(DateTime, nullable=True, comment="平仓时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="记录创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now,
                        nullable=False, comment="最后更新时间")
    
    __table_args__ = (
        # 唯一约束：同一账户同一标的同一方向只能有一条持仓记录
        UniqueConstraint(
            "tenant_id", "account_id", "symbol", "exchange", "position_side",
            name="uq_position_key"
        ),
        Index("idx_position_tenant_account", "tenant_id", "account_id"),
        Index("idx_position_symbol", "symbol"),
        Index("idx_position_status", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
    
    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "id": self.id,
            "position_id": self.position_id,
            "tenant_id": self.tenant_id,
            "account_id": self.account_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "market_type": self.market_type,
            "position_side": self.position_side,
            "quantity": float(self.quantity) if self.quantity else 0,
            "available": float(self.available) if self.available else 0,
            "frozen": float(self.frozen) if self.frozen else 0,
            "avg_cost": float(self.avg_cost) if self.avg_cost else 0,
            "total_cost": float(self.total_cost) if self.total_cost else 0,
            "realized_pnl": float(self.realized_pnl) if self.realized_pnl else 0,
            "unrealized_pnl": float(self.unrealized_pnl) if self.unrealized_pnl else 0,
            "leverage": self.leverage,
            "margin": float(self.margin) if self.margin else None,
            "liquidation_price": float(self.liquidation_price) if self.liquidation_price else None,
            "status": self.status,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PositionChange(Base):
    """
    持仓变动表 - 记录每一笔持仓变动（审计追踪）
    
    严格遵循 append-only 原则，不做 UPDATE/DELETE
    每笔变动必须有来源（成交、调仓、强平等）
    """
    __tablename__ = "fact_position_change"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 变动标识
    change_id = Column(String(64), nullable=False, unique=True, index=True, comment="变动ID")
    
    # 关联持仓
    position_id = Column(String(64), nullable=False, index=True, comment="关联持仓ID")
    
    # 租户与账户（冗余存储）
    tenant_id = Column(Integer, nullable=False, index=True, comment="租户ID")
    account_id = Column(Integer, nullable=False, index=True, comment="账户ID")
    
    # 标的信息（冗余存储）
    symbol = Column(String(32), nullable=False, index=True, comment="交易对")
    position_side = Column(String(16), nullable=False, default="NONE", comment="LONG/SHORT/NONE")
    
    # 变动类型
    change_type = Column(String(16), nullable=False, comment="OPEN/ADD/REDUCE/CLOSE/FREEZE/UNFREEZE/LIQUIDATION/ADJUSTMENT")
    
    # 变动数量
    quantity_change = Column(DECIMAL(20, 8), nullable=False, comment="数量变化（可正可负）")
    available_change = Column(DECIMAL(20, 8), nullable=False, default=0, comment="可用变化")
    frozen_change = Column(DECIMAL(20, 8), nullable=False, default=0, comment="冻结变化")
    
    # 变动后状态（快照）
    quantity_after = Column(DECIMAL(20, 8), nullable=False, comment="变动后总数量")
    available_after = Column(DECIMAL(20, 8), nullable=False, comment="变动后可用")
    frozen_after = Column(DECIMAL(20, 8), nullable=False, comment="变动后冻结")
    avg_cost_after = Column(DECIMAL(20, 8), nullable=False, comment="变动后成本")
    
    # 成交价格（如果是交易触发）
    price = Column(DECIMAL(20, 8), nullable=True, comment="成交价格")
    
    # 盈亏（平仓时记录）
    realized_pnl = Column(DECIMAL(20, 8), nullable=True, comment="本次变动实现盈亏")
    
    # 变动来源（不变量：变动有来源）
    source_type = Column(String(32), nullable=False, comment="来源类型：FILL/ORDER/ADJUSTMENT/LIQUIDATION/TRANSFER/INIT")
    source_id = Column(String(64), nullable=True, index=True, comment="来源ID（如 fill_id）")
    
    # 时间戳
    changed_at = Column(DateTime, nullable=False, comment="变动时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="记录创建时间")
    
    # 备注
    remark = Column(Text, nullable=True, comment="备注说明")
    
    __table_args__ = (
        Index("idx_change_position", "position_id"),
        Index("idx_change_tenant_account", "tenant_id", "account_id"),
        Index("idx_change_symbol", "symbol"),
        Index("idx_change_type", "change_type"),
        Index("idx_change_source", "source_type", "source_id"),
        Index("idx_change_time", "changed_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
    
    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "id": self.id,
            "change_id": self.change_id,
            "position_id": self.position_id,
            "tenant_id": self.tenant_id,
            "account_id": self.account_id,
            "symbol": self.symbol,
            "position_side": self.position_side,
            "change_type": self.change_type,
            "quantity_change": float(self.quantity_change) if self.quantity_change else 0,
            "available_change": float(self.available_change) if self.available_change else 0,
            "frozen_change": float(self.frozen_change) if self.frozen_change else 0,
            "quantity_after": float(self.quantity_after) if self.quantity_after else 0,
            "available_after": float(self.available_after) if self.available_after else 0,
            "frozen_after": float(self.frozen_after) if self.frozen_after else 0,
            "avg_cost_after": float(self.avg_cost_after) if self.avg_cost_after else 0,
            "price": float(self.price) if self.price else None,
            "realized_pnl": float(self.realized_pnl) if self.realized_pnl else None,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "remark": self.remark,
        }
