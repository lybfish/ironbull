"""
Admin - 后台管理员模块（独立于 tenant/user）
"""

from .models import Admin
from .service import AdminService

__all__ = ["Admin", "AdminService"]
