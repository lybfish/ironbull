"""
Merchant API - 用户管理（6 个接口）

- 获取根用户信息
- 创建用户（invite_code 邀请码）
- 用户列表
- 用户详情（合并 balance/level/reward-balance）
- 绑定 API Key
- 解绑 API Key
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Form
from sqlalchemy.orm import Session

from libs.tenant.models import Tenant
from libs.member.service import MemberService
from libs.core.database import get_session
from ..deps import get_db, check_quota as get_tenant
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
    invite_code: Optional[str] = Form(""),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """创建用户（invite_code 为邀请人的邀请码，不传则默认挂在根用户下）"""
    if not email or not password:
        return {"code": 1, "msg": "邮箱和密码不能为空", "data": None}
    from libs.member.repository import MemberRepository
    repo = MemberRepository(db)
    inviter_id = None
    if invite_code and invite_code.strip():
        inviter = repo.get_user_by_invite_code(invite_code.strip())
        if not inviter:
            return {"code": 1, "msg": "邀请码无效", "data": None}
        if inviter.tenant_id != tenant.id:
            return {"code": 1, "msg": "邀请码不属于该商户", "data": None}
        inviter_id = inviter.id
    else:
        inviter_id = tenant.root_user_id
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
    # 文档约定：status 1=正常 2=禁用（库存 0=禁用 1=正常）
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
            "status": 2 if u.status == 0 else 1,
            "create_time": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else "",
        })
    return ok({"list": list_data, "total": total, "page": page, "limit": limit})


@router.get("/user/info")
def user_info(
    email: str = Query(...),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """用户详情（合并 balance/level/reward-balance，一次返回全部信息）"""
    svc = MemberService(db)
    user = svc.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    from libs.member.repository import MemberRepository
    from libs.member.level_service import LevelService
    repo = MemberRepository(db)
    level_svc = LevelService(db)
    # 邀请人邀请码
    inviter_invite_code = ""
    if user.inviter_id:
        inviter = repo.get_user_by_id(user.inviter_id)
        if inviter:
            inviter_invite_code = inviter.invite_code or ""
    # 账户（含完整 API 信息：api_key、api_secret、passphrase，仅限商户端安全环境使用）
    accounts = repo.get_accounts_by_user(user.id)
    # 文档约定：accounts[].status 1=正常 2=禁用（库存 0=禁用 1=正常）
    acc_list = []
    for a in accounts:
        acc_list.append({
            "account_id": a.id,
            "exchange": a.exchange,
            "account_type": a.account_type,
            "api_key": a.api_key or "",
            "api_secret": a.api_secret or "",
            "passphrase": (a.passphrase or "") if a.passphrase else None,
            "balance": float(a.balance or 0),
            "futures_balance": float(a.futures_balance or 0),
            "futures_available": float(a.futures_available or 0),
            "status": 2 if (a.status or 0) == 0 else 1,
        })
    # 策略
    strategies = svc.get_user_strategies(user.id, tenant.id)
    active = sum(1 for s in strategies if s.get("status") == 1)
    total_profit = sum(s.get("total_profit", 0) for s in strategies)
    total_trades = sum(s.get("total_trades", 0) for s in strategies)
    # 团队
    invite_count = repo.count_invitees(user.id)
    sub_ids = repo.get_all_sub_user_ids(user.id)
    self_hold = float(level_svc.get_self_hold(user.id))
    # 文档约定：status 1=正常 2=禁用（库存 0=禁用 1=正常）
    return ok({
        "user_id": user.id,
        "email": user.email,
        "invite_code": user.invite_code,
        "inviter_invite_code": inviter_invite_code,
        "status": 2 if user.status == 0 else 1,
        "create_time": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "",
        "invite_count": invite_count,
        "point_card_self": float(user.point_card_self or 0),
        "point_card_gift": float(user.point_card_gift or 0),
        "point_card_total": float(user.point_card_self or 0) + float(user.point_card_gift or 0),
        "level": user.member_level or 0,
        "level_name": level_svc.get_level_name(user.member_level or 0),
        "is_market_node": user.is_market_node or 0,
        "self_hold": self_hold,
        "team_direct_count": invite_count,
        "team_total_count": len(sub_ids),
        "team_performance": float(user.team_performance or 0),
        "reward_usdt": float(user.reward_usdt or 0),
        "total_reward": float(user.total_reward or 0),
        "withdrawn_reward": float(user.withdrawn_reward or 0),
        "bound_exchanges": list({a.exchange for a in accounts}),
        "accounts": acc_list,
        "active_strategies": active,
        "total_profit": total_profit,
        "total_trades": total_trades,
    })


# 支持的交易所（绑定 API 时 exchange 只能在此列表中）
ALLOWED_EXCHANGES = ["binance", "okx", "gate"]


@router.post(
    "/user/apikey",
    summary="绑定用户 API Key",
    description="支持交易所：binance、okx、gate。选择 OKX 时需多传 passphrase（API Passphrase，创建 API 时设置的密码）。",
)
def user_apikey(
    email: str = Form(...),
    exchange: str = Form(..., description="交易所：binance / okx / gate"),
    api_key: str = Form(...),
    api_secret: str = Form(...),
    passphrase: Optional[str] = Form(None, description="API Passphrase，OKX 必填、Gate 可选、Binance 不填"),
    account_type: Optional[str] = Form("futures"),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """绑定用户 API Key。OKX 需传 passphrase；支持 binance、okx、gate。"""
    ex = exchange.strip().lower()
    if ex not in ALLOWED_EXCHANGES:
        return {"code": 1, "msg": f"不支持的交易所，仅支持: {', '.join(ALLOWED_EXCHANGES)}", "data": None}
    if ex == "okx" and not (passphrase and passphrase.strip()):
        return {"code": 1, "msg": "OKX 必须填写 API Passphrase（创建 API 时设置的密码）", "data": None}
    svc = MemberService(db)
    user = svc.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    acc, err = svc.bind_api_key(
        user.id, tenant.id, ex, api_key, api_secret, account_type=account_type, passphrase=(passphrase or "").strip() or None
    )
    if err:
        return {"code": 1, "msg": err, "data": None}
    return ok({
        "account_id": acc.id,
        "exchange": acc.exchange,
        "account_type": acc.account_type,
    }, msg="绑定成功" if not err else "更新成功")


@router.post("/user/apikey/unbind")
def user_apikey_unbind(
    email: str = Form(...),
    account_id: int = Form(...),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """解绑用户 API Key"""
    svc = MemberService(db)
    user = svc.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    if not svc.unbind_api_key(user.id, account_id, tenant.id):
        return {"code": 1, "msg": "账户不存在", "data": None}
    return ok(None, msg="解绑成功")
