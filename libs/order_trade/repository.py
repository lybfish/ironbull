"""
OrderTrade Module - 数据访问层

OrderRepository 和 FillRepository
提供 Order 和 Fill 的 CRUD 操作
"""

from datetime import datetime
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .models import Order, Fill
from .states import OrderStatus
from .contracts import OrderFilter, FillFilter
from .exceptions import (
    OrderNotFoundError,
    OrderAlreadyExistsError,
    FillNotFoundError,
    FillAlreadyExistsError,
    TenantMismatchError,
)


class OrderRepository:
    """订单数据访问层"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, order: Order) -> Order:
        """
        创建订单
        
        Args:
            order: Order 实例
            
        Returns:
            创建后的 Order（包含 id）
            
        Raises:
            OrderAlreadyExistsError: 订单已存在
        """
        try:
            self.session.add(order)
            self.session.flush()
            return order
        except IntegrityError as e:
            self.session.rollback()
            if "Duplicate entry" in str(e) or "UNIQUE constraint" in str(e):
                raise OrderAlreadyExistsError(order.order_id)
            raise
    
    def get_by_order_id(self, order_id: str, tenant_id: int) -> Optional[Order]:
        """
        根据 order_id 获取订单
        
        Args:
            order_id: 系统订单号
            tenant_id: 租户ID（强制租户隔离）
            
        Returns:
            Order 或 None
        """
        stmt = select(Order).where(
            and_(
                Order.order_id == order_id,
                Order.tenant_id == tenant_id
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()
    
    def get_by_order_id_any_tenant(self, order_id: str) -> Optional[Order]:
        """
        根据 order_id 获取订单（不限租户，内部使用）
        
        Args:
            order_id: 系统订单号
            
        Returns:
            Order 或 None
        """
        stmt = select(Order).where(Order.order_id == order_id)
        return self.session.execute(stmt).scalar_one_or_none()
    
    def get_by_exchange_order_id(
        self, 
        exchange_order_id: str, 
        tenant_id: int,
        exchange: str
    ) -> Optional[Order]:
        """
        根据交易所订单号获取订单
        
        Args:
            exchange_order_id: 交易所订单号
            tenant_id: 租户ID
            exchange: 交易所
            
        Returns:
            Order 或 None
        """
        stmt = select(Order).where(
            and_(
                Order.exchange_order_id == exchange_order_id,
                Order.tenant_id == tenant_id,
                Order.exchange == exchange
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()
    
    def update_status(
        self,
        order_id: str,
        tenant_id: int,
        status: OrderStatus,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        更新订单状态
        
        Args:
            order_id: 订单号
            tenant_id: 租户ID
            status: 新状态
            error_code: 错误码（可选）
            error_message: 错误信息（可选）
            
        Returns:
            是否更新成功
        """
        values = {
            "status": status.value,
            "updated_at": datetime.now(),
        }
        if error_code is not None:
            values["error_code"] = error_code
        if error_message is not None:
            values["error_message"] = error_message
        
        stmt = (
            update(Order)
            .where(
                and_(
                    Order.order_id == order_id,
                    Order.tenant_id == tenant_id
                )
            )
            .values(**values)
        )
        result = self.session.execute(stmt)
        return result.rowcount > 0
    
    def update_fill_info(
        self,
        order_id: str,
        tenant_id: int,
        filled_quantity: float,
        avg_price: float,
        total_fee: float,
        fee_currency: Optional[str],
        status: OrderStatus,
    ) -> bool:
        """
        更新订单成交信息
        
        Args:
            order_id: 订单号
            tenant_id: 租户ID
            filled_quantity: 累计成交数量
            avg_price: 成交均价
            total_fee: 累计手续费
            fee_currency: 手续费币种
            status: 新状态
            
        Returns:
            是否更新成功
        """
        stmt = (
            update(Order)
            .where(
                and_(
                    Order.order_id == order_id,
                    Order.tenant_id == tenant_id
                )
            )
            .values(
                filled_quantity=filled_quantity,
                avg_price=avg_price,
                total_fee=total_fee,
                fee_currency=fee_currency,
                status=status.value,
                updated_at=datetime.now(),
            )
        )
        result = self.session.execute(stmt)
        return result.rowcount > 0
    
    def update_exchange_order_id(
        self,
        order_id: str,
        tenant_id: int,
        exchange_order_id: str,
        status: OrderStatus,
        submitted_at: Optional[datetime] = None,
    ) -> bool:
        """
        更新交易所订单号（提交后）
        
        Args:
            order_id: 系统订单号
            tenant_id: 租户ID
            exchange_order_id: 交易所订单号
            status: 新状态
            submitted_at: 提交时间
            
        Returns:
            是否更新成功
        """
        values = {
            "exchange_order_id": exchange_order_id,
            "status": status.value,
            "updated_at": datetime.now(),
        }
        if submitted_at:
            values["submitted_at"] = submitted_at
        
        stmt = (
            update(Order)
            .where(
                and_(
                    Order.order_id == order_id,
                    Order.tenant_id == tenant_id
                )
            )
            .values(**values)
        )
        result = self.session.execute(stmt)
        return result.rowcount > 0
    
    def list_orders(self, filter: OrderFilter) -> List[Order]:
        """
        查询订单列表
        
        Args:
            filter: 过滤条件
            
        Returns:
            Order 列表
        """
        conditions = [Order.tenant_id == filter.tenant_id]
        
        if filter.account_id:
            conditions.append(Order.account_id == filter.account_id)
        if filter.symbol:
            conditions.append(Order.symbol == filter.symbol)
        if filter.exchange:
            conditions.append(Order.exchange == filter.exchange)
        if filter.side:
            conditions.append(Order.side == filter.side)
        if filter.status:
            conditions.append(Order.status == filter.status)
        if filter.statuses:
            conditions.append(Order.status.in_(filter.statuses))
        if filter.signal_id:
            conditions.append(Order.signal_id == filter.signal_id)
        if filter.trade_type:
            conditions.append(Order.trade_type == filter.trade_type)
        if filter.close_reason:
            conditions.append(Order.close_reason == filter.close_reason)
        if filter.position_side:
            # 确保 position_side 过滤正确应用（统一转为大写）
            pos_side = str(filter.position_side).upper().strip()
            if pos_side and pos_side != 'NONE':
                conditions.append(Order.position_side == pos_side)
        if filter.start_time:
            conditions.append(Order.created_at >= filter.start_time)
        if filter.end_time:
            conditions.append(Order.created_at <= filter.end_time)
        
        stmt = (
            select(Order)
            .where(and_(*conditions))
            .order_by(Order.created_at.desc())
            .limit(filter.limit)
            .offset(filter.offset)
        )
        
        result = self.session.execute(stmt)
        return list(result.scalars().all())
    
    def count_orders(self, filter: OrderFilter) -> int:
        """
        统计订单数量（与 list_orders 使用相同过滤条件）
        """
        conditions = [Order.tenant_id == filter.tenant_id]
        if filter.account_id:
            conditions.append(Order.account_id == filter.account_id)
        if filter.symbol:
            conditions.append(Order.symbol == filter.symbol)
        if filter.exchange:
            conditions.append(Order.exchange == filter.exchange)
        if filter.side:
            conditions.append(Order.side == filter.side)
        if filter.status:
            conditions.append(Order.status == filter.status)
        if filter.statuses:
            conditions.append(Order.status.in_(filter.statuses))
        if filter.signal_id:
            conditions.append(Order.signal_id == filter.signal_id)
        if filter.trade_type:
            conditions.append(Order.trade_type == filter.trade_type)
        if filter.close_reason:
            conditions.append(Order.close_reason == filter.close_reason)
        if filter.position_side:
            # 确保 position_side 过滤正确应用（统一转为大写）
            pos_side = str(filter.position_side).upper().strip()
            if pos_side and pos_side != 'NONE':
                conditions.append(Order.position_side == pos_side)
        if filter.start_time:
            conditions.append(Order.created_at >= filter.start_time)
        if filter.end_time:
            conditions.append(Order.created_at <= filter.end_time)
        stmt = select(func.count(Order.id)).where(and_(*conditions))
        return self.session.execute(stmt).scalar() or 0
    
    def get_active_orders(self, tenant_id: int, account_id: Optional[int] = None) -> List[Order]:
        """
        获取活跃订单（OPEN/PARTIAL）
        
        Args:
            tenant_id: 租户ID
            account_id: 账户ID（可选）
            
        Returns:
            活跃订单列表
        """
        conditions = [
            Order.tenant_id == tenant_id,
            Order.status.in_([OrderStatus.OPEN.value, OrderStatus.PARTIAL.value])
        ]
        
        if account_id:
            conditions.append(Order.account_id == account_id)
        
        stmt = select(Order).where(and_(*conditions)).order_by(Order.created_at.desc())
        return list(self.session.execute(stmt).scalars().all())


