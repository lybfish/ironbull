"""
Data API - 用户管理（只读查看，仅管理员可访问）

GET /api/users           -> 用户列表
GET /api/users/{user_id} -> 用户详情（完整信息，复用 user_manage._user_detail）
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

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
        "is_market_node": u.is_market_node,
        "point_card_self": float(u.point_card_self or 0),
        "point_card_gift": float(u.point_card_gift or 0),
        "reward_usdt": float(u.reward_usdt or 0),
        "total_reward": float(u.total_reward or 0),
        "withdrawn_reward": float(getattr(u, "withdrawn_reward", 0) or 0),
        "team_performance": float(getattr(u, "team_performance", 0) or 0),
        "status": u.status,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("")
def list_users(
    tenant_id: Optional[int] = Query(None, description="按租户筛选"),
    email: Optional[str] = Query(None, description="邮箱模糊"),
    invite_code: Optional[str] = Query(None, description="邀请码精确"),
    inviter_id: Optional[int] = Query(None, description="邀请人ID"),
    point_card_self_min: Optional[float] = Query(None, description="自充点卡≥"),
    point_card_gift_min: Optional[float] = Query(None, description="赠送点卡≥"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """用户列表（支持多条件筛选，返回邀请人码、直推人数、团队业绩、累计奖励等）"""
    query = db.query(User)
    if tenant_id is not None:
        query = query.filter(User.tenant_id == tenant_id)
    if email and email.strip():
        query = query.filter(User.email.like(f"%{email.strip()}%"))
    if invite_code and invite_code.strip():
        query = query.filter(User.invite_code == invite_code.strip())
    if inviter_id is not None:
        query = query.filter(User.inviter_id == inviter_id)
    if point_card_self_min is not None:
        query = query.filter(User.point_card_self >= point_card_self_min)
    if point_card_gift_min is not None:
        query = query.filter(User.point_card_gift >= point_card_gift_min)
    query = query.order_by(User.id.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    # 批量：邀请人邀请码、直推人数
    inviter_ids = list({u.inviter_id for u in items if u.inviter_id})
    inviter_code_map: Dict[int, str] = {}
    if inviter_ids:
        inviters = db.query(User.id, User.invite_code).filter(User.id.in_(inviter_ids)).all()
        inviter_code_map = {r[0]: (r[1] or "") for r in inviters}
    user_ids = [u.id for u in items]
    direct_count_map: Dict[int, int] = {}
    if user_ids:
        rows = (
            db.query(User.inviter_id, func.count(User.id))
            .filter(User.inviter_id.in_(user_ids))
            .group_by(User.inviter_id)
            .all()
        )
        direct_count_map = {r[0]: int(r[1]) for r in rows}

    list_data = []
    for u in items:
        row = _user_dict(u)
        row["inviter_invite_code"] = inviter_code_map.get(u.inviter_id, "") if u.inviter_id else ""
        row["team_direct_count"] = direct_count_map.get(u.id, 0)
        list_data.append(row)
    return {
        "success": True,
        "data": list_data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{user_id}")
def user_detail(
    user_id: int,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """用户详情（完整信息：账户、团队、奖励等），与 user_manage 逻辑一致"""
    from .user_manage import _user_detail as build_user_detail

    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"success": True, "data": build_user_detail(u, db)}
