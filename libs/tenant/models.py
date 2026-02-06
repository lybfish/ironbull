"""
Tenant Models - 租户/代理商表
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.mysql import DECIMAL

from libs.core.database import Base


class Tenant(Base):
    """
    租户/代理商表
    """
    __tablename__ = "dim_tenant"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="代理商名称")
    app_key = Column(String(64), nullable=False, unique=True, index=True, comment="API Key")
    app_secret = Column(String(128), nullable=False, comment="API Secret")
    root_user_id = Column(Integer, nullable=True, comment="根用户ID")
    point_card_self = Column(DECIMAL(20, 8), nullable=False, default=0, comment="自充点卡余额")
    point_card_gift = Column(DECIMAL(20, 8), nullable=False, default=0, comment="赠送点卡余额")
    total_users = Column(Integer, nullable=False, default=0, comment="用户总数")
    tech_reward_total = Column(DECIMAL(20, 8), nullable=False, default=0, comment="累计技术团队分配")
    undist_reward_total = Column(DECIMAL(20, 8), nullable=False, default=0, comment="累计网体未分配")
    status = Column(Integer, nullable=False, default=1, comment="状态 1正常 0禁用")
    quota_plan_id = Column(Integer, nullable=True, comment="套餐ID，关联 dim_quota_plan")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
