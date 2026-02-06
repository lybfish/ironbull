"""
Pointcard Service - 点卡业务逻辑

- 代理商给用户充值/赠送
- 用户间点卡互转（同一邀请链路）
- 盈利扣费 30%（先 self 后 gift，self 进利润池）
"""

from decimal import Decimal
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from libs.member.repository import MemberRepository
from libs.tenant.repository import TenantRepository
from .models import PointCardLog
from .repository import PointCardRepository

# change_type
CHANGE_RECHARGE = 1        # 后台充值
CHANGE_GIFT = 2            # 后台赠送
CHANGE_DISTRIBUTE = 3      # 分发给用户（代理商→用户）
CHANGE_TRANSFER_OUT = 3    # 用户间转出（同值，上下文区分）
CHANGE_TRANSFER_IN = 4     # 转入
CHANGE_DEDUCT = 5          # 盈利扣费

# source_type
SOURCE_ADMIN = 1
SOURCE_AGENT_DISTRIBUTE = 2
SOURCE_PROFIT_DEDUCT = 3
SOURCE_USER_TRANSFER = 4

# card_type
CARD_SELF = 1
CARD_GIFT = 2


class PointCardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PointCardRepository(db)
        self.member_repo = MemberRepository(db)
        self.tenant_repo = TenantRepository(db)

    def recharge_user(
        self,
        tenant_id: int,
        user_id: int,
        amount: Decimal,
        use_self: bool,
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        代理商给用户充值/赠送。
        use_self=True: 扣代理商 self -> 用户 self（充值）
        use_self=False: 扣代理商 gift -> 用户 gift（赠送）
        返回 (success, error_msg, data)
        """
        if amount <= 0:
            return False, "金额必须大于0", None
        tenant = self.tenant_repo.get_by_id(tenant_id)
        if not tenant or tenant.status != 1:
            return False, "代理商不存在或已禁用", None
        user = self.member_repo.get_user_by_id(user_id, tenant_id)
        if not user:
            return False, "用户不存在", None
        if use_self:
            if (tenant.point_card_self or 0) < amount:
                return False, "代理商自充余额不足", None
        else:
            if (tenant.point_card_gift or 0) < amount:
                return False, "代理商赠送余额不足", None
        before_self_u = float(user.point_card_self or 0)
        before_gift_u = float(user.point_card_gift or 0)
        if use_self:
            tenant.point_card_self = (tenant.point_card_self or 0) - amount
            user.point_card_self = (user.point_card_self or 0) + amount
            after_self_u = before_self_u + float(amount)
            after_gift_u = before_gift_u
        else:
            tenant.point_card_gift = (tenant.point_card_gift or 0) - amount
            user.point_card_gift = (user.point_card_gift or 0) + amount
            after_self_u = before_self_u
            after_gift_u = before_gift_u + float(amount)
        self.tenant_repo.update(tenant)
        self.member_repo.update_user(user)
        # 流水：代理商（change_type=3 分发给用户）
        self.repo.create(PointCardLog(
            tenant_id=tenant_id,
            user_id=None,
            related_user_id=user_id,
            change_type=CHANGE_DISTRIBUTE,
            source_type=SOURCE_AGENT_DISTRIBUTE,
            card_type=CARD_SELF if use_self else CARD_GIFT,
            amount=-float(amount),
            before_self=float(tenant.point_card_self or 0) + float(amount) if use_self else float(tenant.point_card_self or 0),
            after_self=float(tenant.point_card_self or 0),
            before_gift=float(tenant.point_card_gift or 0) if not use_self else float(tenant.point_card_gift or 0) + float(amount),
            after_gift=float(tenant.point_card_gift or 0),
            remark=f"分发给用户#{user_id}（{'充值' if use_self else '赠送'}）",
        ))
        # 流水：用户
        self.repo.create(PointCardLog(
            tenant_id=None,
            user_id=user_id,
            change_type=CHANGE_RECHARGE if use_self else CHANGE_GIFT,
            source_type=SOURCE_AGENT_DISTRIBUTE,
            card_type=CARD_SELF if use_self else CARD_GIFT,
            amount=float(amount),
            before_self=before_self_u,
            after_self=after_self_u,
            before_gift=before_gift_u,
            after_gift=after_gift_u,
            remark="代理商充值" if use_self else "代理商赠送",
        ))
        agent_before = float(tenant.point_card_self or 0) + float(tenant.point_card_gift or 0) + float(amount)
        agent_after = float(tenant.point_card_self or 0) + float(tenant.point_card_gift or 0)
        member_before = before_self_u + before_gift_u
        member_after = after_self_u + after_gift_u
        return True, "", {
            "agent_before_total": agent_before,
            "agent_after_total": agent_after,
            "member_before_total": member_before,
            "member_after_total": member_after,
            "amount": float(amount),
        }

    def transfer(
        self,
        tenant_id: int,
        from_user_id: int,
        to_user_id: int,
        amount: Decimal,
        transfer_type: int = 1,
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        用户间点卡互转（同一邀请链路）。
        transfer_type=1: 自充互转（self→self）
        transfer_type=2: 赠送互转（gift→gift）
        返回 (success, error_msg, data)
        """
        if amount <= 0:
            return False, "转账金额必须大于0", None
        from_user = self.member_repo.get_user_by_id(from_user_id, tenant_id)
        to_user = self.member_repo.get_user_by_id(to_user_id, tenant_id)
        if not from_user or not to_user:
            return False, "用户不存在", None
        from_path = (from_user.inviter_path or "").strip().rstrip("/")
        to_path = (to_user.inviter_path or "").strip().rstrip("/")
        # 同一链路：to 是 from 的下级，或 from 是 to 的下级，或有共同根
        same_line = False
        if to_user.inviter_id == from_user_id or (from_user_id and str(from_user_id) in to_path):
            same_line = True
        elif from_user.inviter_id == to_user_id or (to_user_id and str(to_user_id) in from_path):
            same_line = True
        elif from_path and to_path:
            from_parts = from_path.split("/")
            to_parts = to_path.split("/")
            if from_parts and to_parts and from_parts[0] == to_parts[0]:
                same_line = True
        if not same_line:
            return False, "只能在同一邀请链路内转账", None
        use_self = transfer_type == 1
        from_self = Decimal(str(from_user.point_card_self or 0))
        from_gift = Decimal(str(from_user.point_card_gift or 0))
        to_self = Decimal(str(to_user.point_card_self or 0))
        to_gift = Decimal(str(to_user.point_card_gift or 0))
        if use_self:
            if from_self < amount:
                return False, "自充点卡余额不足", None
            from_user.point_card_self = from_self - amount
            to_user.point_card_self = to_self + amount
        else:
            if from_gift < amount:
                return False, "赠送点卡余额不足", None
            from_user.point_card_gift = from_gift - amount
            to_user.point_card_gift = to_gift + amount
        self.member_repo.update_user(from_user)
        self.member_repo.update_user(to_user)
        card_type = CARD_SELF if use_self else CARD_GIFT
        self.repo.create(PointCardLog(
            tenant_id=None,
            user_id=from_user_id,
            related_user_id=to_user_id,
            change_type=CHANGE_TRANSFER_OUT,
            source_type=SOURCE_USER_TRANSFER,
            card_type=card_type,
            amount=-float(amount),
            before_self=float(from_self),
            after_self=float(from_user.point_card_self),
            before_gift=float(from_gift),
            after_gift=float(from_user.point_card_gift),
            remark=f"{'自充' if use_self else '赠送'}转出给用户#{to_user_id}",
        ))
        self.repo.create(PointCardLog(
            tenant_id=None,
            user_id=to_user_id,
            related_user_id=from_user_id,
            change_type=CHANGE_TRANSFER_IN,
            source_type=SOURCE_USER_TRANSFER,
            card_type=card_type,
            amount=float(amount),
            before_self=float(to_self),
            after_self=float(to_user.point_card_self),
            before_gift=float(to_gift),
            after_gift=float(to_user.point_card_gift),
            remark=f"从用户#{from_user_id}{'自充' if use_self else '赠送'}转入",
        ))
        return True, "", {
            "amount": float(amount),
            "type": transfer_type,
            "type_name": "自充互转" if use_self else "赠送互转",
            "from_self_after": float(from_user.point_card_self),
            "from_gift_after": float(from_user.point_card_gift),
            "to_self_after": float(to_user.point_card_self),
            "to_gift_after": float(to_user.point_card_gift),
        }

    def deduct_for_profit(
        self,
        user_id: int,
        profit_amount: Decimal,
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        盈利扣费 30%：先扣 self，再扣 gift。
        self 部分进入利润池（由 reward 模块写 fact_profit_pool），此处只扣点卡并记流水。
        返回 (success, error_msg, data)，data 含 self_deduct, gift_deduct, pool_amount 等供 reward 使用。
        """
        if profit_amount <= 0:
            return False, "盈利金额必须大于0", None
        user = self.member_repo.get_user_by_id(user_id)
        if not user:
            return False, "用户不存在", None
        deduct_total = profit_amount * Decimal("0.30")
        self_bal = Decimal(str(user.point_card_self or 0))
        gift_bal = Decimal(str(user.point_card_gift or 0))
        self_deduct = min(self_bal, deduct_total)
        remaining = deduct_total - self_deduct
        gift_deduct = min(gift_bal, remaining)
        # 更新用户余额
        user.point_card_self = self_bal - self_deduct
        user.point_card_gift = gift_bal - gift_deduct
        self.member_repo.update_user(user)
        # 流水
        self.repo.create(PointCardLog(
            tenant_id=None,
            user_id=user_id,
            change_type=CHANGE_DEDUCT,
            source_type=SOURCE_PROFIT_DEDUCT,
            card_type=CARD_SELF,
            amount=-float(self_deduct + gift_deduct),
            before_self=float(self_bal),
            after_self=float(user.point_card_self),
            before_gift=float(gift_bal),
            after_gift=float(user.point_card_gift),
            remark="盈利扣费30%",
        ))
        pool_amount = self_deduct  # 仅 self 进入利润池
        if pool_amount > 0:
            from libs.reward.models import ProfitPool
            from libs.reward.repository import RewardRepository
            from libs.reward.service import RewardService
            rr = RewardRepository(self.db)
            pp = ProfitPool(
                user_id=user_id,
                profit_amount=profit_amount,
                deduct_amount=deduct_total,
                self_deduct=self_deduct,
                gift_deduct=gift_deduct,
                pool_amount=pool_amount,
                status=1,
            )
            rr.create_profit_pool(pp)
            # 盈利扣费后立即触发分销结算（直推/级差/平级）
            try:
                RewardService(self.db).distribute_for_pool(pp)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("distribute_for_pool failed: %s", e)
        return True, "", {
            "self_deduct": float(self_deduct),
            "gift_deduct": float(gift_deduct),
            "pool_amount": float(pool_amount),
            "deduct_total": float(deduct_total),
        }
