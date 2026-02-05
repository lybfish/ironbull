"""
策略与绑定查询 API（管理后台用）
- GET /api/strategies - 策略列表
- GET /api/strategy-bindings - 按租户的绑定列表（含用户点卡、账户信息）
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from libs.member.repository import MemberRepository
from ..deps import get_db, get_tenant_id

router = APIRouter(prefix="/api", tags=["strategies"])


@router.get("/strategies")
def list_strategies(
    status: Optional[int] = Query(1, description="策略状态 1=启用"),
    tenant_id: int = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    """策略目录列表（dim_strategy）"""
    repo = MemberRepository(db)
    strategies = repo.list_strategies(status=status)
    return {
        "data": [
            {
                "id": s.id,
                "code": s.code,
                "name": s.name,
                "description": (s.description or "").strip(),
                "symbol": s.symbol or "",
                "timeframe": s.timeframe or "",
                "min_capital": float(s.min_capital or 200),
                "risk_level": int(s.risk_level or 1),
                "status": int(s.status or 1),
            }
            for s in strategies
        ],
        "total": len(strategies),
    }


@router.get("/strategy-bindings")
def list_strategy_bindings(
    strategy_code: Optional[str] = Query(None, description="按策略码筛选"),
    status: Optional[int] = Query(None, description="绑定状态 0=关闭 1=开启"),
    tenant_id: int = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    """当前租户下的策略绑定列表（含用户、账户、点卡）"""
    repo = MemberRepository(db)
    bindings = repo.list_bindings_by_tenant(tenant_id, strategy_code=strategy_code, status=status)
    result = []
    for b in bindings:
        user = repo.get_user_by_id(b.user_id)
        acc = repo.get_account_by_id(b.account_id)
        strategy = repo.get_strategy_by_code(b.strategy_code)
        point_total = 0.0
        if user:
            point_total = float(user.point_card_self or 0) + float(user.point_card_gift or 0)
        result.append({
            "id": b.id,
            "user_id": b.user_id,
            "user_email": user.email if user else "",
            "account_id": b.account_id,
            "exchange": acc.exchange if acc else "",
            "strategy_code": b.strategy_code,
            "strategy_name": strategy.name if strategy else b.strategy_code,
            "mode": int(b.mode or 2),
            "status": int(b.status or 1),
            "total_profit": float(b.total_profit or 0),
            "total_trades": int(b.total_trades or 0),
            "point_card_total": point_total,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        })
    return {"data": result, "total": len(result)}
