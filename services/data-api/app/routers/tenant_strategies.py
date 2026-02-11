"""
租户策略实例 API（管理后台）
- GET    /api/tenants/{tenant_id}/tenant-strategies - 列表
- POST   /api/tenants/{tenant_id}/tenant-strategies - 新增实例（可 copy_from_master）
- PUT    /api/tenants/{tenant_id}/tenant-strategies/{id} - 更新
- POST   /api/tenants/{tenant_id}/tenant-strategies/{id}/copy-from-master - 一键复制主策略参数
- DELETE /api/tenants/{tenant_id}/tenant-strategies/{id} - 删除实例
"""

from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from libs.member.models import Strategy, TenantStrategy
from libs.member.repository import MemberRepository
from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api", tags=["tenant-strategies"])

RISK_MODE_PCT = {1: 0.01, 2: 0.015, 3: 0.02}


class TenantStrategyCreate(BaseModel):
    strategy_id: int
    display_name: Optional[str] = None
    display_description: Optional[str] = None
    capital: Optional[float] = None
    leverage: Optional[int] = None
    risk_mode: Optional[int] = None
    max_loss_per_trade: Optional[float] = None
    min_capital: Optional[float] = None
    status: int = 1
    sort_order: int = 0
    copy_from_master: bool = False


class TenantStrategyUpdate(BaseModel):
    display_name: Optional[str] = None
    display_description: Optional[str] = None
    capital: Optional[float] = None
    leverage: Optional[int] = None
    risk_mode: Optional[int] = None
    max_loss_per_trade: Optional[float] = None
    min_capital: Optional[float] = None
    status: Optional[int] = None
    sort_order: Optional[int] = None


def _instance_to_dict(ts: TenantStrategy, strategy: Optional[Strategy] = None) -> dict:
    s = strategy
    # 各字段优先取实例覆盖值，否则继承主策略
    capital = float(ts.capital) if getattr(ts, "capital", None) is not None else (float(getattr(s, "capital", 0) or 0) if s else 0)
    leverage = ts.leverage if ts.leverage is not None else (int(getattr(s, "leverage", 0) or 0) if s else None)
    risk_mode = int(getattr(ts, "risk_mode", None) or 0) if getattr(ts, "risk_mode", None) is not None else (int(getattr(s, "risk_mode", 1) or 1) if s else 1)
    # 自动计算 amount_usdt
    lev = int(leverage or 0)
    pct = RISK_MODE_PCT.get(risk_mode, 0.01)
    amount_usdt = round(capital * pct * lev, 2) if capital > 0 and lev > 0 else (float(ts.amount_usdt) if ts.amount_usdt is not None else (float(getattr(s, "amount_usdt", 0) or 0) if s else 0))
    # 是否以损定仓（从主策略 config 获取）
    risk_based_sizing = False
    if s:
        try:
            cfg = s.get_config() if hasattr(s, "get_config") else {}
            risk_based_sizing = bool(cfg.get("risk_based_sizing", False))
        except Exception:
            pass
    # max_loss_per_trade: 优先取实例级直接设定值，否则 fallback capital × risk_pct
    db_max_loss = float(getattr(ts, "max_loss_per_trade", 0) or 0)
    if db_max_loss <= 0:
        s_max_loss = float(getattr(s, "max_loss_per_trade", 0) or 0) if s else 0
        db_max_loss = s_max_loss
    max_loss_per_trade = db_max_loss if db_max_loss > 0 else (round(capital * pct, 2) if capital > 0 else 0)
    return {
        "id": ts.id,
        "tenant_id": ts.tenant_id,
        "strategy_id": ts.strategy_id,
        "strategy_code": s.code if s else "",
        "strategy_name": s.name if s else "",
        "display_name": ts.display_name or (s.name if s else ""),
        "display_description": ts.display_description or (s.description or "" if s else ""),
        "capital": capital,
        "leverage": leverage,
        "risk_mode": risk_mode,
        "risk_mode_label": {1: "稳健", 2: "均衡", 3: "激进"}.get(risk_mode, "稳健"),
        "amount_usdt": amount_usdt,
        "risk_based_sizing": risk_based_sizing,
        "max_loss_per_trade": max_loss_per_trade,
        "min_capital": float(ts.min_capital) if ts.min_capital is not None else (float(getattr(s, "min_capital", 200) or 200) if s else None),
        "status": int(ts.status or 0),
        "sort_order": int(ts.sort_order or 0),
        "created_at": ts.created_at.isoformat() if ts.created_at else None,
    }


@router.get("/tenants/{tenant_id}/tenant-strategies")
def list_tenant_strategies(
    tenant_id: int,
    status: Optional[int] = None,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """租户下的策略实例列表（含主策略信息）"""
    try:
        repo = MemberRepository(db)
        items = repo.list_tenant_strategies(tenant_id, status=status)
    except Exception as e:
        if "dim_tenant_strategy" in str(e) or "doesn't exist" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail="租户策略表未初始化，请执行迁移: migrations/015_tenant_strategy_instance.sql",
            ) from e
        raise
    strategy_ids = [x.strategy_id for x in items]
    strategies = {}
    if strategy_ids:
        strategies = {s.id: s for s in repo.db.query(Strategy).filter(Strategy.id.in_(strategy_ids)).all()}
    list_data = [_instance_to_dict(ts, strategies.get(ts.strategy_id)) for ts in items]
    return {"success": True, "data": list_data, "total": len(list_data)}


