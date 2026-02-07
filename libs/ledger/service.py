"""
Ledger Module - 业务服务层

实现资金账务管理的核心业务逻辑，确保不变量成立
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from libs.ledger.models import Account, Transaction, EquitySnapshot
from libs.ledger.states import (
    TransactionType,
    TransactionStatus,
    AccountStatus,
    LedgerValidation,
)
from libs.ledger.contracts import (
    AccountDTO,
    TransactionDTO,
    EquitySnapshotDTO,
    DepositDTO,
    WithdrawDTO,
    TradeSettlementDTO,
    FreezeDTO,
    AccountFilter,
    TransactionFilter,
    AccountSummary,
)
from libs.ledger.exceptions import (
    AccountNotFoundError,
    InsufficientBalanceError,
    InsufficientAvailableError,
    FreezeExceedsAvailableError,
    InvalidUnfreezeError,
    DuplicateTransactionError,
    InvalidTransactionError,
    LedgerInvariantViolation,
)
from libs.ledger.repository import (
    AccountRepository,
    TransactionRepository,
    EquitySnapshotRepository,
    generate_transaction_id,
    generate_snapshot_id,
)


class LedgerService:
    """
    账务服务
    
    核心职责：
    1. 入金/出金管理
    2. 交易结算（成交驱动的资金变动）
    3. 冻结/解冻管理
    4. 流水记录（append-only）
    5. 权益快照
    6. 维护不变量
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.account_repo = AccountRepository(session)
        self.transaction_repo = TransactionRepository(session)
        self.snapshot_repo = EquitySnapshotRepository(session)
    
    # ========== 入金/出金 ==========
    
    def deposit(self, dto: DepositDTO) -> AccountDTO:
        """
        入金
        
        增加可用余额，记录流水
        """
        if dto.amount <= 0:
            raise InvalidTransactionError("Deposit amount must be positive")
        
        # 幂等检查
        if dto.source_id:
            existing = self.transaction_repo.get_by_source(
                source_type="DEPOSIT",
                source_id=dto.source_id,
                tenant_id=dto.tenant_id,
            )
            if existing:
                account = self.account_repo.get_by_ledger_account_id(
                    existing.ledger_account_id, dto.tenant_id
                )
                if account:
                    return self._to_account_dto(account)
        
        # 获取或创建账户
        account, _ = self.account_repo.get_or_create(
            tenant_id=dto.tenant_id,
            account_id=dto.account_id,
            currency=dto.currency,
        )
        
        # 更新余额
        amount = dto.amount
        account.balance = Decimal(str(account.balance)) + amount
        account.available = Decimal(str(account.available)) + amount
        account.total_deposit = Decimal(str(account.total_deposit)) + amount
        
        self.account_repo.update(account)
        
        # 记录流水
        self._record_transaction(
            account=account,
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            fee=Decimal("0"),
            source_type="DEPOSIT",
            source_id=dto.source_id,
            transaction_at=dto.deposit_at or datetime.now(),
            remark=dto.remark,
        )
        
        return self._to_account_dto(account)
    
    def withdraw(self, dto: WithdrawDTO) -> AccountDTO:
        """
        出金
        
        减少可用余额，记录流水
        不变量：出金 ≤ 可用
        """
        if dto.amount <= 0:
            raise InvalidTransactionError("Withdraw amount must be positive")
        
        # 幂等检查
        if dto.source_id:
            existing = self.transaction_repo.get_by_source(
                source_type="WITHDRAW",
                source_id=dto.source_id,
                tenant_id=dto.tenant_id,
            )
            if existing:
                account = self.account_repo.get_by_ledger_account_id(
                    existing.ledger_account_id, dto.tenant_id
                )
                if account:
                    return self._to_account_dto(account)
        
        # 获取账户
        account = self.account_repo.get_by_key(
            tenant_id=dto.tenant_id,
            account_id=dto.account_id,
            currency=dto.currency,
        )
        
        if not account:
            raise AccountNotFoundError(
                tenant_id=dto.tenant_id,
                account_id=dto.account_id,
                currency=dto.currency,
            )
        
        amount = dto.amount
        available = Decimal(str(account.available))
        
        # 验证可用余额
        if not LedgerValidation.validate_withdraw_amount(amount, available):
            raise InsufficientAvailableError(
                required=float(amount),
                available=float(available),
                frozen=float(account.frozen),
                currency=dto.currency,
            )
        
        # 更新余额
        account.balance = Decimal(str(account.balance)) - amount
        account.available = available - amount
        account.total_withdraw = Decimal(str(account.total_withdraw)) + amount
        
        self.account_repo.update(account)
        
        # 记录流水
        self._record_transaction(
            account=account,
            transaction_type=TransactionType.WITHDRAW,
            amount=-amount,  # 出金为负
            fee=Decimal("0"),
            source_type="WITHDRAW",
            source_id=dto.source_id,
            transaction_at=dto.withdraw_at or datetime.now(),
            remark=dto.remark,
        )
        
        return self._to_account_dto(account)
    
    # ========== 交易结算 ==========
    
    def settle_trade(self, dto: TradeSettlementDTO) -> AccountDTO:
        """
        交易结算（由成交驱动）
        
        - 买入：扣款 = 数量 * 价格 + 手续费
        - 卖出：入账 = 数量 * 价格 - 手续费
        
        不变量：
        - 买入扣款 ≤ 可用余额
        - 手续费必须记录
        """
        if not dto.fill_id:
            raise InvalidTransactionError("Fill ID is required for trade settlement")
        
        # 幂等检查
        existing = self.transaction_repo.get_by_source(
            source_type="FILL",
            source_id=dto.fill_id,
            tenant_id=dto.tenant_id,
        )
        if existing:
            account = self.account_repo.get_by_ledger_account_id(
                existing.ledger_account_id, dto.tenant_id
            )
            if account:
                return self._to_account_dto(account)
        
        # 获取或创建账户
        account, _ = self.account_repo.get_or_create(
            tenant_id=dto.tenant_id,
            account_id=dto.account_id,
            currency=dto.currency,
        )
        
        # 计算交易金额
        trade_value = dto.quantity * dto.price
        fee = dto.fee
        is_buy = dto.side.upper() == "BUY"
        
        if is_buy:
            # 买入扣款
            total_deduct = trade_value + fee
            available = Decimal(str(account.available))
            
            if total_deduct > available:
                raise InsufficientAvailableError(
                    required=float(total_deduct),
                    available=float(available),
                    frozen=float(account.frozen),
                    currency=dto.currency,
                )
            
            # 更新余额
            account.balance = Decimal(str(account.balance)) - total_deduct
            account.available = available - total_deduct
            account.total_fee = Decimal(str(account.total_fee)) + fee
            
            transaction_type = TransactionType.TRADE_BUY
            amount = -trade_value
        else:
            # 卖出入账
            net_income = trade_value - fee
            
            # 更新余额
            account.balance = Decimal(str(account.balance)) + net_income
            account.available = Decimal(str(account.available)) + net_income
            account.total_fee = Decimal(str(account.total_fee)) + fee
            
            transaction_type = TransactionType.TRADE_SELL
            amount = trade_value
        
        # 记录已实现盈亏
        if dto.realized_pnl is not None:
            account.realized_pnl = Decimal(str(account.realized_pnl)) + dto.realized_pnl
        
        self.account_repo.update(account)
        
        # 记录流水
        self._record_transaction(
            account=account,
            transaction_type=transaction_type,
            amount=amount,
            fee=fee,
            source_type="FILL",
            source_id=dto.fill_id,
            symbol=dto.symbol,
            transaction_at=dto.settled_at or datetime.now(),
        )
        
        return self._to_account_dto(account)
    
    # ========== 冻结/解冻 ==========
    
    def freeze(self, dto: FreezeDTO) -> AccountDTO:
        """
        冻结资金（下单时锁定）
        
        不变量：冻结 ≤ 可用
        """
        if dto.amount <= 0:
            raise InvalidTransactionError("Freeze amount must be positive")
        
        account = self.account_repo.get_by_key(
            tenant_id=dto.tenant_id,
            account_id=dto.account_id,
            currency=dto.currency,
        )
        
        if not account:
            raise AccountNotFoundError(
                tenant_id=dto.tenant_id,
                account_id=dto.account_id,
                currency=dto.currency,
            )
        
        amount = dto.amount
        available = Decimal(str(account.available))
        
        if not LedgerValidation.validate_freeze_amount(amount, available):
            raise FreezeExceedsAvailableError(
                freeze_amount=float(amount),
                available=float(available),
                currency=dto.currency,
            )
        
        # 更新余额
        account.available = available - amount
        account.frozen = Decimal(str(account.frozen)) + amount
        
        self.account_repo.update(account)
        
        # 记录流水
        self._record_transaction(
            account=account,
            transaction_type=TransactionType.FREEZE,
            amount=Decimal("0"),  # 冻结不改变总余额
            fee=Decimal("0"),
            source_type="ORDER",
            source_id=dto.order_id,
            transaction_at=dto.freeze_at or datetime.now(),
        )
        
        return self._to_account_dto(account)
    
    def unfreeze(self, dto: FreezeDTO) -> AccountDTO:
        """
        解冻资金（撤单或成交后释放）
        
        不变量：解冻 ≤ 冻结
        """
        if dto.amount <= 0:
            raise InvalidTransactionError("Unfreeze amount must be positive")
        
        account = self.account_repo.get_by_key(
            tenant_id=dto.tenant_id,
            account_id=dto.account_id,
            currency=dto.currency,
        )
        
        if not account:
            raise AccountNotFoundError(
                tenant_id=dto.tenant_id,
                account_id=dto.account_id,
                currency=dto.currency,
            )
        
        amount = dto.amount
        frozen = Decimal(str(account.frozen))
        
        if not LedgerValidation.validate_unfreeze_amount(amount, frozen):
            raise InvalidUnfreezeError(
                unfreeze_amount=float(amount),
                frozen=float(frozen),
                currency=dto.currency,
            )
        
        # 更新余额
        account.available = Decimal(str(account.available)) + amount
        account.frozen = frozen - amount
        
        self.account_repo.update(account)
        
        # 记录流水
        self._record_transaction(
            account=account,
            transaction_type=TransactionType.UNFREEZE,
            amount=Decimal("0"),  # 解冻不改变总余额
            fee=Decimal("0"),
            source_type="ORDER",
            source_id=dto.order_id,
            transaction_at=dto.freeze_at or datetime.now(),
        )
        
        return self._to_account_dto(account)
    
    # ========== 查询 ==========
    
    def get_account(
        self,
        tenant_id: int,
        account_id: int,
        currency: str = "USDT",
    ) -> Optional[AccountDTO]:
        """获取账户"""
        account = self.account_repo.get_by_key(
            tenant_id=tenant_id,
            account_id=account_id,
            currency=currency,
        )
        return self._to_account_dto(account) if account else None
    
    def get_or_create_account(
        self,
        tenant_id: int,
        account_id: int,
        currency: str = "USDT",
    ) -> AccountDTO:
        """获取或创建账户"""
        account, _ = self.account_repo.get_or_create(
            tenant_id=tenant_id,
            account_id=account_id,
            currency=currency,
        )
        return self._to_account_dto(account)

    def sync_balance_from_exchange(
        self,
        tenant_id: int,
        account_id: int,
        currency: str,
        balance: Decimal,
        available: Decimal,
        frozen: Decimal,
    ) -> AccountDTO:
        """从交易所同步余额到 fact_account（仅更新 balance/available/frozen 快照）"""
        account, _ = self.account_repo.get_or_create(
            tenant_id=tenant_id,
            account_id=account_id,
            currency=currency,
        )
        account.balance = balance
        account.available = available
        account.frozen = frozen
        self.account_repo.update(account)
        return self._to_account_dto(account)
    
    def list_accounts(self, filter: AccountFilter) -> List[AccountDTO]:
        """查询账户列表"""
        accounts = self.account_repo.list_accounts(filter)
        return [self._to_account_dto(a) for a in accounts]
    
    def get_account_summary(
        self,
        tenant_id: int,
        account_id: int,
    ) -> AccountSummary:
        """获取账户汇总"""
        accounts = self.account_repo.get_accounts_by_trading_account(
            tenant_id=tenant_id,
            account_id=account_id,
        )
        
        summary = AccountSummary(
            tenant_id=tenant_id,
            account_id=account_id,
        )
        
        for a in accounts:
            summary.total_balance += float(a.balance)
            summary.total_available += float(a.available)
            summary.total_frozen += float(a.frozen)
            summary.total_deposit += float(a.total_deposit)
            summary.total_withdraw += float(a.total_withdraw)
            summary.total_fee += float(a.total_fee)
            summary.total_realized_pnl += float(a.realized_pnl)
            summary.account_count += 1
        
        return summary
    
    # ========== 流水查询 ==========
    
    def get_transactions(
        self,
        tenant_id: int,
        account_id: int,
        currency: str = "USDT",
        limit: int = 100,
    ) -> List[TransactionDTO]:
        """获取账户流水"""
        account = self.account_repo.get_by_key(
            tenant_id=tenant_id,
            account_id=account_id,
            currency=currency,
        )
        
        if not account:
            return []
        
        transactions = self.transaction_repo.get_transactions_by_account(
            ledger_account_id=account.ledger_account_id,
            tenant_id=tenant_id,
            limit=limit,
        )
        
        return [self._to_transaction_dto(t) for t in transactions]
    
    def list_transactions(self, filter: TransactionFilter) -> List[TransactionDTO]:
        """查询流水列表"""
        transactions = self.transaction_repo.list_transactions(filter)
        return [self._to_transaction_dto(t) for t in transactions]
    
    # ========== 权益快照 ==========
    
    def create_equity_snapshot(
        self,
        tenant_id: int,
        account_id: int,
        currency: str = "USDT",
        unrealized_pnl: Decimal = Decimal("0"),
        position_value: Decimal = Decimal("0"),
        snapshot_at: Optional[datetime] = None,
    ) -> EquitySnapshotDTO:
        """创建权益快照"""
        account = self.account_repo.get_by_key(
            tenant_id=tenant_id,
            account_id=account_id,
            currency=currency,
        )
        
        if not account:
            raise AccountNotFoundError(
                tenant_id=tenant_id,
                account_id=account_id,
                currency=currency,
            )
        
        balance = Decimal(str(account.balance))
        equity = LedgerValidation.calculate_equity(balance, unrealized_pnl)
        margin_used = Decimal(str(account.margin_used))
        margin_ratio = LedgerValidation.calculate_margin_ratio(equity, margin_used)
        
        # 计算收益率
        prev_snapshot = self.snapshot_repo.get_latest(
            ledger_account_id=account.ledger_account_id,
            tenant_id=tenant_id,
        )
        
        daily_return = None
        cumulative_return = None
        net_value = None
        
        if prev_snapshot:
            prev_equity = Decimal(str(prev_snapshot.equity))
            if prev_equity > 0:
                daily_return = (equity - prev_equity) / prev_equity
            
            # 累计收益率基于初始入金
            if account.total_deposit > 0:
                cumulative_return = (equity - Decimal(str(account.total_deposit))) / Decimal(str(account.total_deposit))
        
        # 单位净值
        if account.total_deposit > 0:
            net_value = equity / Decimal(str(account.total_deposit))
        
        snapshot = EquitySnapshot(
            snapshot_id=generate_snapshot_id(),
            ledger_account_id=account.ledger_account_id,
            tenant_id=tenant_id,
            account_id=account_id,
            currency=currency,
            balance=balance,
            unrealized_pnl=unrealized_pnl,
            equity=equity,
            position_value=position_value,
            margin_used=margin_used,
            margin_ratio=margin_ratio,
            net_value=net_value,
            daily_return=daily_return,
            cumulative_return=cumulative_return,
            snapshot_at=snapshot_at or datetime.now(),
        )
        
        self.snapshot_repo.create(snapshot)
        return self._to_snapshot_dto(snapshot)
    
    def get_latest_snapshot(
        self,
        tenant_id: int,
        account_id: int,
        currency: str = "USDT",
    ) -> Optional[EquitySnapshotDTO]:
        """获取最新权益快照"""
        account = self.account_repo.get_by_key(
            tenant_id=tenant_id,
            account_id=account_id,
            currency=currency,
        )
        
        if not account:
            return None
        
        snapshot = self.snapshot_repo.get_latest(
            ledger_account_id=account.ledger_account_id,
            tenant_id=tenant_id,
        )
        
        return self._to_snapshot_dto(snapshot) if snapshot else None
    
    # ========== 校验 ==========
    
    def validate_account_invariants(
        self,
        tenant_id: int,
        account_id: int,
        currency: str = "USDT",
    ) -> bool:
        """
        验证账户不变量
        
        可用 + 冻结 = 总余额
        """
        account = self.account_repo.get_by_key(
            tenant_id=tenant_id,
            account_id=account_id,
            currency=currency,
        )
        
        if not account:
            return True
        
        balance = Decimal(str(account.balance))
        available = Decimal(str(account.available))
        frozen = Decimal(str(account.frozen))
        
        if not LedgerValidation.validate_available_frozen(balance, available, frozen):
            raise LedgerInvariantViolation(
                invariant="可用 + 冻结 = 总余额",
                details=f"balance={balance}, available={available}, frozen={frozen}"
            )
        
        return True
    
    # ========== 内部方法 ==========
    
    def _record_transaction(
        self,
        account: Account,
        transaction_type: TransactionType,
        amount: Decimal,
        fee: Decimal,
        source_type: str,
        source_id: Optional[str],
        symbol: Optional[str] = None,
        transaction_at: datetime = None,
        remark: Optional[str] = None,
    ) -> Transaction:
        """记录流水"""
        transaction = Transaction(
            transaction_id=generate_transaction_id(),
            ledger_account_id=account.ledger_account_id,
            tenant_id=account.tenant_id,
            account_id=account.account_id,
            currency=account.currency,
            transaction_type=transaction_type.value,
            amount=amount,
            fee=fee,
            balance_after=account.balance,
            available_after=account.available,
            frozen_after=account.frozen,
            source_type=source_type,
            source_id=source_id,
            symbol=symbol,
            status=TransactionStatus.COMPLETED.value,
            transaction_at=transaction_at or datetime.now(),
            remark=remark,
        )
        
        return self.transaction_repo.create(transaction)
    
    def _to_account_dto(self, account: Account) -> AccountDTO:
        """模型转 DTO"""
        return AccountDTO(
            ledger_account_id=account.ledger_account_id,
            tenant_id=account.tenant_id,
            account_id=account.account_id,
            currency=account.currency,
            balance=float(account.balance) if account.balance else 0,
            available=float(account.available) if account.available else 0,
            frozen=float(account.frozen) if account.frozen else 0,
            total_deposit=float(account.total_deposit) if account.total_deposit else 0,
            total_withdraw=float(account.total_withdraw) if account.total_withdraw else 0,
            total_fee=float(account.total_fee) if account.total_fee else 0,
            realized_pnl=float(account.realized_pnl) if account.realized_pnl else 0,
            margin_used=float(account.margin_used) if account.margin_used else 0,
            status=account.status,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )
    
    def _to_transaction_dto(self, transaction: Transaction) -> TransactionDTO:
        """流水模型转 DTO"""
        return TransactionDTO(
            transaction_id=transaction.transaction_id,
            ledger_account_id=transaction.ledger_account_id,
            tenant_id=transaction.tenant_id,
            account_id=transaction.account_id,
            currency=transaction.currency,
            transaction_type=transaction.transaction_type,
            amount=float(transaction.amount) if transaction.amount else 0,
            fee=float(transaction.fee) if transaction.fee else 0,
            balance_after=float(transaction.balance_after) if transaction.balance_after else 0,
            available_after=float(transaction.available_after) if transaction.available_after else 0,
            frozen_after=float(transaction.frozen_after) if transaction.frozen_after else 0,
            source_type=transaction.source_type,
            source_id=transaction.source_id,
            symbol=transaction.symbol,
            status=transaction.status,
            transaction_at=transaction.transaction_at,
            created_at=transaction.created_at,
            remark=transaction.remark,
        )
    
    def _to_snapshot_dto(self, snapshot: EquitySnapshot) -> EquitySnapshotDTO:
        """快照模型转 DTO"""
        return EquitySnapshotDTO(
            snapshot_id=snapshot.snapshot_id,
            ledger_account_id=snapshot.ledger_account_id,
            tenant_id=snapshot.tenant_id,
            account_id=snapshot.account_id,
            currency=snapshot.currency,
            balance=float(snapshot.balance) if snapshot.balance else 0,
            unrealized_pnl=float(snapshot.unrealized_pnl) if snapshot.unrealized_pnl else 0,
            equity=float(snapshot.equity) if snapshot.equity else 0,
            position_value=float(snapshot.position_value) if snapshot.position_value else 0,
            margin_used=float(snapshot.margin_used) if snapshot.margin_used else 0,
            margin_ratio=float(snapshot.margin_ratio) if snapshot.margin_ratio else None,
            net_value=float(snapshot.net_value) if snapshot.net_value else None,
            daily_return=float(snapshot.daily_return) if snapshot.daily_return else None,
            cumulative_return=float(snapshot.cumulative_return) if snapshot.cumulative_return else None,
            snapshot_at=snapshot.snapshot_at,
        )
