"""
Pointcard Models - 点卡流水
"""

from datetime import datetime

from sqlalchemy import Column, Integer, BigInteger, String, DateTime
from sqlalchemy.dialects.mysql import DECIMAL

from libs.core.database import Base


class PointCardLog(Base):
    """
    点卡流水表（fact_point_card_log）
    """
    __tablename__ = "fact_point_card_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    related_user_id = Column(Integer, nullable=True)
    change_type = Column(Integer, nullable=False)   # 1充值 2赠送 3转出 4转入 5扣费
    source_type = Column(Integer, nullable=False)   # 1后台 2代理商分发 3盈利扣费 4用户互转
    card_type = Column(Integer, nullable=False)      # 1=self 2=gift
    amount = Column(DECIMAL(20, 8), nullable=False)
    before_self = Column(DECIMAL(20, 8), nullable=False, default=0)
    after_self = Column(DECIMAL(20, 8), nullable=False, default=0)
    before_gift = Column(DECIMAL(20, 8), nullable=False, default=0)
    after_gift = Column(DECIMAL(20, 8), nullable=False, default=0)
    remark = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
