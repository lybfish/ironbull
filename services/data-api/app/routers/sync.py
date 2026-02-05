"""
中心同步 API：向执行节点拉取余额/持仓并写回 fact_account / fact_position。
- POST /api/sync/balance   - 同步余额（可选 node_id、sandbox）
- POST /api/sync/positions - 同步持仓（可选 node_id、sandbox）
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from libs.sync_node import sync_balance_from_nodes, sync_positions_from_nodes
from ..deps import get_db

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/balance")
def post_sync_balance(
    node_id: Optional[int] = None,
    sandbox: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """向执行节点发起余额同步，并写回 fact_account。不传 node_id 则同步所有活跃节点。"""
    result = sync_balance_from_nodes(db, node_id=node_id, sandbox=sandbox)
    db.commit()
    return {"success": True, "result": result}


@router.post("/positions")
def post_sync_positions(
    node_id: Optional[int] = None,
    sandbox: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """向执行节点发起持仓同步，并写回 fact_position。不传 node_id 则同步所有活跃节点。"""
    result = sync_positions_from_nodes(db, node_id=node_id, sandbox=sandbox)
    db.commit()
    return {"success": True, "result": result}
