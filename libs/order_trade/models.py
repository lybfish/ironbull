"""
OrderTrade Module - 数据模型定义

Order（订单）和 Fill（成交）表，满足"一笔订单可有多笔成交"的数据模型。
遵循 append-only 原则（Fill 表），Order 表允许状态更新。
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


class Order(Base):
    """
    订单表 - 记录每个委托的完整生命周期
    
    一个 Order 可以对应多个 Fill（部分成交场景）
    状态变更通过 OrderStateMachine 控制
    """
    __tablename__ = "fact_order"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 订单标识
    order_id = Column(String(64), nullable=False, unique=True, index=True, comment="系统订单号")
    exchange_order_id = Column(String(128), nullable=True, index=True, comment="交易所订单号")
    
    # 租户与账户
    tenant_id = Column(Integer, nullable=False, index=True, comment="租户ID")
    account_id = Column(Integer, nullable=False, index=True, comment="账户ID")
    
    # 关联信号（可选，人工下单无信号）
    signal_id = Column(String(64), nullable=True, index=True, comment="关联信号ID")
    
    # 交易标的
    symbol = Column(String(32), nullable=False, index=True, comment="交易对")
    exchange = Column(String(32), nullable=False, comment="交易所")
    market_type = Column(String(16), nullable=False, default="spot", comment="spot/future")
    
    # 订单参数
    side = Column(String(8), nullable=False, comment="BUY/SELL")
    order_type = Column(String(32), nullable=False, comment="MARKET/LIMIT/STOP_MARKET/TAKE_PROFIT_MARKET")
    trade_type = Column(String(16), nullable=True, default="OPEN",
                        comment="交易类型: OPEN/CLOSE/ADD/REDUCE")
    close_reason = Column(String(32), nullable=True,
                          comment="平仓原因: SL/TP/SIGNAL/MANUAL/LIQUIDATION (仅 trade_type=CLOSE 时)")
    quantity = Column(DECIMAL(20, 8), nullable=False, comment="委托数量")
    price = Column(DECIMAL(20, 8), nullable=True, comment="委托价格（限价单）")
    
    # 止损止盈（可选）
    stop_loss = Column(DECIMAL(20, 8), nullable=True, comment="止损价")
    take_profit = Column(DECIMAL(20, 8), nullable=True, comment="止盈价")
    
    # 合约专用
    position_side = Column(String(16), nullable=True, comment="LONG/SHORT（合约双向持仓）")
    leverage = Column(Integer, nullable=True, comment="杠杆倍数")
    
    # 订单状态
    status = Column(String(16), nullable=False, default="PENDING", index=True, 
                    comment="PENDING/SUBMITTED/OPEN/PARTIAL/FILLED/CANCELLED/REJECTED/EXPIRED/FAILED")
    
    # 累计成交（由 Fill 聚合更新）
    filled_quantity = Column(DECIMAL(20, 8), nullable=False, default=0, comment="累计成交数量")
    avg_price = Column(DECIMAL(20, 8), nullable=True, comment="成交均价")
    total_fee = Column(DECIMAL(20, 8), nullable=False, default=0, comment="累计手续费")
    fee_currency = Column(String(16), nullable=True, comment="手续费币种")
    
    # 错误信息
    error_code = Column(String(32), nullable=True, comment="错误码")
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    submitted_at = Column(DateTime, nullable=True, comment="提交到交易所时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, 
                        nullable=False, comment="最后更新时间")
    
    # 追踪
    request_id = Column(String(64), nullable=True, index=True, comment="请求追踪ID")
    
    __table_args__ = (
        Index("idx_order_tenant_account", "tenant_id", "account_id"),
        Index("idx_order_tenant_status", "tenant_id", "status"),
        Index("idx_order_symbol_time", "symbol", "created_at"),
        Index("idx_order_signal", "signal_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
    
    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "exchange_order_id": self.exchange_order_id,
            "tenant_id": self.tenant_id,
            "account_id": self.account_id,
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "market_type": self.market_type,
            "side": self.side,
            "order_type": self.order_type,
            "trade_type": self.trade_type,
            "close_reason": self.close_reason,
            "quantity": float(self.quantity) if self.quantity else None,
            "price": float(self.price) if self.price else None,
            "stop_loss": float(self.stop_loss) if self.stop_loss else None,
            "take_profit": float(self.take_profit) if self.take_profit else None,
            "position_side": self.position_side,
            "leverage": self.leverage,
            "status": self.status,
            "filled_quantity": float(self.filled_quantity) if self.filled_quantity else 0,
            "avg_price": float(self.avg_price) if self.avg_price else None,
            "total_fee": float(self.total_fee) if self.total_fee else 0,
            "fee_currency": self.fee_currency,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Fill(Base):
    """
    成交表 - 记录每笔成交流水
    
    严格遵循 append-only 原则，不做 UPDATE/DELETE
    每笔成交必须关联到一个 Order
    """
    __tablename__ = "fact_fill"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 成交标识
    fill_id = Column(String(64), nullable=False, unique=True, index=True, comment="系统成交ID")
    exchange_trade_id = Column(String(128), nullable=True, index=True, comment="交易所成交ID")
    
    # 关联订单（必填）
    order_id = Column(String(64), nullable=False, index=True, comment="关联订单ID")
    
    # 租户与账户（冗余存储，便于查询）
    tenant_id = Column(Integer, nullable=False, index=True, comment="租户ID")
    account_id = Column(Integer, nullable=False, index=True, comment="账户ID")
    
    # 交易标的（冗余存储）
    symbol = Column(String(32), nullable=False, index=True, comment="交易对")
    side = Column(String(8), nullable=False, comment="BUY/SELL")
    trade_type = Column(String(16), nullable=True, comment="交易类型: OPEN/CLOSE/ADD/REDUCE（冗余存储）")
    
    # 成交数据
    quantity = Column(DECIMAL(20, 8), nullable=False, comment="成交数量")
    price = Column(DECIMAL(20, 8), nullable=False, comment="成交价格")
    
    # 手续费
    fee = Column(DECIMAL(20, 8), nullable=False, default=0, comment="手续费")
    fee_currency = Column(String(16), nullable=True, comment="手续费币种")
    
    # 时间戳
    filled_at = Column(DateTime, nullable=False, comment="成交时间（交易所时间）")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="记录创建时间")
    
    # 追踪
    request_id = Column(String(64), nullable=True, index=True, comment="请求追踪ID")
    
    __table_args__ = (
        Index("idx_fill_order", "order_id"),
        Index("idx_fill_tenant_account", "tenant_id", "account_id"),
        Index("idx_fill_symbol_time", "symbol", "filled_at"),
        Index("idx_fill_time", "filled_at"),
        UniqueConstraint("order_id", "exchange_trade_id", name="uq_fill_order_exchange"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )
    
    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "id": self.id,
            "fill_id": self.fill_id,
            "exchange_trade_id": self.exchange_trade_id,
            "order_id": self.order_id,
            "tenant_id": self.tenant_id,
            "account_id": self.account_id,
            "symbol": self.symbol,
            "side": self.side,
            "trade_type": self.trade_type,
            "quantity": float(self.quantity) if self.quantity else 0,
            "price": float(self.price) if self.price else 0,
            "fee": float(self.fee) if self.fee else 0,
            "fee_currency": self.fee_currency,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
