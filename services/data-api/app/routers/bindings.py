"""
Data API - 策略绑定查看（仅管理员可访问）

GET /api/strategy-bindings-admin -> 策略绑定列表（支持按租户/用户/状态筛选）
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from libs.member.models import StrategyBinding, User, ExchangeAccount, Strategy
from libs.tenant.models import Tenant

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/strategy-bindings-admin", tags=["bindings"])


def _binding_dict(b: StrategyBinding, user: User = None, tenant: Tenant = None, strategy: Strategy = None, account: ExchangeAccount = None) -> dict:
    # 交易所账户标签
    acc_label = ""
    if account:
        acc_label = f"{account.exchange}({account.api_key[:8]}...)" if account.api_key else account.exchange

    return {
        "id": b.id,
        "user_id": b.user_id,
        "user_email": user.email if user else "",
        "tenant_id": user.tenant_id if user else None,
        "tenant_name": tenant.name if tenant else "",
        "account_id": b.account_id,
        "exchange": account.exchange if account else "",
        "exchange_account_label": acc_label,
        "strategy_code": b.strategy_code,
        "strategy_name": strategy.name if strategy else b.strategy_code,
        "mode": int(b.mode or 2),
        "ratio": int(b.ratio or 100),
        "total_profit": float(b.total_profit or 0),
        "total_trades": int(b.total_trades or 0),
        "point_card_self": float(user.point_card_self or 0) if user else 0,
        "point_card_gift": float(user.point_card_gift or 0) if user else 0,
        "point_card_total": (float(user.point_card_self or 0) + float(user.point_card_gift or 0)) if user else 0,
        "status": int(b.status or 1),
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


@router.get("")
def list_bindings(
    tenant_id: Optional[int] = Query(None, description="按租户筛选"),
    user_id: Optional[int] = Query(None, description="按用户筛选"),
    status: Optional[int] = Query(None, description="按状态筛选 0=停止 1=运行"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """策略绑定列表（含用户、租户、策略、账户信息）"""
    query = db.query(StrategyBinding).join(
        User, StrategyBinding.user_id == User.id, isouter=True
    )

    if tenant_id is not None:
        query = query.filter(User.tenant_id == tenant_id)
    if user_id is not None:
        query = query.filter(StrategyBinding.user_id == user_id)
    if status is not None:
        query = query.filter(StrategyBinding.status == status)

    query = query.order_by(StrategyBinding.id.desc())
    total = query.count()
    bindings = query.offset((page - 1) * page_size).limit(page_size).all()

    # 批量加载关联数据
    user_ids = list(set(b.user_id for b in bindings))
    account_ids = list(set(b.account_id for b in bindings))
    strategy_codes = list(set(b.strategy_code for b in bindings))

    users_map = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        users_map = {u.id: u for u in users}

    tenant_ids = list(set(u.tenant_id for u in users_map.values() if u.tenant_id))
    tenants_map = {}
    if tenant_ids:
        tenants = db.query(Tenant).filter(Tenant.id.in_(tenant_ids)).all()
        tenants_map = {t.id: t for t in tenants}

    accounts_map = {}
    if account_ids:
        accounts = db.query(ExchangeAccount).filter(ExchangeAccount.id.in_(account_ids)).all()
        accounts_map = {a.id: a for a in accounts}

    strategies_map = {}
    if strategy_codes:
        strategies = db.query(Strategy).filter(Strategy.code.in_(strategy_codes)).all()
        strategies_map = {s.code: s for s in strategies}

    result = []
    for b in bindings:
        user = users_map.get(b.user_id)
        tenant = tenants_map.get(user.tenant_id) if user else None
        strategy = strategies_map.get(b.strategy_code)
        account = accounts_map.get(b.account_id)
        result.append(_binding_dict(b, user=user, tenant=tenant, strategy=strategy, account=account))

    return {
        "success": True,
        "data": result,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
