"""
配额计费 — QuotaService

职责：
- 套餐 CRUD
- 检查租户是否超配额（daily/monthly API、用户数、策略数、交易所账户数）
- 记录每日 API 用量（原子 increment）
- 查询用量统计
"""

from datetime import date, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from .models import QuotaPlan, ApiUsage
from libs.tenant.models import Tenant


class QuotaService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- 套餐 CRUD ----------

    def list_plans(self, include_disabled: bool = False) -> List[QuotaPlan]:
        q = self.db.query(QuotaPlan)
        if not include_disabled:
            q = q.filter(QuotaPlan.status == 1)
        return q.order_by(QuotaPlan.sort_order).all()

    def get_plan(self, plan_id: int) -> Optional[QuotaPlan]:
        return self.db.query(QuotaPlan).filter(QuotaPlan.id == plan_id).first()

    def get_plan_by_code(self, code: str) -> Optional[QuotaPlan]:
        return self.db.query(QuotaPlan).filter(QuotaPlan.code == code).first()

    def create_plan(self, **kwargs) -> QuotaPlan:
        plan = QuotaPlan(**kwargs)
        self.db.add(plan)
        self.db.flush()
        return plan

    def update_plan(self, plan_id: int, **kwargs) -> Optional[QuotaPlan]:
        plan = self.get_plan(plan_id)
        if not plan:
            return None
        for k, v in kwargs.items():
            if hasattr(plan, k):
                setattr(plan, k, v)
        self.db.flush()
        return plan

    def toggle_plan(self, plan_id: int) -> Optional[QuotaPlan]:
        plan = self.get_plan(plan_id)
        if not plan:
            return None
        plan.status = 0 if plan.status == 1 else 1
        self.db.flush()
        return plan

    # ---------- 租户套餐分配 ----------

    def assign_plan(self, tenant_id: int, plan_id: int) -> bool:
        """给租户分配套餐"""
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return False
        plan = self.get_plan(plan_id)
        if not plan:
            return False
        tenant.quota_plan_id = plan_id
        self.db.flush()
        return True

    def get_tenant_plan(self, tenant_id: int) -> Optional[QuotaPlan]:
        """获取租户当前套餐"""
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant or not tenant.quota_plan_id:
            return None
        return self.get_plan(tenant.quota_plan_id)

    # ---------- API 用量记录 ----------

    def increment_api_usage(self, tenant_id: int) -> int:
        """原子递增当日 API 调用计数，返回当日已用量"""
        today = date.today()
        usage = self.db.query(ApiUsage).filter(
            ApiUsage.tenant_id == tenant_id,
            ApiUsage.usage_date == today,
        ).first()
        if usage:
            usage.api_calls += 1
            self.db.flush()
            return usage.api_calls
        else:
            usage = ApiUsage(tenant_id=tenant_id, usage_date=today, api_calls=1)
            self.db.add(usage)
            self.db.flush()
            return 1

    def get_daily_usage(self, tenant_id: int, usage_date: Optional[date] = None) -> int:
        """查询某日 API 调用数"""
        usage_date = usage_date or date.today()
        usage = self.db.query(ApiUsage).filter(
            ApiUsage.tenant_id == tenant_id,
            ApiUsage.usage_date == usage_date,
        ).first()
        return usage.api_calls if usage else 0

    def get_monthly_usage(self, tenant_id: int, year: int = 0, month: int = 0) -> int:
        """查询某月 API 调用数"""
        today = date.today()
        if not year:
            year = today.year
        if not month:
            month = today.month
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1)
        else:
            last_day = date(year, month + 1, 1)
        result = self.db.query(sqlfunc.coalesce(sqlfunc.sum(ApiUsage.api_calls), 0)).filter(
            ApiUsage.tenant_id == tenant_id,
            ApiUsage.usage_date >= first_day,
            ApiUsage.usage_date < last_day,
        ).scalar()
        return int(result)

    def get_usage_history(self, tenant_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """查询最近 N 天的 API 用量"""
        start_date = date.today() - timedelta(days=days - 1)
        rows = self.db.query(ApiUsage).filter(
            ApiUsage.tenant_id == tenant_id,
            ApiUsage.usage_date >= start_date,
        ).order_by(ApiUsage.usage_date.desc()).all()
        return [
            {"date": str(r.usage_date), "api_calls": r.api_calls}
            for r in rows
        ]

    # ---------- 配额检查 ----------

    def check_api_quota(self, tenant_id: int) -> Dict[str, Any]:
        """
        检查租户 API 配额，返回：
        {
            "allowed": True/False,
            "daily_limit": 100, "daily_used": 50,
            "monthly_limit": 3000, "monthly_used": 500,
            "plan_name": "免费版",
            "reason": "超出每日限额" / None,
        }
        """
        plan = self.get_tenant_plan(tenant_id)
        if not plan:
            # 未分配套餐：默认放行（可根据策略改为拒绝）
            return {"allowed": True, "plan_name": None, "reason": None,
                    "daily_limit": 0, "daily_used": 0,
                    "monthly_limit": 0, "monthly_used": 0}

        daily_used = self.get_daily_usage(tenant_id)
        monthly_used = self.get_monthly_usage(tenant_id)

        # 0 = 不限制
        if plan.api_calls_daily > 0 and daily_used >= plan.api_calls_daily:
            return {
                "allowed": False,
                "plan_name": plan.name,
                "reason": f"超出每日API限额({plan.api_calls_daily}次/天)",
                "daily_limit": plan.api_calls_daily, "daily_used": daily_used,
                "monthly_limit": plan.api_calls_monthly, "monthly_used": monthly_used,
            }
        if plan.api_calls_monthly > 0 and monthly_used >= plan.api_calls_monthly:
            return {
                "allowed": False,
                "plan_name": plan.name,
                "reason": f"超出每月API限额({plan.api_calls_monthly}次/月)",
                "daily_limit": plan.api_calls_daily, "daily_used": daily_used,
                "monthly_limit": plan.api_calls_monthly, "monthly_used": monthly_used,
            }
        return {
            "allowed": True,
            "plan_name": plan.name,
            "reason": None,
            "daily_limit": plan.api_calls_daily, "daily_used": daily_used,
            "monthly_limit": plan.api_calls_monthly, "monthly_used": monthly_used,
        }

    def check_resource_quota(self, tenant_id: int) -> Dict[str, Any]:
        """
        检查租户资源配额（用户数、策略数、交易所账户数），返回各项 limit/used/exceeded。
        """
        from libs.member.models import User, StrategyBinding, ExchangeAccount

        plan = self.get_tenant_plan(tenant_id)
        if not plan:
            return {"has_plan": False}

        user_count = self.db.query(sqlfunc.count(User.id)).filter(
            User.tenant_id == tenant_id, User.status == 1
        ).scalar() or 0

        strategy_count = self.db.query(sqlfunc.count(StrategyBinding.id)).filter(
            StrategyBinding.tenant_id == tenant_id, StrategyBinding.status == 1
        ).scalar() or 0

        account_count = self.db.query(sqlfunc.count(ExchangeAccount.id)).filter(
            ExchangeAccount.tenant_id == tenant_id, ExchangeAccount.status == 1
        ).scalar() or 0

        def _check(limit: int, used: int) -> Dict:
            return {"limit": limit, "used": used, "exceeded": limit > 0 and used >= limit}

        return {
            "has_plan": True,
            "plan_name": plan.name,
            "users": _check(plan.max_users, user_count),
            "strategies": _check(plan.max_strategies, strategy_count),
            "exchange_accounts": _check(plan.max_exchange_accounts, account_count),
        }
