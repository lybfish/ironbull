"""
Reward Service - 奖励分销逻辑

结算时：技术团队 10% + 网体 20%（直推 25%、级差、平级 10%）
管理功能（结算）暂不实现，等后台；此处仅定义分配逻辑供后续调用。
"""

from decimal import Decimal
from typing import List

from sqlalchemy.orm import Session

from libs.member.models import User
from libs.member.repository import MemberRepository
from libs.member.level_service import LevelService
from libs.member.models import LevelConfig
from .models import ProfitPool, UserReward, RewardLog
from .repository import RewardRepository

TECH_RATE = Decimal("0.10")
NETWORK_RATE = Decimal("0.20")
DIRECT_RATE = Decimal("0.25")
PEER_RATE = Decimal("0.10")
SELF_HOLD_MIN = Decimal("1000")


class RewardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RewardRepository(db)
        self.member_repo = MemberRepository(db)
        self.level_service = LevelService(db)

    def distribute_for_pool(self, pool: ProfitPool) -> List[UserReward]:
        """
        对一条利润池记录进行分销，写入 fact_user_reward 并更新用户 reward_usdt。
        结算时调用（后台触发）。此处实现完整逻辑。
        """
        pool_amount = Decimal(str(pool.pool_amount))
        tech_amount = pool_amount * TECH_RATE
        network_amount = pool_amount * NETWORK_RATE
        rewards = []
        # 技术团队（虚拟 user_id=0 或单独配置，这里用 0 表示不落个人）
        # 实际可写入一条 reward 记录 user_id=0 或跳过
        # 直推奖
        direct_amount = network_amount * DIRECT_RATE
        source_user_for_inviter = self.member_repo.get_user_by_id(pool.user_id) if pool.user_id else None
        inviter_id = source_user_for_inviter.inviter_id if source_user_for_inviter else None
        if inviter_id:
            inviter = self.member_repo.get_user_by_id(inviter_id)
            if inviter and self.level_service.get_self_hold(inviter_id) >= SELF_HOLD_MIN:
                r = UserReward(
                    user_id=inviter_id,
                    source_user_id=pool.user_id,
                    profit_pool_id=pool.id,
                    reward_type="direct",
                    amount=direct_amount,
                    rate=DIRECT_RATE,
                    settle_batch=pool.settle_batch,
                    remark="直推奖励",
                )
                self.repo.create_reward(r)
                before_bal = Decimal(str(inviter.reward_usdt or 0))
                inviter.reward_usdt = before_bal + direct_amount
                inviter.total_reward = (inviter.total_reward or 0) + direct_amount
                self.member_repo.update_user(inviter)
                self.repo.create_reward_log(RewardLog(
                    user_id=inviter_id,
                    change_type="reward_in",
                    ref_type="user_reward",
                    ref_id=r.id,
                    amount=direct_amount,
                    before_balance=before_bal,
                    after_balance=inviter.reward_usdt,
                    remark="直推奖励",
                ))
                rewards.append(r)
        # 级差奖、平级奖：需要邀请路径上市场节点
        source_user = self.member_repo.get_user_by_id(pool.user_id)
        if source_user and source_user.inviter_path:
            path_ids = [int(x) for x in source_user.inviter_path.strip().split("/") if x.strip()]
            level_configs = {c.level: c for c in self.db.query(LevelConfig).all()}
            last_rate = Decimal("0")
            peer_done = False
            source_level = source_user.member_level
            for inviter_id in reversed(path_ids):
                inviter = self.member_repo.get_user_by_id(inviter_id)
                if not inviter or not inviter.is_market_node:
                    continue
                cfg = level_configs.get(inviter.member_level)
                current_rate = Decimal(str(cfg.diff_rate)) if cfg else Decimal("0")
                diff = current_rate - last_rate
                if diff > 0:
                    amount = network_amount * diff
                    r = UserReward(
                        user_id=inviter_id,
                        source_user_id=pool.user_id,
                        profit_pool_id=pool.id,
                        reward_type="level_diff",
                        amount=amount,
                        rate=diff,
                        from_level=source_level,
                        to_level=inviter.member_level,
                        settle_batch=pool.settle_batch,
                        remark="级差奖",
                    )
                    self.repo.create_reward(r)
                    before_bal = Decimal(str(inviter.reward_usdt or 0))
                    inviter.reward_usdt = before_bal + amount
                    inviter.total_reward = (inviter.total_reward or 0) + amount
                    self.member_repo.update_user(inviter)
                    self.repo.create_reward_log(RewardLog(
                        user_id=inviter_id,
                        change_type="reward_in",
                        ref_type="user_reward",
                        ref_id=r.id,
                        amount=amount,
                        before_balance=before_bal,
                        after_balance=inviter.reward_usdt,
                        remark="级差奖",
                    ))
                    rewards.append(r)
                    last_rate = current_rate
                if not peer_done and inviter.member_level == source_level:
                    peer_amount = network_amount * PEER_RATE
                    r = UserReward(
                        user_id=inviter_id,
                        source_user_id=pool.user_id,
                        profit_pool_id=pool.id,
                        reward_type="peer",
                        amount=peer_amount,
                        rate=PEER_RATE,
                        from_level=source_level,
                        to_level=inviter.member_level,
                        settle_batch=pool.settle_batch,
                        remark="平级奖",
                    )
                    self.repo.create_reward(r)
                    before_bal = Decimal(str(inviter.reward_usdt or 0))
                    inviter.reward_usdt = before_bal + peer_amount
                    inviter.total_reward = (inviter.total_reward or 0) + peer_amount
                    self.member_repo.update_user(inviter)
                    self.repo.create_reward_log(RewardLog(
                        user_id=inviter_id,
                        change_type="reward_in",
                        ref_type="user_reward",
                        ref_id=r.id,
                        amount=peer_amount,
                        before_balance=before_bal,
                        after_balance=inviter.reward_usdt,
                        remark="平级奖",
                    ))
                    rewards.append(r)
                    peer_done = True
        pool.status = 2
        self.repo.update_profit_pool(pool)
        return rewards
