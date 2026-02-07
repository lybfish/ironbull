"""
Data API - 信号事件历史查询（仅管理员可访问）

GET /api/signal-events -> 信号事件列表
"""

import json
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from libs.facts.models import SignalEvent

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/signal-events", tags=["signal-events"])


def _event_dict(e: SignalEvent) -> dict:
    detail = e.detail
    if isinstance(detail, str):
        try:
            detail = json.loads(detail)
        except Exception:
            pass
    return {
        "id": e.id,
        "signal_id": e.signal_id,
        "task_id": e.task_id,
        "account_id": e.account_id,
        "event_type": e.event_type,
        "status": e.status,
        "source_service": e.source_service,
        "detail": detail,
        "error_code": e.error_code,
        "error_message": e.error_message,
        "request_id": e.request_id,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("")
def list_signal_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    signal_id: Optional[str] = Query(None, description="按信号ID筛选"),
    event_type: Optional[str] = Query(None, description="按事件类型筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    source_service: Optional[str] = Query(None, description="按来源服务筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 yyyy-MM-dd"),
    end_date: Optional[str] = Query(None, description="结束日期 yyyy-MM-dd"),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """信号事件列表"""
    query = db.query(SignalEvent).order_by(SignalEvent.id.desc())

    if signal_id:
        query = query.filter(SignalEvent.signal_id == signal_id)
    if event_type:
        query = query.filter(SignalEvent.event_type == event_type)
    if status:
        query = query.filter(SignalEvent.status == status)
    if source_service:
        query = query.filter(SignalEvent.source_service == source_service)
    if start_date:
        query = query.filter(SignalEvent.created_at >= f"{start_date} 00:00:00")
    if end_date:
        query = query.filter(SignalEvent.created_at <= f"{end_date} 23:59:59")

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "data": [_event_dict(e) for e in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
