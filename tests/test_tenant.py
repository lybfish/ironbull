"""
TenantService — 需要 DB（rollback 模式）

覆盖：
- get_by_id / get_by_app_key 基础查询
- get_balance 返回格式正确
- deduct_point_card 余额充足扣减成功
- deduct_point_card 余额不足返回 False
"""

import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.tenant.service import TenantService
from libs.tenant.models import Tenant


TENANT_ID = 1


def test_get_by_id(session_rollback):
    """get_by_id 应返回存在的租户"""
    svc = TenantService(session_rollback)
    tenant = svc.get_by_id(TENANT_ID)
    assert tenant is not None
    assert tenant.id == TENANT_ID
    assert tenant.name is not None


def test_get_by_app_key(session_rollback):
    """get_by_app_key 应通过 app_key 查到租户"""
    svc = TenantService(session_rollback)
    tenant = svc.get_by_id(TENANT_ID)
    if not tenant:
        pytest.skip("测试租户不存在")
    found = svc.get_by_app_key(tenant.app_key)
    assert found is not None
    assert found.id == TENANT_ID


def test_get_balance_format(session_rollback):
    """get_balance 应返回含 point_card_self/gift/total 的字典"""
    svc = TenantService(session_rollback)
    balance = svc.get_balance(TENANT_ID)
    assert "point_card_self" in balance
    assert "point_card_gift" in balance
    assert "point_card_total" in balance
    assert balance["point_card_total"] == balance["point_card_self"] + balance["point_card_gift"]


def test_deduct_point_card_success(session_rollback):
    """余额充足时 deduct_point_card 应扣减成功"""
    # 先给租户设置足够的 self 余额
    tenant = session_rollback.query(Tenant).filter(Tenant.id == TENANT_ID).first()
    if not tenant:
        pytest.skip("测试租户不存在")
    tenant.point_card_self = Decimal("1000")
    session_rollback.flush()

    svc = TenantService(session_rollback)
    ok = svc.deduct_point_card(TENANT_ID, Decimal("100"), use_self=True)
    assert ok is True
    session_rollback.flush()
    session_rollback.refresh(tenant)
    assert float(tenant.point_card_self) == 900.0


def test_deduct_point_card_insufficient(session_rollback):
    """余额不足时 deduct_point_card 应返回 False"""
    tenant = session_rollback.query(Tenant).filter(Tenant.id == TENANT_ID).first()
    if not tenant:
        pytest.skip("测试租户不存在")
    tenant.point_card_self = Decimal("10")
    session_rollback.flush()

    svc = TenantService(session_rollback)
    ok = svc.deduct_point_card(TENANT_ID, Decimal("999"), use_self=True)
    assert ok is False
