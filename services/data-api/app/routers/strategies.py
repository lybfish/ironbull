"""
策略与绑定查询 API（管理后台用）
- GET  /api/strategies - 策略列表
- GET  /api/strategies/{id} - 策略详情（单条）
- PUT  /api/strategies/{id} - 更新策略（管理员）
- POST /api/strategies/{id} - 更新策略（同上，推荐用 POST 避免代理对 PUT 的 404）
- PATCH /api/strategies/{id}/toggle - 启用/禁用
- GET  /api/strategy-bindings - 按租户的绑定列表（含用户点卡、账户信息）
"""

from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from libs.member.models import Strategy
from libs.member.repository import MemberRepository
from ..deps import get_db, get_tenant_id_optional, get_current_admin

router = APIRouter(prefix="/api", tags=["strategies"])


RISK_MODE_PCT = {1: 0.01, 2: 0.015, 3: 0.02}


class StrategyUpdateBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    symbol: Optional[str] = None
    symbols: Optional[List[str]] = None
    timeframe: Optional[str] = None
    exchange: Optional[str] = None
    market_type: Optional[str] = None
    min_capital: Optional[float] = None
    risk_level: Optional[int] = None
    capital: Optional[float] = None
    leverage: Optional[int] = None
    risk_mode: Optional[int] = None
    min_confidence: Optional[int] = None
    cooldown_minutes: Optional[int] = None
    status: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    show_to_user: Optional[int] = None
    user_display_name: Optional[str] = None
    user_description: Optional[str] = None


@router.get("/strategies")
def list_strategies(
    status: Optional[int] = Query(None, description="策略状态 1=启用 0=禁用，不传=全部"),
    tenant_id: Optional[int] = Depends(get_tenant_id_optional),
    db: Session = Depends(get_db),
):
    """策略目录列表（dim_strategy），不传 tenant_id 时返回全部策略"""
    repo = MemberRepository(db)
    strategies = repo.list_strategies(status=status)
    return {
        "success": True,
        "data": [_strategy_to_dict(s) for s in strategies],
        "total": len(strategies),
    }


def _strategy_to_dict(s: Strategy) -> dict:
    capital = float(getattr(s, "capital", 0) or 0)
    leverage = int(getattr(s, "leverage", 0) or 0)
    risk_mode = int(getattr(s, "risk_mode", 1) or 1)
    pct = RISK_MODE_PCT.get(risk_mode, 0.01)
    # 如果设置了 capital，自动计算 amount_usdt
    amount_usdt = round(capital * pct * leverage, 2) if capital > 0 and leverage > 0 else float(getattr(s, "amount_usdt", 0) or 0)
    return {
        "id": s.id,
        "code": s.code,
        "name": s.name,
        "description": (s.description or "").strip(),
        "symbol": s.symbol or "",
        "symbols": s.get_symbols() if hasattr(s, "get_symbols") else [s.symbol or ""],
        "timeframe": s.timeframe or "",
        "exchange": getattr(s, "exchange", None),
        "market_type": getattr(s, "market_type", "future"),
        "min_capital": float(s.min_capital or 200),
        "risk_level": int(s.risk_level or 1),
        "capital": capital,
        "leverage": leverage,
        "risk_mode": risk_mode,
        "risk_mode_label": {1: "稳健", 2: "均衡", 3: "激进"}.get(risk_mode, "稳健"),
        "amount_usdt": amount_usdt,
        "min_confidence": int(getattr(s, "min_confidence", 50) or 50),
        "cooldown_minutes": int(getattr(s, "cooldown_minutes", 60) or 60),
        "config": s.config if isinstance(s.config, dict) else {},
        "status": int(s.status or 1),
        "show_to_user": int(getattr(s, "show_to_user", 0) or 0),
        "user_display_name": getattr(s, "user_display_name", None) or "",
        "user_description": getattr(s, "user_description", None) or "",
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.get("/strategies/{strategy_id}")
def get_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
):
    """策略详情（单条）"""
    repo = MemberRepository(db)
    s = repo.get_strategy_by_id(strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="策略不存在")
    return {"success": True, "data": _strategy_to_dict(s)}


