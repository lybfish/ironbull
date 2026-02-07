"""
Ledger Module - 数据仓库层

封装数据库访问，提供 CRUD 操作，确保租户隔离
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from libs.ledger.models import Account, Transaction, EquitySnapshot
from libs.ledger.contracts import AccountFilter, TransactionFilter


def generate_ledger_account_id() -> str:
    """生成账本账户ID"""
    return f"ACCT-{uuid.uuid4().hex[:16].upper()}"


def generate_transaction_id() -> str:
    """生成流水ID"""
    return f"TXN-{uuid.uuid4().hex[:16].upper()}"


def generate_snapshot_id() -> str:
    """生成快照ID"""
    return f"SNAP-{uuid.uuid4().hex[:16].upper()}"


class AccountRepository:
    """账户仓库"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, account: Account) -> Account:
        """创建账户"""
        if not account.ledger_account_id:
            account.ledger_account_id = generate_ledger_account_id()
        
        self.session.add(account)
        self.session.flush()
        return account
    
    def get_by_ledger_account_id(
        self,
        ledger_account_id: str,
        tenant_id: int,
    ) -> Optional[Account]:
        """根据账本账户ID查询"""
        return self.session.query(Account).filter(
            and_(
                Account.ledger_account_id == ledger_account_id,
                Account.tenant_id == tenant_id,
            )
        ).first()
    
    def get_by_key(
        self,
        tenant_id: int,
        account_id: int,
        currency: str = "USDT",
    ) -> Optional[Account]:
        """根据唯一键查询账户"""
        return self.session.query(Account).filter(
            and_(
                Account.tenant_id == tenant_id,
                Account.account_id == account_id,
                Account.currency == currency,
            )
        ).first()
    
    def get_or_create(
        self,
        tenant_id: int,
        account_id: int,
        currency: str = "USDT",
    ) -> Tuple[Account, bool]:
        """获取或创建账户，返回 (account, is_new)"""
        account = self.get_by_key(
            tenant_id=tenant_id,
            account_id=account_id,
            currency=currency,
        )
        
        if account:
            return account, False
        
        # 创建新账户
        account = Account(
            ledger_account_id=generate_ledger_account_id(),
            tenant_id=tenant_id,
            account_id=account_id,
            currency=currency,
            balance=Decimal("0"),
            available=Decimal("0"),
            frozen=Decimal("0"),
            total_deposit=Decimal("0"),
            total_withdraw=Decimal("0"),
            total_fee=Decimal("0"),
            realized_pnl=Decimal("0"),
            margin_used=Decimal("0"),
            status="ACTIVE",
        )
        
        self.session.add(account)
        self.session.flush()
        return account, True
    
    def update(self, account: Account) -> Account:
        """更新账户"""
        account.updated_at = datetime.now()
        self.session.flush()
        return account
    
    def list_accounts(self, filter: AccountFilter) -> List[Account]:
        """查询账户列表"""
        query = self.session.query(Account).filter(
            Account.tenant_id == filter.tenant_id
        )
        
        if filter.account_id is not None:
            query = query.filter(Account.account_id == filter.account_id)
        
        if filter.currency:
            query = query.filter(Account.currency == filter.currency)
        
        if filter.status:
            query = query.filter(Account.status == filter.status)
        
        query = query.order_by(desc(Account.updated_at))
        query = query.limit(filter.limit).offset(filter.offset)
        
        return query.all()
    
    def get_accounts_by_trading_account(
        self,
        tenant_id: int,
        account_id: int,
    ) -> List[Account]:
        """获取交易账户下的所有币种账户"""
        return self.session.query(Account).filter(
            and_(
                Account.tenant_id == tenant_id,
                Account.account_id == account_id,
            )
        ).all()


