"""
提现流程测试

覆盖：
- 申请提现成功 + reward_log 流水
- 余额不足拒绝
- 低于最低金额拒绝
- 审核通过
- 审核拒绝 + 余额退回 + reward_log 流水
- 重复审核拒绝
- 标记打款完成
- 未审核时不允许标记完成

运行：
    cd /path/to/ironbull
    python3 -m pytest tests/test_withdrawal.py -v --tb=short
"""

import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.core.database import init_database, get_session
from libs.member.repository import MemberRepository
from libs.reward.withdrawal_service import WithdrawalService
from libs.reward.models import RewardLog, UserWithdrawal
from libs.reward.repository import RewardRepository

TENANT_ID = 1
USER_ID = 1


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


def _ensure_user_reward(session, user_id, amount):
    """确保用户有足够 reward_usdt"""
    repo = MemberRepository(session)
    user = repo.get_user_by_id(user_id, TENANT_ID)
    if not user:
        pytest.skip(f"用户 {user_id} 不存在")
    user.reward_usdt = amount
    repo.update_user(user)
    session.flush()
    return user


# ---- 申请提现 ----

def test_apply_success(session):
    """正常申请提现：余额充足，应成功并写 reward_log"""
    _ensure_user_reward(session, USER_ID, Decimal("200"))
    svc = WithdrawalService(session)
    w, err = svc.apply(USER_ID, TENANT_ID, Decimal("100"), "TXyz123abc", "TRC20")
    assert err == "", f"申请失败: {err}"
    assert w is not None
    assert w.status == 0
    assert float(w.amount) == 100.0
    assert float(w.fee) > 0
    assert float(w.actual_amount) == float(w.amount) - float(w.fee)
    # 检查 reward_log
    logs = session.query(RewardLog).filter(
        RewardLog.user_id == USER_ID,
        RewardLog.change_type == "withdraw_freeze",
        RewardLog.ref_id == w.id,
    ).all()
    assert len(logs) == 1
    log = logs[0]
    assert float(log.amount) == -100.0
    assert float(log.before_balance) == 200.0
    assert float(log.after_balance) == 100.0


def test_apply_insufficient_balance(session):
    """余额不足时应拒绝"""
    _ensure_user_reward(session, USER_ID, Decimal("10"))
    svc = WithdrawalService(session)
    w, err = svc.apply(USER_ID, TENANT_ID, Decimal("100"), "TXyz123abc", "TRC20")
    assert w is None
    assert "不足" in err


def test_apply_below_minimum(session):
    """低于最低提现金额应拒绝"""
    _ensure_user_reward(session, USER_ID, Decimal("1000"))
    svc = WithdrawalService(session)
    w, err = svc.apply(USER_ID, TENANT_ID, Decimal("10"), "TXyz123abc", "TRC20")
    assert w is None
    assert "最低" in err


# ---- 审核通过 ----

def test_approve_success(session):
    """审核通过：状态 0→1"""
    _ensure_user_reward(session, USER_ID, Decimal("200"))
    svc = WithdrawalService(session)
    w, _ = svc.apply(USER_ID, TENANT_ID, Decimal("100"), "TXyz123abc")
    assert w is not None
    session.flush()
    w2, err = svc.approve(w.id, admin_id=1)
    assert err == "", f"审核失败: {err}"
    assert w2.status == 1
    assert w2.audit_by == 1
    assert w2.audit_at is not None


# ---- 拒绝 ----

def test_reject_returns_balance(session):
    """拒绝提现：状态 0→2，余额退回，写 reward_log"""
    _ensure_user_reward(session, USER_ID, Decimal("200"))
    svc = WithdrawalService(session)
    w, _ = svc.apply(USER_ID, TENANT_ID, Decimal("100"), "TXyz123abc")
    assert w is not None
    session.flush()
    # 此时余额应为 100
    repo = MemberRepository(session)
    user = repo.get_user_by_id(USER_ID, TENANT_ID)
    assert float(user.reward_usdt) == 100.0
    w2, err = svc.reject(w.id, admin_id=1, reason="测试拒绝")
    assert err == "", f"拒绝失败: {err}"
    assert w2.status == 2
    assert w2.reject_reason == "测试拒绝"
    session.flush()
    # 余额应退回 200
    user = repo.get_user_by_id(USER_ID, TENANT_ID)
    assert float(user.reward_usdt) == 200.0
    # 检查 reward_log
    logs = session.query(RewardLog).filter(
        RewardLog.user_id == USER_ID,
        RewardLog.change_type == "withdraw_reject_return",
        RewardLog.ref_id == w.id,
    ).all()
    assert len(logs) == 1
    assert float(logs[0].amount) == 100.0


def test_reject_already_approved_fails(session):
    """已审核通过的提现不允许再拒绝"""
    _ensure_user_reward(session, USER_ID, Decimal("200"))
    svc = WithdrawalService(session)
    w, _ = svc.apply(USER_ID, TENANT_ID, Decimal("100"), "TXyz123abc")
    session.flush()
    svc.approve(w.id, admin_id=1)
    session.flush()
    w2, err = svc.reject(w.id, admin_id=1, reason="迟了")
    assert w2 is None
    assert "不允许" in err


# ---- 标记完成 ----

def test_complete_success(session):
    """审核通过后标记完成：状态 1→3"""
    _ensure_user_reward(session, USER_ID, Decimal("200"))
    svc = WithdrawalService(session)
    w, _ = svc.apply(USER_ID, TENANT_ID, Decimal("100"), "TXyz123abc")
    session.flush()
    svc.approve(w.id, admin_id=1)
    session.flush()
    w3, err = svc.complete(w.id, tx_hash="0xabc123")
    assert err == "", f"完成失败: {err}"
    assert w3.status == 3
    assert w3.tx_hash == "0xabc123"
    assert w3.completed_at is not None


def test_complete_without_approve_fails(session):
    """未审核时不允许标记完成"""
    _ensure_user_reward(session, USER_ID, Decimal("200"))
    svc = WithdrawalService(session)
    w, _ = svc.apply(USER_ID, TENANT_ID, Decimal("100"), "TXyz123abc")
    session.flush()
    w3, err = svc.complete(w.id, tx_hash="0xabc123")
    assert w3 is None
    assert "不允许" in err
