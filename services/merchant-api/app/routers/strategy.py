"""
Merchant API - 策略管理（4 个接口）
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Form
from sqlalchemy.orm import Session

from libs.tenant.models import Tenant
from libs.member.service import MemberService
from libs.member.repository import MemberRepository
from ..deps import get_db, check_quota as get_tenant
from ..schemas import ok

router = APIRouter(prefix="/merchant", tags=["strategy"])


@router.get("/strategies")
def strategies_list(
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """策略列表：按租户策略实例返回，仅包含该租户下已启用的策略（join 主策略，展示名/杠杆/金额以实例覆盖为准）"""
    repo = MemberRepository(db)
    instances = repo.list_tenant_strategies(tenant.id, status=1)
    strategy_ids = [ts.strategy_id for ts in instances]
    strategies = {}
    if strategy_ids:
        from libs.member.models import Strategy
        for s in repo.db.query(Strategy).filter(Strategy.id.in_(strategy_ids)).all():
            strategies[s.id] = s
    list_data = []
    for ts in instances:
        s = strategies.get(ts.strategy_id)
        if not s:
            continue
        cfg = (s.config or {}) if hasattr(s, "config") and hasattr(s.config, "keys") else {}
        min_cap = float(ts.min_capital) if ts.min_capital is not None else (float(s.min_capital) if s.min_capital is not None else (float(cfg.get("min_capital", 200)) if isinstance(cfg, dict) else 200))
        name = (ts.display_name or "").strip() or s.name
        desc = (ts.display_description or "").strip() or (s.description or "").strip() or (cfg.get("description", "") if isinstance(cfg, dict) else "")
        list_data.append({
            "id": s.id,
            "strategy_id": s.id,
            "name": name,
            "description": desc,
            "symbol": s.symbol,
            "timeframe": s.timeframe or "",
            "min_capital": min_cap,
            "status": ts.status,
        })
    return ok(list_data)


@router.post("/user/strategy/open")
def strategy_open(
    email: str = Form(...),
    strategy_id: int = Form(...),
    account_id: int = Form(...),
    mode: int = Form(2),
    capital: float = Form(0, description="本金/最大仓位(USDT)"),
    leverage: int = Form(20, description="杠杆倍数"),
    risk_mode: int = Form(1, description="风险档位: 1=稳健(1%) 2=均衡(1.5%) 3=激进(2%)"),
    min_point_card: float = Form(1.0),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """
    开启策略（需满足最小点卡余额，默认 1.0）；仅允许开通本租户已启用的策略实例。

    用户仓位参数：
    - capital: 本金（USDT），如 1000
    - leverage: 杠杆倍数，如 20
    - risk_mode: 1=稳健(1%) 2=均衡(1.5%) 3=激进(2%)

    下单金额 = capital × risk_pct × leverage
    示例: capital=1000, leverage=20, risk_mode=1 → 1000×1%×20 = 200 USDT
    """
    repo = MemberRepository(db)
    ts = repo.get_tenant_strategy(tenant.id, strategy_id)
    if not ts or ts.status != 1:
        return {"code": 1, "msg": "该策略未对本租户开放或已下架", "data": None}
    svc = MemberService(db)
    user = svc.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    binding, err = svc.open_strategy(
        user.id, tenant.id, strategy_id, account_id,
        mode=mode, min_point_card=min_point_card,
        capital=capital, leverage=leverage, risk_mode=risk_mode,
    )
    if err:
        return {"code": 1, "msg": err, "data": None}
    from libs.member.models import StrategyBinding
    risk_label = StrategyBinding.RISK_MODE_LABELS.get(risk_mode, "稳健")
    return ok({
        "binding_id": binding.id,
        "strategy_id": strategy_id,
        "account_id": account_id,
        "mode": mode,
        "capital": float(binding.capital or 0),
        "leverage": int(binding.leverage or 20),
        "risk_mode": risk_mode,
        "risk_mode_label": risk_label,
        "amount_usdt": float(binding.amount_usdt) if binding.capital else 0,
    }, msg="开启成功")


@router.post("/user/strategy/close")
def strategy_close(
    email: str = Form(...),
    strategy_id: int = Form(...),
    account_id: int = Form(...),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """关闭策略"""
    svc = MemberService(db)
    user = svc.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    if not svc.close_strategy(user.id, tenant.id, strategy_id, account_id):
        return {"code": 1, "msg": "策略绑定不存在", "data": None}
    return ok(None, msg="关闭成功")


@router.post("/user/strategy/update")
def strategy_update(
    email: str = Form(...),
    strategy_id: int = Form(...),
    account_id: int = Form(...),
    capital: float = Form(None, description="本金/最大仓位(USDT)"),
    leverage: int = Form(None, description="杠杆倍数"),
    risk_mode: int = Form(None, description="风险档位: 1=稳健 2=均衡 3=激进"),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """
    修改策略绑定参数（本金/杠杆/风险档位），不影响策略运行状态。
    只传需要修改的字段，未传的保持不变。
    """
    svc = MemberService(db)
    user = svc.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    binding, err = svc.update_strategy_params(
        user.id, tenant.id, strategy_id, account_id,
        capital=capital, leverage=leverage, risk_mode=risk_mode,
    )
    if err:
        return {"code": 1, "msg": err, "data": None}
    from libs.member.models import StrategyBinding
    rm = int(binding.risk_mode or 1)
    return ok({
        "binding_id": binding.id,
        "capital": float(binding.capital or 0),
        "leverage": int(binding.leverage or 20),
        "risk_mode": rm,
        "risk_mode_label": StrategyBinding.RISK_MODE_LABELS.get(rm, "稳健"),
        "amount_usdt": float(binding.amount_usdt) if binding.capital else 0,
    }, msg="修改成功")


@router.get("/user/strategies")
def user_strategies(
    email: str = Query(...),
    tenant: Tenant = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """用户已绑定的策略列表"""
    svc = MemberService(db)
    user = svc.get_user_by_email(email.strip(), tenant.id)
    if not user:
        return {"code": 1, "msg": "用户不存在", "data": None}
    list_data = svc.get_user_strategies(user.id, tenant.id)
    return ok(list_data)
