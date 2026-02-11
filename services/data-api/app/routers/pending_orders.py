"""
Data API - 限价挂单管理（管理后台用）
- GET  /api/pending-limit-orders              - 查询限价挂单列表
- GET  /api/pending-limit-orders/stats        - 挂单统计
- POST /api/pending-limit-orders/{id}/cancel  - 手动撤单（代理到 signal-monitor）
"""

import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from libs.position.models import PendingLimitOrder

from ..deps import get_db, get_tenant_id_optional, get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["pending-limit-orders"])


def _pending_to_dict(row: PendingLimitOrder) -> dict:
    return {
        "id": row.id,
        "pending_key": row.pending_key,
        "order_id": row.order_id,
        "exchange_order_id": row.exchange_order_id,
        "symbol": row.symbol,
        "side": row.side,
        "entry_price": float(row.entry_price) if row.entry_price else None,
        "stop_loss": float(row.stop_loss) if row.stop_loss else None,
        "take_profit": float(row.take_profit) if row.take_profit else None,
        "strategy_code": row.strategy_code,
        "account_id": row.account_id,
        "tenant_id": row.tenant_id,
        "amount_usdt": float(row.amount_usdt) if row.amount_usdt else None,
        "leverage": row.leverage,
        "timeframe": row.timeframe,
        "retest_bars": row.retest_bars,
        "confirm_after_fill": bool(row.confirm_after_fill),
        "post_fill_confirm_bars": row.post_fill_confirm_bars,
        "filled_price": float(row.filled_price) if row.filled_price else None,
        "filled_qty": float(row.filled_qty) if row.filled_qty else None,
        "filled_at": row.filled_at.isoformat() if row.filled_at else None,
        "candles_checked": row.candles_checked,
        "status": row.status,
        "placed_at": row.placed_at.isoformat() if row.placed_at else None,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/pending-limit-orders")
def list_pending_limit_orders(
    tenant_id: Optional[int] = Depends(get_tenant_id_optional),
    account_id: Optional[int] = Query(None, description="按账户ID筛选"),
    strategy_code: Optional[str] = Query(None, description="按策略编码筛选"),
    symbol: Optional[str] = Query(None, description="按交易对筛选"),
    status: Optional[str] = Query(None, description="PENDING/FILLED/CONFIRMING/EXPIRED/CANCELLED"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: Dict[str, Any] = Depends(get_current_admin),
):
    """限价挂单列表"""
    try:
        query = db.query(PendingLimitOrder).order_by(PendingLimitOrder.id.desc())

        if tenant_id is not None:
            query = query.filter(PendingLimitOrder.tenant_id == tenant_id)
        if account_id is not None:
            query = query.filter(PendingLimitOrder.account_id == account_id)
        if strategy_code:
            query = query.filter(PendingLimitOrder.strategy_code == strategy_code)
        if symbol:
            query = query.filter(PendingLimitOrder.symbol == symbol)
        if status:
            query = query.filter(PendingLimitOrder.status == status)

        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "success": True,
            "data": [_pending_to_dict(row) for row in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        logger.exception("查询限价挂单失败")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/pending-limit-orders/stats")
def pending_limit_orders_stats(
    tenant_id: Optional[int] = Depends(get_tenant_id_optional),
    db: Session = Depends(get_db),
    _admin: Dict[str, Any] = Depends(get_current_admin),
):
    """限价挂单统计"""
    try:
        query = db.query(
            PendingLimitOrder.status,
            func.count(PendingLimitOrder.id),
        )
        if tenant_id is not None:
            query = query.filter(PendingLimitOrder.tenant_id == tenant_id)
        rows = query.group_by(PendingLimitOrder.status).all()

        stats = {s: c for s, c in rows}
        return {
            "success": True,
            "stats": {
                "pending": stats.get("PENDING", 0),
                "filled": stats.get("FILLED", 0),
                "confirming": stats.get("CONFIRMING", 0),
                "expired": stats.get("EXPIRED", 0),
                "cancelled": stats.get("CANCELLED", 0),
                "total": sum(stats.values()),
            },
        }
    except Exception as e:
        logger.exception("统计限价挂单失败")
        raise HTTPException(status_code=500, detail=f"统计失败: {str(e)}")


@router.post("/pending-limit-orders/{order_id}/cancel")
def cancel_pending_limit_order(
    order_id: int,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    手动撤销限价挂单。
    代理到 signal-monitor 的撤单接口，由 signal-monitor 负责在交易所撤单 + 更新内存 + 更新 DB。
    """
    # 先查 DB 确认订单存在
    row = db.query(PendingLimitOrder).filter(PendingLimitOrder.id == order_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="挂单不存在")
    if row.status not in ("PENDING", "CONFIRMING"):
        raise HTTPException(
            status_code=400,
            detail=f"当前状态 {row.status} 不可撤单，仅 PENDING/CONFIRMING 可撤"
        )

    # 代理到 signal-monitor
    import httpx
    from libs.core import get_config
    cfg = get_config()
    sm_url = cfg.get_str("signal_monitor_url", "http://127.0.0.1:8020").rstrip("/")

    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                f"{sm_url}/api/pending-orders/cancel",
                json={
                    "pending_key": row.pending_key,
                    "reason": f"管理员 {_admin.get('username', '?')} 手动撤单",
                },
            )
            r.raise_for_status()
            result = r.json()
            return {"success": True, "message": "撤单指令已发送", "detail": result}
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="无法连接 signal-monitor 服务，请确认已启动")
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"signal-monitor 撤单失败: {e.response.text}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"撤单失败: {str(e)}")
