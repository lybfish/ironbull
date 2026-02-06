"""
Data API - 系统监控端点

GET /api/monitor/status -> 返回所有服务 + 节点 + DB/Redis 的实时状态
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from libs.core import get_config
from libs.monitor.health_checker import HealthChecker
from libs.monitor.node_checker import NodeChecker
from libs.monitor.db_checker import DbChecker

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
        "code": 0,
        "msg": "ok",
        "data": {
            "overall": overall,
            "services": [s.to_dict() for s in svc_statuses],
            "nodes": [n.to_dict() for n in node_statuses],
            "db": db_status.to_dict(),
        },
    }
