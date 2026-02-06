"""
Data API - 管理后台登录

POST /api/auth/login  -> 管理员登录，签发 JWT
GET  /api/auth/me     -> 当前管理员信息
POST /api/auth/change-password -> 修改密码
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from libs.admin import AdminService
from libs.core.auth import jwt_encode

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    admin_id: int
    username: str
    nickname: str


@router.post("/login", response_model=LoginResponse)
def login(body: LoginBody, db: Session = Depends(get_db)):
    """管理后台登录：用户名 + 密码，返回 JWT。"""
    svc = AdminService(db)
    admin = svc.verify_login(body.username.strip(), body.password)
    if not admin:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = jwt_encode(admin_id=admin.id, username=admin.username)
    return LoginResponse(
        token=token,
        admin_id=admin.id,
        username=admin.username,
        nickname=admin.nickname or admin.username,
    )


@router.get("/me")
def me(current_admin: Dict[str, Any] = Depends(get_current_admin)):
    """返回当前登录管理员信息（从 JWT 解析）"""
    return {"success": True, "data": current_admin}


@router.get("/logout")
def logout(_: Dict[str, Any] = Depends(get_current_admin)):
    """退出登录（服务端无状态，仅返回成功；前端清除 token 并跳转登录）"""
    return {"success": True, "message": "已退出"}


class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password")
def change_password(
    body: ChangePasswordBody,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """修改当前管理员密码"""
    svc = AdminService(db)
    err = svc.change_password(current_admin["admin_id"], body.old_password, body.new_password)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"success": True, "message": "密码已修改"}