class TransactionRepository:
    """流水仓库"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, transaction: Transaction) -> Transaction:
        """创建流水（append-only）"""
        if not transaction.transaction_id:
            transaction.transaction_id = generate_transaction_id()
        
        self.session.add(transaction)
        self.session.flush()
        return transaction
    
    def get_by_transaction_id(
        self,
        transaction_id: str,
        tenant_id: int,
    ) -> Optional[Transaction]:
        """根据流水ID查询"""
        return self.session.query(Transaction).filter(
            and_(
                Transaction.transaction_id == transaction_id,
                Transaction.tenant_id == tenant_id,
            )
        ).first()
    
    def get_by_source(
        self,
        source_type: str,
        source_id: str,
        tenant_id: int,
        transaction_type: str = None,
    ) -> Optional[Transaction]:
        """根据来源查询流水（用于幂等检查）"""
        query = self.session.query(Transaction).filter(
            and_(
                Transaction.source_type == source_type,
                Transaction.source_id == source_id,
                Transaction.tenant_id == tenant_id,
            )
        )
        
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        return query.first()
    
    def list_transactions(self, filter: TransactionFilter) -> List[Transaction]:
        """查询流水列表"""
        query = self.session.query(Transaction).filter(
            Transaction.tenant_id == filter.tenant_id
        )
        
        if filter.account_id is not None:
            query = query.filter(Transaction.account_id == filter.account_id)
        
        if filter.ledger_account_id:
            query = query.filter(Transaction.ledger_account_id == filter.ledger_account_id)
        
        if filter.currency:
            query = query.filter(Transaction.currency == filter.currency)
        
        if filter.transaction_type:
            query = query.filter(Transaction.transaction_type == filter.transaction_type)
        
        if filter.source_type:
            query = query.filter(Transaction.source_type == filter.source_type)
        
        if filter.source_id:
            query = query.filter(Transaction.source_id == filter.source_id)
        
        if filter.symbol:
            query = query.filter(Transaction.symbol == filter.symbol)
        
        if filter.start_time:
            query = query.filter(Transaction.transaction_at >= filter.start_time)
        
        if filter.end_time:
            query = query.filter(Transaction.transaction_at <= filter.end_time)
        
        query = query.order_by(desc(Transaction.transaction_at))
        query = query.limit(filter.limit).offset(filter.offset)
        
        return query.all()
    
    def get_transactions_by_account(
        self,
        ledger_account_id: str,
        tenant_id: int,
        limit: int = 100,
    ) -> List[Transaction]:
        """获取账户的流水历史"""
        return self.session.query(Transaction).filter(
            and_(
                Transaction.ledger_account_id == ledger_account_id,
                Transaction.tenant_id == tenant_id,
            )
        ).order_by(desc(Transaction.transaction_at)).limit(limit).all()
    
    def sum_by_type(
        self,
        tenant_id: int,
        account_id: Optional[int] = None,
        transaction_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Decimal:
        """按类型汇总金额"""
        query = self.session.query(
            func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.tenant_id == tenant_id
        )
        
        if account_id is not None:
            query = query.filter(Transaction.account_id == account_id)
        
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        if start_time:
            query = query.filter(Transaction.transaction_at >= start_time)
        
        if end_time:
            query = query.filter(Transaction.transaction_at <= end_time)
        
        result = query.scalar()
        return Decimal(str(result)) if result else Decimal("0")
    
    def sum_fees(
        self,
        tenant_id: int,
        account_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Decimal:
        """汇总手续费"""
        query = self.session.query(
            func.coalesce(func.sum(Transaction.fee), 0)
        ).filter(
            Transaction.tenant_id == tenant_id
        )
        
        if account_id is not None:
            query = query.filter(Transaction.account_id == account_id)
        
        if start_time:
            query = query.filter(Transaction.transaction_at >= start_time)
        
        if end_time:
            query = query.filter(Transaction.transaction_at <= end_time)
        
        result = query.scalar()
        return Decimal(str(result)) if result else Decimal("0")


class EquitySnapshotRepository:
    """权益快照仓库"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, snapshot: EquitySnapshot) -> EquitySnapshot:
        """创建快照"""
        if not snapshot.snapshot_id:
            snapshot.snapshot_id = generate_snapshot_id()
        
        self.session.add(snapshot)
        self.session.flush()
        return snapshot
    
    def get_latest(
        self,
        ledger_account_id: str,
        tenant_id: int,
    ) -> Optional[EquitySnapshot]:
        """获取最新快照"""
        return self.session.query(EquitySnapshot).filter(
            and_(
                EquitySnapshot.ledger_account_id == ledger_account_id,
                EquitySnapshot.tenant_id == tenant_id,
            )
        ).order_by(desc(EquitySnapshot.snapshot_at)).first()
    
    def get_by_time(
        self,
        ledger_account_id: str,
        tenant_id: int,
        snapshot_at: datetime,
    ) -> Optional[EquitySnapshot]:
        """获取指定时间的快照"""
        return self.session.query(EquitySnapshot).filter(
            and_(
                EquitySnapshot.ledger_account_id == ledger_account_id,
                EquitySnapshot.tenant_id == tenant_id,
                EquitySnapshot.snapshot_at == snapshot_at,
            )
        ).first()
    
    def list_snapshots(
        self,
        ledger_account_id: str,
        tenant_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[EquitySnapshot]:
        """获取快照列表"""
        query = self.session.query(EquitySnapshot).filter(
            and_(
                EquitySnapshot.ledger_account_id == ledger_account_id,
                EquitySnapshot.tenant_id == tenant_id,
            )
        )
        
        if start_time:
            query = query.filter(EquitySnapshot.snapshot_at >= start_time)
        
        if end_time:
            query = query.filter(EquitySnapshot.snapshot_at <= end_time)
        
        return query.order_by(desc(EquitySnapshot.snapshot_at)).limit(limit).all()
