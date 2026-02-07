"""
执行节点 API
- POST /api/nodes/{node_code}/heartbeat   - 节点心跳（节点调中心）
- GET  /api/nodes                          - 节点列表
- POST /api/nodes                          - 创建节点
- PUT  /api/nodes/{node_id}                - 编辑节点
- DELETE /api/nodes/{node_id}              - 删除/禁用节点
- GET  /api/nodes/{node_id}/accounts       - 查看分配到该节点的交易所账户
"""

from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from libs.execution_node import ExecutionNodeRepository
from libs.execution_node.models import ExecutionNode
from libs.member.models import ExchangeAccount, User
from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api", tags=["nodes"])


# ---------- 心跳（节点调用，无需管理员鉴权） ----------

@router.post("/nodes/{node_code}/heartbeat")
def node_heartbeat(
    node_code: str,
    db: Session = Depends(get_db),
):
    """执行节点心跳：节点定时调用，中心更新 last_heartbeat_at"""
    repo = ExecutionNodeRepository(db)
    if not repo.update_heartbeat(node_code):
        raise HTTPException(status_code=404, detail="节点不存在")
    return {"success": True, "message": "ok"}


# ---------- 节点 CRUD ----------

def _node_dict(n: ExecutionNode) -> dict:
    return {
        "id": n.id,
        "node_code": n.node_code,
        "name": n.name,
        "base_url": (n.base_url or "").rstrip("/"),
        "status": n.status,
        "last_heartbeat_at": n.last_heartbeat_at.isoformat() if n.last_heartbeat_at else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


@router.get("/nodes")
def list_nodes(
    include_disabled: bool = False,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """节点列表。默认仅 status=1，include_disabled=true 返回全部"""
    repo = ExecutionNodeRepository(db)
    if include_disabled:
        nodes = db.query(ExecutionNode).order_by(ExecutionNode.id).all()
    else:
        nodes = repo.list_active()

    # 统计每个节点绑定的账户数
    node_ids = [n.id for n in nodes]
    account_counts: Dict[int, int] = {}
    for nid in node_ids:
        account_counts[nid] = (
            db.query(ExchangeAccount)
            .filter(ExchangeAccount.execution_node_id == nid, ExchangeAccount.status == 1)
            .count()
        )

    return {
        "success": True,
        "data": [
            {**_node_dict(n), "account_count": account_counts.get(n.id, 0)}
            for n in nodes
        ],
        "total": len(nodes),
    }


class NodeCreateRequest(BaseModel):
    node_code: str
    name: str = ""
    base_url: str


@router.post("/nodes")
def create_node(
    body: NodeCreateRequest,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """创建执行节点"""
    repo = ExecutionNodeRepository(db)
    if repo.get_by_code(body.node_code):
        raise HTTPException(status_code=400, detail=f"node_code '{body.node_code}' 已存在")
    node = ExecutionNode(
        node_code=body.node_code,
        name=body.name or body.node_code,
        base_url=body.base_url.rstrip("/"),
        status=1,
    )
    repo.create(node)
    db.commit()
    return {"success": True, "data": _node_dict(node)}


class NodeUpdateRequest(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    status: Optional[int] = None


@router.put("/nodes/{node_id}")
def update_node(
    node_id: int,
    body: NodeUpdateRequest,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """编辑执行节点"""
    repo = ExecutionNodeRepository(db)
    node = repo.get_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")
    if body.name is not None:
        node.name = body.name
    if body.base_url is not None:
        node.base_url = body.base_url.rstrip("/")
    if body.status is not None:
        node.status = body.status
    repo.update(node)
    db.commit()
    return {"success": True, "data": _node_dict(node)}


@router.delete("/nodes/{node_id}")
def delete_node(
    node_id: int,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """禁用执行节点（status=0），并将绑定到该节点的账户重置为本机执行"""
    repo = ExecutionNodeRepository(db)
    node = repo.get_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")
    node.status = 0
    repo.update(node)
    # 将该节点下的账户全部回收到本机
    affected = (
        db.query(ExchangeAccount)
        .filter(ExchangeAccount.execution_node_id == node_id)
        .update({"execution_node_id": None})
    )
    db.commit()
    return {"success": True, "message": f"节点已禁用，{affected} 个账户已回收到本机", "data": _node_dict(node)}


# ---------- 查看节点关联的账户 ----------

@router.get("/nodes/{node_id}/accounts")
def list_node_accounts(
    node_id: int,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """查看分配到指定节点的交易所账户列表"""
    repo = ExecutionNodeRepository(db)
    node = repo.get_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")
    accounts = (
        db.query(ExchangeAccount, User.email)
        .join(User, ExchangeAccount.user_id == User.id, isouter=True)
        .filter(ExchangeAccount.execution_node_id == node_id)
        .order_by(ExchangeAccount.id)
        .all()
    )
    return {
        "success": True,
        "data": [
            {
                "id": a.id,
                "user_id": a.user_id,
                "user_email": email or "",
                "exchange": a.exchange,
                "account_type": a.account_type,
                "status": a.status,
            }
            for a, email in accounts
        ],
        "total": len(accounts),
        "node": _node_dict(node),
    }