@router.post("/tenants/{tenant_id}/tenant-strategies")
def create_tenant_strategy(
    tenant_id: int,
    body: TenantStrategyCreate,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """新增租户策略实例，可选一键复制主策略参数"""
    repo = MemberRepository(db)
    if repo.get_tenant_strategy(tenant_id, body.strategy_id):
        raise HTTPException(status_code=400, detail="该租户下已存在此策略实例")
    strategy = repo.get_strategy_by_id(body.strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="主策略不存在")
    ts = TenantStrategy(
        tenant_id=tenant_id,
        strategy_id=body.strategy_id,
        display_name=body.display_name,
        display_description=body.display_description,
        capital=body.capital,
        leverage=body.leverage,
        risk_mode=body.risk_mode,
        max_loss_per_trade=body.max_loss_per_trade,
        min_capital=body.min_capital,
        status=body.status,
        sort_order=body.sort_order,
    )
    if body.copy_from_master:
        ts.capital = float(getattr(strategy, "capital", 0) or 0) or None
        ts.leverage = int(getattr(strategy, "leverage", 0) or 0)
        ts.risk_mode = int(getattr(strategy, "risk_mode", 1) or 1)
        ts.max_loss_per_trade = float(getattr(strategy, "max_loss_per_trade", 0) or 0) or None
        ts.min_capital = float(getattr(strategy, "min_capital", 200) or 200)
        if not ts.display_name:
            ts.display_name = strategy.name
        if not ts.display_description and strategy.description:
            ts.display_description = (strategy.description or "").strip()
    # 自动计算 amount_usdt
    cap = float(ts.capital or 0)
    lev = int(ts.leverage or 0)
    rm = int(ts.risk_mode or 1)
    if cap > 0 and lev > 0:
        pct = RISK_MODE_PCT.get(rm, 0.01)
        ts.amount_usdt = round(cap * pct * lev, 2)
    repo.create_tenant_strategy(ts)
    db.commit()
    return {"success": True, "data": _instance_to_dict(ts, strategy)}


@router.put("/tenants/{tenant_id}/tenant-strategies/{instance_id}")
def update_tenant_strategy(
    tenant_id: int,
    instance_id: int,
    body: TenantStrategyUpdate,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """更新租户策略实例"""
    repo = MemberRepository(db)
    ts = repo.get_tenant_strategy_by_id(instance_id, tenant_id=tenant_id)
    if not ts:
        raise HTTPException(status_code=404, detail="实例不存在")
    d = body.model_dump(exclude_unset=True) if hasattr(body, 'model_dump') else body.dict(exclude_unset=True)
    for k, v in d.items():
        if hasattr(ts, k):
            setattr(ts, k, v)
    # 自动计算 amount_usdt
    cap = float(ts.capital or 0)
    lev = int(ts.leverage or 0)
    rm = int(getattr(ts, "risk_mode", 1) or 1)
    if cap > 0 and lev > 0:
        pct = RISK_MODE_PCT.get(rm, 0.01)
        ts.amount_usdt = round(cap * pct * lev, 2)
    repo.update_tenant_strategy(ts)
    db.commit()
    strategy = repo.get_strategy_by_id(ts.strategy_id)
    return {"success": True, "data": _instance_to_dict(ts, strategy)}


@router.post("/tenants/{tenant_id}/tenant-strategies/{instance_id}/copy-from-master")
def copy_from_master(
    tenant_id: int,
    instance_id: int,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """一键从主策略复制参数到该实例（leverage、amount_usdt、min_capital、display_name、display_description）"""
    repo = MemberRepository(db)
    ts = repo.get_tenant_strategy_by_id(instance_id, tenant_id=tenant_id)
    if not ts:
        raise HTTPException(status_code=404, detail="实例不存在")
    strategy = repo.get_strategy_by_id(ts.strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="主策略不存在")
    ts.capital = float(getattr(strategy, "capital", 0) or 0) or None
    ts.leverage = int(getattr(strategy, "leverage", 0) or 0)
    ts.risk_mode = int(getattr(strategy, "risk_mode", 1) or 1)
    ts.max_loss_per_trade = float(getattr(strategy, "max_loss_per_trade", 0) or 0) or None
    ts.min_capital = float(getattr(strategy, "min_capital", 200) or 200)
    # 自动计算 amount_usdt
    cap = float(ts.capital or 0)
    lev = int(ts.leverage or 0)
    rm = int(ts.risk_mode or 1)
    if cap > 0 and lev > 0:
        pct = RISK_MODE_PCT.get(rm, 0.01)
        ts.amount_usdt = round(cap * pct * lev, 2)
    if not ts.display_name:
        ts.display_name = strategy.name
    if not ts.display_description and strategy.description:
        ts.display_description = (strategy.description or "").strip()
    repo.update_tenant_strategy(ts)
    db.commit()
    return {"success": True, "data": _instance_to_dict(ts, strategy), "message": "已从主策略复制参数"}


@router.delete("/tenants/{tenant_id}/tenant-strategies/{instance_id}")
def delete_tenant_strategy(
    tenant_id: int,
    instance_id: int,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除租户策略实例"""
    repo = MemberRepository(db)
    ts = repo.get_tenant_strategy_by_id(instance_id, tenant_id=tenant_id)
    if not ts:
        raise HTTPException(status_code=404, detail="实例不存在")
    repo.delete_tenant_strategy(ts)
    db.commit()
    return {"success": True, "message": "已删除"}
