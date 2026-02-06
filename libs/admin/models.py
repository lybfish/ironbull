"""
Admin Models - 后台管理员表
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from libs.core.database import Base


class Admin(Base):
    """
    后台管理员表（dim_admin）
    独立于 dim_tenant / dim_user，用于管理后台登录。
    """
    __tablename__ = "dim_admin"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True, index=True, comment="登录用户名")
    password_hash = Column(String(128), nullable=False, comment="密码哈希(MD5)")
    nickname = Column(String(64), nullable=False, default="", comment="显示昵称")
    status = Column(Integer, nullable=False, default=1, comment="1正常 0禁用")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
