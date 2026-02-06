"""
AdminService — 需要 DB（rollback 模式）

覆盖：
- verify_login 正确凭证返回 Admin
- verify_login 错误密码返回 None
- get_by_id 存在 / 不存在
- change_password 成功 / 旧密码错误
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.admin.service import AdminService


def test_verify_login_correct(session_rollback):
    """正确的 admin/admin123 应返回 Admin 对象"""
    svc = AdminService(session_rollback)
    admin = svc.verify_login("admin", "admin123")
    assert admin is not None
    assert admin.username == "admin"
    assert admin.id >= 1


def test_verify_login_wrong_password(session_rollback):
    """错误密码应返回 None"""
    svc = AdminService(session_rollback)
    admin = svc.verify_login("admin", "wrong_password_xyz")
    assert admin is None


def test_get_by_id_exists(session_rollback):
    """存在的 admin_id 应返回 Admin"""
    svc = AdminService(session_rollback)
    admin = svc.get_by_id(1)
    assert admin is not None
    assert admin.username == "admin"


def test_get_by_id_not_exists(session_rollback):
    """不存在的 admin_id 应返回 None"""
    svc = AdminService(session_rollback)
    admin = svc.get_by_id(99999)
    assert admin is None


def test_change_password_success(session_rollback):
    """正确旧密码修改密码应返回 None（成功）"""
    svc = AdminService(session_rollback)
    err = svc.change_password(1, "admin123", "new_password_456")
    assert err is None
    # 验证新密码可登录
    admin = svc.verify_login("admin", "new_password_456")
    assert admin is not None


def test_change_password_wrong_old(session_rollback):
    """旧密码错误应返回错误信息"""
    svc = AdminService(session_rollback)
    err = svc.change_password(1, "totally_wrong", "new_password")
    assert err is not None
    assert "原密码" in err
