"""
Ledger Module - 数据传输对象（DTOs）

定义 API 层面的数据契约
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List


@dataclass
class AccountDTO:
    """账户数据传输对象"""
    ledger_account_id: str
    tenant_id: int
    account_id: int
    currency: str
    balance: float
    available: float
    frozen: float
    total_deposit: float = 0
    total_withdraw: float = 0
    total_fee: float = 0
    realized_pnl: float = 0
    margin_used: float = 0
    status: str = "ACTIVE"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 计算字段
    unrealized_pnl: Optional[float] = None
    equity: Optional[float] = None


@dataclass
class TransactionDTO:
    """流水数据传输对象"""
    transaction_id: str
    ledger_account_id: str
    tenant_id: int
    account_id: int
    currency: str
    transaction_type: str
    amount: float
    fee: float
    balance_after: float
    available_after: float
    frozen_after: float
    source_type: str
    source_id: Optional[str] = None
    symbol: Optional[str] = None
    status: str = "COMPLETED"
    transaction_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    remark: Optional[str] = None


@dataclass
class EquitySnapshotDTO:
    """权益快照数据传输对象"""
    snapshot_id: str
    ledger_account_id: str
    tenant_id: int
    account_id: int
    currency: str
    balance: float
    unrealized_pnl: float
    equity: float
    position_value: float = 0
    margin_used: float = 0
    margin_ratio: Optional[float] = None
    net_value: Optional[float] = None
    daily_return: Optional[float] = None
    cumulative_return: Optional[float] = None
    snapshot_at: Optional[datetime] = None


@dataclass
class DepositDTO:
    """入金请求"""
    tenant_id: int
    account_id: int
    currency: str = "USDT"
    amount: Decimal = Decimal("0")
    
    # 来源
    source_id: Optional[str] = None  # 外部流水号
    
    # 时间
    deposit_at: Optional[datetime] = None
    
    # 备注
    remark: Optional[str] = None


@dataclass
class WithdrawDTO:
    """出金请求"""
    tenant_id: int
    account_id: int
    currency: str = "USDT"
    amount: Decimal = Decimal("0")
    
    # 来源
    source_id: Optional[str] = None
    
    # 时间
    withdraw_at: Optional[datetime] = None
    
    # 备注
    remark: Optional[str] = None


@dataclass
class TradeSettlementDTO:
    """
    交易结算请求（由成交驱动）
    
    处理买入扣款、卖出入账、手续费扣除
    """
    tenant_id: int
    account_id: int
    currency: str = "USDT"
    
    # 交易信息
    symbol: str = ""
    side: str = ""            # BUY/SELL
    quantity: Decimal = Decimal("0")
    price: Decimal = Decimal("0")
    
    # 费用
    fee: Decimal = Decimal("0")
    fee_currency: str = "USDT"
    
    # 已实现盈亏（平仓时）
    realized_pnl: Optional[Decimal] = None
    
    # 来源关联
    fill_id: Optional[str] = None
    order_id: Optional[str] = None
    
    # 时间
    settled_at: Optional[datetime] = None


@dataclass
class FreezeDTO:
    """冻结/解冻请求"""
    tenant_id: int
    account_id: int
    currency: str = "USDT"
    amount: Decimal = Decimal("0")
    
    # 来源
    order_id: Optional[str] = None
    
    # 时间
    freeze_at: Optional[datetime] = None


@dataclass
class AccountFilter:
    """账户查询过滤条件"""
    tenant_id: int                    # 必填：租户隔离
    account_id: Optional[int] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    
    # 分页
    limit: int = 100
    offset: int = 0


@dataclass
class TransactionFilter:
    """流水查询过滤条件"""
    tenant_id: int                    # 必填：租户隔离
    account_id: Optional[int] = None
    ledger_account_id: Optional[str] = None
    currency: Optional[str] = None
    transaction_type: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    symbol: Optional[str] = None
    
    # 时间范围
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # 分页
    limit: int = 100
    offset: int = 0


@dataclass
class AccountSummary:
    """账户汇总"""
    tenant_id: int
    account_id: int
    total_balance: float = 0          # 总余额（所有币种）
    total_available: float = 0        # 总可用
    total_frozen: float = 0           # 总冻结
    total_equity: float = 0           # 总权益
    total_deposit: float = 0          # 累计入金
    total_withdraw: float = 0         # 累计出金
    total_fee: float = 0              # 累计手续费
    total_realized_pnl: float = 0     # 累计已实现盈亏
    account_count: int = 0            # 账户数量