class FillRepository:
    """成交数据访问层"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, fill: Fill) -> Fill:
        """
        创建成交记录
        
        Args:
            fill: Fill 实例
            
        Returns:
            创建后的 Fill
            
        Raises:
            FillAlreadyExistsError: 成交记录已存在
        """
        try:
            self.session.add(fill)
            self.session.flush()
            return fill
        except IntegrityError as e:
            self.session.rollback()
            if "Duplicate entry" in str(e) or "UNIQUE constraint" in str(e):
                raise FillAlreadyExistsError(fill.fill_id)
            raise
    
    def get_by_fill_id(self, fill_id: str, tenant_id: int) -> Optional[Fill]:
        """
        根据 fill_id 获取成交记录
        
        Args:
            fill_id: 成交ID
            tenant_id: 租户ID
            
        Returns:
            Fill 或 None
        """
        stmt = select(Fill).where(
            and_(
                Fill.fill_id == fill_id,
                Fill.tenant_id == tenant_id
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()
    
    def get_by_exchange_trade_id(
        self,
        order_id: str,
        exchange_trade_id: str,
        tenant_id: int
    ) -> Optional[Fill]:
        """
        根据交易所成交ID获取成交记录（用于幂等检查）
        
        Args:
            order_id: 订单ID
            exchange_trade_id: 交易所成交ID
            tenant_id: 租户ID
            
        Returns:
            Fill 或 None
        """
        stmt = select(Fill).where(
            and_(
                Fill.order_id == order_id,
                Fill.exchange_trade_id == exchange_trade_id,
                Fill.tenant_id == tenant_id
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()
    
    def get_fills_by_order(self, order_id: str, tenant_id: int) -> List[Fill]:
        """
        获取订单的所有成交记录
        
        Args:
            order_id: 订单ID
            tenant_id: 租户ID
            
        Returns:
            Fill 列表
        """
        stmt = (
            select(Fill)
            .where(
                and_(
                    Fill.order_id == order_id,
                    Fill.tenant_id == tenant_id
                )
            )
            .order_by(Fill.filled_at.asc())
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def get_fills_summary(self, order_id: str, tenant_id: int) -> Tuple[float, float, float]:
        """
        获取订单成交汇总
        
        Args:
            order_id: 订单ID
            tenant_id: 租户ID
            
        Returns:
            (total_quantity, weighted_avg_price, total_fee)
        """
        stmt = (
            select(
                func.sum(Fill.quantity).label("total_quantity"),
                func.sum(Fill.quantity * Fill.price).label("total_value"),
                func.sum(Fill.fee).label("total_fee"),
            )
            .where(
                and_(
                    Fill.order_id == order_id,
                    Fill.tenant_id == tenant_id
                )
            )
        )
        result = self.session.execute(stmt).one()
        
        total_quantity = float(result.total_quantity or 0)
        total_value = float(result.total_value or 0)
        total_fee = float(result.total_fee or 0)
        
        avg_price = total_value / total_quantity if total_quantity > 0 else 0
        
        return total_quantity, avg_price, total_fee
    
    def get_max_fill_time(self, order_id: str, tenant_id: int) -> Optional[datetime]:
        """
        获取订单的最大成交时间
        
        Args:
            order_id: 订单ID
            tenant_id: 租户ID
            
        Returns:
            最大成交时间或 None
        """
        stmt = (
            select(func.max(Fill.filled_at))
            .where(
                and_(
                    Fill.order_id == order_id,
                    Fill.tenant_id == tenant_id
                )
            )
        )
        return self.session.execute(stmt).scalar()
    
    def list_fills(self, filter: FillFilter) -> List[Fill]:
        """
        查询成交列表
        
        Args:
            filter: 过滤条件
            
        Returns:
            Fill 列表
        """
        conditions = [Fill.tenant_id == filter.tenant_id]
        
        if filter.account_id:
            conditions.append(Fill.account_id == filter.account_id)
        if filter.order_id:
            conditions.append(Fill.order_id == filter.order_id)
        if filter.symbol:
            conditions.append(Fill.symbol == filter.symbol)
        if filter.side:
            conditions.append(Fill.side == filter.side)
        if filter.trade_type:
            conditions.append(Fill.trade_type == filter.trade_type)
        if filter.start_time:
            conditions.append(Fill.filled_at >= filter.start_time)
        if filter.end_time:
            conditions.append(Fill.filled_at <= filter.end_time)
        
        stmt = (
            select(Fill)
            .where(and_(*conditions))
            .order_by(Fill.filled_at.desc())
            .limit(filter.limit)
            .offset(filter.offset)
        )
        
        result = self.session.execute(stmt)
        return list(result.scalars().all())
    
    def count_fills(self, filter: FillFilter) -> int:
        """
        统计成交数量（与 list_fills 使用相同过滤条件）
        """
        conditions = [Fill.tenant_id == filter.tenant_id]
        if filter.account_id:
            conditions.append(Fill.account_id == filter.account_id)
        if filter.order_id:
            conditions.append(Fill.order_id == filter.order_id)
        if filter.symbol:
            conditions.append(Fill.symbol == filter.symbol)
        if filter.side:
            conditions.append(Fill.side == filter.side)
        if filter.trade_type:
            conditions.append(Fill.trade_type == filter.trade_type)
        if filter.start_time:
            conditions.append(Fill.filled_at >= filter.start_time)
        if filter.end_time:
            conditions.append(Fill.filled_at <= filter.end_time)
        stmt = select(func.count(Fill.id)).where(and_(*conditions))
        return self.session.execute(stmt).scalar() or 0
    
    def get_total_volume(
        self,
        tenant_id: int,
        account_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> float:
        """
        获取总成交额
        
        Args:
            tenant_id: 租户ID
            account_id: 账户ID（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            
        Returns:
            总成交额
        """
        conditions = [Fill.tenant_id == tenant_id]
        
        if account_id:
            conditions.append(Fill.account_id == account_id)
        if start_time:
            conditions.append(Fill.filled_at >= start_time)
        if end_time:
            conditions.append(Fill.filled_at <= end_time)
        
        stmt = (
            select(func.sum(Fill.quantity * Fill.price))
            .where(and_(*conditions))
        )
        result = self.session.execute(stmt).scalar()
        return float(result or 0)
    
    def get_total_fees(
        self,
        tenant_id: int,
        account_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> float:
        """
        获取总手续费
        
        Args:
            tenant_id: 租户ID
            account_id: 账户ID（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            
        Returns:
            总手续费
        """
        conditions = [Fill.tenant_id == tenant_id]
        
        if account_id:
            conditions.append(Fill.account_id == account_id)
        if start_time:
            conditions.append(Fill.filled_at >= start_time)
        if end_time:
            conditions.append(Fill.filled_at <= end_time)
        
        stmt = select(func.sum(Fill.fee)).where(and_(*conditions))
        result = self.session.execute(stmt).scalar()
        return float(result or 0)
