"""
Pointcard Repository - 点卡流水数据访问
"""

from typing import Optional, List

from sqlalchemy.orm import Session

from .models import PointCardLog


class PointCardRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, log: PointCardLog) -> PointCardLog:
        self.db.add(log)
        self.db.flush()
        return log

    def list_logs(
        self,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
        page: int = 1,
        limit: int = 20,
        change_type: Optional[int] = None,
        member_id: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> tuple[List[PointCardLog], int]:
        q = self.db.query(PointCardLog)
        if tenant_id is not None:
            q = q.filter(PointCardLog.tenant_id == tenant_id)
        if user_id is not None:
            q = q.filter(PointCardLog.user_id == user_id)
        if member_id is not None:
            q = q.filter(PointCardLog.user_id == member_id)
        if change_type is not None:
            q = q.filter(PointCardLog.change_type == change_type)
        if start_time:
            q = q.filter(PointCardLog.created_at >= start_time)
        if end_time:
            q = q.filter(PointCardLog.created_at <= end_time)
        total = q.count()
        items = q.order_by(PointCardLog.id.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total
