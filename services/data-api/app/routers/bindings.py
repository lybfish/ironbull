"""
Data API - 策略绑定查看（仅管理员可访问）

GET /api/strategy-bindings-admin -> 策略绑定列表（支持按租户/用户筛选）
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from libs.member.models import StrategyBinding, User

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/strategy-bindings-admin", tags=["bindings"])


def _binding_dict(b: StrategyBinding, email: str = "") -> dict:
    return {
        "id": b.id,
        "user_id": b.user_id,
        "user_email": email,
        "account_id": b.account_id,
        "strategy_code": b.strategy_code,
        "mode": b.mode,
        "ratio": b.ratio,
        "total_profit": float(b.total_profit or 0),
        "total_trades": b.total_trades or 0,
        "status": b.status,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


@router.get("")
def list_bindings(
    tenant_id: Optional[int] = Query(None, description="按租户筛选"),
    user_id: Optional[int] = Query(None, description="按用户筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """策略绑定列表"""
    query = db.query(StrategyBinding, User.email).join(
        User, StrategyBinding.user_id == User.id, isouter=True
    )
    if tenant_id is not None:
        query = query.filter(User.tenant_id == tenant_id)
    if user_id is not None:
        query = query.filter(StrategyBinding.user_id == user_id)
    query = query.order_by(StrategyBinding.id.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "success": True,
        "data": [_binding_dict(b, email or "") for b, email in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
