"""
Data API - 订单与成交查询

GET /api/orders
GET /api/fills
POST /api/manual-order   -> 手动下单（代理到 signal-monitor）
POST /api/close-position -> 手动平仓（代理到 signal-monitor）
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException

from sqlalchemy.orm import Session
from pydantic import BaseModel

from libs.order_trade import OrderTradeService
from libs.order_trade.contracts import OrderFilter, FillFilter

from ..deps import get_db, get_tenant_id, get_account_id_optional, get_current_admin
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
    trade_type: Optional[str] = Query(None, description="OPEN/CLOSE/ADD/REDUCE"),
    close_reason: Optional[str] = Query(None, description="SL/TP/SIGNAL/MANUAL/LIQUIDATION"),
    start_time: Optional[str] = Query(None, description="ISO datetime"),
    end_time: Optional[str] = Query(None, description="ISO datetime"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """订单列表（支持按租户、账户、标的、状态、交易类型、时间范围过滤）"""
    try:
        filt = OrderFilter(
            tenant_id=tenant_id,
            account_id=account_id,
            symbol=symbol,
            exchange=exchange,
            side=side,
            status=status,
            signal_id=signal_id,
            trade_type=trade_type,
            close_reason=close_reason,
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
    trade_type: Optional[str] = Query(None, description="OPEN/CLOSE/ADD/REDUCE"),
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
            trade_type=trade_type,
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
    """手动下单请求体"""
    exchange: Optional[str] = None
    market_type: Optional[str] = None
    symbol: str = ""
    side: str = "buy"
    order_type: str = "market"
    amount: Optional[float] = None
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: Optional[str] = None


class ClosePositionBody(BaseModel):
    """手动平仓请求体"""
    symbol: str
    account_id: Optional[int] = None
    position_side: Optional[str] = None  # LONG/SHORT，多空同时存在时必传


@router.post("/manual-order")
def manual_order(
    body: ManualOrderBody,
    _admin: dict = Depends(get_current_admin),
):
    """手动下单 — 代理到 signal-monitor /api/trading/execute"""
    import httpx
    from libs.core import get_config
    cfg = get_config()
    sm_url = cfg.get_str("signal_monitor_url", "http://127.0.0.1:8020").rstrip("/")

    payload = {
        "symbol": body.symbol,
        "side": body.side.upper(),
        "entry_price": body.price or 0,
        "stop_loss": body.stop_loss or 0,
        "take_profit": body.take_profit or 0,
        "confidence": 100,
    }
    if body.strategy:
        payload["strategy"] = body.strategy

    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(f"{sm_url}/api/trading/execute", json=payload)
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="无法连接 signal-monitor 服务，请确认已启动")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下单失败: {str(e)}")


@router.post("/close-position")
def close_position(
    body: ClosePositionBody,
    _admin: dict = Depends(get_current_admin),
):
    """手动平仓 — 代理到 signal-monitor /api/trading/close"""
    import httpx
    from libs.core import get_config
    cfg = get_config()
    sm_url = cfg.get_str("signal_monitor_url", "http://127.0.0.1:8020").rstrip("/")

    try:
        payload = {"symbol": body.symbol}
        if body.account_id is not None:
            payload["account_id"] = body.account_id
        if body.position_side:
            payload["position_side"] = body.position_side
        with httpx.Client(timeout=30.0) as client:
            r = client.post(f"{sm_url}/api/trading/close", json=payload)
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="无法连接 signal-monitor 服务")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"平仓失败: {str(e)}")
