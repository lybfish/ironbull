"""
Tenant Service - 租户业务逻辑
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from .models import Tenant
from .repository import TenantRepository


class TenantService:
    def __init__(self, db: Session):
        self.repo = TenantRepository(db)

    def get_by_id(self, tenant_id: int) -> Optional[Tenant]:
        return self.repo.get_by_id(tenant_id)

    def get_by_app_key(self, app_key: str) -> Optional[Tenant]:
        return self.repo.get_by_app_key(app_key)

    def get_balance(self, tenant_id: int) -> dict:
        """
        获取代理商点卡余额
        """
        tenant = self.repo.get_by_id(tenant_id)
        if not tenant:
            return {"point_card_self": 0, "point_card_gift": 0, "point_card_total": 0}
        self_val = float(tenant.point_card_self or 0)
        gift_val = float(tenant.point_card_gift or 0)
        return {
            "point_card_self": self_val,
            "point_card_gift": gift_val,
            "point_card_total": self_val + gift_val,
        }

    def deduct_point_card(
        self,
        tenant_id: int,
        amount: Decimal,
        use_self: bool,
    ) -> bool:
        """
        扣减代理商点卡。use_self=True 扣 self，否则扣 gift。
        余额不足返回 False。
        """
        tenant = self.repo.get_by_id(tenant_id)
        if not tenant:
            return False
        if use_self:
            if (tenant.point_card_self or 0) < amount:
                return False
            tenant.point_card_self = (tenant.point_card_self or 0) - amount
        else:
            if (tenant.point_card_gift or 0) < amount:
                return False
            tenant.point_card_gift = (tenant.point_card_gift or 0) - amount
        self.repo.update(tenant)
        return True
