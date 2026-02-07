"""
OrderTrade Module - DTO 数据传输对象

定义 API 层的输入输出数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from .states import OrderStatus


# ============ Order DTOs ============

@dataclass
class CreateOrderDTO:
    """创建订单请求"""
    tenant_id: int
    account_id: int
    symbol: str
    exchange: str
    side: str                           # BUY/SELL
    order_type: str                     # MARKET/LIMIT/STOP_MARKET/TAKE_PROFIT_MARKET
    quantity: float
    
    # 可选字段
    price: Optional[float] = None       # 限价单价格
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    signal_id: Optional[str] = None
    market_type: str = "spot"           # spot/future
    position_side: Optional[str] = None # LONG/SHORT（合约）
    leverage: Optional[int] = None
    trade_type: Optional[str] = "OPEN"  # OPEN/CLOSE/ADD/REDUCE
    close_reason: Optional[str] = None  # SL/TP/SIGNAL/MANUAL/LIQUIDATION（仅 CLOSE 时）
    request_id: Optional[str] = None


@dataclass
class UpdateOrderDTO:
    """更新订单请求"""
    order_id: str
    tenant_id: int
    
    # 可更新字段
    exchange_order_id: Optional[str] = None
    status: Optional[OrderStatus] = None
    filled_quantity: Optional[float] = None
    avg_price: Optional[float] = None
    total_fee: Optional[float] = None
    fee_currency: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    submitted_at: Optional[datetime] = None


@dataclass
class OrderDTO:
    """订单数据传输对象"""
    order_id: str
    exchange_order_id: Optional[str]
    tenant_id: int
    account_id: int
    signal_id: Optional[str]
    symbol: str
    exchange: str
    market_type: str
    side: str
    order_type: str
    trade_type: Optional[str]
    close_reason: Optional[str]
    quantity: float
    price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    position_side: Optional[str]
    leverage: Optional[int]
    status: str
    filled_quantity: float
    avg_price: Optional[float]
    total_fee: float
    fee_currency: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    submitted_at: Optional[datetime]
    updated_at: datetime
    
    @property
    def is_filled(self) -> bool:
        """是否完全成交"""
        return self.status == OrderStatus.FILLED.value
    
    @property
    def is_terminal(self) -> bool:
        """是否为终态"""
        return OrderStatus(self.status).is_terminal()
    
    @property
    def remaining_quantity(self) -> float:
        """剩余未成交数量"""
        return max(0, self.quantity - self.filled_quantity)
    
    def to_dict(self) -> dict:
        """转为字典"""
        return {
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
            "quantity": self.quantity,
            "price": self.price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_side": self.position_side,
            "leverage": self.leverage,
            "status": self.status,
            "filled_quantity": self.filled_quantity,
            "avg_price": self.avg_price,
            "total_fee": self.total_fee,
            "fee_currency": self.fee_currency,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_filled": self.is_filled,
            "is_terminal": self.is_terminal,
            "remaining_quantity": self.remaining_quantity,
        }


@dataclass
class OrderFilter:
    """订单查询过滤条件"""
    tenant_id: int
    account_id: Optional[int] = None
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    side: Optional[str] = None
    status: Optional[str] = None
    statuses: Optional[List[str]] = None    # 多状态过滤
    signal_id: Optional[str] = None
    trade_type: Optional[str] = None        # OPEN/CLOSE/ADD/REDUCE
    close_reason: Optional[str] = None      # SL/TP/SIGNAL/MANUAL/LIQUIDATION
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


# ============ Fill DTOs ============

@dataclass
class RecordFillDTO:
    """记录成交请求"""
    order_id: str
    tenant_id: int
    account_id: int
    symbol: str
    side: str
    quantity: float
    price: float
    filled_at: datetime
    
    # 可选字段
    exchange_trade_id: Optional[str] = None
    fee: float = 0.0
    fee_currency: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class FillDTO:
    """成交数据传输对象"""
    fill_id: str
    exchange_trade_id: Optional[str]
    order_id: str
    tenant_id: int
    account_id: int
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float
    fee_currency: Optional[str]
    filled_at: datetime
    created_at: datetime
    exchange: Optional[str] = None
    market_type: Optional[str] = None
    trade_type: Optional[str] = None
    
    @property
    def value(self) -> float:
        """成交金额"""
        return self.quantity * self.price
    
    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "fill_id": self.fill_id,
            "exchange_trade_id": self.exchange_trade_id,
            "order_id": self.order_id,
            "tenant_id": self.tenant_id,
            "account_id": self.account_id,
            "symbol": self.symbol,
            "side": self.side,
            "trade_type": self.trade_type,
            "quantity": self.quantity,
            "price": self.price,
            "fee": self.fee,
            "fee_currency": self.fee_currency,
            "exchange": self.exchange,
            "market_type": self.market_type,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "value": self.value,
        }


@dataclass
class FillFilter:
    """成交查询过滤条件"""
    tenant_id: int
    account_id: Optional[int] = None
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    trade_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


# ============ 聚合 DTOs ============

@dataclass
class OrderWithFillsDTO:
    """订单及其所有成交"""
    order: OrderDTO
    fills: List[FillDTO] = field(default_factory=list)
    
    @property
    def fill_count(self) -> int:
        """成交笔数"""
        return len(self.fills)
    
    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "order": self.order.to_dict(),
            "fills": [f.to_dict() for f in self.fills],
            "fill_count": self.fill_count,
        }


@dataclass
class OrderSummary:
    """订单统计摘要"""
    tenant_id: int
    account_id: int
    total_orders: int
    pending_orders: int
    open_orders: int
    filled_orders: int
    cancelled_orders: int
    failed_orders: int
    total_fills: int
    total_volume: float         # 总成交额
    total_fees: float           # 总手续费
    
    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "tenant_id": self.tenant_id,
            "account_id": self.account_id,
            "total_orders": self.total_orders,
            "pending_orders": self.pending_orders,
            "open_orders": self.open_orders,
            "filled_orders": self.filled_orders,
            "cancelled_orders": self.cancelled_orders,
            "failed_orders": self.failed_orders,
            "total_fills": self.total_fills,
            "total_volume": self.total_volume,
            "total_fees": self.total_fees,
        }
