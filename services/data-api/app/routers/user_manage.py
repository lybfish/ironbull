"""
Data API - 用户管理扩展（管理员操作用户的 merchant-api 等价功能）

GET    /api/users/{user_id}          -> 用户详情
POST   /api/users/{user_id}/recharge -> 给用户充值/赠送点卡
GET    /api/users/{user_id}/team     -> 用户直推团队
POST   /api/users/{user_id}/set-market-node -> 设置/取消市场节点
GET    /api/pointcard-logs           -> 平台点卡流水（admin 级）
GET    /api/rewards                  -> 平台奖励记录（admin 级）
"""

from decimal import Decimal
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from libs.member.models import User, ExchangeAccount, StrategyBinding
from libs.member.repository import MemberRepository
from libs.member.level_service import LevelService
from libs.pointcard.models import PointCardLog
from libs.pointcard.service import PointCardService
from libs.reward.models import UserReward, UserWithdrawal
from libs.reward.repository import RewardRepository

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api", tags=["user-manage"])

LEVEL_NAMES = {0: "普通", 1: "V1", 2: "V2", 3: "V3", 4: "V4", 5: "V5"}
REWARD_TYPE_NAME = {"direct": "直推奖", "level_diff": "级差奖", "peer": "平级奖"}
CHANGE_TYPE_NAME = {1: "充值", 2: "赠送", 3: "分发/转出", 4: "转入", 5: "盈利扣费"}


