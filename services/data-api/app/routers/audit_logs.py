"""
Data API - 审计日志查询（仅管理员可访问）

GET /api/audit-logs -> 审计日志列表（支持筛选）
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

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


@router.get("")
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[str] = Query(None, description="按操作类型筛选"),
    admin_name: Optional[str] = Query(None, description="按操作人筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 yyyy-MM-dd"),
    end_date: Optional[str] = Query(None, description="结束日期 yyyy-MM-dd"),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """审计日志列表"""
    query = db.query(AuditLog).order_by(AuditLog.id.desc())

    if action:
        query = query.filter(AuditLog.action.like(f"%{action}%"))
    if admin_name:
        query = query.filter(AuditLog.source_service.like(f"%{admin_name}%"))
    if start_date:
        query = query.filter(AuditLog.created_at >= f"{start_date} 00:00:00")
    if end_date:
        query = query.filter(AuditLog.created_at <= f"{end_date} 23:59:59")

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "data": [_audit_dict(log) for log in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
