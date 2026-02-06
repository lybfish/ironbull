"""
Merchant API - 依赖注入（认证、DB、配额）
"""

from typing import Generator, Optional

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from libs.core.database import get_session
from libs.core.auth import extract_sign_headers, verify_timestamp, verify_sign
from libs.tenant.service import TenantService
from libs.tenant.models import Tenant
from libs.quota import QuotaService
from .schemas import fail


def get_db() -> Generator[Session, None, None]:
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_tenant(
    x_app_key: Optional[str] = Header(None, alias="X-App-Key"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp"),
    x_sign: Optional[str] = Header(None, alias="X-Sign"),
    db: Session = Depends(get_db),
) -> Tenant:
    try:
        app_key, timestamp, sign = extract_sign_headers(x_app_key, x_timestamp, x_sign)
        verify_timestamp(timestamp)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    tenant_service = TenantService(db)
    tenant = tenant_service.get_by_app_key(app_key)
    if not tenant:
        raise HTTPException(status_code=401, detail="AppKey无效或已禁用")
    if not verify_sign(app_key, timestamp, sign, tenant.app_secret):
        raise HTTPException(status_code=401, detail="签名验证失败")
    return tenant


def check_quota(
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> Tenant:
    """
    配额检查依赖：认证通过后检查 API 调用配额，超限返回 429。
    同时记录当日用量。路由中用 Depends(check_quota) 替代 Depends(get_tenant)。
    """
    quota_svc = QuotaService(db)
    result = quota_svc.check_api_quota(tenant.id)
    if not result["allowed"]:
        raise HTTPException(status_code=429, detail=result["reason"])
    # 记录用量
    quota_svc.increment_api_usage(tenant.id)
    return tenant
