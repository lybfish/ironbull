"""
OrderTrade Module - 核心业务服务

OrderTradeService 提供订单和成交的核心业务逻辑
确保所有不变量约束得到强制执行
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from .models import Order, Fill
from .states import OrderStatus, OrderStateMachine, FillValidation
from .repository import OrderRepository, FillRepository
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
from .exceptions import (
    OrderNotFoundError,
    OrderInTerminalStateError,
    OrderNotCancellableError,
    FillAlreadyExistsError,
    FillOrderMismatchError,
    TenantMismatchError,
    ValidationError,
)


def _generate_order_id() -> str:
    """生成系统订单号"""
    return f"ORD-{uuid.uuid4().hex[:16].upper()}"


def _generate_fill_id() -> str:
    """生成系统成交ID"""
    return f"FILL-{uuid.uuid4().hex[:16].upper()}"


def _order_to_dto(order: Order) -> OrderDTO:
    """Order 模型转 DTO"""
    return OrderDTO(
        order_id=order.order_id,
        exchange_order_id=order.exchange_order_id,
        tenant_id=order.tenant_id,
        account_id=order.account_id,
        signal_id=order.signal_id,
        symbol=order.symbol,
        exchange=order.exchange,
        market_type=order.market_type,
        side=order.side,
        order_type=order.order_type,
        quantity=float(order.quantity) if order.quantity else 0,
        price=float(order.price) if order.price else None,
        stop_loss=float(order.stop_loss) if order.stop_loss else None,
        take_profit=float(order.take_profit) if order.take_profit else None,
        position_side=order.position_side,
        leverage=order.leverage,
        status=order.status,
        filled_quantity=float(order.filled_quantity) if order.filled_quantity else 0,
        avg_price=float(order.avg_price) if order.avg_price else None,
        total_fee=float(order.total_fee) if order.total_fee else 0,
        fee_currency=order.fee_currency,
        error_code=order.error_code,
        error_message=order.error_message,
        created_at=order.created_at,
        submitted_at=order.submitted_at,
        updated_at=order.updated_at,
    )


def _fill_to_dto(fill: Fill) -> FillDTO:
    """Fill 模型转 DTO"""
    return FillDTO(
        fill_id=fill.fill_id,
        exchange_trade_id=fill.exchange_trade_id,
        order_id=fill.order_id,
        tenant_id=fill.tenant_id,
        account_id=fill.account_id,
        symbol=fill.symbol,
        side=fill.side,
        quantity=float(fill.quantity) if fill.quantity else 0,
        price=float(fill.price) if fill.price else 0,
        fee=float(fill.fee) if fill.fee else 0,
        fee_currency=fill.fee_currency,
        filled_at=fill.filled_at,
        created_at=fill.created_at,
    )


class OrderTradeService:
    """
    订单成交服务
    
    核心职责：
    1. 创建和管理订单生命周期
    2. 记录成交流水
    3. 强制执行不变量约束
    4. 提供查询能力
    """
    
    def __init__(self, session: Session):
        """
        初始化服务
        
        Args:
            session: 数据库会话
        """
        self.session = session
        self.order_repo = OrderRepository(session)
        self.fill_repo = FillRepository(session)
    
    # ============ 订单操作 ============
    
    def create_order(self, dto: CreateOrderDTO) -> OrderDTO:
        """
        创建订单
        
        Args:
            dto: 创建订单请求
            
        Returns:
            创建后的订单 DTO
        """
        # 参数验证
        if dto.quantity <= 0:
            raise ValidationError("quantity", "must be positive")
        if dto.order_type == "LIMIT" and dto.price is None:
            raise ValidationError("price", "required for LIMIT order")
        
        # 创建订单
        order = Order(
            order_id=_generate_order_id(),
            tenant_id=dto.tenant_id,
            account_id=dto.account_id,
            signal_id=dto.signal_id,
            symbol=dto.symbol,
            exchange=dto.exchange,
            market_type=dto.market_type,
            side=dto.side,
            order_type=dto.order_type,
            quantity=dto.quantity,
            price=dto.price,
            stop_loss=dto.stop_loss,
            take_profit=dto.take_profit,
            position_side=dto.position_side,
            leverage=dto.leverage,
            status=OrderStatus.PENDING.value,
            filled_quantity=0,
            total_fee=0,
            request_id=dto.request_id,
        )
        
        order = self.order_repo.create(order)
        return _order_to_dto(order)
    
    def submit_order(
        self,
        order_id: str,
        tenant_id: int,
        exchange_order_id: str,
        submitted_at: Optional[datetime] = None,
    ) -> OrderDTO:
        """
        提交订单到交易所
        
        Args:
            order_id: 系统订单号
            tenant_id: 租户ID
            exchange_order_id: 交易所订单号
            submitted_at: 提交时间
            
        Returns:
            更新后的订单 DTO
        """
        order = self._get_order_or_raise(order_id, tenant_id)
        
        # 验证状态转换
        current_status = OrderStatus(order.status)
        OrderStateMachine.validate_transition(current_status, OrderStatus.SUBMITTED)
        
        # 更新订单
        self.order_repo.update_exchange_order_id(
            order_id=order_id,
            tenant_id=tenant_id,
            exchange_order_id=exchange_order_id,
            status=OrderStatus.SUBMITTED,
            submitted_at=submitted_at or datetime.utcnow(),
        )
        
        # 重新获取更新后的订单
        order = self._get_order_or_raise(order_id, tenant_id)
        return _order_to_dto(order)
    
    def confirm_order(self, order_id: str, tenant_id: int) -> OrderDTO:
        """
        确认订单（交易所已接收）
        
        Args:
            order_id: 系统订单号
            tenant_id: 租户ID
            
        Returns:
            更新后的订单 DTO
        """
        order = self._get_order_or_raise(order_id, tenant_id)
        
        # 验证状态转换
        current_status = OrderStatus(order.status)
        OrderStateMachine.validate_transition(current_status, OrderStatus.OPEN)
        
        # 更新状态
        self.order_repo.update_status(order_id, tenant_id, OrderStatus.OPEN)
        
        order = self._get_order_or_raise(order_id, tenant_id)
        return _order_to_dto(order)
    
    def cancel_order(
        self,
        order_id: str,
        tenant_id: int,
        reason: Optional[str] = None,
    ) -> OrderDTO:
        """
        取消订单
        
        Args:
            order_id: 系统订单号
            tenant_id: 租户ID
            reason: 取消原因
            
        Returns:
            更新后的订单 DTO
        """
        order = self._get_order_or_raise(order_id, tenant_id)
        
        current_status = OrderStatus(order.status)
        
        # 检查是否可取消
        if not current_status.is_cancellable():
            raise OrderNotCancellableError(order_id, order.status)
        
        # 验证状态转换
        OrderStateMachine.validate_transition(current_status, OrderStatus.CANCELLED)
        
        # 更新状态
        self.order_repo.update_status(
            order_id=order_id,
            tenant_id=tenant_id,
            status=OrderStatus.CANCELLED,
            error_message=reason,
        )
        
        order = self._get_order_or_raise(order_id, tenant_id)
        return _order_to_dto(order)
    
    def reject_order(
        self,
        order_id: str,
        tenant_id: int,
        error_code: str,
        error_message: str,
    ) -> OrderDTO:
        """
        拒绝订单
        
        Args:
            order_id: 系统订单号
            tenant_id: 租户ID
            error_code: 错误码
            error_message: 错误信息
            
        Returns:
            更新后的订单 DTO
        """
        order = self._get_order_or_raise(order_id, tenant_id)
        
        current_status = OrderStatus(order.status)
        OrderStateMachine.validate_transition(current_status, OrderStatus.REJECTED)
        
        self.order_repo.update_status(
            order_id=order_id,
            tenant_id=tenant_id,
            status=OrderStatus.REJECTED,
            error_code=error_code,
            error_message=error_message,
        )
        
        order = self._get_order_or_raise(order_id, tenant_id)
        return _order_to_dto(order)
    
    def fail_order(
        self,
        order_id: str,
        tenant_id: int,
        error_code: str,
        error_message: str,
    ) -> OrderDTO:
        """
        标记订单失败
        
        Args:
            order_id: 系统订单号
            tenant_id: 租户ID
            error_code: 错误码
            error_message: 错误信息
            
        Returns:
            更新后的订单 DTO
        """
        order = self._get_order_or_raise(order_id, tenant_id)
        
        current_status = OrderStatus(order.status)
        if current_status.is_terminal():
            raise OrderInTerminalStateError(order_id, order.status)
        
        OrderStateMachine.validate_transition(current_status, OrderStatus.FAILED)
        
        self.order_repo.update_status(
            order_id=order_id,
            tenant_id=tenant_id,
            status=OrderStatus.FAILED,
            error_code=error_code,
            error_message=error_message,
        )
        
        order = self._get_order_or_raise(order_id, tenant_id)
        return _order_to_dto(order)
    
    def get_order(self, order_id: str, tenant_id: int) -> OrderDTO:
        """
        获取订单
        
        Args:
            order_id: 系统订单号
            tenant_id: 租户ID
            
        Returns:
            订单 DTO
        """
        order = self._get_order_or_raise(order_id, tenant_id)
        return _order_to_dto(order)
    
    def list_orders(self, filter: OrderFilter) -> List[OrderDTO]:
        """
        查询订单列表
        
        Args:
            filter: 过滤条件
            
        Returns:
            订单 DTO 列表
        """
        orders = self.order_repo.list_orders(filter)
        return [_order_to_dto(o) for o in orders]
    
    def get_active_orders(
        self,
        tenant_id: int,
        account_id: Optional[int] = None
    ) -> List[OrderDTO]:
        """
        获取活跃订单
        
        Args:
            tenant_id: 租户ID
            account_id: 账户ID（可选）
            
        Returns:
            活跃订单列表
        """
        orders = self.order_repo.get_active_orders(tenant_id, account_id)
        return [_order_to_dto(o) for o in orders]
    
    # ============ 成交操作 ============
    
    def record_fill(self, dto: RecordFillDTO) -> FillDTO:
        """
        记录成交
        
        核心方法，确保所有不变量约束：
        1. 成交 ≤ 订单
        2. 成交不可逆（append-only）
        3. 时间有序
        4. 关联完整
        
        Args:
            dto: 成交记录请求
            
        Returns:
            成交 DTO
        """
        # 获取订单
        order = self._get_order_or_raise(dto.order_id, dto.tenant_id)
        
        # 验证订单状态（必须是活跃状态或已提交）
        current_status = OrderStatus(order.status)
        if current_status.is_terminal() and current_status != OrderStatus.FILLED:
            raise OrderInTerminalStateError(dto.order_id, order.status)
        
        # 验证成交与订单匹配
        if dto.symbol != order.symbol:
            raise FillOrderMismatchError(
                fill_id="(new)",
                order_id=dto.order_id,
                reason=f"symbol mismatch: fill={dto.symbol}, order={order.symbol}"
            )
        if dto.side != order.side:
            raise FillOrderMismatchError(
                fill_id="(new)",
                order_id=dto.order_id,
                reason=f"side mismatch: fill={dto.side}, order={order.side}"
            )
        
        # 幂等检查：如果有交易所成交ID，检查是否已存在
        if dto.exchange_trade_id:
            existing = self.fill_repo.get_by_exchange_trade_id(
                order_id=dto.order_id,
                exchange_trade_id=dto.exchange_trade_id,
                tenant_id=dto.tenant_id,
            )
            if existing:
                # 已存在，返回现有记录（幂等）
                return _fill_to_dto(existing)
        
        # 获取现有成交汇总
        existing_filled, _, existing_fee = self.fill_repo.get_fills_summary(
            dto.order_id, dto.tenant_id
        )
        
        # 不变量检查：成交 ≤ 订单
        order_quantity = float(order.quantity)
        new_fill_qty = float(dto.quantity)
        FillValidation.validate_fill_quantity(
            order_quantity=order_quantity,
            existing_filled=existing_filled,
            new_fill_quantity=new_fill_qty,
        )
        
        # 不变量检查：时间有序
        max_fill_time = self.fill_repo.get_max_fill_time(dto.order_id, dto.tenant_id)
        if max_fill_time:
            FillValidation.validate_fill_time_order(
                existing_max_time=max_fill_time.timestamp(),
                new_fill_time=dto.filled_at.timestamp(),
            )
        
        # 创建成交记录
        fill = Fill(
            fill_id=_generate_fill_id(),
            exchange_trade_id=dto.exchange_trade_id,
            order_id=dto.order_id,
            tenant_id=dto.tenant_id,
            account_id=dto.account_id,
            symbol=dto.symbol,
            side=dto.side,
            quantity=dto.quantity,
            price=dto.price,
            fee=dto.fee,
            fee_currency=dto.fee_currency,
            filled_at=dto.filled_at,
            request_id=dto.request_id,
        )
        
        fill = self.fill_repo.create(fill)
        
        # 更新订单成交信息（统一转为 float 避免类型不兼容）
        fill_quantity = float(dto.quantity)
        fill_price = float(dto.price)
        fill_fee = float(dto.fee) if dto.fee else 0
        
        new_filled_quantity = existing_filled + fill_quantity
        new_total_fee = existing_fee + fill_fee
        
        # 计算加权平均价
        existing_avg_price = float(order.avg_price) if order.avg_price else 0
        new_total_value = (existing_filled * existing_avg_price) + (fill_quantity * fill_price)
        new_avg_price = new_total_value / new_filled_quantity if new_filled_quantity > 0 else 0
        
        # 确定新状态
        new_status = OrderStateMachine.determine_status_after_fill(
            order_quantity=order_quantity,
            filled_quantity=new_filled_quantity,
            current_status=current_status,
        )
        
        # 更新订单
        self.order_repo.update_fill_info(
            order_id=dto.order_id,
            tenant_id=dto.tenant_id,
            filled_quantity=new_filled_quantity,
            avg_price=new_avg_price,
            total_fee=new_total_fee,
            fee_currency=dto.fee_currency,
            status=new_status,
        )
        
        return _fill_to_dto(fill)
    
    def get_fills_by_order(self, order_id: str, tenant_id: int) -> List[FillDTO]:
        """
        获取订单的所有成交
        
        Args:
            order_id: 订单ID
            tenant_id: 租户ID
            
        Returns:
            成交列表
        """
        fills = self.fill_repo.get_fills_by_order(order_id, tenant_id)
        return [_fill_to_dto(f) for f in fills]
    
    def list_fills(self, filter: FillFilter) -> List[FillDTO]:
        """
        查询成交列表
        
        Args:
            filter: 过滤条件
            
        Returns:
            成交列表
        """
        fills = self.fill_repo.list_fills(filter)
        return [_fill_to_dto(f) for f in fills]
    
    # ============ 聚合查询 ============
    
    def get_order_with_fills(self, order_id: str, tenant_id: int) -> OrderWithFillsDTO:
        """
        获取订单及其所有成交
        
        Args:
            order_id: 订单ID
            tenant_id: 租户ID
            
        Returns:
            订单及成交 DTO
        """
        order = self._get_order_or_raise(order_id, tenant_id)
        fills = self.fill_repo.get_fills_by_order(order_id, tenant_id)
        
        return OrderWithFillsDTO(
            order=_order_to_dto(order),
            fills=[_fill_to_dto(f) for f in fills],
        )
    
    def get_order_summary(self, tenant_id: int, account_id: int) -> OrderSummary:
        """
        获取订单统计摘要
        
        Args:
            tenant_id: 租户ID
            account_id: 账户ID
            
        Returns:
            订单摘要
        """
        base_filter = OrderFilter(tenant_id=tenant_id, account_id=account_id)
        
        # 统计各状态订单数
        total = self.order_repo.count_orders(base_filter)
        
        pending_filter = OrderFilter(
            tenant_id=tenant_id, 
            account_id=account_id,
            statuses=[OrderStatus.PENDING.value, OrderStatus.SUBMITTED.value]
        )
        pending = self.order_repo.count_orders(pending_filter)
        
        open_filter = OrderFilter(
            tenant_id=tenant_id,
            account_id=account_id,
            statuses=[OrderStatus.OPEN.value, OrderStatus.PARTIAL.value]
        )
        open_orders = self.order_repo.count_orders(open_filter)
        
        filled_filter = OrderFilter(
            tenant_id=tenant_id,
            account_id=account_id,
            status=OrderStatus.FILLED.value
        )
        filled = self.order_repo.count_orders(filled_filter)
        
        cancelled_filter = OrderFilter(
            tenant_id=tenant_id,
            account_id=account_id,
            status=OrderStatus.CANCELLED.value
        )
        cancelled = self.order_repo.count_orders(cancelled_filter)
        
        failed_filter = OrderFilter(
            tenant_id=tenant_id,
            account_id=account_id,
            statuses=[OrderStatus.FAILED.value, OrderStatus.REJECTED.value]
        )
        failed = self.order_repo.count_orders(failed_filter)
        
        # 统计成交
        fill_filter = FillFilter(tenant_id=tenant_id, account_id=account_id)
        total_fills = self.fill_repo.count_fills(fill_filter)
        total_volume = self.fill_repo.get_total_volume(tenant_id, account_id)
        total_fees = self.fill_repo.get_total_fees(tenant_id, account_id)
        
        return OrderSummary(
            tenant_id=tenant_id,
            account_id=account_id,
            total_orders=total,
            pending_orders=pending,
            open_orders=open_orders,
            filled_orders=filled,
            cancelled_orders=cancelled,
            failed_orders=failed,
            total_fills=total_fills,
            total_volume=total_volume,
            total_fees=total_fees,
        )
    
    # ============ 辅助方法 ============
    
    def _get_order_or_raise(self, order_id: str, tenant_id: int) -> Order:
        """获取订单，不存在则抛异常"""
        order = self.order_repo.get_by_order_id(order_id, tenant_id)
        if not order:
            raise OrderNotFoundError(order_id)
        return order
