"""
共享 pytest fixtures

- db_session:  module 级，初始化数据库并返回 session
- session_rollback: function 级，测试结束后自动 rollback，不落库
- admin_token: 签发一个有效 admin JWT
- tenant_fixture: 返回测试租户 (id=1)
"""

import os
import sys

import pytest

# 保证可导入 libs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.core.database import init_database, get_session


TENANT_ID = 1


@pytest.fixture(scope="module")
def db_session():
    """Module 级 DB session，所有需要数据库的测试共享"""
    init_database()
    session = get_session()
    yield session
    session.close()


@pytest.fixture
def session_rollback(db_session):
    """每个测试结束后 rollback，不落库"""
    try:
        yield db_session
    finally:
        db_session.rollback()


@pytest.fixture
def admin_token():
    """签发一个有效的管理后台 JWT"""
    from libs.core.auth.jwt import encode
    return encode(admin_id=1, username="admin", exp_hours=1)


@pytest.fixture
def tenant_fixture(db_session):
    """返回测试租户 (id=1)，不存在则 skip"""
    from libs.tenant.models import Tenant
    tenant = db_session.query(Tenant).filter(Tenant.id == TENANT_ID).first()
    if not tenant:
        pytest.skip(f"测试租户 id={TENANT_ID} 不存在")
    return tenant
