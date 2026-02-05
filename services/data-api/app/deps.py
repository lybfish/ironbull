"""
Data API - 依赖注入（DB Session、租户/账户）
优先从 Authorization: Bearer <JWT> 解析 tenant_id；无 token 时从 query 取 tenant_id（兼容旧调用）。
"""

from typing import Generator, Optional

from fastapi import Query, Header
from sqlalchemy.orm import Session

from libs.core.database import get_session
from libs.core.auth import jwt_decode


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


def _token_tenant(authorization: Optional[str] = Header(None, alias="Authorization")) -> Optional[int]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    payload = jwt_decode(token)
    if not payload:
        return None
    return payload.get("tenant_id")


def get_tenant_id(
    tenant_id: Optional[int] = Query(None, description="租户ID（无 JWT 时必填）"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> int:
    """租户ID：有 Bearer JWT 则从 token 取，否则用 query 的 tenant_id（必填）。"""
    from fastapi import HTTPException
    tid = _token_tenant(authorization)
    if tid is not None:
        return int(tid)
    if tenant_id is not None:
        return int(tenant_id)
    raise HTTPException(status_code=400, detail="请登录或传入 tenant_id")


def get_account_id_optional(account_id: Optional[int] = Query(None, description="账户ID（可选）")) -> Optional[int]:
    return account_id
