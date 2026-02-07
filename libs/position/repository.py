"""
Position Module - 数据仓库层

封装数据库访问，提供 CRUD 操作，确保租户隔离
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from libs.position.models import Position, PositionChange
from libs.position.contracts import PositionFilter, PositionChangeFilter


def generate_position_id() -> str:
    """生成持仓ID"""
    return f"POS-{uuid.uuid4().hex[:16].upper()}"


def generate_change_id() -> str:
    """生成变动ID"""
    return f"CHG-{uuid.uuid4().hex[:16].upper()}"


class PositionRepository:
    """持仓仓库"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, position: Position) -> Position:
        """创建持仓记录"""
        if not position.position_id:
            position.position_id = generate_position_id()
        
        self.session.add(position)
        self.session.flush()
        return position
    
    def get_by_position_id(
        self,
        position_id: str,
        tenant_id: int,
    ) -> Optional[Position]:
        """根据持仓ID查询"""
        return self.session.query(Position).filter(
            and_(
                Position.position_id == position_id,
                Position.tenant_id == tenant_id,
            )
        ).first()
    
    def get_by_key(
        self,
        tenant_id: int,
        account_id: int,
        symbol: str,
        exchange: str,
        position_side: str = "NONE",
    ) -> Optional[Position]:
        """根据唯一键查询持仓"""
        return self.session.query(Position).filter(
            and_(
                Position.tenant_id == tenant_id,
                Position.account_id == account_id,
                Position.symbol == symbol,
                Position.exchange == exchange,
                Position.position_side == position_side,
            )
        ).first()
    
    def get_or_create(
        self,
        tenant_id: int,
        account_id: int,
        symbol: str,
        exchange: str,
        market_type: str = "spot",
        position_side: str = "NONE",
    ) -> Tuple[Position, bool]:
        """获取或创建持仓记录，返回 (position, is_new)"""
        position = self.get_by_key(
            tenant_id=tenant_id,
            account_id=account_id,
            symbol=symbol,
            exchange=exchange,
            position_side=position_side,
        )
        
        if position:
            return position, False
        
        # 创建新持仓
        position = Position(
            position_id=generate_position_id(),
            tenant_id=tenant_id,
            account_id=account_id,
            symbol=symbol,
            exchange=exchange,
            market_type=market_type,
            position_side=position_side,
            quantity=Decimal("0"),
            available=Decimal("0"),
            frozen=Decimal("0"),
            avg_cost=Decimal("0"),
            total_cost=Decimal("0"),
            realized_pnl=Decimal("0"),
            status="OPEN",
        )
        
        self.session.add(position)
        self.session.flush()
        return position, True
    
    def update(self, position: Position) -> Position:
        """更新持仓"""
        position.updated_at = datetime.now()
        self.session.flush()
        return position
    
    def list_positions(self, filter: PositionFilter) -> List[Position]:
        """查询持仓列表"""
        query = self.session.query(Position).filter(
            Position.tenant_id == filter.tenant_id
        )
        
        if filter.account_id is not None:
            query = query.filter(Position.account_id == filter.account_id)
        
        if filter.symbol:
            query = query.filter(Position.symbol == filter.symbol)
        
        if filter.exchange:
            query = query.filter(Position.exchange == filter.exchange)
        
        if filter.market_type:
            query = query.filter(Position.market_type == filter.market_type)
        
        if filter.position_side:
            query = query.filter(Position.position_side == filter.position_side)
        
        if filter.status:
            query = query.filter(Position.status == filter.status)
        
        if filter.close_reason:
            query = query.filter(Position.close_reason == filter.close_reason)
        
        if filter.has_position is True:
            query = query.filter(Position.quantity > 0)
        elif filter.has_position is False:
            query = query.filter(Position.quantity == 0)
        
        query = query.order_by(desc(Position.updated_at))
        query = query.limit(filter.limit).offset(filter.offset)
        
        return query.all()
    
    def count_positions(self, filter: PositionFilter) -> int:
        """统计持仓数量"""
        query = self.session.query(Position).filter(
            Position.tenant_id == filter.tenant_id
        )
        
        if filter.account_id is not None:
            query = query.filter(Position.account_id == filter.account_id)
        
        if filter.symbol:
            query = query.filter(Position.symbol == filter.symbol)
        
        if filter.status:
            query = query.filter(Position.status == filter.status)
        
        if filter.close_reason:
            query = query.filter(Position.close_reason == filter.close_reason)
        
        if filter.has_position is True:
            query = query.filter(Position.quantity > 0)
        
        return query.count()
    
    def get_positions_by_account(
        self,
        tenant_id: int,
        account_id: int,
        has_position: bool = True,
    ) -> List[Position]:
        """获取账户所有持仓"""
        query = self.session.query(Position).filter(
            and_(
                Position.tenant_id == tenant_id,
                Position.account_id == account_id,
            )
        )
        
        if has_position:
            query = query.filter(Position.quantity > 0)
        
        return query.all()
    
    def get_positions_by_symbol(
        self,
        tenant_id: int,
        symbol: str,
        exchange: Optional[str] = None,
    ) -> List[Position]:
        """获取某标的的所有持仓"""
        query = self.session.query(Position).filter(
            and_(
                Position.tenant_id == tenant_id,
                Position.symbol == symbol,
            )
        )
        
        if exchange:
            query = query.filter(Position.exchange == exchange)
        
        return query.all()


