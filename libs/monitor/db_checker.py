"""
DB Checker - 数据库 + Redis 连通性检测
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from libs.core.logger import get_logger

log = get_logger("db-checker")


@dataclass
class DbStatus:
    mysql_ok: bool = False
    mysql_latency_ms: float = 0.0
    mysql_error: Optional[str] = None
    redis_ok: bool = False
    redis_latency_ms: float = 0.0
    redis_error: Optional[str] = None
    checked_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "mysql_ok": self.mysql_ok,
            "mysql_latency_ms": round(self.mysql_latency_ms, 1),
            "mysql_error": self.mysql_error,
            "redis_ok": self.redis_ok,
            "redis_latency_ms": round(self.redis_latency_ms, 1),
            "redis_error": self.redis_error,
            "checked_at": self.checked_at,
        }


class DbChecker:
    """数据库 + Redis 连通性检测器"""

    def check(self) -> DbStatus:
        status = DbStatus()

        # ---- MySQL ----
        start = time.time()
        try:
            from sqlalchemy import text
            from libs.core.database import get_engine
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            status.mysql_ok = True
            status.mysql_latency_ms = (time.time() - start) * 1000
        except Exception as e:
            status.mysql_latency_ms = (time.time() - start) * 1000
            status.mysql_error = str(e)
            log.error("MySQL 连接失败", error=str(e))

        # ---- Redis ----
        start = time.time()
        try:
            from libs.core.redis_client import check_redis_connection
            ok = check_redis_connection()
            status.redis_ok = ok
            status.redis_latency_ms = (time.time() - start) * 1000
            if not ok:
                status.redis_error = "ping 失败"
        except Exception as e:
            status.redis_latency_ms = (time.time() - start) * 1000
            status.redis_error = str(e)
            log.error("Redis 连接失败", error=str(e))

        return status
