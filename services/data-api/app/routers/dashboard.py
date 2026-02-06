"""
Data API - 平台级 Dashboard 汇总

GET /api/dashboard/summary -> 平台汇总数据（Redis 缓存 60s，减轻 DB 压力）
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from libs.tenant.models import Tenant
from libs.member.models import User, StrategyBinding
from libs.order_trade.models import Order
from libs.execution_node.models import ExecutionNode

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

CACHE_KEY_DASHBOARD = "ironbull:cache:dashboard:summary"
CACHE_TTL = 60  # 秒


def _compute_summary(db: Session) -> dict:
    total_tenants = db.query(func.count(Tenant.id)).scalar() or 0
    active_tenants = db.query(func.count(Tenant.id)).filter(Tenant.status == 1).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    total_nodes = db.query(func.count(ExecutionNode.id)).scalar() or 0
    online_nodes = db.query(func.count(ExecutionNode.id)).filter(ExecutionNode.status == 1).scalar() or 0
    active_bindings = db.query(func.count(StrategyBinding.id)).filter(StrategyBinding.status == 1).scalar() or 0
    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "total_users": total_users,
        "total_orders": total_orders,
        "total_nodes": total_nodes,
        "online_nodes": online_nodes,
        "active_bindings": active_bindings,
    }


@router.get("/summary")
def summary(
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """平台级汇总：租户数、用户数、订单数、节点数、策略绑定数（缓存 60s）"""
    try:
        from libs.core.redis_client import get_json, set_with_ttl
        cached = get_json(CACHE_KEY_DASHBOARD)
        if cached and isinstance(cached, dict) and "data" in cached:
            return {"success": True, "data": cached["data"], "cached": True}
    except Exception:
        pass

    data = _compute_summary(db)
    try:
        from libs.core.redis_client import set_with_ttl
        set_with_ttl(CACHE_KEY_DASHBOARD, {"data": data}, CACHE_TTL)
    except Exception:
        pass
    return {"success": True, "data": data, "cached": False}