def _user_detail(u: User, db: Session) -> dict:
    """构建完整用户详情"""
    repo = MemberRepository(db)

    # 邀请人信息
    inviter_email = ""
    inviter_invite_code = ""
    if u.inviter_id:
        inviter = repo.get_user_by_id(u.inviter_id)
        if inviter:
            inviter_email = inviter.email or ""
            inviter_invite_code = inviter.invite_code or ""

    # 交易所账户
    accounts = repo.get_accounts_by_user(u.id) if hasattr(repo, 'get_accounts_by_user') else []
    acc_list = [{
        "id": a.id,
        "exchange": a.exchange,
        "account_type": getattr(a, 'account_type', 'futures'),
        "balance": float(getattr(a, 'balance', 0) or 0),
        "futures_balance": float(getattr(a, 'futures_balance', 0) or 0),
        "status": a.status,
    } for a in accounts]

    # 团队
    invite_count = repo.count_invitees(u.id) if hasattr(repo, 'count_invitees') else 0
    sub_ids = repo.get_all_sub_user_ids(u.id) if hasattr(repo, 'get_all_sub_user_ids') else []

    # 策略绑定
    bindings = db.query(StrategyBinding).filter(
        StrategyBinding.user_id == u.id,
        StrategyBinding.status == 1,
    ).all()
    active_strategies = len(bindings)

    return {
        "id": u.id,
        "tenant_id": u.tenant_id,
        "email": u.email,
        "invite_code": u.invite_code,
        "inviter_id": u.inviter_id,
        "inviter_email": inviter_email,
        "inviter_invite_code": inviter_invite_code,
        "is_root": u.is_root or 0,
        "member_level": u.member_level or 0,
        "level_name": LEVEL_NAMES.get(u.member_level or 0, "普通"),
        "is_market_node": getattr(u, 'is_market_node', 0) or 0,
        "point_card_self": float(u.point_card_self or 0),
        "point_card_gift": float(u.point_card_gift or 0),
        "point_card_total": float(u.point_card_self or 0) + float(u.point_card_gift or 0),
        "reward_usdt": float(u.reward_usdt or 0),
        "total_reward": float(u.total_reward or 0),
        "withdrawn_reward": float(getattr(u, 'withdrawn_reward', 0) or 0),
        "team_direct_count": invite_count,
        "team_total_count": len(sub_ids),
        "team_performance": float(getattr(u, 'team_performance', 0) or 0),
        "active_strategies": active_strategies,
        "accounts": acc_list,
        "status": u.status,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("/users/{user_id}")
def user_detail(
    user_id: int,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """用户详情（完整信息：账户、团队、策略、奖励）"""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"success": True, "data": _user_detail(u, db)}


class ToggleStatusBody(BaseModel):
    status: int = 1  # 1=正常, 0=禁用


@router.post("/users/{user_id}/toggle-status")
def toggle_user_status(
    user_id: int,
    body: ToggleStatusBody,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """启用/禁用用户"""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.status = body.status
    db.merge(u)
    db.commit()
    status_label = "启用" if body.status == 1 else "禁用"
    return {"success": True, "message": f"用户已{status_label}"}


class RechargeUserBody(BaseModel):
    amount: float
    card_type: str = "self"  # self=充值, gift=赠送


@router.post("/users/{user_id}/recharge")
def recharge_user(
    user_id: int,
    body: RechargeUserBody,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """给用户充值/赠送点卡"""
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="金额必须大于0")
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")

    svc = PointCardService(db)
    use_self = body.card_type != "gift"
    success, err, data = svc.recharge_user(u.tenant_id, u.id, Decimal(str(body.amount)), use_self)
    if not success:
        raise HTTPException(status_code=400, detail=err)
    return {
        "success": True,
        "data": data,
        "message": f"{'充值' if use_self else '赠送'}成功 {body.amount} 点卡",
    }


@router.get("/users/{user_id}/team")
def user_team(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """用户直推团队"""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    repo = MemberRepository(db)
    level_svc = LevelService(db)
    items, total = repo.get_direct_members(u.id, page, page_size)
    list_data = []
    for m in items:
        sub_count = repo.count_invitees(m.id)
        list_data.append({
            "id": m.id,
            "email": m.email,
            "member_level": m.member_level or 0,
            "level_name": LEVEL_NAMES.get(m.member_level or 0, "普通"),
            "is_market_node": getattr(m, 'is_market_node', 0) or 0,
            "point_card_self": float(m.point_card_self or 0),
            "point_card_gift": float(m.point_card_gift or 0),
            "sub_count": sub_count,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return {"success": True, "data": list_data, "total": total}


class SetMarketNodeBody(BaseModel):
    is_node: int = 1  # 1=设置, 0=取消


@router.post("/users/{user_id}/set-market-node")
def set_market_node(
    user_id: int,
    body: SetMarketNodeBody,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """设置/取消市场节点"""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.is_market_node = 1 if body.is_node else 0
    db.merge(u)
    db.flush()
    return {"success": True, "message": "已设置为市场节点" if body.is_node else "已取消市场节点"}


# ---- 平台级点卡流水（由 main 显式注册 /api/pointcard-logs，此处仅定义实现） ----

def list_pointcard_logs(
    tenant_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    change_type: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """平台级点卡流水（可按租户、用户、类型筛选）"""
    query = db.query(PointCardLog).order_by(PointCardLog.id.desc())
    if tenant_id is not None:
        query = query.filter(PointCardLog.tenant_id == tenant_id)
    if user_id is not None:
        query = query.filter(PointCardLog.user_id == user_id)
    if change_type is not None:
        query = query.filter(PointCardLog.change_type == change_type)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    # 批量查用户邮箱
    user_ids = {log.user_id for log in items if log.user_id}
    email_map = {}
    if user_ids:
        rows = db.query(User.id, User.email).filter(User.id.in_(user_ids)).all()
        email_map = {r[0]: r[1] for r in rows}

    list_data = []
    for log in items:
        list_data.append({
            "id": log.id,
            "tenant_id": log.tenant_id,
            "user_id": log.user_id,
            "user_email": email_map.get(log.user_id, ""),
            "change_type": log.change_type,
            "change_type_name": CHANGE_TYPE_NAME.get(log.change_type, str(log.change_type)),
            "source_type": log.source_type,
            "card_type": log.card_type,
            "amount": float(log.amount or 0),
            "before_self": float(log.before_self or 0),
            "after_self": float(log.after_self or 0),
            "before_gift": float(log.before_gift or 0),
            "after_gift": float(log.after_gift or 0),
            "remark": log.remark or "",
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return {"success": True, "data": list_data, "total": total, "page": page, "page_size": page_size}


# ---- 平台级奖励记录（由 main 显式注册 /api/rewards，此处仅定义实现） ----

def list_rewards(
    tenant_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    reward_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """平台级奖励记录（可按租户、用户、奖励类型筛选）"""
    query = db.query(UserReward).order_by(UserReward.id.desc())
    if tenant_id is not None:
        query = query.join(User, UserReward.user_id == User.id).filter(User.tenant_id == tenant_id)
    if user_id is not None:
        query = query.filter(UserReward.user_id == user_id)
    if reward_type:
        query = query.filter(UserReward.reward_type == reward_type)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    # 批量查用户邮箱
    all_user_ids = set()
    for r in items:
        if r.user_id:
            all_user_ids.add(r.user_id)
        if r.source_user_id:
            all_user_ids.add(r.source_user_id)
    email_map = {}
    if all_user_ids:
        rows = db.query(User.id, User.email).filter(User.id.in_(all_user_ids)).all()
        email_map = {r[0]: r[1] for r in rows}

    list_data = []
    for r in items:
        list_data.append({
            "id": r.id,
            "tenant_id": None,
            "user_id": r.user_id,
            "user_email": email_map.get(r.user_id, ""),
            "source_user_id": r.source_user_id,
            "source_email": email_map.get(r.source_user_id, ""),
            "reward_type": r.reward_type,
            "reward_type_name": REWARD_TYPE_NAME.get(r.reward_type, r.reward_type or ""),
            "amount": float(r.amount or 0),
            "rate": float(r.rate or 0),
            "settle_batch": r.settle_batch or "",
            "remark": r.remark or "",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return {"success": True, "data": list_data, "total": total, "page": page, "page_size": page_size}
