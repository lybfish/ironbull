"""
OrderTrade Module - 订单与成交管理

提供订单（Order）和成交（Fill）的完整生命周期管理，
满足 SaaS 蓝图要求的"一笔订单可有多笔成交"的数据模型。

核心组件：
- OrderTradeService: 核心业务服务
- Order/Fill: 数据模型
- OrderStatus: 订单状态枚举
- OrderStateMachine: 状态流转控制

不变量约束：
1. 成交 ≤ 订单（成交数量不超过订单数量）
2. 成交不可逆（Fill 表 append-only）
3. 状态机合法（订单状态按规则流转）
4. 时间有序（成交时间单调递增）
5. 关联完整（成交必须关联订单）
6. 租户隔离（跨租户不可见）

使用示例：
    from libs.order_trade import OrderTradeService, CreateOrderDTO
    from libs.core.database import get_session
    
    with get_session() as session:
        service = OrderTradeService(session)
        
        # 创建订单
        order = service.create_order(CreateOrderDTO(
            tenant_id=1,
            account_id=1,
            symbol="BTC/USDT",
            exchange="binance",
            side="BUY",
            order_type="MARKET",
            quantity=0.01,
        ))
        
        # 记录成交
        fill = service.record_fill(RecordFillDTO(
            order_id=order.order_id,
            tenant_id=1,
            account_id=1,
            symbol="BTC/USDT",
            side="BUY",
            quantity=0.01,
            price=50000.0,
            filled_at=datetime.utcnow(),
        ))
        
        session.commit()
"""

# Models
from .models import Order, Fill

# States
from .states import OrderStatus, OrderStateMachine, FillValidation

# Contracts (DTOs)
from .contracts import (
    CreateOrderDTO,
    UpdateOrderDTO,
    OrderDTO,
    OrderFilter,
    RecordFillDTO,
    FillDTO,
    FillFilter,
    OrderWithFillsDTO,
    OrderSummary,
)

# Exceptions
from .exceptions import (
    OrderTradeError,
    OrderNotFoundError,
    OrderAlreadyExistsError,
    InvalidStateTransitionError,
    OrderNotCancellableError,
    OrderInTerminalStateError,
    FillNotFoundError,
    FillAlreadyExistsError,
    FillQuantityExceededError,
    FillTimeOrderError,
    FillOrderMismatchError,
    TenantMismatchError,
    ValidationError,
    InvariantViolationError,
)

# Repository
from .repository import OrderRepository, FillRepository

# Service
from .service import OrderTradeService


__all__ = [
    # Models
    "Order",
    "Fill",
    # States
    "OrderStatus",
    "OrderStateMachine",
    "FillValidation",
    # Contracts
    "CreateOrderDTO",
    "UpdateOrderDTO",
    "OrderDTO",
    "OrderFilter",
    "RecordFillDTO",
    "FillDTO",
    "FillFilter",
    "OrderWithFillsDTO",
    "OrderSummary",
    # Exceptions
    "OrderTradeError",
    "OrderNotFoundError",
    "OrderAlreadyExistsError",
    "InvalidStateTransitionError",
    "OrderNotCancellableError",
    "OrderInTerminalStateError",
    "FillNotFoundError",
    "FillAlreadyExistsError",
    "FillQuantityExceededError",
    "FillTimeOrderError",
    "FillOrderMismatchError",
    "TenantMismatchError",
    "ValidationError",
    "InvariantViolationError",
    # Repository
    "OrderRepository",
    "FillRepository",
    # Service
    "OrderTradeService",
]
