"""
Facts Repository - 事实层数据访问

提供对 Trade/Ledger/FreezeRecord/SignalEvent 的访问封装。
遵循 append-only 原则，主要是 INSERT 和 SELECT 操作。
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from libs.core import get_db, get_logger
from .models import Trade, Ledger, FreezeRecord, SignalEvent, AuditLog

logger = get_logger("facts-repository")


class FactsRepository:
    """
    事实层数据仓库
    
    Usage:
        repo = FactsRepository()
        repo.create_trade(...)
        
    或者使用 session：
        with get_db() as db:
            repo = FactsRepository(db)
            repo.create_trade(...)
    """
    
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._owns_session = session is None
    
    def _get_session(self) -> Session:
        if self._session is not None:
            return self._session
        from libs.core.database import get_session
        return get_session()
    
    # ==================== Trade ====================
    
    def create_trade(
        self,
        signal_id: str,
        task_id: str,
        account_id: int,
        user_id: int,
        symbol: str,
        side: str,
        trade_type: str,
        quantity: float,
        *,
        canonical_symbol: Optional[str] = None,
        exchange: Optional[str] = None,
        order_type: str = "MARKET",
        entry_price: Optional[float] = None,
        filled_price: Optional[float] = None,
        filled_quantity: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        fee: float = 0,
        fee_currency: Optional[str] = None,
        order_id: Optional[str] = None,
        exchange_order_id: Optional[str] = None,
        status: str = "pending",
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        strategy_code: Optional[str] = None,
        timeframe: Optional[str] = None,
        executed_at: Optional[datetime] = None,
        request_id: Optional[str] = None,
    ) -> Trade:
        """创建交易记录"""
        session = self._get_session()
        
        trade = Trade(
            signal_id=signal_id,
            task_id=task_id,
            account_id=account_id,
            user_id=user_id,
            symbol=symbol,
            canonical_symbol=canonical_symbol,
            exchange=exchange,
            side=side,
            trade_type=trade_type,
            order_type=order_type,
            entry_price=entry_price,
            filled_price=filled_price,
            quantity=quantity,
            filled_quantity=filled_quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            fee=fee,
            fee_currency=fee_currency,
            order_id=order_id,
            exchange_order_id=exchange_order_id,
            status=status,
            error_code=error_code,
            error_message=error_message,
            strategy_code=strategy_code,
            timeframe=timeframe,
            executed_at=executed_at,
            request_id=request_id,
        )
        
        session.add(trade)
        if self._owns_session:
            session.commit()
            session.refresh(trade)
        
        logger.info(
            "trade created",
            trade_id=trade.id,
            signal_id=signal_id,
            task_id=task_id,
            status=status,
        )
        
        return trade
    
    def get_trade_by_task_id(self, task_id: str) -> Optional[Trade]:
        """根据 task_id 获取交易记录"""
        session = self._get_session()
        return session.query(Trade).filter(Trade.task_id == task_id).first()
    
    def get_trades_by_signal_id(self, signal_id: str) -> List[Trade]:
        """根据 signal_id 获取所有交易记录"""
        session = self._get_session()
        return session.query(Trade).filter(Trade.signal_id == signal_id).order_by(Trade.created_at).all()
    
    def get_trades_by_account(self, account_id: int, limit: int = 100) -> List[Trade]:
        """获取账户的交易记录"""
        session = self._get_session()
        return session.query(Trade).filter(Trade.account_id == account_id).order_by(Trade.created_at.desc()).limit(limit).all()
    
    # ==================== Ledger ====================
    
    def create_ledger(
        self,
        account_id: int,
        user_id: int,
        ledger_type: str,
        amount: float,
        currency: str = "USDT",
        *,
        trade_id: Optional[int] = None,
        signal_id: Optional[str] = None,
        balance_before: Optional[float] = None,
        balance_after: Optional[float] = None,
        description: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Ledger:
        """创建账本流水"""
        session = self._get_session()
        
        ledger = Ledger(
            account_id=account_id,
            user_id=user_id,
            trade_id=trade_id,
            signal_id=signal_id,
            ledger_type=ledger_type,
            currency=currency,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            request_id=request_id,
        )
        
        session.add(ledger)
        if self._owns_session:
            session.commit()
            session.refresh(ledger)
        
        logger.info(
            "ledger created",
            ledger_id=ledger.id,
            account_id=account_id,
            ledger_type=ledger_type,
            amount=amount,
        )
        
        return ledger
    
    def get_ledgers_by_account(self, account_id: int, limit: int = 100) -> List[Ledger]:
        """获取账户的流水记录"""
        session = self._get_session()
        return session.query(Ledger).filter(Ledger.account_id == account_id).order_by(Ledger.created_at.desc()).limit(limit).all()
    
    def get_ledgers_by_signal_id(self, signal_id: str) -> List[Ledger]:
        """根据 signal_id 获取关联流水"""
        session = self._get_session()
        return session.query(Ledger).filter(Ledger.signal_id == signal_id).order_by(Ledger.created_at).all()
    
    # ==================== FreezeRecord ====================
    
    def create_freeze(
        self,
        account_id: int,
        user_id: int,
        freeze_type: str,
        amount: float,
        currency: str = "USDT",
        *,
        signal_id: Optional[str] = None,
        task_id: Optional[str] = None,
        reason: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> FreezeRecord:
        """创建冻结记录"""
        session = self._get_session()
        
        freeze = FreezeRecord(
            account_id=account_id,
            user_id=user_id,
            signal_id=signal_id,
            task_id=task_id,
            freeze_type=freeze_type,
            currency=currency,
            amount=amount,
            status="frozen",
            reason=reason,
            request_id=request_id,
        )
        
        session.add(freeze)
        if self._owns_session:
            session.commit()
            session.refresh(freeze)
        
        logger.info(
            "freeze created",
            freeze_id=freeze.id,
            account_id=account_id,
            amount=amount,
        )
        
        return freeze
    
    def release_freeze(self, freeze_id: int) -> Optional[FreezeRecord]:
        """释放冻结"""
        session = self._get_session()
        freeze = session.query(FreezeRecord).filter(FreezeRecord.id == freeze_id).first()
        if freeze and freeze.status == "frozen":
            freeze.status = "released"
            freeze.released_at = datetime.utcnow()
            if self._owns_session:
                session.commit()
            logger.info("freeze released", freeze_id=freeze_id)
        return freeze
    
    def get_active_freezes(self, account_id: int) -> List[FreezeRecord]:
        """获取账户的活跃冻结"""
        session = self._get_session()
        return session.query(FreezeRecord).filter(
            FreezeRecord.account_id == account_id,
            FreezeRecord.status == "frozen"
        ).all()
    
    # ==================== SignalEvent ====================
    
    def create_signal_event(
        self,
        signal_id: str,
        event_type: str,
        status: str,
        source_service: str,
        *,
        task_id: Optional[str] = None,
        account_id: Optional[int] = None,
        detail: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> SignalEvent:
        """创建信号事件"""
        session = self._get_session()
        
        event = SignalEvent(
            signal_id=signal_id,
            task_id=task_id,
            account_id=account_id,
            event_type=event_type,
            status=status,
            source_service=source_service,
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            error_code=error_code,
            error_message=error_message,
            request_id=request_id,
        )
        
        session.add(event)
        if self._owns_session:
            session.commit()
            session.refresh(event)
        
        logger.info(
            "signal event created",
            event_id=event.id,
            signal_id=signal_id,
            event_type=event_type,
            status=status,
        )
        
        return event
    
    def get_signal_events(self, signal_id: str) -> List[SignalEvent]:
        """获取信号的所有事件（链路追踪）"""
        session = self._get_session()
        return session.query(SignalEvent).filter(
            SignalEvent.signal_id == signal_id
        ).order_by(SignalEvent.created_at).all()
    
    def get_signal_timeline(self, signal_id: str) -> List[Dict[str, Any]]:
        """获取信号的完整时间线"""
        events = self.get_signal_events(signal_id)
        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "status": e.status,
                "source_service": e.source_service,
                "detail": json.loads(e.detail) if e.detail else None,
                "error_code": e.error_code,
                "error_message": e.error_message,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
    
    # ==================== 链路查询 ====================
    
    def get_full_signal_chain(self, signal_id: str) -> Dict[str, Any]:
        """
        获取信号的完整链路数据
        
        Returns:
            {
                "signal_id": "...",
                "events": [...],      # 状态事件
                "trades": [...],      # 交易记录
                "ledgers": [...],     # 账本流水
            }
        """
        return {
            "signal_id": signal_id,
            "events": self.get_signal_timeline(signal_id),
            "trades": [
                {
                    "id": t.id,
                    "task_id": t.task_id,
                    "symbol": t.symbol,
                    "side": t.side,
                    "trade_type": t.trade_type,
                    "quantity": float(t.quantity) if t.quantity else None,
                    "filled_price": float(t.filled_price) if t.filled_price else None,
                    "filled_quantity": float(t.filled_quantity) if t.filled_quantity else None,
                    "status": t.status,
                    "error_code": t.error_code,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "executed_at": t.executed_at.isoformat() if t.executed_at else None,
                }
                for t in self.get_trades_by_signal_id(signal_id)
            ],
            "ledgers": [
                {
                    "id": l.id,
                    "ledger_type": l.ledger_type,
                    "amount": float(l.amount) if l.amount else None,
                    "currency": l.currency,
                    "description": l.description,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in self.get_ledgers_by_signal_id(signal_id)
            ],
        }
    
    # ==================== AuditLog ====================
    
    def create_audit_log(
        self,
        action: str,
        source_service: str,
        *,
        signal_id: Optional[str] = None,
        task_id: Optional[str] = None,
        account_id: Optional[int] = None,
        user_id: Optional[int] = None,
        status_before: Optional[str] = None,
        status_after: Optional[str] = None,
        source_ip: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
        duration_ms: Optional[int] = None,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> AuditLog:
        """
        创建审计日志
        
        Args:
            action: 动作类型（使用 AuditAction 枚举）
            source_service: 来源服务
            signal_id: 信号ID
            task_id: 任务ID
            account_id: 账户ID
            status_before: 变更前状态
            status_after: 变更后状态
            success: 是否成功
            error_code: 错误码
            error_message: 错误信息
            retry_count: 重试次数
            duration_ms: 操作耗时
            request_id: 请求追踪ID
        """
        session = self._get_session()
        
        audit = AuditLog(
            signal_id=signal_id,
            task_id=task_id,
            account_id=account_id,
            user_id=user_id,
            action=action,
            status_before=status_before,
            status_after=status_after,
            source_service=source_service,
            source_ip=source_ip,
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            success=1 if success else 0,
            error_code=error_code,
            error_message=error_message,
            retry_count=retry_count,
            duration_ms=duration_ms,
            request_id=request_id,
            trace_id=trace_id,
        )
        
        session.add(audit)
        if self._owns_session:
            session.commit()
            session.refresh(audit)
        
        logger.info(
            "audit log created",
            audit_id=audit.id,
            action=action,
            signal_id=signal_id,
            task_id=task_id,
            success=success,
        )
        
        return audit
    
    def get_audit_logs_by_signal(self, signal_id: str, limit: int = 100) -> List[AuditLog]:
        """获取信号的所有审计日志"""
        session = self._get_session()
        return session.query(AuditLog).filter(
            AuditLog.signal_id == signal_id
        ).order_by(AuditLog.created_at).limit(limit).all()
    
    def get_audit_logs_by_task(self, task_id: str, limit: int = 100) -> List[AuditLog]:
        """获取任务的所有审计日志"""
        session = self._get_session()
        return session.query(AuditLog).filter(
            AuditLog.task_id == task_id
        ).order_by(AuditLog.created_at).limit(limit).all()
    
    def get_failed_audits(self, limit: int = 100) -> List[AuditLog]:
        """获取失败的审计记录（用于排查问题）"""
        session = self._get_session()
        return session.query(AuditLog).filter(
            AuditLog.success == 0
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    def get_audit_timeline(self, signal_id: str) -> List[Dict[str, Any]]:
        """获取信号的完整审计时间线"""
        audits = self.get_audit_logs_by_signal(signal_id)
        return [
            {
                "id": a.id,
                "action": a.action,
                "status_before": a.status_before,
                "status_after": a.status_after,
                "source_service": a.source_service,
                "success": a.success == 1,
                "error_code": a.error_code,
                "error_message": a.error_message,
                "retry_count": a.retry_count,
                "duration_ms": a.duration_ms,
                "detail": json.loads(a.detail) if a.detail else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in audits
        ]
    
    def get_full_signal_chain_with_audit(self, signal_id: str) -> Dict[str, Any]:
        """
        获取信号的完整链路数据（包含审计日志）
        """
        chain = self.get_full_signal_chain(signal_id)
        chain["audit_logs"] = self.get_audit_timeline(signal_id)
        return chain
    
    # ========== 统计查询方法（v1 Phase 4 风控增强）==========
    
    def count_trades_since(self, account_id: int, since: datetime) -> int:
        """统计指定时间以来的交易数"""
        session = self._get_session()
        return session.query(Trade).filter(
            Trade.account_id == account_id,
            Trade.created_at >= since,
        ).count()
    
    def sum_losses_since(self, account_id: int, since: datetime) -> float:
        """统计指定时间以来的总亏损（负收益）"""
        session = self._get_session()
        from sqlalchemy import func
        
        result = session.query(func.sum(Trade.realized_pnl)).filter(
            Trade.account_id == account_id,
            Trade.created_at >= since,
            Trade.realized_pnl < 0,  # 只统计亏损
        ).scalar()
        
        return abs(result) if result else 0.0
    
    def count_consecutive_losses(self, account_id: int, limit: int = 20) -> int:
        """
        统计连续亏损次数
        
        从最近的交易开始往前数，直到遇到盈利为止
        """
        session = self._get_session()
        recent_trades = session.query(Trade).filter(
            Trade.account_id == account_id,
            Trade.status == "filled",
            Trade.realized_pnl.isnot(None),
        ).order_by(Trade.created_at.desc()).limit(limit).all()
        
        consecutive = 0
        for trade in recent_trades:
            if trade.realized_pnl is not None and trade.realized_pnl < 0:
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def get_last_trade_time(self, account_id: int) -> Optional[datetime]:
        """获取最后一次交易时间"""
        session = self._get_session()
        trade = session.query(Trade).filter(
            Trade.account_id == account_id,
        ).order_by(Trade.created_at.desc()).first()
        
        return trade.created_at if trade else None
    
    def get_account_position_count(self, account_id: int) -> int:
        """获取账户当前持仓数量（未平仓）"""
        session = self._get_session()
        # 统计 trade_type='OPEN' 且没有对应 'CLOSE' 的记录
        # 简化：统计最近的 OPEN 类型交易（v0 简化实现）
        return session.query(Trade).filter(
            Trade.account_id == account_id,
            Trade.trade_type == "OPEN",
            Trade.status == "filled",
        ).count()
    
    def close(self):
        """关闭会话（如果是自己创建的）"""
        if self._owns_session and self._session is not None:
            self._session.close()
