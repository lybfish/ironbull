"""
Data API - 系统监控端点

GET /api/monitor/status  -> 返回所有服务 + 节点 + DB/Redis 的实时状态
GET /api/monitor/metrics -> API 指标（延迟、错误率、请求量统计）
"""

from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from libs.core import get_config
from libs.monitor.health_checker import HealthChecker
from libs.monitor.node_checker import NodeChecker
from libs.monitor.db_checker import DbChecker
from libs.facts.models import AuditLog
from libs.order_trade.models import Order, Fill

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


def _build_service_list():
    """从配置构建服务列表"""
    config = get_config()
    services = config.get("monitor_services", None)
    if services:
        return [{"name": s["name"], "url": s["url"]} for s in services]
    return [
        {"name": "data-api", "url": "http://127.0.0.1:8026/health"},
        {"name": "merchant-api", "url": "http://127.0.0.1:8010/health"},
        {"name": "signal-monitor", "url": "http://127.0.0.1:8020/health"},
    ]


@router.get("/status")
def monitor_status(
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """系统监控状态：服务健康、节点心跳、DB/Redis"""
    config = get_config()
    node_timeout = config.get_int("monitor_node_timeout", 180)

    # 1. 服务健康
    services = _build_service_list()
    hc = HealthChecker(services, timeout=3.0)
    svc_statuses = hc.check_all()

    # 2. 节点心跳
    nc = NodeChecker(db, timeout_seconds=node_timeout)
    node_statuses = nc.check_all()

    # 3. DB/Redis
    dbc = DbChecker()
    db_status = dbc.check()

    # 汇总
    all_services_ok = all(s.healthy for s in svc_statuses)
    all_nodes_ok = all(n.online for n in node_statuses) if node_statuses else True
    all_db_ok = db_status.mysql_ok and db_status.redis_ok
    overall = "healthy" if (all_services_ok and all_nodes_ok and all_db_ok) else "degraded"

    return {
        "success": True,
        "data": {
            "overall": overall,
            "services": [s.to_dict() for s in svc_statuses],
            "nodes": [n.to_dict() for n in node_statuses],
            "db": db_status.to_dict(),
        },
    }


@router.get("/metrics")
def monitor_metrics(
    days: int = Query(7, ge=1, le=30),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    系统指标统计：
    - 审计日志维度：API 调用量、成功率、平均延迟
    - 业务维度：每日订单量、成交量
    - 按服务分组的错误分布
    """
    start = datetime.now() - timedelta(days=days)
    date_list = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]

    # 1. 每日 API 调用量（审计日志）
    api_rows = (
        db.query(cast(AuditLog.created_at, Date).label("d"), func.count(AuditLog.id))
        .filter(AuditLog.created_at >= start)
        .group_by("d")
        .all()
    )
    api_map = {str(r[0]): r[1] for r in api_rows}

    # 2. 每日错误数
    err_rows = (
        db.query(cast(AuditLog.created_at, Date).label("d"), func.count(AuditLog.id))
        .filter(AuditLog.created_at >= start, AuditLog.success == False)  # noqa: E712
        .group_by("d")
        .all()
    )
    err_map = {str(r[0]): r[1] for r in err_rows}

    # 3. 平均延迟（有 duration_ms 的记录）
    latency_rows = (
        db.query(
            cast(AuditLog.created_at, Date).label("d"),
            func.avg(AuditLog.duration_ms),
            func.max(AuditLog.duration_ms),
        )
        .filter(AuditLog.created_at >= start, AuditLog.duration_ms.isnot(None))
        .group_by("d")
        .all()
    )
    latency_avg_map = {str(r[0]): round(float(r[1] or 0), 1) for r in latency_rows}
    latency_max_map = {str(r[0]): round(float(r[2] or 0), 1) for r in latency_rows}

    # 4. 按服务统计错误数
    svc_err_rows = (
        db.query(AuditLog.source_service, func.count(AuditLog.id))
        .filter(AuditLog.created_at >= start, AuditLog.success == False)  # noqa: E712
        .group_by(AuditLog.source_service)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
        .all()
    )

    # 5. 总计指标
    total_calls = db.query(func.count(AuditLog.id)).filter(AuditLog.created_at >= start).scalar() or 0
    total_errors = db.query(func.count(AuditLog.id)).filter(
        AuditLog.created_at >= start, AuditLog.success == False  # noqa: E712
    ).scalar() or 0
    avg_latency = db.query(func.avg(AuditLog.duration_ms)).filter(
        AuditLog.created_at >= start, AuditLog.duration_ms.isnot(None)
    ).scalar()

    return {
        "success": True,
        "data": {
            "summary": {
                "total_calls": total_calls,
                "total_errors": total_errors,
                "error_rate": round(total_errors / total_calls * 100, 2) if total_calls > 0 else 0,
                "avg_latency_ms": round(float(avg_latency or 0), 1),
            },
            "daily": {
                "dates": date_list,
                "api_calls": [api_map.get(d, 0) for d in date_list],
                "errors": [err_map.get(d, 0) for d in date_list],
                "avg_latency": [latency_avg_map.get(d, 0) for d in date_list],
                "max_latency": [latency_max_map.get(d, 0) for d in date_list],
            },
            "error_by_service": [
                {"service": r[0] or "unknown", "count": r[1]} for r in svc_err_rows
            ],
        },
    }
