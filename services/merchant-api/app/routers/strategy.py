"""
Merchant API - 策略管理（4 个接口）
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Form
from sqlalchemy.orm import Session

from libs.tenant.models import Tenant
from libs.member.service import MemberService
from libs.member.repository import MemberRepository
from ..deps import get_db, check_quota as get_tenant
from ..schemas import ok

router = APIRouter(prefix="/merchant", tags=["strategy"])


@router.get("/strategies")
def strategies_list(
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """策略列表"""
    repo = MemberRepository(db)
    items = repo.list_strategies(status=1)
    list_data = []
    for s in items:
        cfg = (s.config or {}) if hasattr(s.config, "keys") else {}
        min_cap = float(cfg.get("min_capital", 200)) if isinstance(cfg, dict) else 200
        if hasattr(s, "min_capital") and s.min_capital is not None:
            min_cap = float(s.min_capital)
        list_data.append({
            "id": s.id,
            "name": s.name,
            "description": (s.description or "").strip() or (cfg.get("description", "") if isinstance(cfg, dict) else ""),
            "symbol": s.symbol,
            "timeframe": s.timeframe or "",
            "min_capital": min_cap,
            "status": s.status,
        })
    return ok(list_data)


@router.post("/user/strategy/open")
def strategy_open(
    email: str = Form(...),
    strategy_id: int = Form(...),
    account_id: int = Form(...),
    mode: int = Form(2),
    min_point_card: float = Form(1.0),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """开启策略（需满足最小点卡余额，默认 1.0）"""
    svc = MemberService(db)
    user = svc.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    binding, err = svc.open_strategy(user.id, tenant.id, strategy_id, account_id, mode=mode, min_point_card=min_point_card)
    if err:
        return {"code": 1, "msg": err, "data": None}
    return ok({
        "binding_id": binding.id,
        "strategy_id": strategy_id,
        "account_id": account_id,
        "mode": mode,
    }, msg="开启成功")


@router.post("/user/strategy/close")
def strategy_close(
    email: str = Form(...),
    strategy_id: int = Form(...),
    account_id: int = Form(...),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """关闭策略"""
    svc = MemberService(db)
    user = svc.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    if not svc.close_strategy(user.id, tenant.id, strategy_id, account_id):
        return {"code": 1, "msg": "策略绑定不存在", "data": None}
    return ok(None, msg="关闭成功")


@router.get("/user/strategies")
def user_strategies(
    email: str = Query(...),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """用户已绑定的策略列表"""
    svc = MemberService(db)
    user = svc.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    list_data = svc.get_user_strategies(user.id, tenant.id)
    return ok(list_data)
