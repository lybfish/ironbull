"""
Merchant API - 用户管理（6 个接口）
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Form
from sqlalchemy.orm import Session

from libs.tenant.models import Tenant
from libs.member.service import MemberService
from libs.core.database import get_session
from ..deps import get_db, get_tenant
from ..schemas import ok, fail

router = APIRouter(prefix="/merchant", tags=["user"])


@router.get("/root-user")
def root_user(
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """获取根用户信息"""
    svc = MemberService(db)
    user = svc.get_root_user(tenant.id)
    if not user:
        return {"code": 1, "msg": "根用户未设置", "data": None}
    return ok({
        "user_id": user.id,
        "email": user.email,
        "invite_code": user.invite_code,
        "create_time": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "",
    })


@router.post("/user/create")
def user_create(
    email: str = Form(...),
    password: str = Form(...),
    inviter_id: Optional[int] = Form(0),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """创建用户"""
    if not email or not password:
        return {"code": 1, "msg": "邮箱和密码不能为空", "data": None}
    inviter_id = inviter_id or tenant.root_user_id
    svc = MemberService(db)
    user, err = svc.create_user(tenant.id, email, password, inviter_id=inviter_id, root_user_id=tenant.root_user_id)
    if err:
        return {"code": 1, "msg": err, "data": None}
    return ok({
        "user_id": user.id,
        "email": user.email,
        "invite_code": user.invite_code,
        "inviter_id": user.inviter_id or 0,
        "create_time": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "",
    }, msg="创建成功")


@router.get("/users")
def users_list(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    email: Optional[str] = None,
    invite_code: Optional[str] = None,
    status: Optional[int] = None,
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """用户列表"""
    from libs.member.repository import MemberRepository
    repo = MemberRepository(db)
    items, total = repo.list_users(tenant.id, page, limit, email, invite_code, status)
    list_data = []
    for u in items:
        list_data.append({
            "user_id": u.id,
            "email": u.email,
            "invite_code": u.invite_code,
            "inviter_id": u.inviter_id or 0,
            "is_root": u.is_root or 0,
            "point_card_self": float(u.point_card_self or 0),
            "point_card_gift": float(u.point_card_gift or 0),
            "point_card_total": float(u.point_card_self or 0) + float(u.point_card_gift or 0),
            "status": u.status,
            "create_time": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else "",
        })
    return ok({"list": list_data, "total": total, "page": page, "limit": limit})


@router.get("/user/info")
def user_info(
    user_id: Optional[int] = Query(None),
    email: Optional[str] = Query(None),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """用户详情"""
    if not user_id and not email:
        return {"code": 1, "msg": "请提供 user_id 或 email", "data": None}
    svc = MemberService(db)
    if user_id:
        user = svc.get_user(user_id, tenant.id)
    else:
        user = svc.get_user_by_email(email, tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    from libs.member.repository import MemberRepository
    repo = MemberRepository(db)
    accounts = repo.get_accounts_by_user(user.id)
    invite_count = repo.count_invitees(user.id)
    strategies = svc.get_user_strategies(user.id, tenant.id)
    active = sum(1 for s in strategies if s.get("status") == 1)
    total_profit = sum(s.get("total_profit", 0) for s in strategies)
    total_trades = sum(s.get("total_trades", 0) for s in strategies)
    acc_list = [{
        "account_id": a.id,
        "exchange": a.exchange,
        "account_type": a.account_type,
        "balance": float(a.balance or 0),
        "futures_balance": float(a.futures_balance or 0),
        "futures_available": float(a.futures_available or 0),
        "status": a.status,
    } for a in accounts]
    return ok({
        "user_id": user.id,
        "email": user.email,
        "invite_code": user.invite_code,
        "status": user.status,
        "create_time": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "",
        "inviter_id": user.inviter_id or 0,
        "invite_count": invite_count,
        "point_card_self": float(user.point_card_self or 0),
        "point_card_gift": float(user.point_card_gift or 0),
        "point_card_total": float(user.point_card_self or 0) + float(user.point_card_gift or 0),
        "accounts": acc_list,
        "active_strategies": active,
        "total_profit": total_profit,
        "total_trades": total_trades,
    })


@router.post("/user/apikey")
def user_apikey(
    user_id: int = Form(...),
    exchange: str = Form(...),
    api_key: str = Form(...),
    api_secret: str = Form(...),
    account_type: Optional[str] = Form("futures"),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """绑定用户 API Key"""
    svc = MemberService(db)
    acc, err = svc.bind_api_key(user_id, tenant.id, exchange, api_key, api_secret, account_type=account_type)
    if err:
        return {"code": 1, "msg": err, "data": None}
    return ok({
        "account_id": acc.id,
        "exchange": acc.exchange,
        "account_type": acc.account_type,
    }, msg="绑定成功" if not err else "更新成功")


@router.post("/user/apikey/unbind")
def user_apikey_unbind(
    user_id: int = Form(...),
    account_id: int = Form(...),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """解绑用户 API Key"""
    svc = MemberService(db)
    if not svc.unbind_api_key(user_id, account_id, tenant.id):
        return {"code": 1, "msg": "账户不存在", "data": None}
    return ok(None, msg="解绑成功")
