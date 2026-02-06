"""
Data API - 平台级 Dashboard 汇总

GET /api/dashboard/summary -> 平台汇总数据
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


@router.get("/summary")
def summary(
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """平台级汇总：租户数、用户数、订单数、节点数、策略绑定数"""
    total_tenants = db.query(func.count(Tenant.id)).scalar() or 0
    active_tenants = db.query(func.count(Tenant.id)).filter(Tenant.status == 1).scalar() or 0

    total_users = db.query(func.count(User.id)).scalar() or 0

    total_orders = db.query(func.count(Order.id)).scalar() or 0

    total_nodes = db.query(func.count(ExecutionNode.id)).scalar() or 0
    online_nodes = db.query(func.count(ExecutionNode.id)).filter(ExecutionNode.status == 1).scalar() or 0

    active_bindings = db.query(func.count(StrategyBinding.id)).filter(StrategyBinding.status == 1).scalar() or 0

    return {
        "success": True,
        "data": {
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "total_users": total_users,
            "total_orders": total_orders,
            "total_nodes": total_nodes,
            "online_nodes": online_nodes,
            "active_bindings": active_bindings,
        },
    }
