"""
Position Module - 数据模型定义

Position（持仓）、PositionChange（持仓变动）、PendingLimitOrder（限价挂单追踪）表
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
    Boolean,
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
    
    # 自管止盈止损（不挂交易所单，由 position_monitor 监控到价平仓）
    entry_price = Column(DECIMAL(20, 8), nullable=True, comment="入场价格")
    stop_loss = Column(DECIMAL(20, 8), nullable=True, comment="止损价格")
    take_profit = Column(DECIMAL(20, 8), nullable=True, comment="止盈价格")
    strategy_code = Column(String(64), nullable=True, comment="策略代码（用于冷却回调）")
    
    # 状态
    status = Column(String(16), nullable=False, default="OPEN", comment="OPEN/CLOSED/LIQUIDATED")
    close_reason = Column(String(32), nullable=True,
                          comment="平仓原因: SL/TP/SIGNAL/MANUAL/LIQUIDATION")
    
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
        Index("idx_position_tenant_account_status", "tenant_id", "account_id", "status"),  # 常用分页查询
        Index("idx_position_tenant_updated", "tenant_id", "updated_at"),                   # 时间排序查询
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
            "entry_price": float(self.entry_price) if self.entry_price else None,
            "stop_loss": float(self.stop_loss) if self.stop_loss else None,
            "take_profit": float(self.take_profit) if self.take_profit else None,
            "strategy_code": self.strategy_code,
            "status": self.status,
            "close_reason": self.close_reason,
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


class PendingLimitOrder(Base):
    """
    限价挂单追踪表 - 跟踪已在交易所挂出但尚未成交的限价单

    生命周期：
      1. 挂单 → status=PENDING（策略产生信号，限价单提交到交易所）
      2a. 成交 → status=FILLED（交易所确认成交，写入 SL/TP 到持仓）
      2b. 超时 → status=EXPIRED（超过 retest_bars 仍未成交，撤单）
      2c. 撤单 → status=CANCELLED（手动撤单或程序重启清理）
      2d. 确认中 → status=CONFIRMING（成交后等待确认形态，仅 confirm_after_fill=True）

    作用：
      - 程序重启后可从 DB 恢复 pending 状态，不丢单
      - 后台可查看当前限价单状态
      - 防止重复挂单（同策略+同交易对只能有一个 PENDING）
    """
    __tablename__ = "fact_pending_limit_order"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 关联键：strategy_code + symbol 组合唯一标识一个挂单
    pending_key = Column(String(128), nullable=False, unique=True, index=True,
                         comment="唯一键 strategy_code:symbol")

    # 订单信息
    order_id = Column(String(64), nullable=True, comment="系统订单号")
    exchange_order_id = Column(String(128), nullable=True, index=True, comment="交易所订单号")
    symbol = Column(String(32), nullable=False, comment="交易对")
    side = Column(String(8), nullable=False, comment="BUY/SELL")
    entry_price = Column(DECIMAL(20, 8), nullable=False, comment="挂单价格")
    stop_loss = Column(DECIMAL(20, 8), nullable=True, comment="止损价")
    take_profit = Column(DECIMAL(20, 8), nullable=True, comment="止盈价")

    # 策略 & 账户
    strategy_code = Column(String(64), nullable=False, index=True, comment="策略代码")
    account_id = Column(Integer, nullable=False, index=True, comment="交易所账户ID")
    tenant_id = Column(Integer, nullable=False, comment="租户ID")
    amount_usdt = Column(DECIMAL(20, 2), nullable=True, comment="下单金额 USDT")
    leverage = Column(Integer, nullable=True, comment="杠杆倍数")

    # 超时 & 确认参数
    timeframe = Column(String(8), nullable=False, default="15m", comment="K线周期")
    retest_bars = Column(Integer, nullable=False, default=20, comment="最大等待K线数")
    confirm_after_fill = Column(Boolean, nullable=False, default=False,
                                comment="成交后是否需要确认")
    post_fill_confirm_bars = Column(Integer, nullable=False, default=3,
                                    comment="确认等待K线数")

    # 成交信息（FILLED/CONFIRMING 时填充）
    filled_price = Column(DECIMAL(20, 8), nullable=True, comment="成交价")
    filled_qty = Column(DECIMAL(20, 8), nullable=True, comment="成交数量")
    filled_at = Column(DateTime, nullable=True, comment="成交时间")
    candles_checked = Column(Integer, nullable=False, default=0, comment="已检查确认K线数")

    # 状态
    status = Column(String(16), nullable=False, default="PENDING",
                    comment="PENDING/FILLED/CONFIRMING/EXPIRED/CANCELLED")

    # 时间
    placed_at = Column(DateTime, nullable=False, default=datetime.now, comment="挂单时间")
    closed_at = Column(DateTime, nullable=True, comment="结束时间（成交/撤单/超时）")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        Index("idx_pending_strategy_symbol", "strategy_code", "symbol"),
        Index("idx_pending_status", "status"),
        Index("idx_pending_account", "account_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pending_key": self.pending_key,
            "order_id": self.order_id,
            "exchange_order_id": self.exchange_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "entry_price": float(self.entry_price) if self.entry_price else None,
            "stop_loss": float(self.stop_loss) if self.stop_loss else None,
            "take_profit": float(self.take_profit) if self.take_profit else None,
            "strategy_code": self.strategy_code,
            "account_id": self.account_id,
            "tenant_id": self.tenant_id,
            "amount_usdt": float(self.amount_usdt) if self.amount_usdt else None,
            "leverage": self.leverage,
            "timeframe": self.timeframe,
            "retest_bars": self.retest_bars,
            "confirm_after_fill": self.confirm_after_fill,
            "post_fill_confirm_bars": self.post_fill_confirm_bars,
            "filled_price": float(self.filled_price) if self.filled_price else None,
            "filled_qty": float(self.filled_qty) if self.filled_qty else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "candles_checked": self.candles_checked,
            "status": self.status,
            "placed_at": self.placed_at.isoformat() if self.placed_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }
