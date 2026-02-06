"""
Admin Service - 后台管理员业务逻辑
"""

import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .models import Admin


def _hash_password(password: str) -> str:
    """MD5 哈希（与项目现有 member 模块一致）"""
    return hashlib.md5(password.encode()).hexdigest()


class AdminService:
    def __init__(self, db: Session):
        self.db = db

    def verify_login(self, username: str, password: str) -> Optional[Admin]:
        """验证管理员登录：用户名 + 密码，返回 Admin 或 None。"""
        admin = self.db.query(Admin).filter(Admin.username == username).first()
        if not admin or not admin.password_hash:
            return None
        if admin.status != 1:
            return None
        if _hash_password(password) != admin.password_hash:
            return None
        # 更新最后登录时间
        admin.last_login_at = datetime.utcnow()
        self.db.merge(admin)
        self.db.flush()
        return admin

    def get_by_id(self, admin_id: int) -> Optional[Admin]:
        return self.db.query(Admin).filter(Admin.id == admin_id).first()

    def change_password(self, admin_id: int, old_password: str, new_password: str) -> Optional[str]:
        """修改密码，返回错误信息或 None。"""
        admin = self.get_by_id(admin_id)
        if not admin:
            return "管理员不存在"
        if _hash_password(old_password) != admin.password_hash:
            return "原密码错误"
        admin.password_hash = _hash_password(new_password)
        self.db.merge(admin)
        self.db.flush()
        return None
