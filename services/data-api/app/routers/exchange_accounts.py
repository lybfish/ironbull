"""
Data API - 交易所账户查看（仅管理员可访问）

GET /api/exchange-accounts -> 交易所账户列表（支持按租户/用户筛选）
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from libs.member.models import ExchangeAccount, User

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/exchange-accounts", tags=["exchange-accounts"])


def _account_dict(a: ExchangeAccount, email: str = "") -> dict:
    return {
        "id": a.id,
        "user_id": a.user_id,
        "user_email": email,
        "tenant_id": a.tenant_id,
        "exchange": a.exchange,
        "account_type": a.account_type,
        "api_key": a.api_key[:8] + "****" if a.api_key else "",  # 脱敏
        "balance": float(a.balance or 0),
        "futures_balance": float(a.futures_balance or 0),
        "futures_available": float(a.futures_available or 0),
        "execution_node_id": a.execution_node_id,
        "status": a.status,
        "last_sync_at": a.last_sync_at.isoformat() if a.last_sync_at else None,
        "last_sync_error": a.last_sync_error,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("")
def list_exchange_accounts(
    tenant_id: Optional[int] = Query(None, description="按租户筛选"),
    user_id: Optional[int] = Query(None, description="按用户筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """交易所账户列表"""
    query = db.query(ExchangeAccount, User.email).join(
        User, ExchangeAccount.user_id == User.id, isouter=True
    )
    if tenant_id is not None:
        query = query.filter(ExchangeAccount.tenant_id == tenant_id)
    if user_id is not None:
        query = query.filter(ExchangeAccount.user_id == user_id)
    query = query.order_by(ExchangeAccount.id.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "success": True,
        "data": [_account_dict(a, email or "") for a, email in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
