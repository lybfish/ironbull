"""
Merchant API - 点卡管理（3 个接口）
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, Form
from sqlalchemy.orm import Session

from libs.tenant.models import Tenant
from libs.tenant.service import TenantService
from libs.pointcard.service import PointCardService
from libs.pointcard.repository import PointCardRepository
from ..deps import get_db, check_quota as get_tenant
from ..schemas import ok

router = APIRouter(prefix="/merchant", tags=["pointcard"])

# 商户代理商流水（未传 email）：change_type 中文名
CHANGE_TYPE_NAME_AGENT = {1: "后台充值", 2: "后台赠送", 3: "分发给用户"}
# 用户点卡流水（传了 email）：change_type 中文名
CHANGE_TYPE_NAME_USER = {1: "充值", 2: "赠送", 3: "转出", 4: "转入", 5: "盈利扣费"}
SOURCE_TYPE_NAME = {1: "自充", 2: "赠送"}


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
    email: str = Form(...),
    amount: float = Form(...),
    type: int = Form(2),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """给用户充值/赠送点卡。type=1 充值(self)，type=2 赠送(gift)"""
    from libs.member.repository import MemberRepository
    repo = MemberRepository(db)
    user = repo.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    use_self = type == 1
    svc = PointCardService(db)
    success, err, data = svc.recharge_user(tenant.id, user.id, Decimal(str(amount)), use_self)
    if not success:
        return {"code": 1, "msg": err, "data": None}
    return ok(data, msg="分发成功")


@router.get(
    "/point-card/logs",
    summary="点卡流水",
    description="分页查询点卡变动记录。传 email 时查该用户自己的点卡流水（App 点卡记录）；不传时查商户的代理商点卡流水。"
    " 返回 list[].remark 为系统写入的备注，取值见 docs/api/LEDGER_REMARKS.md（用户流水：代理商充值/赠送、转出/转入、盈利扣费30%；商户流水：后台充值、分发给用户#xxx 等）。",
)
def point_card_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1),
    change_type: Optional[int] = None,
    email: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """点卡流水（商户维度，可筛 email）。备注 remark 含义见 docs/api/LEDGER_REMARKS.md"""
    # 若传了 email 先解析为 user_id
    filter_user_id = None
    if email and email.strip():
        from libs.member.repository import MemberRepository
        repo_m = MemberRepository(db)
        u = repo_m.get_user_by_email(email.strip(), tenant.id)
        if not u:
            return ok({"list": [], "total": 0, "page": page, "limit": limit})
        filter_user_id = u.id
    repo = PointCardRepository(db)
    items, total = repo.list_logs(
        tenant_id=tenant.id,
        page=page,
        limit=limit,
        change_type=change_type,
        user_id=filter_user_id,
        start_time=start_time,
        end_time=end_time,
    )
    is_user_flow = filter_user_id is not None
    name_map = CHANGE_TYPE_NAME_USER if is_user_flow else CHANGE_TYPE_NAME_AGENT
    list_data = []
    for log in items:
        created_ts = int(log.created_at.timestamp()) if log.created_at else 0
        created_str = log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else ""
        # 用户流水：source_type 按文档 1=自充 2=赠送（用 card_type）；商户流水用原 source_type
        src_type = (log.card_type or 0) if is_user_flow else (log.source_type or 0)
        row = {
            "id": log.id,
            "change_type": log.change_type,
            "change_type_name": name_map.get(log.change_type, ""),
            "source_type": src_type,
            "amount": float(log.amount or 0),
            "before_self": float(log.before_self or 0),
            "after_self": float(log.after_self or 0),
            "before_gift": float(log.before_gift or 0),
            "after_gift": float(log.after_gift or 0),
            "member_id": log.related_user_id or log.user_id,
            "to_type": log.card_type,
            "remark": log.remark or "",
            "create_time": created_ts,
            "create_time_str": created_str,
        }
        if is_user_flow and (log.card_type or 0) in SOURCE_TYPE_NAME:
            row["source_type_name"] = SOURCE_TYPE_NAME.get(log.card_type, "")
        list_data.append(row)
    return ok({"list": list_data, "total": total, "page": page, "limit": limit})
