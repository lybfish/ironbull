"""
Ledger Module - 状态定义与校验逻辑

定义交易类型、账户状态及校验规则
"""

from enum import Enum
from decimal import Decimal
from typing import Optional


class TransactionType(str, Enum):
    """交易/流水类型"""
    # 入金出金
    DEPOSIT = "DEPOSIT"          # 入金
    WITHDRAW = "WITHDRAW"        # 出金
    
    # 交易相关
    TRADE_BUY = "TRADE_BUY"      # 买入（扣款）
    TRADE_SELL = "TRADE_SELL"    # 卖出（入账）
    FEE = "FEE"                  # 手续费
    
    # 盈亏
    REALIZED_PNL = "REALIZED_PNL"    # 已实现盈亏
    FUNDING_FEE = "FUNDING_FEE"      # 资金费率（合约）
    
    # 冻结操作
    FREEZE = "FREEZE"            # 冻结
    UNFREEZE = "UNFREEZE"        # 解冻
    
    # 调整
    ADJUSTMENT = "ADJUSTMENT"    # 调账
    TRANSFER_IN = "TRANSFER_IN"  # 划转入
    TRANSFER_OUT = "TRANSFER_OUT"  # 划转出
    
    # 其他
    INTEREST = "INTEREST"        # 利息
    DIVIDEND = "DIVIDEND"        # 分红
    REBATE = "REBATE"            # 返佣


class TransactionStatus(str, Enum):
    """交易状态"""
    PENDING = "PENDING"          # 待处理
    COMPLETED = "COMPLETED"      # 已完成
    FAILED = "FAILED"            # 失败
    CANCELLED = "CANCELLED"      # 已取消
    REVERSED = "REVERSED"        # 已冲正


class AccountStatus(str, Enum):
    """账户状态"""
    ACTIVE = "ACTIVE"            # 活跃
    FROZEN = "FROZEN"            # 冻结（整个账户）
    CLOSED = "CLOSED"            # 已关闭


class LedgerValidation:
    """账务校验规则"""
    
    @staticmethod
    def validate_balance(balance: Decimal) -> bool:
        """验证余额非负"""
        return balance >= 0
    
    @staticmethod
    def validate_available_frozen(
        total: Decimal,
        available: Decimal,
        frozen: Decimal
    ) -> bool:
        """
        不变量：可用 + 冻结 = 总余额
        """
        return total == available + frozen
    
    @staticmethod
    def validate_withdraw_amount(
        withdraw_amount: Decimal,
        available: Decimal
    ) -> bool:
        """
        验证出金金额不超过可用余额
        """
        return withdraw_amount <= available
    
    @staticmethod
    def validate_freeze_amount(
        freeze_amount: Decimal,
        available: Decimal
    ) -> bool:
        """
        验证冻结金额不超过可用余额
        """
        return freeze_amount <= available
    
    @staticmethod
    def validate_unfreeze_amount(
        unfreeze_amount: Decimal,
        frozen: Decimal
    ) -> bool:
        """
        验证解冻金额不超过冻结金额
        """
        return unfreeze_amount <= frozen
    
    @staticmethod
    def calculate_equity(
        balance: Decimal,
        unrealized_pnl: Decimal = Decimal("0"),
    ) -> Decimal:
        """
        计算总权益
        
        权益 = 余额 + 未实现盈亏
        """
        return balance + unrealized_pnl
    
    @staticmethod
    def calculate_margin_ratio(
        equity: Decimal,
        margin_used: Decimal,
    ) -> Optional[Decimal]:
        """
        计算保证金率
        
        保证金率 = 权益 / 已用保证金
        """
        if margin_used == 0:
            return None
        return equity / margin_used