class PositionChangeRepository:
    """持仓变动仓库"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, change: PositionChange) -> PositionChange:
        """创建变动记录（append-only）"""
        if not change.change_id:
            change.change_id = generate_change_id()
        
        self.session.add(change)
        self.session.flush()
        return change
    
    def get_by_change_id(
        self,
        change_id: str,
        tenant_id: int,
    ) -> Optional[PositionChange]:
        """根据变动ID查询"""
        return self.session.query(PositionChange).filter(
            and_(
                PositionChange.change_id == change_id,
                PositionChange.tenant_id == tenant_id,
            )
        ).first()
    
    def get_by_source(
        self,
        source_type: str,
        source_id: str,
        tenant_id: int,
    ) -> Optional[PositionChange]:
        """根据来源查询变动（用于幂等检查）"""
        return self.session.query(PositionChange).filter(
            and_(
                PositionChange.source_type == source_type,
                PositionChange.source_id == source_id,
                PositionChange.tenant_id == tenant_id,
            )
        ).first()
    
    def list_changes(self, filter: PositionChangeFilter) -> List[PositionChange]:
        """查询变动列表"""
        query = self.session.query(PositionChange).filter(
            PositionChange.tenant_id == filter.tenant_id
        )
        
        if filter.account_id is not None:
            query = query.filter(PositionChange.account_id == filter.account_id)
        
        if filter.position_id:
            query = query.filter(PositionChange.position_id == filter.position_id)
        
        if filter.symbol:
            query = query.filter(PositionChange.symbol == filter.symbol)
        
        if filter.change_type:
            query = query.filter(PositionChange.change_type == filter.change_type)
        
        if filter.source_type:
            query = query.filter(PositionChange.source_type == filter.source_type)
        
        if filter.source_id:
            query = query.filter(PositionChange.source_id == filter.source_id)
        
        if filter.start_time:
            query = query.filter(PositionChange.changed_at >= filter.start_time)
        
        if filter.end_time:
            query = query.filter(PositionChange.changed_at <= filter.end_time)
        
        query = query.order_by(desc(PositionChange.changed_at))
        query = query.limit(filter.limit).offset(filter.offset)
        
        return query.all()
    
    def get_changes_by_position(
        self,
        position_id: str,
        tenant_id: int,
        limit: int = 100,
    ) -> List[PositionChange]:
        """获取持仓的变动历史"""
        return self.session.query(PositionChange).filter(
            and_(
                PositionChange.position_id == position_id,
                PositionChange.tenant_id == tenant_id,
            )
        ).order_by(desc(PositionChange.changed_at)).limit(limit).all()
    
    def get_latest_change(
        self,
        position_id: str,
        tenant_id: int,
    ) -> Optional[PositionChange]:
        """获取持仓最近一次变动"""
        return self.session.query(PositionChange).filter(
            and_(
                PositionChange.position_id == position_id,
                PositionChange.tenant_id == tenant_id,
            )
        ).order_by(desc(PositionChange.changed_at)).first()
    
    def sum_realized_pnl(
        self,
        tenant_id: int,
        account_id: Optional[int] = None,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Decimal:
        """汇总已实现盈亏"""
        from sqlalchemy import func
        
        query = self.session.query(
            func.coalesce(func.sum(PositionChange.realized_pnl), 0)
        ).filter(
            and_(
                PositionChange.tenant_id == tenant_id,
                PositionChange.realized_pnl.isnot(None),
            )
        )
        
        if account_id is not None:
            query = query.filter(PositionChange.account_id == account_id)
        
        if symbol:
            query = query.filter(PositionChange.symbol == symbol)
        
        if start_time:
            query = query.filter(PositionChange.changed_at >= start_time)
        
        if end_time:
            query = query.filter(PositionChange.changed_at <= end_time)
        
        result = query.scalar()
        return Decimal(str(result)) if result else Decimal("0")
