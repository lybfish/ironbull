"""
配额计费 QuotaService — 需要 DB（rollback 模式）

覆盖：
- list_plans 返回预置套餐
- get_plan_by_code 正确查询
- create_plan + get_plan 持久化
- toggle_plan 切换 status
- assign_plan 更新 tenant.quota_plan_id
- increment_api_usage 原子递增
- check_api_quota 未超限 allowed=True
- check_api_quota 超限 allowed=False
"""

import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.quota.service import QuotaService
from libs.quota.models import ApiUsage


TENANT_ID = 1


def test_list_plans_returns_presets(session_rollback):
    """list_plans 应返回预置的 4 个套餐"""
    svc = QuotaService(session_rollback)
    plans = svc.list_plans(include_disabled=True)
    assert len(plans) >= 4
    codes = {p.code for p in plans}
    assert {"free", "basic", "pro", "enterprise"}.issubset(codes)


def test_get_plan_by_code_free(session_rollback):
    """get_plan_by_code('free') 应返回免费版"""
    svc = QuotaService(session_rollback)
    plan = svc.get_plan_by_code("free")
    assert plan is not None
    assert plan.name == "免费版"
    assert plan.api_calls_daily == 100


def test_create_and_get_plan(session_rollback):
    """create_plan 后 get_plan 应能查到"""
    svc = QuotaService(session_rollback)
    plan = svc.create_plan(
        name="测试套餐",
        code="__test_plan__",
        api_calls_daily=50,
        api_calls_monthly=1000,
        max_users=3,
        max_strategies=1,
        max_exchange_accounts=1,
        price_monthly=9.9,
        description="pytest 临时套餐",
    )
    session_rollback.flush()
    assert plan.id is not None
    fetched = svc.get_plan(plan.id)
    assert fetched is not None
    assert fetched.code == "__test_plan__"
    assert fetched.api_calls_daily == 50


def test_toggle_plan(session_rollback):
    """toggle_plan 应切换 status"""
    svc = QuotaService(session_rollback)
    plan = svc.get_plan_by_code("free")
    assert plan is not None
    original_status = plan.status
    toggled = svc.toggle_plan(plan.id)
    assert toggled is not None
    assert toggled.status != original_status
    # 切回来
    svc.toggle_plan(plan.id)


def test_assign_plan(session_rollback):
    """assign_plan 应更新 tenant.quota_plan_id"""
    svc = QuotaService(session_rollback)
    from libs.tenant.models import Tenant
    tenant = session_rollback.query(Tenant).filter(Tenant.id == TENANT_ID).first()
    if not tenant:
        pytest.skip("测试租户不存在")
    pro = svc.get_plan_by_code("pro")
    assert pro is not None
    ok = svc.assign_plan(TENANT_ID, pro.id)
    assert ok is True
    session_rollback.flush()
    session_rollback.refresh(tenant)
    assert tenant.quota_plan_id == pro.id


def test_increment_api_usage(session_rollback):
    """increment_api_usage 应原子递增并返回当日计数"""
    svc = QuotaService(session_rollback)
    # 清除今天可能存在的记录
    today = date.today()
    existing = session_rollback.query(ApiUsage).filter(
        ApiUsage.tenant_id == TENANT_ID,
        ApiUsage.usage_date == today,
    ).first()
    if existing:
        existing.api_calls = 0
        session_rollback.flush()
    count1 = svc.increment_api_usage(TENANT_ID)
    count2 = svc.increment_api_usage(TENANT_ID)
    assert count2 == count1 + 1


def test_check_api_quota_allowed(session_rollback):
    """套餐未超限时 check_api_quota 应返回 allowed=True"""
    svc = QuotaService(session_rollback)
    # 分配企业版（无限制）
    enterprise = svc.get_plan_by_code("enterprise")
    svc.assign_plan(TENANT_ID, enterprise.id)
    session_rollback.flush()
    result = svc.check_api_quota(TENANT_ID)
    assert result["allowed"] is True
    assert result["reason"] is None


def test_check_api_quota_exceeded(session_rollback):
    """日限额已满时 check_api_quota 应返回 allowed=False"""
    svc = QuotaService(session_rollback)
    # 分配免费版（日限 100）
    free = svc.get_plan_by_code("free")
    svc.assign_plan(TENANT_ID, free.id)
    session_rollback.flush()
    # 把今日用量设为 100
    today = date.today()
    usage = session_rollback.query(ApiUsage).filter(
        ApiUsage.tenant_id == TENANT_ID,
        ApiUsage.usage_date == today,
    ).first()
    if usage:
        usage.api_calls = 100
    else:
        usage = ApiUsage(tenant_id=TENANT_ID, usage_date=today, api_calls=100)
        session_rollback.add(usage)
    session_rollback.flush()
    result = svc.check_api_quota(TENANT_ID)
    assert result["allowed"] is False
    assert "每日" in result["reason"]
