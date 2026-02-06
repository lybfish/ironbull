"""
Reward Service - 奖励分销逻辑

结算时：技术团队 10% + 网体 20%（直推 25%、级差、平级 10%）+ 平台留存 70%
所有资金去向均写入 UserReward + RewardLog，全部可溯源。
未满足条件 / 网体预算用完的部分归入**对应租户的根账户**。
租户表累计追踪 tech_reward_total 和 undist_reward_total。

核心规则：
  - 网体 20% 是**硬预算**，直推+级差+平级 合计不超过 network_amount
  - 分配优先级：直推 > 级差 > 平级
  - 预算用完即停，不超发
"""

from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from libs.member.models import User
from libs.member.repository import MemberRepository
from libs.member.level_service import LevelService
from libs.member.models import LevelConfig
from libs.tenant.models import Tenant
from libs.tenant.repository import TenantRepository
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
        self.tenant_repo = TenantRepository(db)

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _get_root_user_id(self, tenant_id: int) -> Optional[int]:
        """获取租户的根账户 user_id"""
        tenant = self.tenant_repo.get_by_id(tenant_id)
        if tenant and tenant.root_user_id:
            return tenant.root_user_id
        # fallback: 查 is_root=1
        root = self.db.query(User).filter(
            User.tenant_id == tenant_id, User.is_root == 1
        ).first()
        return root.id if root else None

    def _create_reward_with_log(
        self,
        user_id: int,
        source_user_id: int,
        profit_pool_id: int,
        reward_type: str,
        amount: Decimal,
        rate: Decimal,
        settle_batch: str,
        remark: str,
        from_level: int = None,
        to_level: int = None,
    ) -> UserReward:
        """统一入口：写 UserReward + RewardLog + 更新用户余额"""
        r = UserReward(
            user_id=user_id,
            source_user_id=source_user_id,
            profit_pool_id=profit_pool_id,
            reward_type=reward_type,
            amount=amount,
            rate=rate,
            from_level=from_level,
            to_level=to_level,
            settle_batch=settle_batch,
            remark=remark,
        )
        self.repo.create_reward(r)

        before_bal = Decimal("0")
        after_bal = Decimal("0")
        user = self.member_repo.get_user_by_id(user_id)
        if user:
            before_bal = Decimal(str(user.reward_usdt or 0))
            user.reward_usdt = before_bal + amount
            user.total_reward = Decimal(str(user.total_reward or 0)) + amount
            self.member_repo.update_user(user)
            after_bal = user.reward_usdt

        self.repo.create_reward_log(RewardLog(
            user_id=user_id,
            change_type="reward_in",
            ref_type="user_reward",
            ref_id=r.id,
            amount=amount,
            before_balance=before_bal,
            after_balance=after_bal,
            remark=remark,
        ))
        return r

    # ------------------------------------------------------------------
    # 主方法
    # ------------------------------------------------------------------
    def distribute_for_pool(self, pool: ProfitPool) -> List[UserReward]:
        """
        对一条利润池记录进行全额分销。

        资金分配（每一分钱都有 UserReward + RewardLog）：

          pool_amount (100%)
          ├── tech_team      = 10%            → 租户根账户
          ├── network        = 20% (硬预算)
          │   ├── direct        优先级 1      → 邀请人 / 根账户(direct_undist)
          │   ├── level_diff    优先级 2      → 各市场节点（受预算限制）
          │   ├── peer          优先级 3      → 同级节点 / 根账户(peer_undist)
          │   └── network_left  剩余          → 根账户(network_undist)
          └── platform_retain = 70%           → 租户根账户

        不超发：direct + level_diff + peer <= network_amount
        """
        pool_amount = Decimal(str(pool.pool_amount))
        tech_amount = pool_amount * TECH_RATE
        network_amount = pool_amount * NETWORK_RATE
        platform_amount = pool_amount - tech_amount - network_amount  # 固定 70%

        # 获取产生利润的用户信息
        source_user = self.member_repo.get_user_by_id(pool.user_id)
        if not source_user:
            raise ValueError(f"利润池 user_id={pool.user_id} 用户不存在")

        tenant_id = source_user.tenant_id
        root_user_id = self._get_root_user_id(tenant_id)
        if not root_user_id:
            raise ValueError(f"租户 {tenant_id} 无根账户，无法分配")

        rewards: List[UserReward] = []

        # ==================== 1. 技术团队 10% → 租户根账户 ================
        rewards.append(self._create_reward_with_log(
            user_id=root_user_id,
            source_user_id=pool.user_id,
            profit_pool_id=pool.id,
            reward_type="tech_team",
            amount=tech_amount,
            rate=TECH_RATE,
            settle_batch=pool.settle_batch,
            remark="技术团队 10%",
        ))

        # ==================== 2. 网体 20%（预算制）========================
        budget = network_amount  # 剩余预算，分完即停
        direct_distributed = Decimal("0")
        diff_distributed = Decimal("0")
        peer_distributed = Decimal("0")

        # --- 2a. 直推奖（优先级 1）---
        direct_wanted = network_amount * DIRECT_RATE
        inviter_id = source_user.inviter_id
        direct_ok = False

        if inviter_id and budget > 0:
            inviter = self.member_repo.get_user_by_id(inviter_id)
            if inviter and self.level_service.get_self_hold(inviter_id) >= SELF_HOLD_MIN:
                actual_direct = min(direct_wanted, budget)
                rewards.append(self._create_reward_with_log(
                    user_id=inviter_id,
                    source_user_id=pool.user_id,
                    profit_pool_id=pool.id,
                    reward_type="direct",
                    amount=actual_direct,
                    rate=DIRECT_RATE,
                    settle_batch=pool.settle_batch,
                    remark="直推奖励",
                ))
                direct_distributed = actual_direct
                budget -= actual_direct
                direct_ok = True

        if not direct_ok:
            # 直推未发放 → 根账户
            reason = "无邀请人" if not inviter_id else "邀请人自持不足"
            actual_direct_undist = min(direct_wanted, budget)
            if actual_direct_undist > 0:
                rewards.append(self._create_reward_with_log(
                    user_id=root_user_id,
                    source_user_id=pool.user_id,
                    profit_pool_id=pool.id,
                    reward_type="direct_undist",
                    amount=actual_direct_undist,
                    rate=DIRECT_RATE,
                    settle_batch=pool.settle_batch,
                    remark="直推未发放（" + reason + "）→ 根账户",
                ))
                budget -= actual_direct_undist

        # --- 2b. 级差奖（优先级 2）---
        if source_user.inviter_path and budget > 0:
            path_ids = [
                int(x)
                for x in source_user.inviter_path.strip().split("/")
                if x.strip()
            ]
            level_configs = {
                c.level: c for c in self.db.query(LevelConfig).all()
            }
            last_rate = Decimal("0")
            source_level = source_user.member_level

            for anc_id in reversed(path_ids):
                if budget <= 0:
                    break
                anc = self.member_repo.get_user_by_id(anc_id)
                if not anc or not anc.is_market_node:
                    continue

                cfg = level_configs.get(anc.member_level)
                current_rate = Decimal(str(cfg.diff_rate)) if cfg else Decimal("0")
                diff = current_rate - last_rate
                if diff > 0:
                    wanted = network_amount * diff
                    actual = min(wanted, budget)
                    rewards.append(self._create_reward_with_log(
                        user_id=anc_id,
                        source_user_id=pool.user_id,
                        profit_pool_id=pool.id,
                        reward_type="level_diff",
                        amount=actual,
                        rate=diff,
                        from_level=source_level,
                        to_level=anc.member_level,
                        settle_batch=pool.settle_batch,
                        remark="级差奖 S" + str(source_level) + "->S" + str(anc.member_level)
                               + " diff=" + str(diff)
                               + (" (预算封顶)" if actual < wanted else ""),
                    ))
                    diff_distributed += actual
                    budget -= actual
                    last_rate = current_rate

        # --- 2c. 平级奖（优先级 3）---
        peer_wanted = network_amount * PEER_RATE
        peer_done = False

        if source_user.inviter_path and budget > 0:
            path_ids = [
                int(x)
                for x in source_user.inviter_path.strip().split("/")
                if x.strip()
            ]
            source_level = source_user.member_level
            for anc_id in reversed(path_ids):
                anc = self.member_repo.get_user_by_id(anc_id)
                if not anc or not anc.is_market_node:
                    continue
                if anc.member_level == source_level:
                    actual_peer = min(peer_wanted, budget)
                    rewards.append(self._create_reward_with_log(
                        user_id=anc_id,
                        source_user_id=pool.user_id,
                        profit_pool_id=pool.id,
                        reward_type="peer",
                        amount=actual_peer,
                        rate=PEER_RATE,
                        from_level=source_level,
                        to_level=anc.member_level,
                        settle_batch=pool.settle_batch,
                        remark="平级奖" + (" (预算封顶)" if actual_peer < peer_wanted else ""),
                    ))
                    peer_distributed = actual_peer
                    budget -= actual_peer
                    peer_done = True
                    break

        if not peer_done:
            # 平级未发放 → 根账户
            actual_peer_undist = min(peer_wanted, budget)
            if actual_peer_undist > 0:
                rewards.append(self._create_reward_with_log(
                    user_id=root_user_id,
                    source_user_id=pool.user_id,
                    profit_pool_id=pool.id,
                    reward_type="peer_undist",
                    amount=actual_peer_undist,
                    rate=PEER_RATE,
                    settle_batch=pool.settle_batch,
                    remark="平级未发放（无同级市场节点）→ 根账户",
                ))
                budget -= actual_peer_undist

        # --- 2d. 网体剩余预算 → 根账户 ---
        if budget > 0:
            rewards.append(self._create_reward_with_log(
                user_id=root_user_id,
                source_user_id=pool.user_id,
                profit_pool_id=pool.id,
                reward_type="network_undist",
                amount=budget,
                rate=Decimal("0"),
                settle_batch=pool.settle_batch,
                remark="网体剩余预算 → 根账户",
            ))

        # ==================== 3. 平台留存 70% → 租户根账户 ================
        rewards.append(self._create_reward_with_log(
            user_id=root_user_id,
            source_user_id=pool.user_id,
            profit_pool_id=pool.id,
            reward_type="platform_retain",
            amount=platform_amount,
            rate=Decimal("1") - TECH_RATE - NETWORK_RATE,
            settle_batch=pool.settle_batch,
            remark="平台留存 70%",
        ))

        # ==================== 4. 更新 ProfitPool 追踪字段 =================
        pool.tech_amount = tech_amount
        pool.network_amount = network_amount
        pool.platform_amount = platform_amount
        pool.direct_distributed = direct_distributed
        pool.diff_distributed = diff_distributed
        pool.peer_distributed = peer_distributed
        pool.network_undistributed = network_amount - direct_distributed - diff_distributed - peer_distributed

        pool.status = 2
        self.repo.update_profit_pool(pool)

        # ==================== 5. 更新租户累计字段 =========================
        tenant = self.tenant_repo.get_by_id(tenant_id)
        if tenant:
            tenant.tech_reward_total = Decimal(str(tenant.tech_reward_total or 0)) + tech_amount
            undist_this_pool = network_amount - direct_distributed - diff_distributed - peer_distributed
            tenant.undist_reward_total = Decimal(str(tenant.undist_reward_total or 0)) + undist_this_pool
            self.db.merge(tenant)
            self.db.flush()

        return rewards
