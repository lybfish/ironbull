"""
Withdrawal Service - 提现申请

审核/打款由后台触发，此处仅实现申请与查询。
"""

from decimal import Decimal
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from libs.member.repository import MemberRepository
from .models import UserWithdrawal
from .repository import RewardRepository

MIN_WITHDRAW = Decimal("50")
FEE_RATE = Decimal("0.05")


class WithdrawalService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RewardRepository(db)
        self.member_repo = MemberRepository(db)

    def apply(
        self,
        user_id: int,
        tenant_id: int,
        amount: Decimal,
        wallet_address: str,
        wallet_network: str = "TRC20",
        remark: Optional[str] = None,
    ) -> Tuple[Optional[UserWithdrawal], str]:
        """
        申请提现。最低 50 USDT，手续费 5%。
        返回 (withdrawal, error_msg)
        """
        if amount < MIN_WITHDRAW:
            return None, f"最低提现金额为 {MIN_WITHDRAW} USDT"
        user = self.member_repo.get_user_by_id(user_id, tenant_id)
        if not user:
            return None, "用户不存在"
        balance = Decimal(str(user.reward_usdt or 0))
        if balance < amount:
            return None, "奖励余额不足"
        fee = (amount * FEE_RATE).quantize(Decimal("0.01"))
        actual = amount - fee
        w = UserWithdrawal(
            user_id=user_id,
            amount=amount,
            fee=fee,
            actual_amount=actual,
            wallet_address=wallet_address,
            wallet_network=wallet_network,
            status=0,
        )
        self.repo.create_withdrawal(w)
        user.reward_usdt = balance - amount
        self.member_repo.update_user(user)
        return w, ""

    def get_withdrawal(self, withdrawal_id: int, user_id: Optional[int] = None) -> Optional[UserWithdrawal]:
        return self.repo.get_withdrawal(withdrawal_id, user_id)

    def list_withdrawals(
        self,
        user_id: int,
        page: int = 1,
        limit: int = 20,
        status: Optional[int] = None,
    ) -> tuple[List[UserWithdrawal], int]:
        return self.repo.list_withdrawals(user_id, page, limit, status)
