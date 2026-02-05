"""
Tenant Repository - 租户数据访问
"""

from typing import Optional

from sqlalchemy.orm import Session

from .models import Tenant


class TenantRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tenant_id: int) -> Optional[Tenant]:
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_by_app_key(self, app_key: str) -> Optional[Tenant]:
        return self.db.query(Tenant).filter(
            Tenant.app_key == app_key,
            Tenant.status == 1,
        ).first()

    def update(self, tenant: Tenant) -> Tenant:
        self.db.merge(tenant)
        self.db.flush()
        return tenant
