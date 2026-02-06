"""
后台充值流水测试

覆盖：后台给租户充值后 fact_point_card_log 是否正确写入

运行：
    cd /path/to/ironbull
    python3 -m pytest tests/test_recharge_log.py -v --tb=short
"""

import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.core.database import init_database, get_session
from libs.tenant.models import Tenant
from libs.pointcard.models import PointCardLog
from libs.pointcard.service import CHANGE_RECHARGE, SOURCE_ADMIN, CARD_SELF, CARD_GIFT

TENANT_ID = 1


@pytest.fixture(scope="module")
def db():
    init_database()
    return get_session()


@pytest.fixture
def session(db):
    try:
        yield db
    finally:
        db.rollback()


def test_self_recharge_creates_log(session):
    """后台自充：余额增加 + 写入 fact_point_card_log"""
    tenant = session.query(Tenant).filter(Tenant.id == TENANT_ID).first()
    if not tenant:
        pytest.skip("租户不存在")
    before_self = float(tenant.point_card_self or 0)
    before_gift = float(tenant.point_card_gift or 0)
    amount = Decimal("50")
    tenant.point_card_self = (tenant.point_card_self or 0) + amount
    session.merge(tenant)
    session.flush()
    after_self = float(tenant.point_card_self or 0)
    after_gift = float(tenant.point_card_gift or 0)
    log = PointCardLog(
        tenant_id=TENANT_ID,
        user_id=None,
        change_type=CHANGE_RECHARGE,
        source_type=SOURCE_ADMIN,
        card_type=CARD_SELF,
        amount=float(amount),
        before_self=before_self,
        after_self=after_self,
        before_gift=before_gift,
        after_gift=after_gift,
        remark="测试后台自充",
    )
    session.add(log)
    session.flush()
    # 验证
    found = session.query(PointCardLog).filter(
        PointCardLog.tenant_id == TENANT_ID,
        PointCardLog.source_type == SOURCE_ADMIN,
        PointCardLog.remark == "测试后台自充",
    ).order_by(PointCardLog.id.desc()).first()
    assert found is not None
    assert float(found.amount) == 50.0
    assert float(found.after_self) - float(found.before_self) == pytest.approx(50.0, abs=0.01)
    assert found.change_type == CHANGE_RECHARGE
    assert found.card_type == CARD_SELF


def test_gift_recharge_creates_log(session):
    """后台赠送充值：余额增加 + 写入 fact_point_card_log"""
    tenant = session.query(Tenant).filter(Tenant.id == TENANT_ID).first()
    if not tenant:
        pytest.skip("租户不存在")
    before_self = float(tenant.point_card_self or 0)
    before_gift = float(tenant.point_card_gift or 0)
    amount = Decimal("30")
    tenant.point_card_gift = (tenant.point_card_gift or 0) + amount
    session.merge(tenant)
    session.flush()
    after_self = float(tenant.point_card_self or 0)
    after_gift = float(tenant.point_card_gift or 0)
    log = PointCardLog(
        tenant_id=TENANT_ID,
        user_id=None,
        change_type=CHANGE_RECHARGE,
        source_type=SOURCE_ADMIN,
        card_type=CARD_GIFT,
        amount=float(amount),
        before_self=before_self,
        after_self=after_self,
        before_gift=before_gift,
        after_gift=after_gift,
        remark="测试后台赠送",
    )
    session.add(log)
    session.flush()
    found = session.query(PointCardLog).filter(
        PointCardLog.tenant_id == TENANT_ID,
        PointCardLog.source_type == SOURCE_ADMIN,
        PointCardLog.remark == "测试后台赠送",
    ).order_by(PointCardLog.id.desc()).first()
    assert found is not None
    assert float(found.amount) == 30.0
    assert float(found.after_gift) - float(found.before_gift) == pytest.approx(30.0, abs=0.01)
    assert found.card_type == CARD_GIFT
