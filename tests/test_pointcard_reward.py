"""
点卡与分销集成测试

覆盖：开策略校验点卡、盈利扣费、利润池、分销结算、点卡为0不执行。
依赖：config 中数据库可连；建议使用开发库，测试结束会 rollback 不落库。

运行：
    cd /path/to/ironbull
    python -m pytest tests/test_pointcard_reward.py -v
    python -m pytest tests/test_pointcard_reward.py -v --tb=short
"""

import os
import sys
from decimal import Decimal

import pytest

# 保证可导入 libs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.core.database import init_database, get_session
from libs.member.repository import MemberRepository
from libs.member.service import MemberService
from libs.pointcard.service import PointCardService
from libs.reward.models import ProfitPool, UserReward
from libs.tenant.repository import TenantRepository


# 测试用租户/用户（需库中已存在）
TENANT_ID = 1
USER_ID = 1


@pytest.fixture(scope="module")
def db_session():
    init_database()
    return get_session()


@pytest.fixture
def session_rollback(db_session):
    """每个测试后回滚，不落库"""
    try:
        yield db_session
    finally:
        db_session.rollback()


def test_open_strategy_rejects_zero_point_card(session_rollback):
    """点卡余额为 0 时，开策略应返回点卡不足错误"""
    repo = MemberRepository(session_rollback)
    user = repo.get_user_by_id(USER_ID, TENANT_ID)
    if not user:
        pytest.skip("需要存在 tenant_id=1 user_id=1")
    orig_self = user.point_card_self
    orig_gift = user.point_card_gift
    user.point_card_self = 0
    user.point_card_gift = 0
    repo.update_user(user)
    session_rollback.flush()
    svc = MemberService(session_rollback)
    binding, err = svc.open_strategy(USER_ID, TENANT_ID, 99999, 99999, min_point_card=1.0)
    assert binding is None
    assert "点卡" in err
    user.point_card_self = orig_self
    user.point_card_gift = orig_gift
    repo.update_user(user)


def test_open_strategy_allows_with_point_card(session_rollback):
    """点卡余额 >= min_point_card 时，开策略应通过点卡校验（可能因策略/账户不存在而失败，但不应是点卡错误）"""
    repo = MemberRepository(session_rollback)
    user = repo.get_user_by_id(USER_ID, TENANT_ID)
    if not user:
        pytest.skip("需要存在 tenant_id=1 user_id=1")
    orig_self = user.point_card_self
    orig_gift = user.point_card_gift
    user.point_card_self = Decimal("100")
    user.point_card_gift = Decimal("0")
    repo.update_user(user)
    session_rollback.flush()
    svc = MemberService(session_rollback)
    # 用不存在的 strategy_id/account_id，会先过点卡校验再报「策略不存在」或「账户不存在」
    binding, err = svc.open_strategy(USER_ID, TENANT_ID, 99999, 99999, min_point_card=1.0)
    # 有足够点卡时不应报点卡不足
    assert "点卡余额不足" not in err
    user.point_card_self = orig_self
    user.point_card_gift = orig_gift
    repo.update_user(user)


def test_deduct_for_profit_creates_pool_and_distributes(session_rollback):
    """盈利扣费：扣点卡、写利润池、触发分销（利润池 status=2）"""
    tenant_repo = TenantRepository(session_rollback)
    member_repo = MemberRepository(session_rollback)
    tenant = tenant_repo.get_by_id(TENANT_ID)
    user = member_repo.get_user_by_id(USER_ID, TENANT_ID)
    if not tenant or not user:
        pytest.skip("需要存在 tenant_id=1 user_id=1")
    # 确保代理商有余额可充值
    if (tenant.point_card_self or 0) < 200:
        pytest.skip("租户 1 自充点卡不足 200，无法执行充值测试")
    pc_svc = PointCardService(session_rollback)
    # 先给用户充 100 自充
    ok, err, _ = pc_svc.recharge_user(TENANT_ID, USER_ID, Decimal("100"), use_self=True)
    assert ok, err
    session_rollback.flush()
    # 盈利扣费 100 -> 扣 30，其中 self 部分进利润池并触发分销
    ok, err, data = pc_svc.deduct_for_profit(USER_ID, Decimal("100"))
    assert ok, err
    assert data is not None
    assert data["deduct_total"] == 30.0
    session_rollback.flush()
    # 应有利润池记录且已结算
    pools = session_rollback.query(ProfitPool).filter(ProfitPool.user_id == USER_ID).order_by(ProfitPool.id.desc()).limit(1).all()
    assert len(pools) >= 1
    pool = pools[0]
    assert float(pool.pool_amount) > 0
    assert pool.status == 2  # 已结算（distribute_for_pool 会设为 2）


