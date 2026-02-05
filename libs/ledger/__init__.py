"""
Ledger Module - 资金/权益/账务管理模块

职责：
- 资金账户的余额管理（可用、冻结、总权益）
- 资金变动的记账（入金、出金、成交扣款、手续费等）
- 权益快照的定时/事件触发计算
- 费用的计提与扣减
- 提供账务流水查询与对账能力
- 支持多币种、多账户的账务隔离

不变量：
1. 资金守恒：可用 + 冻结 = 总余额
2. 流水可追溯：任一余额变动必须有对应的账务流水
3. 费用不遗漏：每笔成交的手续费必须在账务中体现
4. 租户隔离：跨租户不可见
5. 不可逆变更留痕：调账必须保留原始记录
"""

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
)
from libs.ledger.exceptions import (
    LedgerError,
    AccountNotFoundError,
    InsufficientBalanceError,
    InsufficientAvailableError,
    FreezeExceedsAvailableError,
    InvalidUnfreezeError,
    DuplicateTransactionError,
    TenantMismatchError,
    InvalidTransactionError,
    AccountAlreadyExistsError,
)
from libs.ledger.repository import (
    AccountRepository,
    TransactionRepository,
    EquitySnapshotRepository,
)
from libs.ledger.service import LedgerService

__all__ = [
    # Models
    "Account",
    "Transaction",
    "EquitySnapshot",
    # States
    "TransactionType",
    "TransactionStatus",
    "AccountStatus",
    "LedgerValidation",
    # Contracts (DTOs)
    "AccountDTO",
    "TransactionDTO",
    "EquitySnapshotDTO",
    "DepositDTO",
    "WithdrawDTO",
    "TradeSettlementDTO",
    "FreezeDTO",
    "AccountFilter",
    "TransactionFilter",
    # Exceptions
    "LedgerError",
    "AccountNotFoundError",
    "InsufficientBalanceError",
    "InsufficientAvailableError",
    "FreezeExceedsAvailableError",
    "InvalidUnfreezeError",
    "DuplicateTransactionError",
    "TenantMismatchError",
    "InvalidTransactionError",
    "AccountAlreadyExistsError",
    # Repository
    "AccountRepository",
    "TransactionRepository",
    "EquitySnapshotRepository",
    # Service
    "LedgerService",
]
