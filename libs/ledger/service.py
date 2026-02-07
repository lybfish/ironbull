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
        unrealized_pnl: Decimal = Decimal("0"),
        margin_used: Decimal = Decimal("0"),
        margin_ratio: Decimal = Decimal("0"),
        equity: Decimal = Decimal("0"),
    ) -> AccountDTO:
        """
        从交易所同步余额到 fact_account。
        
        除了更新余额/可用/冻结快照，还更新合约扩展字段（未实现盈亏、保证金、权益）。
        
        入金/出金检测逻辑（v2）：
        - 用 synced_balance（上次交易所同步余额）而非 balance（会被 settle_trade 修改）做对比
        - 两次同步之间的余额差 = 已知交易活动（已实现盈亏 + 手续费）+ 未知变动（真实入金/出金）
        - 查询两次同步之间的 FILL 流水，得到已知的余额变动
        - 只将"无法解释的差额"（> 1 USDT）记为入金/出金
        """
        account, created = self.account_repo.get_or_create(
            tenant_id=tenant_id,
            account_id=account_id,
            currency=currency,
        )
        
        # 用 synced_balance 做对比（不受 settle_trade 干扰）
        last_synced = Decimal(str(account.synced_balance or 0))
        raw_diff = balance - last_synced
        
        # 更新余额快照 + 合约扩展字段
        account.balance = balance
        account.available = available
        account.frozen = frozen
        account.synced_balance = balance  # 更新同步余额
        # 合约扩展字段（每次同步都从交易所覆盖）
        account.margin_used = margin_used
        account.unrealized_pnl = unrealized_pnl
        account.equity = equity if equity else balance + unrealized_pnl
        account.margin_ratio = margin_ratio
        
        # 首次创建账户且有余额 → 视为初始入金
        if created and balance > Decimal("0.01"):
            account.total_deposit = Decimal(str(account.total_deposit or 0)) + balance
            self.account_repo.update(account)
            self._record_transaction(
                account=account,
                transaction_type=TransactionType.DEPOSIT,
                amount=balance,
                fee=Decimal("0"),
                source_type="SYNC",
                source_id=None,
                transaction_at=datetime.now(),
                remark="交易所余额初始同步",
            )
            return self._to_account_dto(account)
        
        # 计算已知的交易活动导致的余额变化（排除入金/出金/同步类型的流水）
        explained_change = self._calc_explained_balance_change(account)
        
        # 未解释的差额 = 总差额 - 已知交易活动
        unexplained = raw_diff - explained_change
        
        # 阈值：1 USDT（避免资金费率、精度误差等小额波动误判）
        TRANSFER_THRESHOLD = Decimal("1.0")
        
        if abs(unexplained) > TRANSFER_THRESHOLD:
            if unexplained > 0:
                # 无法解释的余额增加 → 可能是外部入金
                account.total_deposit = Decimal(str(account.total_deposit or 0)) + unexplained
                self.account_repo.update(account)
                self._record_transaction(
                    account=account,
                    transaction_type=TransactionType.DEPOSIT,
                    amount=unexplained,
                    fee=Decimal("0"),
                    source_type="SYNC",
                    source_id=None,
                    transaction_at=datetime.now(),
                    remark=f"交易所同步检测入金 +{float(unexplained):.4f}"
                           f"（总差额{float(raw_diff):+.4f}，已知交易{float(explained_change):+.4f}）",
                )
            else:
                # 无法解释的余额减少 → 可能是外部出金
                withdraw_amount = abs(unexplained)
                account.total_withdraw = Decimal(str(account.total_withdraw or 0)) + withdraw_amount
                self.account_repo.update(account)
                self._record_transaction(
                    account=account,
                    transaction_type=TransactionType.WITHDRAW,
                    amount=-withdraw_amount,
                    fee=Decimal("0"),
                    source_type="SYNC",
                    source_id=None,
                    transaction_at=datetime.now(),
                    remark=f"交易所同步检测出金 -{float(withdraw_amount):.4f}"
                           f"（总差额{float(raw_diff):+.4f}，已知交易{float(explained_change):+.4f}）",
                )
        else:
            self.account_repo.update(account)
        
        return self._to_account_dto(account)
    
    def _calc_explained_balance_change(self, account) -> Decimal:
        """
        计算上次同步以来、由已知交易活动导致的交易所余额变化。
        
        对于合约交易所，钱包余额的变化来自：
        - 已实现盈亏（平仓盈利/亏损）
        - 手续费（交易手续费）
        - 资金费率（合约 funding fee）
        
        注意：settle_trade 用现货逻辑记账（扣/加全额），与交易所真实余额变化不同。
        因此这里查询 fact_fill 的手续费 + fact_position 的已实现盈亏变化来估算。
        
        简化方案：查最近的 fill 手续费总和。已实现盈亏较难准确追踪，
        依赖 synced_balance 的 diff + 阈值过滤来兜底。
        """
        try:
            from sqlalchemy import func
            from libs.order_trade.models import Fill
            
            # 查询该账户自上次更新以来的成交手续费总和
            result = self.session.query(
                func.coalesce(func.sum(Fill.fee), 0),
            ).filter(
                Fill.account_id == account.account_id,
                Fill.tenant_id == account.tenant_id,
                Fill.created_at >= account.updated_at,
            ).scalar()
            
            total_fee = Decimal(str(result or 0))
            # 手续费会减少交易所余额
            return -total_fee
        except Exception:
            return Decimal("0")
    
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
        _balance = float(account.balance) if account.balance else 0
        _unrealized = float(account.unrealized_pnl) if getattr(account, 'unrealized_pnl', None) else 0
        _equity = float(account.equity) if getattr(account, 'equity', None) else _balance + _unrealized
        return AccountDTO(
            ledger_account_id=account.ledger_account_id,
            tenant_id=account.tenant_id,
            account_id=account.account_id,
            currency=account.currency,
            balance=_balance,
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
            unrealized_pnl=_unrealized,
            equity=_equity,
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
