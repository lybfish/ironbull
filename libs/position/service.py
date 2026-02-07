"""
Position Module - 业务服务层

实现持仓管理的核心业务逻辑，确保不变量成立
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from libs.position.models import Position, PositionChange
from libs.position.states import (
    PositionSide,
    PositionStatus,
    ChangeType,
    PositionValidation,
)
from libs.position.contracts import (
    PositionDTO,
    PositionChangeDTO,
    UpdatePositionDTO,
    FreezePositionDTO,
    PositionFilter,
    PositionChangeFilter,
    PositionSummary,
)
from libs.position.exceptions import (
    PositionNotFoundError,
    InsufficientPositionError,
    InsufficientAvailableError,
    FreezeExceedsAvailableError,
    InvalidFreezeReleaseError,
    TenantMismatchError,
    InvalidChangeSourceError,
    PositionInvariantViolation,
)
from libs.position.repository import (
    PositionRepository,
    PositionChangeRepository,
    generate_change_id,
)


class PositionService:
    """
    持仓服务
    
    核心职责：
    1. 成交驱动的持仓更新（开仓/加仓/减仓/平仓）
    2. 冻结/解冻管理
    3. 成本计算（加权平均）
    4. 盈亏计算
    5. 维护不变量
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.position_repo = PositionRepository(session)
        self.change_repo = PositionChangeRepository(session)
    
    # ========== 持仓更新（由成交驱动）==========
    
    def update_position_by_fill(self, dto: UpdatePositionDTO) -> PositionDTO:
        """
        根据成交更新持仓
        
        自动判断：
        - 开仓：无持仓时买入
        - 加仓：有持仓且同方向
        - 减仓：有持仓且反方向
        - 平仓：减仓至零
        
        不变量检查：
        - 卖出 ≤ 可用
        - 可用 + 冻结 = 总持仓
        - 变动有来源
        """
        # 验证来源
        if not dto.fill_id:
            raise InvalidChangeSourceError("FILL", source_type="FILL", source_id=dto.fill_id)
        
        # 幂等检查：同一 fill_id 不重复处理
        existing_change = self.change_repo.get_by_source(
            source_type="FILL",
            source_id=dto.fill_id,
            tenant_id=dto.tenant_id,
        )
        if existing_change:
            # 已处理过，返回当前持仓状态
            position = self.position_repo.get_by_position_id(
                existing_change.position_id, dto.tenant_id
            )
            if position:
                return self._to_dto(position)
        
        # 获取或创建持仓
        position, is_new = self.position_repo.get_or_create(
            tenant_id=dto.tenant_id,
            account_id=dto.account_id,
            symbol=dto.symbol,
            exchange=dto.exchange,
            market_type=dto.market_type,
            position_side=dto.position_side,
        )
        
        # 确定变动类型和数量
        is_buy = dto.side.upper() == "BUY"
        quantity = dto.quantity
        price = dto.price
        
        # 对于合约，根据 position_side 判断是开仓还是平仓
        # LONG + BUY = 开仓/加仓
        # LONG + SELL = 减仓/平仓
        # SHORT + SELL = 开仓/加仓
        # SHORT + BUY = 减仓/平仓
        # 对于现货 (NONE)，BUY = 加仓，SELL = 减仓
        
        position_side = PositionSide(dto.position_side)
        is_opening = self._is_opening_position(position_side, dto.side.upper())
        
        if is_opening:
            # 开仓/加仓
            return self._add_position(position, quantity, price, dto)
        else:
            # 减仓/平仓
            return self._reduce_position(position, quantity, price, dto)
    
    def _is_opening_position(self, position_side: PositionSide, side: str) -> bool:
        """判断是否是开仓方向"""
        if position_side == PositionSide.LONG:
            return side == "BUY"
        elif position_side == PositionSide.SHORT:
            return side == "SELL"
        else:  # NONE (现货)
            return side == "BUY"
    
    def _add_position(
        self,
        position: Position,
        quantity: Decimal,
        price: Decimal,
        dto: UpdatePositionDTO,
    ) -> PositionDTO:
        """加仓（开仓或追加）"""
        current_quantity = Decimal(str(position.quantity))
        current_cost = Decimal(str(position.avg_cost))
        
        # 记录变动前状态
        quantity_before = current_quantity
        available_before = Decimal(str(position.available))
        frozen_before = Decimal(str(position.frozen))
        
        # 计算新的平均成本
        new_avg_cost = PositionValidation.calculate_avg_cost(
            current_quantity, current_cost, quantity, price
        )
        
        # 更新持仓
        new_quantity = current_quantity + quantity
        new_available = Decimal(str(position.available)) + quantity
        
        position.quantity = new_quantity
        position.available = new_available
        position.avg_cost = new_avg_cost
        position.total_cost = new_quantity * new_avg_cost
        position.status = PositionStatus.OPEN.value
        
        if not position.opened_at:
            position.opened_at = dto.filled_at or datetime.now()
        
        if dto.leverage:
            position.leverage = dto.leverage
        
        self.position_repo.update(position)
        
        # 确定变动类型
        change_type = ChangeType.OPEN if quantity_before == 0 else ChangeType.ADD
        
        # 记录变动
        self._record_change(
            position=position,
            change_type=change_type,
            quantity_change=quantity,
            available_change=quantity,
            frozen_change=Decimal("0"),
            price=price,
            realized_pnl=None,
            source_type="FILL",
            source_id=dto.fill_id,
            changed_at=dto.filled_at or datetime.now(),
        )
        
        return self._to_dto(position)
    
    def _reduce_position(
        self,
        position: Position,
        quantity: Decimal,
        price: Decimal,
        dto: UpdatePositionDTO,
    ) -> PositionDTO:
        """减仓（部分平仓或全部平仓）"""
        current_quantity = Decimal(str(position.quantity))
        current_available = Decimal(str(position.available))
        current_frozen = Decimal(str(position.frozen))
        current_cost = Decimal(str(position.avg_cost))
        
        # 不变量检查：卖出 ≤ 可用
        # 注意：实际可卖 = 可用 + 本次解冻的冻结量（如果订单已冻结）
        # 简化处理：这里假设已经解冻
        if quantity > current_available:
            raise InsufficientAvailableError(
                symbol=position.symbol,
                required=float(quantity),
                available=float(current_available),
                frozen=float(current_frozen),
            )
        
        # 计算已实现盈亏
        position_side = PositionSide(position.position_side)
        realized_pnl = PositionValidation.calculate_realized_pnl(
            close_quantity=quantity,
            close_price=price,
            avg_cost=current_cost,
            side=position_side,
        )
        
        # 更新持仓
        new_quantity = current_quantity - quantity
        new_available = current_available - quantity
        
        position.quantity = new_quantity
        position.available = new_available
        position.realized_pnl = Decimal(str(position.realized_pnl)) + realized_pnl
        
        # 判断是否完全平仓
        if new_quantity == 0:
            position.status = PositionStatus.CLOSED.value
            position.closed_at = dto.filled_at or datetime.now()
            position.avg_cost = Decimal("0")
            position.total_cost = Decimal("0")
            change_type = ChangeType.CLOSE
        else:
            position.total_cost = new_quantity * current_cost
            change_type = ChangeType.REDUCE
        
        self.position_repo.update(position)
        
        # 记录变动
        self._record_change(
            position=position,
            change_type=change_type,
            quantity_change=-quantity,  # 减仓为负
            available_change=-quantity,
            frozen_change=Decimal("0"),
            price=price,
            realized_pnl=realized_pnl,
            source_type="FILL",
            source_id=dto.fill_id,
            changed_at=dto.filled_at or datetime.now(),
        )
        
        return self._to_dto(position)
    
    # ========== 冻结/解冻 ==========
    
    def freeze_position(self, dto: FreezePositionDTO) -> PositionDTO:
        """
        冻结持仓（下单时锁定）
        
        不变量：冻结 ≤ 可用
        """
        position = self.position_repo.get_by_key(
            tenant_id=dto.tenant_id,
            account_id=dto.account_id,
            symbol=dto.symbol,
            exchange=dto.exchange,
            position_side=dto.position_side,
        )
        
        if not position:
            raise PositionNotFoundError(
                tenant_id=dto.tenant_id,
                account_id=dto.account_id,
                symbol=dto.symbol,
                position_side=dto.position_side,
            )
        
        quantity = dto.quantity
        current_available = Decimal(str(position.available))
        
        # 验证冻结数量
        if not PositionValidation.validate_freeze_quantity(quantity, current_available):
            raise FreezeExceedsAvailableError(
                symbol=dto.symbol,
                freeze_amount=float(quantity),
                available=float(current_available),
            )
        
        # 更新持仓
        position.available = current_available - quantity
        position.frozen = Decimal(str(position.frozen)) + quantity
        
        self.position_repo.update(position)
        
        # 记录变动
        self._record_change(
            position=position,
            change_type=ChangeType.FREEZE,
            quantity_change=Decimal("0"),  # 总量不变
            available_change=-quantity,
            frozen_change=quantity,
            price=None,
            realized_pnl=None,
            source_type="ORDER",
            source_id=dto.order_id,
            changed_at=dto.freeze_at or datetime.now(),
        )
        
        return self._to_dto(position)
    
    def unfreeze_position(self, dto: FreezePositionDTO) -> PositionDTO:
        """
        解冻持仓（撤单时释放）
        
        不变量：解冻 ≤ 冻结
        """
        position = self.position_repo.get_by_key(
            tenant_id=dto.tenant_id,
            account_id=dto.account_id,
            symbol=dto.symbol,
            exchange=dto.exchange,
            position_side=dto.position_side,
        )
        
        if not position:
            raise PositionNotFoundError(
                tenant_id=dto.tenant_id,
                account_id=dto.account_id,
                symbol=dto.symbol,
                position_side=dto.position_side,
            )
        
        quantity = dto.quantity
        current_frozen = Decimal(str(position.frozen))
        
        # 验证解冻数量
        if quantity > current_frozen:
            raise InvalidFreezeReleaseError(
                symbol=dto.symbol,
                release_amount=float(quantity),
                frozen=float(current_frozen),
            )
        
        # 更新持仓
        position.available = Decimal(str(position.available)) + quantity
        position.frozen = current_frozen - quantity
        
        self.position_repo.update(position)
        
        # 记录变动
        self._record_change(
            position=position,
            change_type=ChangeType.UNFREEZE,
            quantity_change=Decimal("0"),  # 总量不变
            available_change=quantity,
            frozen_change=-quantity,
            price=None,
            realized_pnl=None,
            source_type="ORDER",
            source_id=dto.order_id,
            changed_at=dto.freeze_at or datetime.now(),
        )
        
        return self._to_dto(position)
    
    # ========== 同步（从交易所/节点回报写入） ==========

    def sync_position_from_exchange(
        self,
        tenant_id: int,
        account_id: int,
        symbol: str,
        exchange: str,
        market_type: str,
        position_side: str,
        quantity: Decimal,
        avg_cost: Decimal,
        leverage: int = None,
        unrealized_pnl: Decimal = None,
        liquidation_price: Decimal = None,
    ) -> PositionDTO:
        """从交易所同步单条持仓到 fact_position（按 key 存在则更新）"""
        position, _ = self.position_repo.get_or_create(
            tenant_id=tenant_id,
            account_id=account_id,
            symbol=symbol,
            exchange=exchange,
            market_type=market_type,
            position_side=position_side,
        )
        position.quantity = quantity
        position.available = quantity
        position.frozen = Decimal("0")
        position.avg_cost = avg_cost
        position.total_cost = quantity * avg_cost
        position.status = "OPEN" if quantity > 0 else "CLOSED"
        # 合约附加字段（从交易所同步）
        if leverage is not None:
            position.leverage = leverage
        if unrealized_pnl is not None:
            position.unrealized_pnl = unrealized_pnl
        if liquidation_price is not None:
            position.liquidation_price = liquidation_price
        self.position_repo.update(position)
        return self._to_dto(position)
    
    # ========== 查询 ==========
    
    def get_position(
        self,
        tenant_id: int,
        account_id: int,
        symbol: str,
        exchange: str,
        position_side: str = "NONE",
    ) -> Optional[PositionDTO]:
        """获取单个持仓"""
        position = self.position_repo.get_by_key(
            tenant_id=tenant_id,
            account_id=account_id,
            symbol=symbol,
            exchange=exchange,
            position_side=position_side,
        )
        
        return self._to_dto(position) if position else None
    
    def get_position_by_id(
        self,
        position_id: str,
        tenant_id: int,
    ) -> Optional[PositionDTO]:
        """根据持仓ID获取"""
        position = self.position_repo.get_by_position_id(position_id, tenant_id)
        return self._to_dto(position) if position else None
    
    def list_positions(self, filter: PositionFilter) -> List[PositionDTO]:
        """查询持仓列表"""
        positions = self.position_repo.list_positions(filter)
        return [self._to_dto(p) for p in positions]
    
    def get_account_positions(
        self,
        tenant_id: int,
        account_id: int,
        has_position: bool = True,
    ) -> List[PositionDTO]:
        """获取账户所有持仓"""
        positions = self.position_repo.get_positions_by_account(
            tenant_id=tenant_id,
            account_id=account_id,
            has_position=has_position,
        )
        return [self._to_dto(p) for p in positions]
    
    def get_position_summary(
        self,
        tenant_id: int,
        account_id: int,
    ) -> PositionSummary:
        """获取持仓汇总"""
        positions = self.position_repo.get_positions_by_account(
            tenant_id=tenant_id,
            account_id=account_id,
            has_position=True,
        )
        
        summary = PositionSummary(
            tenant_id=tenant_id,
            account_id=account_id,
        )
        
        for p in positions:
            summary.total_positions += 1
            summary.total_quantity += float(p.quantity)
            summary.total_cost += float(p.total_cost)
            summary.total_realized_pnl += float(p.realized_pnl)
            
            if p.market_type == "spot":
                summary.spot_positions += 1
            else:
                summary.future_positions += 1
            
            if p.position_side == "LONG":
                summary.long_positions += 1
            elif p.position_side == "SHORT":
                summary.short_positions += 1
        
        return summary
    
    # ========== 变动历史 ==========
    
    def get_position_changes(
        self,
        position_id: str,
        tenant_id: int,
        limit: int = 100,
    ) -> List[PositionChangeDTO]:
        """获取持仓变动历史"""
        changes = self.change_repo.get_changes_by_position(
            position_id=position_id,
            tenant_id=tenant_id,
            limit=limit,
        )
        return [self._change_to_dto(c) for c in changes]
    
    def list_changes(self, filter: PositionChangeFilter) -> List[PositionChangeDTO]:
        """查询变动列表"""
        changes = self.change_repo.list_changes(filter)
        return [self._change_to_dto(c) for c in changes]
    
    def get_realized_pnl(
        self,
        tenant_id: int,
        account_id: Optional[int] = None,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> float:
        """汇总已实现盈亏"""
        result = self.change_repo.sum_realized_pnl(
            tenant_id=tenant_id,
            account_id=account_id,
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
        )
        return float(result)
    
    # ========== 校验 ==========
    
    def validate_position_invariants(
        self,
        tenant_id: int,
        account_id: int,
        symbol: str,
        exchange: str,
        position_side: str = "NONE",
    ) -> bool:
        """
        验证持仓不变量
        
        1. 可用 + 冻结 = 总持仓
        2. 数量 >= 0
        """
        position = self.position_repo.get_by_key(
            tenant_id=tenant_id,
            account_id=account_id,
            symbol=symbol,
            exchange=exchange,
            position_side=position_side,
        )
        
        if not position:
            return True  # 无持仓视为合法
        
        quantity = Decimal(str(position.quantity))
        available = Decimal(str(position.available))
        frozen = Decimal(str(position.frozen))
        
        # 不变量1：可用 + 冻结 = 总持仓
        if not PositionValidation.validate_available_frozen(quantity, available, frozen):
            raise PositionInvariantViolation(
                invariant="可用 + 冻结 = 总持仓",
                details=f"quantity={quantity}, available={available}, frozen={frozen}"
            )
        
        # 不变量2：数量非负
        if not PositionValidation.validate_quantity(quantity):
            raise PositionInvariantViolation(
                invariant="持仓数量 >= 0",
                details=f"quantity={quantity}"
            )
        
        return True
    
    # ========== 内部方法 ==========
    
    def _record_change(
        self,
        position: Position,
        change_type: ChangeType,
        quantity_change: Decimal,
        available_change: Decimal,
        frozen_change: Decimal,
        price: Optional[Decimal],
        realized_pnl: Optional[Decimal],
        source_type: str,
        source_id: Optional[str],
        changed_at: datetime,
        remark: Optional[str] = None,
    ) -> PositionChange:
        """记录持仓变动"""
        change = PositionChange(
            change_id=generate_change_id(),
            position_id=position.position_id,
            tenant_id=position.tenant_id,
            account_id=position.account_id,
            symbol=position.symbol,
            position_side=position.position_side,
            change_type=change_type.value,
            quantity_change=quantity_change,
            available_change=available_change,
            frozen_change=frozen_change,
            quantity_after=position.quantity,
            available_after=position.available,
            frozen_after=position.frozen,
            avg_cost_after=position.avg_cost,
            price=price,
            realized_pnl=realized_pnl,
            source_type=source_type,
            source_id=source_id,
            changed_at=changed_at,
            remark=remark,
        )
        
        return self.change_repo.create(change)
    
    def _to_dto(self, position: Position) -> PositionDTO:
        """模型转 DTO"""
        return PositionDTO(
            position_id=position.position_id,
            tenant_id=position.tenant_id,
            account_id=position.account_id,
            symbol=position.symbol,
            exchange=position.exchange,
            market_type=position.market_type,
            position_side=position.position_side,
            quantity=float(position.quantity) if position.quantity else 0,
            available=float(position.available) if position.available else 0,
            frozen=float(position.frozen) if position.frozen else 0,
            avg_cost=float(position.avg_cost) if position.avg_cost else 0,
            total_cost=float(position.total_cost) if position.total_cost else 0,
            realized_pnl=float(position.realized_pnl) if position.realized_pnl else 0,
            unrealized_pnl=float(position.unrealized_pnl) if position.unrealized_pnl else 0,
            leverage=position.leverage,
            margin=float(position.margin) if position.margin else None,
            liquidation_price=float(position.liquidation_price) if position.liquidation_price else None,
            status=position.status,
            opened_at=position.opened_at,
            closed_at=position.closed_at,
            created_at=position.created_at,
            updated_at=position.updated_at,
        )
    
    def _change_to_dto(self, change: PositionChange) -> PositionChangeDTO:
        """变动模型转 DTO"""
        return PositionChangeDTO(
            change_id=change.change_id,
            position_id=change.position_id,
            tenant_id=change.tenant_id,
            account_id=change.account_id,
            symbol=change.symbol,
            position_side=change.position_side,
            change_type=change.change_type,
            quantity_change=float(change.quantity_change) if change.quantity_change else 0,
            available_change=float(change.available_change) if change.available_change else 0,
            frozen_change=float(change.frozen_change) if change.frozen_change else 0,
            quantity_after=float(change.quantity_after) if change.quantity_after else 0,
            available_after=float(change.available_after) if change.available_after else 0,
            frozen_after=float(change.frozen_after) if change.frozen_after else 0,
            avg_cost_after=float(change.avg_cost_after) if change.avg_cost_after else 0,
            price=float(change.price) if change.price else None,
            realized_pnl=float(change.realized_pnl) if change.realized_pnl else None,
            source_type=change.source_type,
            source_id=change.source_id,
            changed_at=change.changed_at,
            created_at=change.created_at,
            remark=change.remark,
        )
