"""
Reward Repository - 利润池、奖励、提现数据访问
"""

from typing import Optional, List

from sqlalchemy.orm import Session

from .models import ProfitPool, UserReward, RewardLog, UserWithdrawal


class RewardRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------- ProfitPool ----------
    def create_profit_pool(self, p: ProfitPool) -> ProfitPool:
        self.db.add(p)
        self.db.flush()
        return p

    def get_pending_pools(self, limit: int = 100) -> List[ProfitPool]:
        return self.db.query(ProfitPool).filter(ProfitPool.status == 1).order_by(ProfitPool.id).limit(limit).all()

    def update_profit_pool(self, p: ProfitPool) -> ProfitPool:
        self.db.merge(p)
        self.db.flush()
        return p

    # ---------- UserReward ----------
    def create_reward(self, r: UserReward) -> UserReward:
        self.db.add(r)
        self.db.flush()
        return r

    def list_rewards(
        self,
        user_id: int,
        page: int = 1,
        limit: int = 20,
        reward_type: Optional[str] = None,
    ) -> tuple[List[UserReward], int]:
        q = self.db.query(UserReward).filter(UserReward.user_id == user_id)
        if reward_type:
            q = q.filter(UserReward.reward_type == reward_type)
        total = q.count()
        items = q.order_by(UserReward.id.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total

    # ---------- RewardLog ----------
    def create_reward_log(self, log: RewardLog) -> RewardLog:
        self.db.add(log)
        self.db.flush()
        return log

    def list_reward_logs(
        self,
        user_id: int,
        page: int = 1,
        limit: int = 20,
        change_type: Optional[str] = None,
    ) -> tuple[List[RewardLog], int]:
        q = self.db.query(RewardLog).filter(RewardLog.user_id == user_id)
        if change_type:
            q = q.filter(RewardLog.change_type == change_type)
        total = q.count()
        items = q.order_by(RewardLog.id.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total

    # ---------- UserWithdrawal ----------
    def create_withdrawal(self, w: UserWithdrawal) -> UserWithdrawal:
        self.db.add(w)
        self.db.flush()
        return w

    def get_withdrawal(self, withdrawal_id: int, user_id: Optional[int] = None) -> Optional[UserWithdrawal]:
        q = self.db.query(UserWithdrawal).filter(UserWithdrawal.id == withdrawal_id)
        if user_id is not None:
            q = q.filter(UserWithdrawal.user_id == user_id)
        return q.first()

    def list_withdrawals(
        self,
        user_id: int,
        page: int = 1,
        limit: int = 20,
        status: Optional[int] = None,
    ) -> tuple[List[UserWithdrawal], int]:
        q = self.db.query(UserWithdrawal).filter(UserWithdrawal.user_id == user_id)
        if status is not None:
            q = q.filter(UserWithdrawal.status == status)
        total = q.count()
        items = q.order_by(UserWithdrawal.id.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total

    def update_withdrawal(self, w: UserWithdrawal) -> UserWithdrawal:
        self.db.merge(w)
        self.db.flush()
        return w

    def list_all_withdrawals(
        self,
        page: int = 1,
        limit: int = 20,
        status: Optional[int] = None,
    ) -> tuple[List[UserWithdrawal], int]:
        """管理员查询所有用户的提现记录"""
        q = self.db.query(UserWithdrawal)
        if status is not None:
            q = q.filter(UserWithdrawal.status == status)
        total = q.count()
        items = q.order_by(UserWithdrawal.id.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total
