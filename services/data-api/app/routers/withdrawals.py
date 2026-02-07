"""
Data API - 提现管理（仅管理员可访问）

GET    /api/withdrawals               -> 提现列表（全平台）
POST   /api/withdrawals/{id}/approve  -> 审核通过
POST   /api/withdrawals/{id}/reject   -> 拒绝
POST   /api/withdrawals/{id}/complete -> 标记打款完成
"""

from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from libs.reward.withdrawal_service import WithdrawalService
from libs.reward.models import UserWithdrawal
from libs.member.models import User

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/withdrawals", tags=["withdrawals"])

STATUS_MAP = {0: "待审核", 1: "已通过", 2: "已拒绝", 3: "已完成"}


def _withdrawal_dict(w: UserWithdrawal, email: str = None) -> dict:
    return {
        "id": w.id,
        "user_id": w.user_id,
        "user_email": email or "",
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
    user_id: Optional[int] = Query(None, description="按用户ID筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 yyyy-MM-dd"),
    end_date: Optional[str] = Query(None, description="结束日期 yyyy-MM-dd"),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """提现列表（全平台，可按状态/用户/日期筛选），包含服务端统计"""
    # ---- 构建查询 ----
    q = db.query(UserWithdrawal, User.email).outerjoin(
        User, User.id == UserWithdrawal.user_id
    )
    if status is not None:
        q = q.filter(UserWithdrawal.status == status)
    if user_id is not None:
        q = q.filter(UserWithdrawal.user_id == user_id)
    if start_date:
        try:
            q = q.filter(UserWithdrawal.created_at >= datetime.strptime(start_date, "%Y-%m-%d"))
        except ValueError:
            pass
    if end_date:
        try:
            q = q.filter(UserWithdrawal.created_at < datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59))
        except ValueError:
            pass

    total = q.count()
    rows = q.order_by(UserWithdrawal.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # ---- 服务端统计（基于全量，不受分页影响）----
    stat_q = db.query(
        UserWithdrawal.status,
        func.count(UserWithdrawal.id).label("cnt"),
        func.coalesce(func.sum(UserWithdrawal.amount), 0).label("sum_amount"),
        func.coalesce(func.sum(UserWithdrawal.fee), 0).label("sum_fee"),
    ).group_by(UserWithdrawal.status).all()

    stats = {"pending": 0, "approved": 0, "rejected": 0, "completed": 0,
             "total_amount": 0, "total_fee": 0, "total_count": 0}
    for row in stat_q:
        s, cnt, amt, fee = row
        stats["total_count"] += cnt
        stats["total_amount"] += float(amt)
        stats["total_fee"] += float(fee)
        if s == 0:
            stats["pending"] = cnt
        elif s == 1:
            stats["approved"] = cnt
        elif s == 2:
            stats["rejected"] = cnt
        elif s == 3:
            stats["completed"] = cnt

    return {
        "success": True,
        "data": [_withdrawal_dict(w, email) for w, email in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "stats": stats,
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