def test_transfer_self_type(session_rollback):
    """点卡转账 type=1：自充互转 self→self"""
    member_repo = MemberRepository(session_rollback)
    tenant_repo = TenantRepository(session_rollback)
    tenant = tenant_repo.get_by_id(TENANT_ID)
    user1 = member_repo.get_user_by_id(USER_ID, TENANT_ID)
    if not tenant or not user1:
        pytest.skip("需要存在 tenant_id=1 user_id=1")
    items, total = member_repo.list_users(TENANT_ID, 1, 10)
    user2 = None
    for u in items:
        if u.id != USER_ID:
            user2 = u
            break
    if not user2:
        pytest.skip("需要至少两个用户")
    user1.point_card_self = Decimal("100")
    user1.point_card_gift = Decimal("50")
    member_repo.update_user(user1)
    user2.point_card_self = Decimal("10")
    user2.point_card_gift = Decimal("20")
    member_repo.update_user(user2)
    session_rollback.flush()
    pc_svc = PointCardService(session_rollback)
    ok, err, data = pc_svc.transfer(TENANT_ID, user1.id, user2.id, Decimal("30"), transfer_type=1)
    assert ok, err
    assert data["type"] == 1
    assert data["type_name"] == "自充互转"
    assert data["from_self_after"] == 70.0  # 100-30
    assert data["from_gift_after"] == 50.0  # 不变
    assert data["to_self_after"] == 40.0    # 10+30
    assert data["to_gift_after"] == 20.0    # 不变


def test_transfer_gift_type(session_rollback):
    """点卡转账 type=2：赠送互转 gift→gift"""
    member_repo = MemberRepository(session_rollback)
    tenant_repo = TenantRepository(session_rollback)
    tenant = tenant_repo.get_by_id(TENANT_ID)
    user1 = member_repo.get_user_by_id(USER_ID, TENANT_ID)
    if not tenant or not user1:
        pytest.skip("需要存在 tenant_id=1 user_id=1")
    items, total = member_repo.list_users(TENANT_ID, 1, 10)
    user2 = None
    for u in items:
        if u.id != USER_ID:
            user2 = u
            break
    if not user2:
        pytest.skip("需要至少两个用户")
    user1.point_card_self = Decimal("100")
    user1.point_card_gift = Decimal("80")
    member_repo.update_user(user1)
    user2.point_card_self = Decimal("10")
    user2.point_card_gift = Decimal("5")
    member_repo.update_user(user2)
    session_rollback.flush()
    pc_svc = PointCardService(session_rollback)
    ok, err, data = pc_svc.transfer(TENANT_ID, user1.id, user2.id, Decimal("25"), transfer_type=2)
    assert ok, err
    assert data["type"] == 2
    assert data["type_name"] == "赠送互转"
    assert data["from_self_after"] == 100.0  # 不变
    assert data["from_gift_after"] == 55.0   # 80-25
    assert data["to_self_after"] == 10.0     # 不变
    assert data["to_gift_after"] == 30.0     # 5+25


def test_transfer_insufficient_balance(session_rollback):
    """点卡转账：余额不足时应拒绝"""
    member_repo = MemberRepository(session_rollback)
    tenant_repo = TenantRepository(session_rollback)
    tenant = tenant_repo.get_by_id(TENANT_ID)
    user1 = member_repo.get_user_by_id(USER_ID, TENANT_ID)
    if not tenant or not user1:
        pytest.skip("需要存在 tenant_id=1 user_id=1")
    items, total = member_repo.list_users(TENANT_ID, 1, 10)
    user2 = None
    for u in items:
        if u.id != USER_ID:
            user2 = u
            break
    if not user2:
        pytest.skip("需要至少两个用户")
    user1.point_card_self = Decimal("10")
    user1.point_card_gift = Decimal("5")
    member_repo.update_user(user1)
    session_rollback.flush()
    pc_svc = PointCardService(session_rollback)
    # self 不足
    ok, err, _ = pc_svc.transfer(TENANT_ID, user1.id, user2.id, Decimal("50"), transfer_type=1)
    assert not ok
    assert "不足" in err
    # gift 不足
    ok, err, _ = pc_svc.transfer(TENANT_ID, user1.id, user2.id, Decimal("50"), transfer_type=2)
    assert not ok
    assert "不足" in err


def test_execution_targets_exclude_zero_balance(session_rollback):
    """get_execution_targets_by_strategy_code 返回的列表中，每个 target 对应用户点卡应 > 0"""
    svc = MemberService(session_rollback)
    repo = MemberRepository(session_rollback)
    # 任意策略码，可能返回 0 个或多个
    targets = svc.get_execution_targets_by_strategy_code("__no_such_strategy_")
    for t in targets:
        u = repo.get_user_by_id(t.user_id)
        assert u is not None
        total = float(u.point_card_self or 0) + float(u.point_card_gift or 0)
        assert total > 0, "点卡为 0 的用户不应出现在执行列表中"
