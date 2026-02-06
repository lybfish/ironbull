"""
Data API - 订单与成交查询

GET /api/orders
GET /api/fills
"""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from libs.order_trade import OrderTradeService
from libs.order_trade.contracts import OrderFilter, FillFilter

from ..deps import get_db, get_tenant_id, get_account_id_optional
from ..serializers import dto_to_dict

router = APIRouter(prefix="/api", tags=["orders"])


def _parse_datetime(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


@router.get("/orders")
def list_orders(
    tenant_id: int = Depends(get_tenant_id),
    account_id: Optional[int] = Depends(get_account_id_optional),
    symbol: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    side: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    signal_id: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None, description="ISO datetime"),
    end_time: Optional[str] = Query(None, description="ISO datetime"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """订单列表（支持按租户、账户、标的、状态、时间范围过滤）"""
    filt = OrderFilter(
        tenant_id=tenant_id,
        account_id=account_id,
        symbol=symbol,
        exchange=exchange,
        side=side,
        status=status,
        signal_id=signal_id,
        start_time=_parse_datetime(start_time),
        end_time=_parse_datetime(end_time),
        limit=limit,
        offset=offset,
    )
    svc = OrderTradeService(db)
    orders, total = svc.list_orders(filt)
    return {"success": True, "data": [dto_to_dict(o) for o in orders], "total": total}


@router.get("/fills")
def list_fills(
    tenant_id: int = Depends(get_tenant_id),
    account_id: Optional[int] = Depends(get_account_id_optional),
    order_id: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    side: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None, description="ISO datetime"),
    end_time: Optional[str] = Query(None, description="ISO datetime"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """成交列表（支持按租户、账户、订单、标的、时间范围过滤）"""
    filt = FillFilter(
        tenant_id=tenant_id,
        account_id=account_id,
        order_id=order_id,
        symbol=symbol,
        side=side,
        start_time=_parse_datetime(start_time),
        end_time=_parse_datetime(end_time),
        limit=limit,
        offset=offset,
    )
    svc = OrderTradeService(db)
    fills, total = svc.list_fills(filt)
    return {"success": True, "data": [dto_to_dict(f) for f in fills], "total": total}
