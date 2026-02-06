"""
Data API - 交易所账户管理（仅管理员可访问）

GET    /api/exchange-accounts                          -> 账户列表
PUT    /api/exchange-accounts/{account_id}/assign-node  -> 分配执行节点
POST   /api/exchange-accounts/batch-assign-node         -> 批量分配执行节点
"""

from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from libs.member.models import ExchangeAccount, User
from libs.execution_node import ExecutionNodeRepository

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/exchange-accounts", tags=["exchange-accounts"])


def _account_dict(a: ExchangeAccount, email: str = "") -> dict:
    return {
        "id": a.id,
        "user_id": a.user_id,
        "user_email": email,
        "tenant_id": a.tenant_id,
        "exchange": a.exchange,
        "account_type": a.account_type,
        "api_key": a.api_key[:8] + "****" if a.api_key else "",  # 脱敏
        "balance": float(a.balance or 0),
        "futures_balance": float(a.futures_balance or 0),
        "futures_available": float(a.futures_available or 0),
        "execution_node_id": a.execution_node_id,
        "status": a.status,
        "last_sync_at": a.last_sync_at.isoformat() if a.last_sync_at else None,
        "last_sync_error": a.last_sync_error,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("")
def list_exchange_accounts(
    tenant_id: Optional[int] = Query(None, description="按租户筛选"),
    user_id: Optional[int] = Query(None, description="按用户筛选"),
    execution_node_id: Optional[int] = Query(None, description="按节点筛选"),
    unassigned: Optional[bool] = Query(None, description="仅未分配节点的账户"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """交易所账户列表（支持按节点筛选 / 查看未分配账户）"""
    query = db.query(ExchangeAccount, User.email).join(
        User, ExchangeAccount.user_id == User.id, isouter=True
    )
    if tenant_id is not None:
        query = query.filter(ExchangeAccount.tenant_id == tenant_id)
    if user_id is not None:
        query = query.filter(ExchangeAccount.user_id == user_id)
    if execution_node_id is not None:
        query = query.filter(ExchangeAccount.execution_node_id == execution_node_id)
    if unassigned:
        query = query.filter(
            (ExchangeAccount.execution_node_id == None) | (ExchangeAccount.execution_node_id == 0)  # noqa: E711
        )
    query = query.order_by(ExchangeAccount.id.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "success": True,
        "data": [_account_dict(a, email or "") for a, email in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ---------- 分配节点 ----------

class AssignNodeRequest(BaseModel):
    execution_node_id: Optional[int] = None  # None 或 0 = 回收到本机


@router.put("/{account_id}/assign-node")
def assign_node(
    account_id: int,
    body: AssignNodeRequest,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    将交易所账户分配到指定执行节点。
    - execution_node_id = null/0：回收到本机执行
    - execution_node_id = N：分配到节点 N（会校验节点存在且启用）
    """
    account = db.query(ExchangeAccount).filter(ExchangeAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")

    node_id = body.execution_node_id
    if node_id and node_id > 0:
        node_repo = ExecutionNodeRepository(db)
        node = node_repo.get_by_id(node_id)
        if not node:
            raise HTTPException(status_code=404, detail=f"节点 {node_id} 不存在")
        if node.status != 1:
            raise HTTPException(status_code=400, detail=f"节点 {node.name} 已禁用")
        account.execution_node_id = node_id
    else:
        account.execution_node_id = None

    db.merge(account)
    db.commit()

    email = ""
    user = db.query(User).filter(User.id == account.user_id).first()
    if user:
        email = user.email
    return {"success": True, "data": _account_dict(account, email)}


class BatchAssignRequest(BaseModel):
    account_ids: List[int]
    execution_node_id: Optional[int] = None  # None 或 0 = 回收到本机


@router.post("/batch-assign-node")
def batch_assign_node(
    body: BatchAssignRequest,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    批量分配账户到执行节点。
    - account_ids：要分配的账户 ID 列表
    - execution_node_id = null/0：回收到本机
    - execution_node_id = N：分配到节点 N
    """
    if not body.account_ids:
        raise HTTPException(status_code=400, detail="account_ids 不能为空")

    node_id = body.execution_node_id
    if node_id and node_id > 0:
        node_repo = ExecutionNodeRepository(db)
        node = node_repo.get_by_id(node_id)
        if not node:
            raise HTTPException(status_code=404, detail=f"节点 {node_id} 不存在")
        if node.status != 1:
            raise HTTPException(status_code=400, detail=f"节点 {node.name} 已禁用")
    else:
        node_id = None

    affected = (
        db.query(ExchangeAccount)
        .filter(ExchangeAccount.id.in_(body.account_ids))
        .update({"execution_node_id": node_id}, synchronize_session="fetch")
    )
    db.commit()

    return {
        "success": True,
        "affected": affected,
        "execution_node_id": node_id,
        "message": f"{affected} 个账户已{'回收到本机' if not node_id else '分配到节点 ' + str(node_id)}",
    }
