"""
Data API - 用户管理（只读查看，仅管理员可访问）

GET /api/users -> 用户列表（支持按租户筛选）
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from libs.member.models import User

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/users", tags=["users"])


def _user_dict(u: User) -> dict:
    return {
        "id": u.id,
        "tenant_id": u.tenant_id,
        "email": u.email,
        "is_root": u.is_root,
        "invite_code": u.invite_code,
        "inviter_id": u.inviter_id,
        "member_level": u.member_level,
        "point_card_self": float(u.point_card_self or 0),
        "point_card_gift": float(u.point_card_gift or 0),
        "reward_usdt": float(u.reward_usdt or 0),
        "total_reward": float(u.total_reward or 0),
        "status": u.status,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("")
def list_users(
    tenant_id: Optional[int] = Query(None, description="按租户筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """用户列表（可按租户筛选，分页）"""
    query = db.query(User)
    if tenant_id is not None:
        query = query.filter(User.tenant_id == tenant_id)
    query = query.order_by(User.id.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "success": True,
        "data": [_user_dict(u) for u in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
