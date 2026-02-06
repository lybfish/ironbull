"""
Merchant API - 会员分销与奖励（6 个接口）

- 点卡转账（邮箱互转）
- 用户团队（直推）
- 设置市场节点
- 奖励记录
- 申请提现
- 提现记录
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, Form
from sqlalchemy.orm import Session

from libs.tenant.models import Tenant
from libs.member.level_service import LevelService
from libs.pointcard.service import PointCardService
from libs.reward.withdrawal_service import WithdrawalService
from libs.reward.repository import RewardRepository
from ..deps import get_db, check_quota as get_tenant
from ..schemas import ok

router = APIRouter(prefix="/merchant", tags=["reward"])

REWARD_TYPE_NAME = {"direct": "直推奖", "level_diff": "级差奖", "peer": "平级奖"}
WITHDRAWAL_STATUS_NAME = {0: "待审核", 1: "已通过", 2: "已拒绝", 3: "已完成"}


@router.post("/user/transfer-point-card")
def transfer_point_card(
    from_email: str = Form(...),
    to_email: str = Form(...),
    amount: float = Form(...),
    type: int = Form(1),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """点卡互转（同一邀请链路）type=1 自充互转(self→self), type=2 赠送互转(gift→gift)"""
    from libs.member.repository import MemberRepository
    repo = MemberRepository(db)
    from_user = repo.get_user_by_email(from_email.strip(), tenant.id)
    if not from_user:
        return {"code": 1, "msg": "发送方邮箱不存在", "data": None}
    to_user = repo.get_user_by_email(to_email.strip(), tenant.id)
    if not to_user:
        return {"code": 1, "msg": "接收方邮箱不存在", "data": None}
    if from_user.id == to_user.id:
        return {"code": 1, "msg": "不能给自己转账", "data": None}
    svc = PointCardService(db)
    success, err, data = svc.transfer(tenant.id, from_user.id, to_user.id, Decimal(str(amount)), transfer_type=type)
    if not success:
        return {"code": 1, "msg": err, "data": None}
    type_name = data["type_name"]
    return ok({
        "from_email": from_email.strip(),
        "to_email": to_email.strip(),
        "type": data["type"],
        "type_name": type_name,
        "amount": data["amount"],
        "from_self_after": data["from_self_after"],
        "from_gift_after": data["from_gift_after"],
        "to_self_after": data["to_self_after"],
        "to_gift_after": data["to_gift_after"],
    }, msg=f"{type_name}成功")


@router.get("/user/team")
def user_team(
    email: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """用户团队（直推）"""
    from libs.member.repository import MemberRepository
    repo = MemberRepository(db)
    user = repo.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    level_svc = LevelService(db)
    items, total = repo.get_direct_members(user.id, page, limit)
    list_data = []
    for u in items:
        sub_count = repo.count_invitees(u.id)
        list_data.append({
            "user_id": u.id,
            "email": u.email,
            "level": u.member_level or 0,
            "level_name": level_svc.get_level_name(u.member_level or 0),
            "is_market_node": u.is_market_node or 0,
            "team_performance": float(u.team_performance or 0),
            "sub_count": sub_count,
            "create_time": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else "",
        })
    sub_ids = repo.get_all_sub_user_ids(user.id)
    team_perf = repo.sum_futures_balance_by_user_ids(sub_ids) if sub_ids else Decimal("0")
    self_hold = level_svc.get_self_hold(user.id)
    return ok({
        "list": list_data,
        "total": total,
        "page": page,
        "limit": limit,
        "team_stats": {
            "direct_count": total,
            "total_count": len(sub_ids),
            "total_performance": float(team_perf),
        },
    })


@router.post("/user/set-market-node")
def set_market_node(
    email: str = Form(...),
    is_node: int = Form(...),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """设置市场节点"""
    from libs.member.repository import MemberRepository
    repo = MemberRepository(db)
    user = repo.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    user.is_market_node = 1 if is_node else 0
    repo.update_user(user)
    return ok(None, msg="已设置为市场节点" if is_node else "已取消市场节点资格")


@router.get(
    "/user/rewards",
    summary="奖励流水",
    description="分页查询用户奖励记录（直推/级差/平级）。list[].remark 取值为：直推奖励、级差奖、平级奖。详见 docs/api/LEDGER_REMARKS.md。",
)
def user_rewards(
    email: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1),
    reward_type: Optional[str] = None,
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """奖励记录。备注 remark 含义见 docs/api/LEDGER_REMARKS.md"""
    from libs.member.repository import MemberRepository
    repo_m = MemberRepository(db)
    user = repo_m.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    repo = RewardRepository(db)
    items, total = repo.list_rewards(user.id, page, limit, reward_type)
    # 批量查 source_user 邮箱
    source_ids = {r.source_user_id for r in items if r.source_user_id}
    email_map = {}
    if source_ids:
        from libs.member.models import User
        rows = db.query(User.id, User.email).filter(User.id.in_(source_ids)).all()
        email_map = {row[0]: row[1] for row in rows}
    list_data = []
    for r in items:
        list_data.append({
            "id": r.id,
            "reward_type": r.reward_type,
            "reward_type_name": REWARD_TYPE_NAME.get(r.reward_type, r.reward_type),
            "amount": float(r.amount or 0),
            "source_user_id": r.source_user_id,
            "source_email": email_map.get(r.source_user_id, ""),
            "rate": float(r.rate or 0),
            "settle_batch": r.settle_batch or "",
            "remark": r.remark or "",
            "create_time": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
        })
    return ok({"list": list_data, "total": total, "page": page, "limit": limit})


@router.post("/user/withdraw")
def user_withdraw(
    email: str = Form(...),
    amount: float = Form(...),
    wallet_address: str = Form(...),
    wallet_network: Optional[str] = Form("TRC20"),
    remark: Optional[str] = Form(None),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """申请提现"""
    from libs.member.repository import MemberRepository
    repo_m = MemberRepository(db)
    user = repo_m.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    svc = WithdrawalService(db)
    w, err = svc.apply(user.id, tenant.id, Decimal(str(amount)), wallet_address, wallet_network or "TRC20", remark)
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
    email: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1),
    status: Optional[int] = None,
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """提现记录"""
    from libs.member.repository import MemberRepository
    repo_m = MemberRepository(db)
    user = repo_m.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    repo = RewardRepository(db)
    items, total = repo.list_withdrawals(user.id, page, limit, status)
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
