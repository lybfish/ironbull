"""
Admin Service - 后台管理员业务逻辑

密码策略：新密码用 bcrypt，旧 MD5 密码登录时自动升级为 bcrypt。
"""

import hashlib
from datetime import datetime
from typing import Optional

import bcrypt
from sqlalchemy.orm import Session

from .models import Admin


def _hash_password(password: str) -> str:
    """用 bcrypt 哈希密码"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, password_hash: str) -> bool:
    """
    验证密码：优先 bcrypt，兼容旧 MD5。
    MD5 哈希固定 32 位十六进制；bcrypt 以 $2b$ 开头。
    """
    if password_hash.startswith("$2b$") or password_hash.startswith("$2a$"):
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    # 兼容旧 MD5
    return hashlib.md5(password.encode()).hexdigest() == password_hash


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
        if not _verify_password(password, admin.password_hash):
            return None
        # 自动升级：如果还是 MD5 哈希，改成 bcrypt
        if not admin.password_hash.startswith("$2b$"):
            admin.password_hash = _hash_password(password)
        # 更新最后登录时间
        admin.last_login_at = datetime.now()
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
        if not _verify_password(old_password, admin.password_hash):
            return "原密码错误"
        admin.password_hash = _hash_password(new_password)
        self.db.merge(admin)
        self.db.flush()
        return None
