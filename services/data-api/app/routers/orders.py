"""
Data API - 订单与成交查询

GET /api/orders
GET /api/fills
POST /api/manual-order -> 占位（返回 501，实际下单需 execution-node 等接入）
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException

from sqlalchemy.orm import Session
from pydantic import BaseModel

from libs.order_trade import OrderTradeService
from libs.order_trade.contracts import OrderFilter, FillFilter

from ..deps import get_db, get_tenant_id, get_account_id_optional
from ..serializers import dto_to_dict
from ..utils import parse_datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["orders"])


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
    try:
        filt = OrderFilter(
            tenant_id=tenant_id,
            account_id=account_id,
            symbol=symbol,
            exchange=exchange,
            side=side,
            status=status,
            signal_id=signal_id,
            start_time=parse_datetime(start_time),
            end_time=parse_datetime(end_time),
            limit=limit,
            offset=offset,
        )
        svc = OrderTradeService(db)
        orders, total = svc.list_orders(filt)
        return {"success": True, "data": [dto_to_dict(o) for o in orders], "total": total}
    except Exception as e:
        logger.exception("订单查询失败")
        raise HTTPException(status_code=500, detail=f"订单查询失败: {str(e)}")


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
    try:
        filt = FillFilter(
            tenant_id=tenant_id,
            account_id=account_id,
            order_id=order_id,
            symbol=symbol,
            side=side,
            start_time=parse_datetime(start_time),
            end_time=parse_datetime(end_time),
            limit=limit,
            offset=offset,
        )
        svc = OrderTradeService(db)
        fills, total = svc.list_fills(filt)
        return {"success": True, "data": [dto_to_dict(f) for f in fills], "total": total}
    except Exception as e:
        logger.exception("成交查询失败")
        raise HTTPException(status_code=500, detail=f"成交查询失败: {str(e)}")


class ManualOrderBody(BaseModel):
    """手动下单请求体（占位，实际由 execution-node 等实现）"""
    exchange: Optional[str] = None
    market_type: Optional[str] = None
    symbol: str = ""
    side: str = "buy"
    order_type: str = "market"
    amount: Optional[float] = None
    price: Optional[float] = None


@router.post("/manual-order")
def manual_order_placeholder(
    _body: ManualOrderBody,
) -> None:
    """占位：手动下单接口尚未在 data-api 实现，请通过 execution-node 或后续接入。返回 501 避免前端 404。"""
    raise HTTPException(
        status_code=501,
        detail="手动下单接口尚未实现，请通过 execution-node 或运维配置接入后再使用。",
    )
