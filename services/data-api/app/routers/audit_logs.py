"""
Data API - 审计日志查询（仅管理员可访问）

GET /api/audit-logs         -> 审计日志列表（支持筛选）
GET /api/audit-logs/export  -> 导出 CSV
GET /api/audit-logs/stats   -> 操作统计
"""

from typing import Dict, Any, Optional
from io import StringIO
import csv

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from libs.facts.models import AuditLog

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


def _audit_dict(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "signal_id": log.signal_id,
        "task_id": log.task_id,
        "account_id": log.account_id,
        "user_id": log.user_id,
        "action": log.action or "",
        "status_before": log.status_before or "",
        "status_after": log.status_after or "",
        "source_service": log.source_service or "",
        "source_ip": log.source_ip or "",
        "detail": log.detail or "",
        "success": log.success,
        "error_code": log.error_code,
        "error_message": log.error_message,
        "retry_count": log.retry_count or 0,
        "duration_ms": log.duration_ms,
        "request_id": log.request_id,
        "trace_id": log.trace_id,
        "created_at": log.created_at.isoformat() if log.created_at else None,
        # 前端用的友好字段
        "admin_name": log.source_service or "",
        "target_type": "",
        "target_id": log.account_id or log.user_id or "",
        "ip": log.source_ip or "",
    }


def _build_query(db, action, admin_name, start_date, end_date, success, source_service):
    """构建审计日志通用查询"""
    query = db.query(AuditLog).order_by(AuditLog.id.desc())
    if action:
        query = query.filter(AuditLog.action.like(f"%{action}%"))
    if admin_name:
        query = query.filter(AuditLog.source_service.like(f"%{admin_name}%"))
    if start_date:
        query = query.filter(AuditLog.created_at >= f"{start_date} 00:00:00")
    if end_date:
        query = query.filter(AuditLog.created_at <= f"{end_date} 23:59:59")
    if success is not None:
        query = query.filter(AuditLog.success == success)
    if source_service:
        query = query.filter(AuditLog.source_service == source_service)
    return query


@router.get("")
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[str] = Query(None, description="按操作类型筛选"),
    admin_name: Optional[str] = Query(None, description="按操作人筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 yyyy-MM-dd"),
    end_date: Optional[str] = Query(None, description="结束日期 yyyy-MM-dd"),
    success: Optional[bool] = Query(None, description="是否成功"),
    source_service: Optional[str] = Query(None, description="来源服务"),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """审计日志列表"""
    query = _build_query(db, action, admin_name, start_date, end_date, success, source_service)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "data": [_audit_dict(log) for log in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/export")
def export_audit_logs(
    action: Optional[str] = Query(None),
    admin_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    success: Optional[bool] = Query(None),
    source_service: Optional[str] = Query(None),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """导出审计日志为 CSV"""
    query = _build_query(db, action, admin_name, start_date, end_date, success, source_service)
    items = query.limit(10000).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "操作", "来源服务", "来源IP", "状态变更(前)", "状态变更(后)",
        "成功", "错误码", "错误信息", "耗时(ms)", "详情", "时间"
    ])
    for log in items:
        writer.writerow([
            log.id,
            log.action or "",
            log.source_service or "",
            log.source_ip or "",
            log.status_before or "",
            log.status_after or "",
            "是" if log.success else "否",
            log.error_code or "",
            log.error_message or "",
            log.duration_ms or "",
            (log.detail or "")[:200],
            log.created_at.isoformat() if log.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )


@router.get("/stats")
def audit_log_stats(
    days: int = Query(30, ge=7, le=90),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """审计日志统计（按操作类型、按天分布）"""
    from datetime import datetime, timedelta
    start = datetime.now() - timedelta(days=days)

    # 按操作类型统计
    action_rows = (
        db.query(AuditLog.action, func.count(AuditLog.id))
        .filter(AuditLog.created_at >= start)
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
        .limit(20)
        .all()
    )

    # 按天分布
    daily_rows = (
        db.query(cast(AuditLog.created_at, Date).label("d"), func.count(AuditLog.id))
        .filter(AuditLog.created_at >= start)
        .group_by("d")
        .all()
    )
    daily_map = {str(r[0]): r[1] for r in daily_rows}
    date_list = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]

    # 成功/失败统计
    success_count = db.query(func.count(AuditLog.id)).filter(
        AuditLog.created_at >= start, AuditLog.success == True  # noqa: E712
    ).scalar() or 0
    fail_count = db.query(func.count(AuditLog.id)).filter(
        AuditLog.created_at >= start, AuditLog.success == False  # noqa: E712
    ).scalar() or 0

    return {
        "success": True,
        "data": {
            "by_action": [{"action": r[0] or "unknown", "count": r[1]} for r in action_rows],
            "daily": {
                "dates": date_list,
                "counts": [daily_map.get(d, 0) for d in date_list],
            },
            "success_count": success_count,
            "fail_count": fail_count,
        },
    }
