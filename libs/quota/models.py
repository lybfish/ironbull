"""配额计费 — ORM Models"""

from sqlalchemy import Column, Integer, String, DateTime, Date, DECIMAL
from sqlalchemy.sql import func

from libs.core.database import Base


class QuotaPlan(Base):
    """套餐定义"""
    __tablename__ = "dim_quota_plan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    code = Column(String(32), nullable=False, unique=True)
    api_calls_daily = Column(Integer, nullable=False, default=0)
    api_calls_monthly = Column(Integer, nullable=False, default=0)
    max_users = Column(Integer, nullable=False, default=0)
    max_strategies = Column(Integer, nullable=False, default=0)
    max_exchange_accounts = Column(Integer, nullable=False, default=0)
    price_monthly = Column(DECIMAL(10, 2), nullable=False, default=0)
    description = Column(String(255), nullable=False, default="")
    status = Column(Integer, nullable=False, default=1)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ApiUsage(Base):
    """每日 API 用量统计"""
    __tablename__ = "fact_api_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=False)
    usage_date = Column(Date, nullable=False)
    api_calls = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
