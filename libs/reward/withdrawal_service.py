"""
Withdrawal Service - 提现申请

审核/打款由后台触发，此处仅实现申请与查询。
"""

from decimal import Decimal
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from libs.member.repository import MemberRepository
from .models import UserWithdrawal, RewardLog
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
        before_bal = balance
        user.reward_usdt = balance - amount
        self.member_repo.update_user(user)
        # 写入奖励流水：提现冻结
        self.repo.create_reward_log(RewardLog(
            user_id=user_id,
            change_type="withdraw_freeze",
            ref_type="user_withdrawal",
            ref_id=w.id,
            amount=-amount,
            before_balance=before_bal,
            after_balance=user.reward_usdt,
            remark="提现冻结",
        ))
        return w, ""

    def approve(self, withdrawal_id: int, admin_id: int) -> Tuple[Optional[UserWithdrawal], str]:
        """
        管理员审核通过提现。状态 0→1（已通过，待打款）。
        """
        w = self.repo.get_withdrawal(withdrawal_id)
        if not w:
            return None, "提现记录不存在"
        if w.status != 0:
            return None, f"当前状态({w.status})不允许审核"
        from datetime import datetime
        w.status = 1
        w.audit_by = admin_id
        w.audit_at = datetime.now()
        self.repo.update_withdrawal(w)
        return w, ""

    def reject(self, withdrawal_id: int, admin_id: int, reason: str = "") -> Tuple[Optional[UserWithdrawal], str]:
        """
        管理员拒绝提现。状态 0→2（已拒绝），退回 reward_usdt。
        """
        w = self.repo.get_withdrawal(withdrawal_id)
        if not w:
            return None, "提现记录不存在"
        if w.status != 0:
            return None, f"当前状态({w.status})不允许拒绝"
        from datetime import datetime
        w.status = 2
        w.reject_reason = reason
        w.audit_by = admin_id
        w.audit_at = datetime.now()
        self.repo.update_withdrawal(w)
        # 退回 reward_usdt
        user = self.member_repo.get_user_by_id(w.user_id)
        if user:
            before_bal = Decimal(str(user.reward_usdt or 0))
            user.reward_usdt = before_bal + w.amount
            self.member_repo.update_user(user)
            self.repo.create_reward_log(RewardLog(
                user_id=w.user_id,
                change_type="withdraw_reject_return",
                ref_type="user_withdrawal",
                ref_id=w.id,
                amount=w.amount,
                before_balance=before_bal,
                after_balance=user.reward_usdt,
                remark=f"提现拒绝退回: {reason}" if reason else "提现拒绝退回",
            ))
        return w, ""

    def complete(self, withdrawal_id: int, tx_hash: str = "") -> Tuple[Optional[UserWithdrawal], str]:
        """
        标记提现打款完成。状态 1→3（已完成），记录 tx_hash。
        """
        w = self.repo.get_withdrawal(withdrawal_id)
        if not w:
            return None, "提现记录不存在"
        if w.status != 1:
            return None, f"当前状态({w.status})不允许标记完成，需先审核通过"
        from datetime import datetime
        w.status = 3
        w.tx_hash = tx_hash or None
        w.completed_at = datetime.now()
        self.repo.update_withdrawal(w)
        # 更新用户已提现累计
        user = self.member_repo.get_user_by_id(w.user_id)
        if user:
            user.withdrawn_reward = (user.withdrawn_reward or 0) + w.actual_amount
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

    def list_all_withdrawals(
        self,
        page: int = 1,
        limit: int = 20,
        status: Optional[int] = None,
    ) -> tuple[List[UserWithdrawal], int]:
        """管理员查看所有提现记录"""
        return self.repo.list_all_withdrawals(page, limit, status)
