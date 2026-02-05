"""
Data API - 登录与 JWT

POST /api/auth/login  -> 签发 JWT
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from libs.member import MemberService
from libs.core.auth import jwt_encode

from ..deps import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    tenant_id: int
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    tenant_id: int
    user_id: int
    email: str


@router.post("/login", response_model=LoginResponse)
def login(body: LoginBody, db: Session = Depends(get_db)):
    """管理后台登录：租户ID + 邮箱 + 密码，返回 JWT。"""
    svc = MemberService(db)
    user = svc.verify_login(body.tenant_id, body.email.strip(), body.password)
    if not user:
        raise HTTPException(status_code=401, detail="租户/邮箱或密码错误")
    token = jwt_encode(tenant_id=user.tenant_id, user_id=user.id)
    return LoginResponse(
        token=token,
        tenant_id=user.tenant_id,
        user_id=user.id,
        email=user.email,
    )
