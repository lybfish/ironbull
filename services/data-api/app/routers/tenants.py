"""
Data API - 租户管理（仅管理员可访问）

GET    /api/tenants              -> 租户列表
POST   /api/tenants              -> 创建租户
PUT    /api/tenants/{id}         -> 编辑租户
PATCH  /api/tenants/{id}/toggle  -> 启用/禁用
POST   /api/tenants/{id}/recharge -> 充值点卡
"""

import secrets
from decimal import Decimal
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from libs.tenant.models import Tenant
from libs.quota.models import QuotaPlan
from libs.pointcard.models import PointCardLog
from libs.pointcard.service import (
    CHANGE_RECHARGE, SOURCE_ADMIN, CARD_SELF, CARD_GIFT,
)

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


class TenantCreate(BaseModel):
    name: str
    status: int = 1


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[int] = None


def _tenant_dict(t: Tenant, plan_name: str = None) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "app_key": t.app_key,
        "app_secret": t.app_secret,
        "root_user_id": t.root_user_id,
        "point_card_self": float(t.point_card_self or 0),
        "point_card_gift": float(t.point_card_gift or 0),
        "total_users": t.total_users or 0,
        "status": t.status,
        "quota_plan_id": t.quota_plan_id,
        "quota_plan_name": plan_name,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


@router.get("")
def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """租户列表（分页，含套餐名称）"""
    query = db.query(Tenant).order_by(Tenant.id.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    # 批量查套餐名
    plan_ids = {t.quota_plan_id for t in items if t.quota_plan_id}
    plan_map = {}
    if plan_ids:
        plans = db.query(QuotaPlan).filter(QuotaPlan.id.in_(plan_ids)).all()
        plan_map = {p.id: p.name for p in plans}
    return {
        "success": True,
        "data": [_tenant_dict(t, plan_map.get(t.quota_plan_id)) for t in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("")
def create_tenant(
    body: TenantCreate,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """创建租户（自动生成 app_key / app_secret）"""
    tenant = Tenant(
        name=body.name.strip(),
        app_key=secrets.token_hex(16),
        app_secret=secrets.token_hex(32),
        status=body.status,
    )
    db.add(tenant)
    db.flush()
    return {"success": True, "data": _tenant_dict(tenant)}


@router.put("/{tenant_id}")
def update_tenant(
    tenant_id: int,
    body: TenantUpdate,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """编辑租户"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    if body.name is not None:
        tenant.name = body.name.strip()
    if body.status is not None:
        tenant.status = body.status
    db.merge(tenant)
    db.flush()
    return {"success": True, "data": _tenant_dict(tenant)}


@router.patch("/{tenant_id}/toggle")
def toggle_tenant(
    tenant_id: int,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """启用/禁用租户"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    tenant.status = 0 if tenant.status == 1 else 1
    db.merge(tenant)
    db.flush()
    return {"success": True, "data": _tenant_dict(tenant)}


class RechargeBody(BaseModel):
    amount: float
    card_type: str = "self"  # self=自充, gift=赠送


@router.post("/{tenant_id}/recharge")
def recharge_point_card(
    tenant_id: int,
    body: RechargeBody,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """给租户充值点卡（补流水）"""
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="充值金额必须大于0")
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    amount = Decimal(str(body.amount))
    before_self = float(tenant.point_card_self or 0)
    before_gift = float(tenant.point_card_gift or 0)
    if body.card_type == "gift":
        tenant.point_card_gift = (tenant.point_card_gift or 0) + amount
    else:
        tenant.point_card_self = (tenant.point_card_self or 0) + amount
    db.merge(tenant)
    db.flush()
    after_self = float(tenant.point_card_self or 0)
    after_gift = float(tenant.point_card_gift or 0)
    # 写入点卡流水
    log = PointCardLog(
        tenant_id=tenant_id,
        user_id=None,
        change_type=CHANGE_RECHARGE,
        source_type=SOURCE_ADMIN,
        card_type=CARD_GIFT if body.card_type == "gift" else CARD_SELF,
        amount=float(amount),
        before_self=before_self,
        after_self=after_self,
        before_gift=before_gift,
        after_gift=after_gift,
        remark=f"后台充值({body.card_type})",
    )
    db.add(log)
    db.flush()
    return {"success": True, "data": _tenant_dict(tenant), "message": f"已充值 {body.amount} 点卡({body.card_type})"}
