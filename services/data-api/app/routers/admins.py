"""
Data API - 管理员账号管理（仅管理员可访问）

GET    /api/admins              -> 管理员列表
POST   /api/admins              -> 创建管理员
PUT    /api/admins/{id}         -> 编辑管理员
PATCH  /api/admins/{id}/toggle  -> 启用/禁用
POST   /api/admins/{id}/reset-password -> 重置密码
"""

import hashlib
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from libs.admin.models import Admin

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/admins", tags=["admins"])


def _hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


class AdminCreate(BaseModel):
    username: str
    password: str
    nickname: str = ""


class AdminUpdate(BaseModel):
    nickname: Optional[str] = None


class ResetPasswordBody(BaseModel):
    new_password: str


def _admin_dict(a: Admin) -> dict:
    return {
        "id": a.id,
        "username": a.username,
        "nickname": a.nickname or "",
        "status": a.status,
        "last_login_at": a.last_login_at.isoformat() if a.last_login_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("")
def list_admins(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员列表"""
    query = db.query(Admin).order_by(Admin.id.asc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "success": True,
        "data": [_admin_dict(a) for a in items],
        "total": total,
    }


@router.post("")
def create_admin(
    body: AdminCreate,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """创建管理员"""
    username = body.username.strip()
    if not username or not body.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    existing = db.query(Admin).filter(Admin.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    admin = Admin(
        username=username,
        password_hash=_hash_password(body.password),
        nickname=body.nickname.strip() or username,
    )
    db.add(admin)
    db.flush()
    return {"success": True, "data": _admin_dict(admin)}


@router.put("/{admin_id}")
def update_admin(
    admin_id: int,
    body: AdminUpdate,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """编辑管理员"""
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")
    if body.nickname is not None:
        admin.nickname = body.nickname.strip()
    db.merge(admin)
    db.flush()
    return {"success": True, "data": _admin_dict(admin)}


@router.patch("/{admin_id}/toggle")
def toggle_admin(
    admin_id: int,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """启用/禁用管理员（不能禁用自己）"""
    if admin_id == current_admin["admin_id"]:
        raise HTTPException(status_code=400, detail="不能禁用自己")
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")
    admin.status = 0 if admin.status == 1 else 1
    db.merge(admin)
    db.flush()
    return {"success": True, "data": _admin_dict(admin)}


@router.post("/{admin_id}/reset-password")
def reset_password(
    admin_id: int,
    body: ResetPasswordBody,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """重置管理员密码"""
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")
    if not body.new_password:
        raise HTTPException(status_code=400, detail="新密码不能为空")
    admin.password_hash = _hash_password(body.new_password)
    db.merge(admin)
    db.flush()
    return {"success": True, "message": "密码已重置"}