def _do_update_strategy(strategy_id: int, body: StrategyUpdateBody, db: Session):
    """更新策略逻辑（供 PUT/POST 共用）"""
    repo = MemberRepository(db)
    s = repo.get_strategy_by_id(strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="策略不存在")
    d = body.model_dump(exclude_unset=True) if hasattr(body, "model_dump") else body.dict(exclude_unset=True)
    for k, v in d.items():
        if k == "symbols" and v is not None:
            setattr(s, "symbols", v)
        elif hasattr(s, k):
            setattr(s, k, v)
    # 自动计算 amount_usdt = capital × risk_pct × leverage
    cap = float(s.capital or 0)
    lev = int(s.leverage or 20)
    rm = int(s.risk_mode or 1)
    if cap > 0 and lev > 0:
        pct = RISK_MODE_PCT.get(rm, 0.01)
        s.amount_usdt = round(cap * pct * lev, 2)
    repo.update_strategy(s)
    db.commit()
    return {"success": True, "data": _strategy_to_dict(s)}


@router.put("/strategies/{strategy_id}")
def update_strategy_put(
    strategy_id: int,
    body: StrategyUpdateBody,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """更新策略（管理员），PUT"""
    return _do_update_strategy(strategy_id, body, db)


@router.post("/strategies/{strategy_id}")
def update_strategy_post(
    strategy_id: int,
    body: StrategyUpdateBody,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """更新策略（管理员），POST（部分代理对 PUT 支持不佳时可用）"""
    return _do_update_strategy(strategy_id, body, db)


@router.patch("/strategies/{strategy_id}/toggle")
def toggle_strategy(
    strategy_id: int,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """启用/禁用策略"""
    repo = MemberRepository(db)
    s = repo.get_strategy_by_id(strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="策略不存在")
    s.status = 0 if s.status == 1 else 1
    repo.update_strategy(s)
    db.commit()
    return {"success": True, "status": int(s.status), "message": "已启用" if s.status == 1 else "已禁用"}


@router.get("/strategy-bindings")
def list_strategy_bindings(
    strategy_code: Optional[str] = Query(None, description="按策略码筛选"),
    status: Optional[int] = Query(None, description="绑定状态 0=关闭 1=开启"),
    tenant_id: Optional[int] = Depends(get_tenant_id_optional),
    db: Session = Depends(get_db),
):
    """当前租户下的策略绑定列表（含用户、账户、点卡）。不传 tenant_id 时返回空列表，页面可正常加载。"""
    if tenant_id is None:
        return {"success": True, "data": [], "total": 0}
    repo = MemberRepository(db)
    bindings = repo.list_bindings_by_tenant(tenant_id, strategy_code=strategy_code, status=status)
    result = []
    for b in bindings:
        user = repo.get_user_by_id(b.user_id)
        acc = repo.get_account_by_id(b.account_id)
        strategy = repo.get_strategy_by_code(b.strategy_code)
        strategy_name = strategy.name if strategy else b.strategy_code
        if strategy and user:
            ts = repo.get_tenant_strategy(tenant_id, strategy.id)
            if ts and (ts.display_name or "").strip():
                strategy_name = (ts.display_name or "").strip()
        point_total = 0.0
        if user:
            point_total = float(user.point_card_self or 0) + float(user.point_card_gift or 0)
        from libs.member.models import StrategyBinding as SB
        risk_mode = int(b.risk_mode or 1)
        result.append({
            "id": b.id,
            "user_id": b.user_id,
            "user_email": user.email if user else "",
            "account_id": b.account_id,
            "exchange": acc.exchange if acc else "",
            "strategy_code": b.strategy_code,
            "strategy_name": strategy_name,
            "mode": int(b.mode or 2),
            "status": int(b.status or 1),
            # 用户仓位参数
            "capital": float(b.capital or 0),
            "leverage": int(b.leverage or 20),
            "risk_mode": risk_mode,
            "risk_mode_label": SB.RISK_MODE_LABELS.get(risk_mode, "稳健"),
            "amount_usdt": float(b.amount_usdt) if b.capital else 0,
            # 统计
            "total_profit": float(b.total_profit or 0),
            "total_trades": int(b.total_trades or 0),
            "point_card_total": point_total,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        })
    return {"success": True, "data": result, "total": len(result)}
