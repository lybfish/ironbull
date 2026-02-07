"""
Execution Node Model - 执行节点表
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from libs.core.database import Base


class ExecutionNode(Base):
    """
    执行节点表（dim_execution_node）
    """
    __tablename__ = "dim_execution_node"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_code = Column(String(32), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False, default="")
    base_url = Column(String(255), nullable=False)
    status = Column(Integer, nullable=False, default=1)  # 1 在线 0 禁用
    last_heartbeat_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
