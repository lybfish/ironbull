"""
Merchant API - 会员分销与奖励（8 个接口）
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, Form
from sqlalchemy.orm import Session

from libs.tenant.models import Tenant
from libs.member.service import MemberService
from libs.member.level_service import LevelService
from libs.pointcard.service import PointCardService
from libs.reward.withdrawal_service import WithdrawalService
from libs.reward.repository import RewardRepository
from ..deps import get_db, get_tenant
from ..schemas import ok

router = APIRouter(prefix="/merchant", tags=["reward"])

REWARD_TYPE_NAME = {"direct": "直推奖", "level_diff": "级差奖", "peer": "平级奖"}
WITHDRAWAL_STATUS_NAME = {0: "待审核", 1: "已通过", 2: "已拒绝", 3: "已完成"}


@router.post("/user/transfer-point-card")
def transfer_point_card(
    from_user_id: int = Form(...),
    to_user_id: int = Form(...),
    amount: float = Form(...),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """点卡互转（同一邀请链路）"""
    svc = PointCardService(db)
    success, err, data = svc.transfer(tenant.id, from_user_id, to_user_id, Decimal(str(amount)))
    if not success:
        return {"code": 1, "msg": err, "data": None}
    return ok(data, msg="转账成功")


@router.get("/user/level")
def user_level(
    user_id: int,
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """用户等级"""
    from libs.member.repository import MemberRepository
    repo = MemberRepository(db)
    user = repo.get_user_by_id(user_id, tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    level_svc = LevelService(db)
    self_hold = level_svc.get_self_hold(user_id)
    return ok({
        "user_id": user_id,
        "level": user.member_level or 0,
        "level_name": level_svc.get_level_name(user.member_level or 0),
        "is_market_node": user.is_market_node or 0,
        "team_performance": float(user.team_performance or 0),
        "self_hold": float(self_hold),
        "reward_usdt": float(user.reward_usdt or 0),
        "total_reward": float(user.total_reward or 0),
        "withdrawn_reward": float(user.withdrawn_reward or 0),
    })


@router.get("/user/team")
def user_team(
    user_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """用户团队（直推）"""
    from libs.member.repository import MemberRepository
    repo = MemberRepository(db)
    user = repo.get_user_by_id(user_id, tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    level_svc = LevelService(db)
    items, total = repo.get_direct_members(user_id, page, limit)
    list_data = []
    for u in items:
        sub_count = repo.count_invitees(u.id)
        list_data.append({
            "user_id": u.id,
            "email": u.email,
            "level": u.member_level or 0,
            "level_name": level_svc.get_level_name(u.member_level or 0),
            "is_market_node": u.is_market_node or 0,
            "self_hold": float(level_svc.get_self_hold(u.id)),
            "team_performance": float(u.team_performance or 0),
            "sub_count": sub_count,
            "create_time": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else "",
        })
    sub_ids = repo.get_all_sub_user_ids(user_id)
    team_perf = repo.sum_futures_balance_by_user_ids(sub_ids) if sub_ids else Decimal("0")
    self_hold = level_svc.get_self_hold(user_id)
    return ok({
        "list": list_data,
        "total": total,
        "page": page,
        "limit": limit,
        "team_stats": {
            "direct_count": total,
            "total_count": len(sub_ids),
            "team_performance": float(team_perf),
            "self_hold": float(self_hold),
        },
    })


@router.post("/user/set-market-node")
def set_market_node(
    user_id: int = Form(...),
    is_node: int = Form(...),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """设置市场节点"""
    from libs.member.repository import MemberRepository
    repo = MemberRepository(db)
    user = repo.get_user_by_id(user_id, tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    user.is_market_node = 1 if is_node else 0
    repo.update_user(user)
    return ok(None, msg="已设置为市场节点" if is_node else "已取消市场节点资格")


@router.get("/user/rewards")
def user_rewards(
    user_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1),
    reward_type: Optional[str] = None,
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """奖励记录"""
    from libs.member.repository import MemberRepository
    repo_m = MemberRepository(db)
    user = repo_m.get_user_by_id(user_id, tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    repo = RewardRepository(db)
    items, total = repo.list_rewards(user_id, page, limit, reward_type)
    list_data = []
    for r in items:
        list_data.append({
            "id": r.id,
            "reward_type": r.reward_type,
            "reward_type_name": REWARD_TYPE_NAME.get(r.reward_type, r.reward_type),
            "amount": float(r.amount or 0),
            "source_user_id": r.source_user_id,
            "source_email": "",
            "rate": float(r.rate or 0),
            "settle_batch": r.settle_batch or "",
            "remark": r.remark or "",
            "create_time": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
        })
    return ok({"list": list_data, "total": total, "page": page, "limit": limit})


@router.get("/user/reward-balance")
def user_reward_balance(
    user_id: int,
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """奖励余额"""
    from libs.member.repository import MemberRepository
    repo = MemberRepository(db)
    user = repo.get_user_by_id(user_id, tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    return ok({
        "user_id": user_id,
        "reward_usdt": float(user.reward_usdt or 0),
        "total_reward": float(user.total_reward or 0),
        "withdrawn_reward": float(user.withdrawn_reward or 0),
    })


@router.post("/user/withdraw")
def user_withdraw(
    user_id: int = Form(...),
    amount: float = Form(...),
    wallet_address: str = Form(...),
    wallet_network: Optional[str] = Form("TRC20"),
    remark: Optional[str] = Form(None),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """申请提现"""
    svc = WithdrawalService(db)
    w, err = svc.apply(user_id, tenant.id, Decimal(str(amount)), wallet_address, wallet_network or "TRC20", remark)
    if err:
        return {"code": 1, "msg": err, "data": None}
    return ok({
        "withdrawal_id": w.id,
        "amount": float(w.amount),
        "fee": float(w.fee),
        "actual_amount": float(w.actual_amount),
        "status": w.status,
        "status_name": WITHDRAWAL_STATUS_NAME.get(w.status, ""),
        "create_time": w.created_at.strftime("%Y-%m-%d %H:%M:%S") if w.created_at else "",
    }, msg="申请成功")


@router.get("/user/withdrawals")
def user_withdrawals(
    user_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1),
    status: Optional[int] = None,
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """提现记录"""
    from libs.member.repository import MemberRepository
    repo_m = MemberRepository(db)
    user = repo_m.get_user_by_id(user_id, tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    repo = RewardRepository(db)
    items, total = repo.list_withdrawals(user_id, page, limit, status)
    list_data = []
    for w in items:
        list_data.append({
            "id": w.id,
            "amount": float(w.amount),
            "fee": float(w.fee),
            "actual_amount": float(w.actual_amount),
            "wallet_address": w.wallet_address,
            "wallet_network": w.wallet_network,
            "status": w.status,
            "status_name": WITHDRAWAL_STATUS_NAME.get(w.status, ""),
            "tx_hash": w.tx_hash or "",
            "audit_time": w.audit_at.strftime("%Y-%m-%d %H:%M:%S") if w.audit_at else "",
            "complete_time": w.completed_at.strftime("%Y-%m-%d %H:%M:%S") if w.completed_at else "",
            "create_time": w.created_at.strftime("%Y-%m-%d %H:%M:%S") if w.created_at else "",
        })
    return ok({"list": list_data, "total": total, "page": page, "limit": limit})
