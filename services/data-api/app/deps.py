"""
Data API - 依赖注入（DB Session、管理员鉴权、租户选择）

管理后台登录体系：
 - JWT 中存 admin_id + username（平台级超管）
 - 超管可查看所有租户数据，通过 query 参数 tenant_id 选择要查看的租户
"""

from typing import Generator, Optional, Dict, Any

from fastapi import Query, Header, HTTPException
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


def get_current_admin(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Dict[str, Any]:
    """
    从 Bearer JWT 解析管理员信息。
    返回 {"admin_id": int, "username": str}
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    token = authorization[7:].strip()
    payload = jwt_decode(token)
    if not payload or "admin_id" not in payload:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return {
        "admin_id": int(payload["admin_id"]),
        "username": payload.get("username", ""),
    }


def get_tenant_id(
    tenant_id: Optional[int] = Query(None, description="要查看的租户ID"),
) -> int:
    """
    超管选择要查看的租户（通过 query 参数）。
    这个依赖不再从 JWT 取 tenant_id（JWT 里只有 admin_id）。
    """
    if tenant_id is not None:
        return int(tenant_id)
    raise HTTPException(status_code=400, detail="请选择租户（tenant_id）")


def get_tenant_id_optional(tenant_id: Optional[int] = Query(None, description="要查看的租户ID（可选）")) -> Optional[int]:
    """租户ID可选，不传时返回 None（用于策略目录等全局列表）"""
    return int(tenant_id) if tenant_id is not None else None


def get_account_id_optional(account_id: Optional[int] = Query(None, description="账户ID（可选）")) -> Optional[int]:
    return account_id
