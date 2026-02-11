"""
Data API - 信号事件历史查询（仅管理员可访问）

GET /api/signal-events -> 信号事件列表（含服务端统计）
GET /api/signal-events/strategies -> 可选策略列表（用于前端下拉框）
"""

import json
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
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


@router.get("/strategies")
def list_signal_strategies(
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    返回信号事件中出现过的所有策略代码列表，供前端下拉筛选。
    同时从 dim_strategy 获取可读名称。
    """
    # 从 fact_signal_event 的 detail JSON 中提取不重复的 strategy 值
    rows = db.execute(text(
        "SELECT DISTINCT JSON_UNQUOTE(JSON_EXTRACT(detail, '$.strategy')) AS strat "
        "FROM fact_signal_event "
        "WHERE detail IS NOT NULL AND JSON_EXTRACT(detail, '$.strategy') IS NOT NULL "
        "ORDER BY strat"
    )).fetchall()
    codes = [r[0] for r in rows if r[0]]

    # 从 dim_strategy 获取可读名称
    name_map = {}
    if codes:
        placeholders = ",".join([f":c{i}" for i in range(len(codes))])
        bind = {f"c{i}": c for i, c in enumerate(codes)}
        name_rows = db.execute(
            text(f"SELECT code, name FROM dim_strategy WHERE code IN ({placeholders})"),
            bind
        ).fetchall()
        name_map = {r[0]: r[1] for r in name_rows}

    return {
        "success": True,
        "data": [
            {"code": c, "name": name_map.get(c, c)}
            for c in codes
        ],
    }


@router.get("")
def list_signal_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    signal_id: Optional[str] = Query(None, description="按信号ID筛选"),
    event_type: Optional[str] = Query(None, description="按事件类型筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    source_service: Optional[str] = Query(None, description="按来源服务筛选"),
    strategy_code: Optional[str] = Query(None, description="按策略代码筛选（匹配 detail JSON 中的 strategy 字段）"),
    start_date: Optional[str] = Query(None, description="开始日期 yyyy-MM-dd"),
    end_date: Optional[str] = Query(None, description="结束日期 yyyy-MM-dd"),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """信号事件列表（含全局统计）"""
    query = db.query(SignalEvent).order_by(SignalEvent.id.desc())

    if signal_id:
        query = query.filter(SignalEvent.signal_id == signal_id)
    if event_type:
        query = query.filter(SignalEvent.event_type == event_type)
    if status:
        query = query.filter(SignalEvent.status == status)
    if source_service:
        query = query.filter(SignalEvent.source_service == source_service)
    if strategy_code:
        # detail 是 TEXT 类型存储的 JSON，通过 JSON_EXTRACT 筛选
        query = query.filter(
            text("JSON_UNQUOTE(JSON_EXTRACT(detail, '$.strategy')) = :strat").bindparams(strat=strategy_code)
        )
    if start_date:
        query = query.filter(SignalEvent.created_at >= f"{start_date} 00:00:00")
    if end_date:
        query = query.filter(SignalEvent.created_at <= f"{end_date} 23:59:59")

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    # 服务端统计（全局，不受筛选影响）
    stats_rows = db.query(
        SignalEvent.status,
        func.count(SignalEvent.id),
    ).group_by(SignalEvent.status).all()

    stats_map = {s: c for s, c in stats_rows}
    global_total = sum(stats_map.values())
    executed = stats_map.get("executed", 0)
    failed = stats_map.get("failed", 0) + stats_map.get("rejected", 0)
    pending = global_total - executed - failed

    return {
        "success": True,
        "data": [_event_dict(e) for e in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "stats": {
            "total": global_total,
            "executed": executed,
            "failed": failed,
            "pending": pending,
        },
    }
