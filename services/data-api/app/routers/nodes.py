"""
执行节点 API（心跳、列表）
- POST /api/nodes/{node_code}/heartbeat - 节点心跳（节点调中心）
- GET /api/nodes - 节点列表（管理后台用，需鉴权）
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from libs.execution_node import ExecutionNodeRepository
from ..deps import get_db

router = APIRouter(prefix="/api", tags=["nodes"])


@router.post("/nodes/{node_code}/heartbeat")
def node_heartbeat(
    node_code: str,
    db: Session = Depends(get_db),
):
    """执行节点心跳：节点定时调用，中心更新 last_heartbeat_at"""
    repo = ExecutionNodeRepository(db)
    if not repo.update_heartbeat(node_code):
        raise HTTPException(status_code=404, detail="节点不存在")
    return {"code": 0, "msg": "ok"}


@router.get("/nodes")
def list_nodes(db: Session = Depends(get_db)):
    """节点列表（仅 status=1），供管理后台或 signal-monitor 路由使用"""
    repo = ExecutionNodeRepository(db)
    nodes = repo.list_active()
    return {
        "data": [
            {
                "id": n.id,
                "node_code": n.node_code,
                "name": n.name,
                "base_url": n.base_url.rstrip("/"),
                "status": n.status,
                "last_heartbeat_at": n.last_heartbeat_at.isoformat() if n.last_heartbeat_at else None,
            }
            for n in nodes
        ],
        "total": len(nodes),
    }
