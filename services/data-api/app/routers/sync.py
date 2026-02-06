"""
中心同步 API：向执行节点拉取余额/持仓并写回 fact_account / fact_position。
- POST /api/sync/balance   - 同步余额（可选 node_id、sandbox）
- POST /api/sync/positions - 同步持仓（可选 node_id、sandbox）
"""

import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from libs.sync_node import sync_balance_from_nodes, sync_positions_from_nodes
from ..deps import get_db, get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/balance")
def post_sync_balance(
    node_id: Optional[int] = None,
    sandbox: Optional[bool] = None,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """向执行节点发起余额同步，并写回 fact_account。不传 node_id 则同步所有活跃节点。"""
    try:
        result = sync_balance_from_nodes(db, node_id=node_id, sandbox=sandbox)
        db.commit()
        return {"success": True, "data": result}
    except Exception as e:
        logger.exception("余额同步失败")
        raise HTTPException(status_code=500, detail=f"余额同步失败: {str(e)}")


@router.post("/positions")
def post_sync_positions(
    node_id: Optional[int] = None,
    sandbox: Optional[bool] = None,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """向执行节点发起持仓同步，并写回 fact_position。不传 node_id 则同步所有活跃节点。"""
    try:
        result = sync_positions_from_nodes(db, node_id=node_id, sandbox=sandbox)
        db.commit()
        return {"success": True, "data": result}
    except Exception as e:
        logger.exception("持仓同步失败")
        raise HTTPException(status_code=500, detail=f"持仓同步失败: {str(e)}")
