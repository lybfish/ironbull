"""
Data API - 提现管理（仅管理员可访问）

GET    /api/withdrawals               -> 提现列表（全平台）
POST   /api/withdrawals/{id}/approve  -> 审核通过
POST   /api/withdrawals/{id}/reject   -> 拒绝
POST   /api/withdrawals/{id}/complete -> 标记打款完成
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from libs.reward.withdrawal_service import WithdrawalService
from libs.reward.models import UserWithdrawal

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/withdrawals", tags=["withdrawals"])

STATUS_MAP = {0: "待审核", 1: "已通过", 2: "已拒绝", 3: "已完成"}


def _withdrawal_dict(w: UserWithdrawal) -> dict:
    return {
        "id": w.id,
        "user_id": w.user_id,
        "amount": float(w.amount),
        "fee": float(w.fee),
        "actual_amount": float(w.actual_amount),
        "wallet_address": w.wallet_address,
        "wallet_network": w.wallet_network,
        "status": w.status,
        "status_text": STATUS_MAP.get(w.status, "未知"),
        "tx_hash": w.tx_hash,
        "reject_reason": w.reject_reason,
        "audit_by": w.audit_by,
        "audit_at": w.audit_at.isoformat() if w.audit_at else None,
        "completed_at": w.completed_at.isoformat() if w.completed_at else None,
        "created_at": w.created_at.isoformat() if w.created_at else None,
        "updated_at": w.updated_at.isoformat() if w.updated_at else None,
    }


@router.get("")
def list_withdrawals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[int] = Query(None),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """提现列表（全平台，可按状态筛选）"""
    svc = WithdrawalService(db)
    items, total = svc.list_all_withdrawals(page, page_size, status)
    return {
        "success": True,
        "data": [_withdrawal_dict(w) for w in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


class RejectBody(BaseModel):
    reason: str = ""


class CompleteBody(BaseModel):
    tx_hash: str = ""


@router.post("/{withdrawal_id}/approve")
def approve_withdrawal(
    withdrawal_id: int,
    admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """审核通过提现"""
    svc = WithdrawalService(db)
    w, err = svc.approve(withdrawal_id, admin["admin_id"])
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"success": True, "data": _withdrawal_dict(w)}


@router.post("/{withdrawal_id}/reject")
def reject_withdrawal(
    withdrawal_id: int,
    body: RejectBody,
    admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """拒绝提现（退回余额）"""
    svc = WithdrawalService(db)
    w, err = svc.reject(withdrawal_id, admin["admin_id"], body.reason)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"success": True, "data": _withdrawal_dict(w)}


@router.post("/{withdrawal_id}/complete")
def complete_withdrawal(
    withdrawal_id: int,
    body: CompleteBody,
    admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """标记打款完成"""
    svc = WithdrawalService(db)
    w, err = svc.complete(withdrawal_id, body.tx_hash)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"success": True, "data": _withdrawal_dict(w)}
