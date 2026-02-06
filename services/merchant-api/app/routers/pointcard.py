"""
Merchant API - 点卡管理（4 个接口）
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, Form
from sqlalchemy.orm import Session

from libs.tenant.models import Tenant
from libs.tenant.service import TenantService
from libs.pointcard.service import PointCardService
from libs.pointcard.repository import PointCardRepository
from libs.core.database import get_session
from ..deps import get_db, check_quota as get_tenant
from ..schemas import ok

router = APIRouter(prefix="/merchant", tags=["pointcard"])

CHANGE_TYPE_NAME = {1: "后台充值", 2: "后台赠送", 3: "分发给用户", 4: "转入", 5: "扣费"}


@router.get("/balance")
def balance(
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """获取商户点卡余额"""
    svc = TenantService(db)
    data = svc.get_balance(tenant.id)
    return ok(data)


@router.post("/user/recharge")
def user_recharge(
    user_id: int = Form(...),
    amount: float = Form(...),
    type: int = Form(2),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """给用户充值/赠送点卡。type=1 充值(self)，type=2 赠送(gift)"""
    use_self = type == 1
    svc = PointCardService(db)
    success, err, data = svc.recharge_user(tenant.id, user_id, Decimal(str(amount)), use_self)
    if not success:
        return {"code": 1, "msg": err, "data": None}
    return ok(data, msg="分发成功")


@router.get("/user/balance")
def user_balance(
    user_id: int,
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """获取用户点卡余额"""
    from libs.member.repository import MemberRepository
    repo = MemberRepository(db)
    user = repo.get_user_by_id(user_id, tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    self_val = float(user.point_card_self or 0)
    gift_val = float(user.point_card_gift or 0)
    return ok({
        "user_id": user_id,
        "point_card_self": self_val,
        "point_card_gift": gift_val,
        "point_card_total": self_val + gift_val,
    })


@router.get("/point-card/logs")
def point_card_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1),
    change_type: Optional[int] = None,
    member_id: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """点卡流水（商户维度，可筛 member_id）"""
    repo = PointCardRepository(db)
    items, total = repo.list_logs(
        tenant_id=tenant.id,
        page=page,
        limit=limit,
        change_type=change_type,
        member_id=member_id,
        start_time=start_time,
        end_time=end_time,
    )
    list_data = []
    for log in items:
        list_data.append({
            "id": log.id,
            "change_type": log.change_type,
            "change_type_name": CHANGE_TYPE_NAME.get(log.change_type, ""),
            "source_type": log.source_type,
            "amount": float(log.amount or 0),
            "before_self": float(log.before_self or 0),
            "after_self": float(log.after_self or 0),
            "before_gift": float(log.before_gift or 0),
            "after_gift": float(log.after_gift or 0),
            "member_id": log.user_id,
            "to_type": log.card_type,
            "remark": log.remark or "",
            "create_time": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
        })
    return ok({"list": list_data, "total": total, "page": page, "limit": limit})
