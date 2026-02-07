"""
利润池管理 — 查看分发状态、手动重试失败的利润池

GET  /api/profit-pools            -> 利润池列表
POST /api/profit-pools/{id}/retry -> 手动重试失败的利润池
GET  /api/profit-pools/stats      -> 利润池统计
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from libs.reward.models import ProfitPool
from libs.reward.repository import RewardRepository
from libs.reward.service import RewardService
from libs.member.models import User

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/profit-pools", tags=["profit-pools"])

MAX_RETRY = 10  # 最大重试次数


def _pool_dict(p: ProfitPool, user_email: str = None) -> dict:
    return {
        "id": p.id,
        "user_id": p.user_id,
        "user_email": user_email or "",
        "profit_amount": float(p.profit_amount or 0),
        "deduct_amount": float(p.deduct_amount or 0),
        "self_deduct": float(p.self_deduct or 0),
        "gift_deduct": float(p.gift_deduct or 0),
        "pool_amount": float(p.pool_amount or 0),
        "tech_amount": float(p.tech_amount or 0),
        "network_amount": float(p.network_amount or 0),
        "platform_amount": float(p.platform_amount or 0),
        "direct_distributed": float(p.direct_distributed or 0),
        "diff_distributed": float(p.diff_distributed or 0),
        "peer_distributed": float(p.peer_distributed or 0),
        "network_undistributed": float(p.network_undistributed or 0),
        "status": p.status,
        "status_text": {1: "待结算", 2: "已结算", 3: "分发失败"}.get(p.status, "未知"),
        "retry_count": p.retry_count or 0,
        "last_error": p.last_error,
        "settle_batch": p.settle_batch,
        "settled_at": p.settled_at.isoformat() if p.settled_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.get("")
def list_profit_pools(
    status: Optional[int] = Query(None, description="状态: 1待结算 2已结算 3失败"),
    user_id: Optional[int] = Query(None, description="用户ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """利润池列表（支持按状态、用户筛选）"""
    query = db.query(ProfitPool)
    if status is not None:
        query = query.filter(ProfitPool.status == status)
    if user_id is not None:
        query = query.filter(ProfitPool.user_id == user_id)
    query = query.order_by(ProfitPool.id.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    # 批量获取用户邮箱
    user_ids = list({p.user_id for p in items})
    email_map: Dict[int, str] = {}
    if user_ids:
        rows = db.query(User.id, User.email).filter(User.id.in_(user_ids)).all()
        email_map = {r[0]: r[1] for r in rows}

    return {
        "success": True,
        "data": [_pool_dict(p, email_map.get(p.user_id)) for p in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/stats")
def profit_pool_stats(
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """利润池统计概览"""
    rows = (
        db.query(ProfitPool.status, func.count(ProfitPool.id), func.sum(ProfitPool.pool_amount))
        .group_by(ProfitPool.status)
        .all()
    )
    status_map = {1: "pending", 2: "settled", 3: "failed"}
    stats = {}
    for status_val, count, total_amount in rows:
        key = status_map.get(status_val, f"status_{status_val}")
        stats[key] = {"count": count, "total_amount": float(total_amount or 0)}

    # 失败中超过重试限制的数量
    stuck_count = (
        db.query(func.count(ProfitPool.id))
        .filter(ProfitPool.status == 3, ProfitPool.retry_count >= MAX_RETRY)
        .scalar() or 0
    )
    stats["stuck"] = {"count": stuck_count, "description": f"重试超过{MAX_RETRY}次无法恢复"}

    return {"success": True, "data": stats}


@router.post("/{pool_id}/retry")
def retry_profit_pool(
    pool_id: int,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """手动重试失败的利润池分发"""
    pool = db.query(ProfitPool).filter(ProfitPool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="利润池记录不存在")
    if pool.status == 2:
        raise HTTPException(status_code=400, detail="该利润池已结算完成，无需重试")
    if pool.status not in (1, 3):
        raise HTTPException(status_code=400, detail=f"当前状态 {pool.status} 不支持重试")

    try:
        RewardService(db).distribute_for_pool(pool)
        db.commit()
        return {
            "success": True,
            "message": f"利润池 #{pool_id} 分发成功",
            "data": _pool_dict(pool),
        }
    except Exception as e:
        db.rollback()
        # 更新重试次数和错误信息
        pool.retry_count = (pool.retry_count or 0) + 1
        pool.last_error = str(e)[:500]
        pool.status = 3
        db.add(pool)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"重试失败（第{pool.retry_count}次）：{str(e)[:200]}"
        )
