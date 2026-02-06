"""
Node Checker - 节点心跳超时检测

查 dim_execution_node 表，检测 last_heartbeat_at 超时的节点。
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from sqlalchemy.orm import Session

from libs.execution_node.models import ExecutionNode
from libs.core.logger import get_logger

log = get_logger("node-checker")


@dataclass
class NodeStatus:
    node_code: str
    name: str
    base_url: str
    status: int  # 1=在线 0=禁用
    online: bool = False
    last_heartbeat: Optional[str] = None
    seconds_since_heartbeat: Optional[float] = None
    checked_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "node_code": self.node_code,
            "name": self.name,
            "base_url": self.base_url,
            "status": self.status,
            "online": self.online,
            "last_heartbeat": self.last_heartbeat,
            "seconds_since_heartbeat": round(self.seconds_since_heartbeat, 0) if self.seconds_since_heartbeat is not None else None,
            "checked_at": self.checked_at,
        }


class NodeChecker:
    """节点心跳超时检测器"""

    def __init__(self, db: Session, timeout_seconds: int = 180):
        """
        Args:
            db: 数据库 session
            timeout_seconds: 心跳超时秒数（默认 180s = 3 分钟）
        """
        self.db = db
        self.timeout_seconds = timeout_seconds

    def check_all(self) -> List[NodeStatus]:
        """检查所有活跃节点的心跳状态"""
        nodes = (
            self.db.query(ExecutionNode)
            .filter(ExecutionNode.status == 1)
            .order_by(ExecutionNode.id)
            .all()
        )
        now = datetime.utcnow()
        results: List[NodeStatus] = []
        for node in nodes:
            hb = node.last_heartbeat_at
            if hb:
                delta = (now - hb).total_seconds()
                online = delta < self.timeout_seconds
                hb_str = hb.strftime("%Y-%m-%d %H:%M:%S")
            else:
                delta = None
                online = False
                hb_str = None
            results.append(NodeStatus(
                node_code=node.node_code,
                name=node.name or node.node_code,
                base_url=node.base_url,
                status=node.status,
                online=online,
                last_heartbeat=hb_str,
                seconds_since_heartbeat=delta,
            ))
        return results
