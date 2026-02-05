"""
Merchant API - 依赖注入（认证、DB）
"""

from typing import Generator, Optional

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from libs.core.database import get_session
from libs.core.auth import extract_sign_headers, verify_timestamp, verify_sign
from libs.tenant.service import TenantService
from libs.tenant.models import Tenant
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
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    verify_timestamp(timestamp)
    tenant_service = TenantService(db)
    tenant = tenant_service.get_by_app_key(app_key)
    if not tenant:
        raise HTTPException(status_code=401, detail="AppKey无效或已禁用")
    if not verify_sign(app_key, timestamp, sign, tenant.app_secret):
        raise HTTPException(status_code=401, detail="签名验证失败")
    return tenant
