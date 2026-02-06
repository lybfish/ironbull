"""
配额计费管理 API（管理后台用）
- GET    /api/quota-plans          - 套餐列表
- POST   /api/quota-plans          - 创建套餐
- PUT    /api/quota-plans/{id}     - 更新套餐
- PATCH  /api/quota-plans/{id}/toggle - 启用/停用
- POST   /api/tenants/{id}/assign-plan - 给租户分配套餐
- GET    /api/quota-usage/{tenant_id}  - 租户用量查询
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from libs.quota import QuotaService
from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api", tags=["quota"])


class PlanCreate(BaseModel):
    name: str
    code: str
    api_calls_daily: int = 0
    api_calls_monthly: int = 0
    max_users: int = 0
    max_strategies: int = 0
    max_exchange_accounts: int = 0
    price_monthly: float = 0.0
    description: str = ""
    sort_order: int = 0


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    api_calls_daily: Optional[int] = None
    api_calls_monthly: Optional[int] = None
    max_users: Optional[int] = None
    max_strategies: Optional[int] = None
    max_exchange_accounts: Optional[int] = None
    price_monthly: Optional[float] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


class AssignPlan(BaseModel):
    plan_id: int


def _plan_dict(p):
    return {
        "id": p.id,
        "name": p.name,
        "code": p.code,
        "api_calls_daily": p.api_calls_daily,
        "api_calls_monthly": p.api_calls_monthly,
        "max_users": p.max_users,
        "max_strategies": p.max_strategies,
        "max_exchange_accounts": p.max_exchange_accounts,
        "price_monthly": float(p.price_monthly),
        "description": p.description,
        "status": p.status,
        "sort_order": p.sort_order,
    }


@router.get("/quota-plans")
def list_plans(
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    svc = QuotaService(db)
    plans = svc.list_plans(include_disabled=True)
    return {"data": [_plan_dict(p) for p in plans], "total": len(plans)}


@router.post("/quota-plans")
def create_plan(
    body: PlanCreate,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    svc = QuotaService(db)
    if svc.get_plan_by_code(body.code):
        raise HTTPException(status_code=400, detail=f"套餐编码 '{body.code}' 已存在")
    plan = svc.create_plan(**body.dict())
    db.commit()
    return {"code": 0, "data": _plan_dict(plan)}


@router.put("/quota-plans/{plan_id}")
def update_plan(
    plan_id: int,
    body: PlanUpdate,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    svc = QuotaService(db)
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="无更新字段")
    plan = svc.update_plan(plan_id, **updates)
    if not plan:
        raise HTTPException(status_code=404, detail="套餐不存在")
    db.commit()
    return {"code": 0, "data": _plan_dict(plan)}


@router.patch("/quota-plans/{plan_id}/toggle")
def toggle_plan(
    plan_id: int,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    svc = QuotaService(db)
    plan = svc.toggle_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="套餐不存在")
    db.commit()
    return {"code": 0, "status": plan.status}


@router.post("/tenants/{tenant_id}/assign-plan")
def assign_plan(
    tenant_id: int,
    body: AssignPlan,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    svc = QuotaService(db)
    ok = svc.assign_plan(tenant_id, body.plan_id)
    if not ok:
        raise HTTPException(status_code=400, detail="租户或套餐不存在")
    db.commit()
    return {"code": 0, "msg": "套餐分配成功"}


@router.get("/quota-usage/{tenant_id}")
def get_usage(
    tenant_id: int,
    days: int = 30,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    svc = QuotaService(db)
    api_check = svc.check_api_quota(tenant_id)
    resource_check = svc.check_resource_quota(tenant_id)
    history = svc.get_usage_history(tenant_id, days=days)
    return {
        "api_quota": api_check,
        "resource_quota": resource_check,
        "usage_history": history,
    }
