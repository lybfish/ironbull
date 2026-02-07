"""
Trade Settlement Service - 交易结算服务

协调 OrderTrade、Position、Ledger 三个模块，实现交易闭环：
  成交(Fill) → 持仓更新(Position) → 资金结算(Ledger)

遵循 SaaS 蓝图的数据流向：
  OrderTrade → Position → Ledger

职责：
- 接收成交通知，触发持仓和资金更新
- 确保三个模块的一致性（同一事务）
- 提供幂等性保证（通过 fill_id 去重）
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session

from libs.core import get_logger
from libs.order_trade import (
    OrderTradeService,
    CreateOrderDTO,
    RecordFillDTO,
    OrderDTO,
    FillDTO,
)
from libs.position import (
    PositionService,
    UpdatePositionDTO,
    PositionDTO,
)
from libs.ledger import (
    LedgerService,
    TradeSettlementDTO,
    DepositDTO,
    AccountDTO,
)

logger = get_logger("settlement")


@dataclass
class SettlementResult:
    """结算结果"""
    success: bool
    fill_id: Optional[str] = None
    order_id: Optional[str] = None
    position_id: Optional[str] = None
    ledger_account_id: Optional[str] = None
    
    # 成交信息
    symbol: Optional[str] = None
    side: Optional[str] = None
    quantity: float = 0
    price: float = 0
    fee: float = 0
    
    # 持仓变化
    position_quantity_after: float = 0
    position_avg_cost: float = 0
    realized_pnl: float = 0
    
    # 资金变化
    balance_after: float = 0
    available_after: float = 0
    
    # 错误信息
    error: Optional[str] = None


class TradeSettlementService:
    """
    交易结算服务
    
    协调三个核心模块的数据更新，确保：
    1. 原子性：同一事务内完成所有更新
    2. 一致性：OrderTrade → Position → Ledger 顺序执行
    3. 幂等性：通过 fill_id 防止重复结算
    
    使用示例：
        with get_session() as session:
            settlement = TradeSettlementService(session, tenant_id=1, account_id=1)
            
            result = settlement.settle_fill(
                order_id="ORD-xxx",
                symbol="BTC/USDT",
                exchange="binance",
                side="BUY",
                quantity=0.1,
                price=50000,
                fee=5,
                exchange_trade_id="xxx",
            )
            
            session.commit()
    """
    
    def __init__(
        self,
        session: Session,
        tenant_id: int,
        account_id: int,
        currency: str = "USDT",
    ):
        self.session = session
        self.tenant_id = tenant_id
        self.account_id = account_id
        self.currency = currency
        
        # 初始化三个核心服务
        self.order_trade_service = OrderTradeService(session)
        self.position_service = PositionService(session)
        self.ledger_service = LedgerService(session)
    
    def settle_fill(
        self,
        order_id: str,
        symbol: str,
        exchange: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal = Decimal("0"),
        fee_currency: str = "USDT",
        exchange_trade_id: Optional[str] = None,
        filled_at: Optional[datetime] = None,
        position_side: str = "NONE",
        market_type: str = "spot",
    ) -> SettlementResult:
        """
        结算成交
        
        完整流程：
        1. 记录成交到 OrderTrade
        2. 更新持仓到 Position
        3. 结算资金到 Ledger
        
        Args:
            order_id: 订单ID
            symbol: 交易对
            exchange: 交易所
            side: 方向 (BUY/SELL)
            quantity: 成交数量
            price: 成交价格
            fee: 手续费
            fee_currency: 手续费币种
            exchange_trade_id: 交易所成交ID
            filled_at: 成交时间
            position_side: 持仓方向 (LONG/SHORT/NONE)
            market_type: 市场类型 (spot/future)
        
        Returns:
            SettlementResult: 结算结果
        """
        filled_at = filled_at or datetime.now()
        
        try:
            # 1. 记录成交到 OrderTrade
            fill = self._record_fill(
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                fee=fee,
                fee_currency=fee_currency,
                exchange_trade_id=exchange_trade_id,
                filled_at=filled_at,
            )
            
            if not fill:
                return SettlementResult(
                    success=False,
                    error="Failed to record fill",
                )
            
            # 2. 更新持仓到 Position
            position, realized_pnl = self._update_position(
                symbol=symbol,
                exchange=exchange,
                side=side,
                quantity=quantity,
                price=price,
                fill_id=fill.fill_id,
                filled_at=filled_at,
                position_side=position_side,
                market_type=market_type,
            )
            
            # 3. 结算资金到 Ledger
            account = self._settle_ledger(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                fee=fee,
                fee_currency=fee_currency,
                fill_id=fill.fill_id,
                realized_pnl=realized_pnl,
                filled_at=filled_at,
            )
            
            logger.info(
                "settlement completed",
                fill_id=fill.fill_id,
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=float(quantity),
                price=float(price),
                realized_pnl=float(realized_pnl) if realized_pnl else 0,
            )

            # 4. 盈利时扣点卡（30%）：仅当 account 对应平台用户且 realized_pnl > 0 时
            if realized_pnl is not None and realized_pnl > 0:
                self._deduct_point_card_for_profit(realized_pnl)
            
            return SettlementResult(
                success=True,
                fill_id=fill.fill_id,
                order_id=order_id,
                position_id=position.position_id if position else None,
                ledger_account_id=account.ledger_account_id if account else None,
                symbol=symbol,
                side=side,
                quantity=float(quantity),
                price=float(price),
                fee=float(fee),
                position_quantity_after=position.quantity if position else 0,
                position_avg_cost=position.avg_cost if position else 0,
                realized_pnl=float(realized_pnl) if realized_pnl else 0,
                balance_after=account.balance if account else 0,
                available_after=account.available if account else 0,
            )
            
        except Exception as e:
            logger.error("settlement failed", error=str(e), order_id=order_id)
            return SettlementResult(
                success=False,
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=float(quantity),
                price=float(price),
                error=str(e),
            )
    
    def _record_fill(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal,
        fee_currency: str,
        exchange_trade_id: Optional[str],
        filled_at: datetime,
    ) -> Optional[FillDTO]:
        """记录成交"""
        try:
            fill = self.order_trade_service.record_fill(RecordFillDTO(
                order_id=order_id,
                tenant_id=self.tenant_id,
                account_id=self.account_id,
                symbol=symbol,
                side=side.upper(),
                quantity=quantity,
                price=price,
                filled_at=filled_at,
                exchange_trade_id=exchange_trade_id,
                fee=fee,
                fee_currency=fee_currency,
            ))
            return fill
        except Exception as e:
            logger.warning("record fill failed", error=str(e))
            return None
    
    def _update_position(
        self,
        symbol: str,
        exchange: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        fill_id: str,
        filled_at: datetime,
        position_side: str,
        market_type: str,
    ) -> tuple[Optional[PositionDTO], Optional[Decimal]]:
        """更新持仓"""
        try:
            # 获取更新前的持仓成本（用于计算盈亏）
            old_position = self.position_service.get_position(
                tenant_id=self.tenant_id,
                account_id=self.account_id,
                symbol=symbol,
                exchange=exchange,
                position_side=position_side,
            )
            old_avg_cost = Decimal(str(old_position.avg_cost)) if old_position else Decimal("0")
            old_realized_pnl = Decimal(str(old_position.realized_pnl)) if old_position else Decimal("0")
            
            # 更新持仓
            position = self.position_service.update_position_by_fill(UpdatePositionDTO(
                tenant_id=self.tenant_id,
                account_id=self.account_id,
                symbol=symbol,
                exchange=exchange,
                market_type=market_type,
                position_side=position_side,
                side=side.upper(),
                quantity=quantity,
                price=price,
                fill_id=fill_id,
                filled_at=filled_at,
            ))
            
            # 计算本次变动的已实现盈亏
            new_realized_pnl = Decimal(str(position.realized_pnl))
            realized_pnl = new_realized_pnl - old_realized_pnl
            
            return position, realized_pnl
            
        except Exception as e:
            logger.warning("update position failed", error=str(e))
            return None, None
    
    def _settle_ledger(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal,
        fee_currency: str,
        fill_id: str,
        realized_pnl: Optional[Decimal],
        filled_at: datetime,
    ) -> Optional[AccountDTO]:
        """结算资金"""
        try:
            account = self.ledger_service.settle_trade(TradeSettlementDTO(
                tenant_id=self.tenant_id,
                account_id=self.account_id,
                currency=self.currency,
                symbol=symbol,
                side=side.upper(),
                quantity=quantity,
                price=price,
                fee=fee,
                fee_currency=fee_currency,
                realized_pnl=realized_pnl,
                fill_id=fill_id,
                settled_at=filled_at,
            ))
            return account
        except Exception as e:
            logger.warning("settle ledger failed", error=str(e))
            return None

    def _deduct_point_card_for_profit(self, realized_pnl: Decimal) -> None:
        """
        盈利时扣点卡 30%（自充进利润池，赠送销毁）。
        仅当 self.account_id 对应 fact_exchange_account 且能解析出 user_id 时执行。
        """
        try:
            from libs.member.models import ExchangeAccount
            from libs.pointcard.service import PointCardService
            acc = self.session.query(ExchangeAccount).filter(
                ExchangeAccount.id == self.account_id,
                ExchangeAccount.tenant_id == self.tenant_id,
                ExchangeAccount.status == 1,
            ).first()
            if not acc or not acc.user_id:
                return
            svc = PointCardService(self.session)
            ok, err, _ = svc.deduct_for_profit(acc.user_id, realized_pnl)
            if ok:
                logger.info(
                    "point_card deducted for profit",
                    user_id=acc.user_id,
                    profit=float(realized_pnl),
                )
            else:
                logger.warning("point_card deduct failed", user_id=acc.user_id, msg=err)
        except Exception as e:
            logger.warning("point_card deduct error", error=str(e))
    
    # ========== 便捷方法 ==========
    
    def create_order(
        self,
        symbol: str,
        exchange: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        signal_id: Optional[str] = None,
        position_side: str = "NONE",
        market_type: str = "spot",
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        leverage: Optional[int] = None,
        trade_type: Optional[str] = "OPEN",
        close_reason: Optional[str] = None,
    ) -> OrderDTO:
        """创建订单（委托前）"""
        return self.order_trade_service.create_order(CreateOrderDTO(
            tenant_id=self.tenant_id,
            account_id=self.account_id,
            symbol=symbol,
            exchange=exchange,
            side=side.upper(),
            order_type=order_type.upper(),
            quantity=quantity,
            price=price,
            signal_id=signal_id,
            position_side=position_side,
            market_type=market_type,
            stop_loss=float(stop_loss) if stop_loss is not None else None,
            take_profit=float(take_profit) if take_profit is not None else None,
            leverage=int(leverage) if leverage is not None else None,
            trade_type=trade_type or "OPEN",
            close_reason=close_reason,
        ))
    
    def submit_order(
        self,
        order_id: str,
        exchange_order_id: str,
    ) -> OrderDTO:
        """提交订单（委托后）"""
        return self.order_trade_service.submit_order(
            order_id=order_id,
            tenant_id=self.tenant_id,
            exchange_order_id=exchange_order_id,
            submitted_at=datetime.now(),
        )
    
    def fail_order(
        self,
        order_id: str,
        error_code: str,
        error_message: str,
    ) -> OrderDTO:
        """标记订单失败"""
        return self.order_trade_service.fail_order(
            order_id=order_id,
            tenant_id=self.tenant_id,
            error_code=error_code,
            error_message=error_message,
        )
    
    def deposit(
        self,
        amount: Decimal,
        source_id: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> AccountDTO:
        """入金"""
        return self.ledger_service.deposit(DepositDTO(
            tenant_id=self.tenant_id,
            account_id=self.account_id,
            currency=self.currency,
            amount=amount,
            source_id=source_id,
            remark=remark,
        ))
    
    def get_account(self) -> Optional[AccountDTO]:
        """获取账户"""
        return self.ledger_service.get_account(
            tenant_id=self.tenant_id,
            account_id=self.account_id,
            currency=self.currency,
        )
    
    def get_positions(self, has_position: bool = True):
        """获取持仓列表"""
        return self.position_service.get_account_positions(
            tenant_id=self.tenant_id,
            account_id=self.account_id,
            has_position=has_position,
        )
