"""
Data API - 平台级 Dashboard 汇总

GET /api/dashboard/summary -> 平台汇总数据（Redis 缓存 60s，减轻 DB 压力）
GET /api/dashboard/trends  -> 趋势数据（近 N 天的订单量、用户增长、交易额、利润池）
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from libs.tenant.models import Tenant
from libs.member.models import User, StrategyBinding
from libs.order_trade.models import Order, Fill
from libs.execution_node.models import ExecutionNode
from libs.reward.models import ProfitPool

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


@router.get("/trends")
def trends(
    days: int = Query(30, ge=7, le=90, description="趋势天数"),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    近 N 天趋势数据：
    - 每日订单量
    - 每日新增用户
    - 每日成交额
    - 每日利润池入池金额
    """
    start_date = datetime.now() - timedelta(days=days)

    # 构建日期序列
    date_list = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]

    # 1. 每日订单量
    order_rows = (
        db.query(cast(Order.created_at, Date).label("d"), func.count(Order.id))
        .filter(Order.created_at >= start_date)
        .group_by("d")
        .all()
    )
    order_map = {str(r[0]): r[1] for r in order_rows}

    # 2. 每日新增用户
    user_rows = (
        db.query(cast(User.created_at, Date).label("d"), func.count(User.id))
        .filter(User.created_at >= start_date)
        .group_by("d")
        .all()
    )
    user_map = {str(r[0]): r[1] for r in user_rows}

    # 3. 每日成交额 (fills.value)
    try:
        fill_rows = (
            db.query(cast(Fill.traded_at, Date).label("d"), func.sum(Fill.value))
            .filter(Fill.traded_at >= start_date)
            .group_by("d")
            .all()
        )
        fill_map = {str(r[0]): float(r[1] or 0) for r in fill_rows}
    except Exception:
        fill_map = {}

    # 4. 每日利润池入池金额
    pool_rows = (
        db.query(cast(ProfitPool.created_at, Date).label("d"), func.sum(ProfitPool.pool_amount))
        .filter(ProfitPool.created_at >= start_date)
        .group_by("d")
        .all()
    )
    pool_map = {str(r[0]): float(r[1] or 0) for r in pool_rows}

    return {
        "success": True,
        "data": {
            "dates": date_list,
            "orders": [order_map.get(d, 0) for d in date_list],
            "new_users": [user_map.get(d, 0) for d in date_list],
            "trade_volume": [round(fill_map.get(d, 0), 2) for d in date_list],
            "pool_amount": [round(pool_map.get(d, 0), 4) for d in date_list],
        },
    }
