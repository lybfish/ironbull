"""
Execution Node Repository - 节点数据访问
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from .models import ExecutionNode


class ExecutionNodeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, node_id: int) -> Optional[ExecutionNode]:
        return self.db.query(ExecutionNode).filter(ExecutionNode.id == node_id).first()

    def get_by_code(self, node_code: str) -> Optional[ExecutionNode]:
        return self.db.query(ExecutionNode).filter(ExecutionNode.node_code == node_code).first()

    def list_active(self, limit: int = 200) -> List[ExecutionNode]:
        return (
            self.db.query(ExecutionNode)
            .filter(ExecutionNode.status == 1)
            .order_by(ExecutionNode.id)
            .limit(limit)
            .all()
        )

    def update_heartbeat(self, node_code: str) -> bool:
        node = self.get_by_code(node_code)
        if not node:
            return False
        node.last_heartbeat_at = datetime.now()
        self.db.merge(node)
        self.db.flush()
        return True

    def create(self, node: ExecutionNode) -> ExecutionNode:
        self.db.add(node)
        self.db.flush()
        return node

    def update(self, node: ExecutionNode) -> ExecutionNode:
        self.db.merge(node)
        self.db.flush()
        return node
