"""
Data API - 策略绑定管理（仅管理员可访问）

GET    /api/strategy-bindings-admin             -> 列表
POST   /api/strategy-bindings-admin             -> 新增绑定
PUT    /api/strategy-bindings-admin/{id}        -> 编辑
DELETE /api/strategy-bindings-admin/{id}        -> 删除
GET    /api/strategy-bindings-admin/form-options -> 新增/编辑表单所需下拉选项
"""

from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from libs.member.models import StrategyBinding, User, ExchangeAccount, Strategy
from libs.tenant.models import Tenant

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/strategy-bindings-admin", tags=["bindings"])

RISK_MODE_MAP = {1: 0.01, 2: 0.015, 3: 0.02}
RISK_MODE_LABELS = {1: "稳健", 2: "均衡", 3: "激进"}


# ── helpers ──────────────────────────────────────────────────

def _binding_dict(
    b: StrategyBinding,
    user: User = None,
    tenant: Tenant = None,
    strategy: Strategy = None,
    account: ExchangeAccount = None,
) -> dict:
    acc_label = ""
    if account:
        acc_label = f"{account.exchange}({account.api_key[:8]}...)" if account.api_key else account.exchange

    risk_mode = int(b.risk_mode or 0)
    risk_label = RISK_MODE_LABELS.get(risk_mode, "-")

    strat_config = strategy.get_config() if strategy else {}
    risk_based = bool(strat_config.get("risk_based_sizing", False))
    max_loss = float(b.max_loss_per_trade or 0)

    # 如果没有直接设 max_loss_per_trade，回退到 capital × risk_pct
    if max_loss <= 0 and float(b.capital or 0) > 0 and risk_mode > 0:
        pct = RISK_MODE_MAP.get(risk_mode, 0.01)
        max_loss = round(float(b.capital) * pct, 2)

    return {
        "id": b.id,
        "user_id": b.user_id,
        "user_email": user.email if user else "",
        "tenant_id": user.tenant_id if user else None,
        "tenant_name": tenant.name if tenant else "",
        "account_id": b.account_id,
        "exchange": account.exchange if account else "",
        "exchange_account_label": acc_label,
        "strategy_code": b.strategy_code,
        "strategy_name": strategy.name if strategy else b.strategy_code,
        "mode": int(b.mode or 2),
        "ratio": int(b.ratio or 100),
        # 用户仓位参数
        "capital": float(b.capital or 0),
        "leverage": int(b.leverage or 20),
        "risk_mode": risk_mode,
        "risk_mode_label": risk_label,
        "max_loss_per_trade": max_loss,
        "amount_usdt": float(b.amount_usdt) if b.capital else 0,
        "margin_per_trade": round(float(b.capital or 0) * b.risk_pct, 2) if b.capital else 0,
        # 统计
        "total_profit": float(b.total_profit or 0),
        "total_trades": int(b.total_trades or 0),
        "point_card_self": float(user.point_card_self or 0) if user else 0,
        "point_card_gift": float(user.point_card_gift or 0) if user else 0,
        "point_card_total": (float(user.point_card_self or 0) + float(user.point_card_gift or 0)) if user else 0,
        "status": int(b.status or 1),
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "risk_based_sizing": risk_based,
    }


def _load_related(db: Session, bindings: list) -> tuple:
    """批量加载关联的 user/tenant/strategy/account"""
    user_ids = list(set(b.user_id for b in bindings))
    account_ids = list(set(b.account_id for b in bindings))
    strategy_codes = list(set(b.strategy_code for b in bindings))

    users_map = {}
    if user_ids:
        users_map = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    tenant_ids = list(set(u.tenant_id for u in users_map.values() if u.tenant_id))
    tenants_map = {}
    if tenant_ids:
        tenants_map = {t.id: t for t in db.query(Tenant).filter(Tenant.id.in_(tenant_ids)).all()}

    accounts_map = {}
    if account_ids:
        accounts_map = {a.id: a for a in db.query(ExchangeAccount).filter(ExchangeAccount.id.in_(account_ids)).all()}

    strategies_map = {}
    if strategy_codes:
        strategies_map = {s.code: s for s in db.query(Strategy).filter(Strategy.code.in_(strategy_codes)).all()}

    return users_map, tenants_map, accounts_map, strategies_map


# ── 列表 ─────────────────────────────────────────────────────

@router.get("")
def list_bindings(
    tenant_id: Optional[int] = Query(None, description="按租户筛选"),
    user_id: Optional[int] = Query(None, description="按用户筛选"),
    status: Optional[int] = Query(None, description="按状态筛选 0=停止 1=运行"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """策略绑定列表"""
    query = db.query(StrategyBinding).join(
        User, StrategyBinding.user_id == User.id, isouter=True
    )

    if tenant_id is not None:
        query = query.filter(User.tenant_id == tenant_id)
    if user_id is not None:
        query = query.filter(StrategyBinding.user_id == user_id)
    if status is not None:
        query = query.filter(StrategyBinding.status == status)

    query = query.order_by(StrategyBinding.id.desc())
    total = query.count()
    bindings = query.offset((page - 1) * page_size).limit(page_size).all()

    users_map, tenants_map, accounts_map, strategies_map = _load_related(db, bindings)

    result = []
    for b in bindings:
        user = users_map.get(b.user_id)
        tenant = tenants_map.get(user.tenant_id) if user else None
        strategy = strategies_map.get(b.strategy_code)
        account = accounts_map.get(b.account_id)
        result.append(_binding_dict(b, user=user, tenant=tenant, strategy=strategy, account=account))

    return {"success": True, "data": result, "total": total, "page": page, "page_size": page_size}


# ── 表单选项 ─────────────────────────────────────────────────

@router.get("/form-options")
def form_options(
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    返回新增/编辑绑定所需的下拉选项：
    - strategies: 所有启用策略
    - users: 所有用户（含租户信息）
    - accounts: 所有交易所账户
    """
    strategies = db.query(Strategy).filter(Strategy.status == 1).order_by(Strategy.id).all()
    users = db.query(User).filter(User.status == 1).order_by(User.id).all()
    accounts = db.query(ExchangeAccount).filter(ExchangeAccount.status == 1).order_by(ExchangeAccount.id).all()
    tenants = db.query(Tenant).all()
    tenant_map = {t.id: t.name for t in tenants}

    return {
        "success": True,
        "data": {
            "strategies": [
                {
                    "id": s.id,
                    "code": s.code,
                    "name": s.name,
                    "leverage": int(s.leverage or 20),
                    "capital": float(s.capital or 0),
                    "risk_mode": int(s.risk_mode or 1) if s.risk_mode else None,
                    "max_loss_per_trade": float(s.max_loss_per_trade or 0) if s.max_loss_per_trade else 0,
                    "risk_based_sizing": bool((s.get_config() or {}).get("risk_based_sizing", False)),
                }
                for s in strategies
            ],
            "users": [
                {
                    "id": u.id,
                    "email": u.email,
                    "tenant_id": u.tenant_id,
                    "tenant_name": tenant_map.get(u.tenant_id, ""),
                }
                for u in users
            ],
            "accounts": [
                {
                    "id": a.id,
                    "user_id": a.user_id,
                    "exchange": a.exchange,
                    "label": f"{a.exchange}({a.api_key[:8]}...)" if a.api_key else a.exchange,
                }
                for a in accounts
            ],
        },
    }


# ── 新增绑定 ─────────────────────────────────────────────────

class CreateBindingBody(BaseModel):
    user_id: int
    account_id: int
    strategy_code: str
    mode: int = 2               # 1=单次 2=循环
    capital: float = 0
    leverage: int = 20
    risk_mode: Optional[int] = None          # 非以损定仓策略用
    max_loss_per_trade: Optional[float] = None  # 以损定仓策略用
    status: int = 1


@router.post("")
def create_binding(
    body: CreateBindingBody,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员新增策略绑定"""
    # 校验用户
    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        return {"success": False, "message": "用户不存在"}

    # 校验账户
    account = db.query(ExchangeAccount).filter(ExchangeAccount.id == body.account_id).first()
    if not account:
        return {"success": False, "message": "交易所账户不存在"}
    if account.user_id != body.user_id:
        return {"success": False, "message": "交易所账户不属于该用户"}

    # 校验策略
    strategy = db.query(Strategy).filter(Strategy.code == body.strategy_code, Strategy.status == 1).first()
    if not strategy:
        return {"success": False, "message": "策略不存在或未启用"}

    # 检查重复
    existing = db.query(StrategyBinding).filter(
        StrategyBinding.user_id == body.user_id,
        StrategyBinding.account_id == body.account_id,
        StrategyBinding.strategy_code == body.strategy_code,
    ).first()
    if existing:
        return {"success": False, "message": f"该用户已绑定此策略 (ID: {existing.id})"}

    # mode 校验
    if body.mode not in (1, 2):
        return {"success": False, "message": "执行模式无效（1=单次 2=循环）"}

    binding = StrategyBinding(
        user_id=body.user_id,
        account_id=body.account_id,
        strategy_code=body.strategy_code,
        mode=body.mode,
        capital=body.capital if body.capital > 0 else None,
        leverage=body.leverage if body.leverage > 0 else 20,
        risk_mode=body.risk_mode,
        max_loss_per_trade=body.max_loss_per_trade if body.max_loss_per_trade and body.max_loss_per_trade > 0 else None,
        status=body.status,
    )
    db.add(binding)
    db.commit()
    db.refresh(binding)

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first() if user.tenant_id else None
    return {
        "success": True,
        "message": "绑定创建成功",
        "data": _binding_dict(binding, user=user, tenant=tenant, strategy=strategy, account=account),
    }


# ── 编辑绑定 ─────────────────────────────────────────────────

class UpdateBindingBody(BaseModel):
    capital: Optional[float] = None
    leverage: Optional[int] = None
    risk_mode: Optional[int] = None
    max_loss_per_trade: Optional[float] = None
    mode: Optional[int] = None
    status: Optional[int] = None


@router.put("/{binding_id}")
def update_binding(
    binding_id: int,
    body: UpdateBindingBody,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员修改策略绑定参数"""
    binding = db.query(StrategyBinding).filter(StrategyBinding.id == binding_id).first()
    if not binding:
        return {"success": False, "message": "绑定不存在"}

    changed = []

    if body.capital is not None and body.capital > 0:
        binding.capital = body.capital
        changed.append(f"本金={body.capital}")

    if body.leverage is not None and body.leverage > 0:
        binding.leverage = body.leverage
        changed.append(f"杠杆={body.leverage}")

    if body.risk_mode is not None:
        if body.risk_mode > 0 and body.risk_mode not in RISK_MODE_MAP:
            return {"success": False, "message": "无效的风险档位（1=稳健 2=均衡 3=激进）"}
        binding.risk_mode = body.risk_mode if body.risk_mode > 0 else None
        changed.append(f"风险={RISK_MODE_LABELS.get(body.risk_mode, '无')}")

    if body.max_loss_per_trade is not None:
        binding.max_loss_per_trade = body.max_loss_per_trade if body.max_loss_per_trade > 0 else None
        changed.append(f"每单最大亏损={body.max_loss_per_trade}")

    if body.mode is not None and body.mode in (1, 2):
        binding.mode = body.mode
        changed.append(f"模式={'循环' if body.mode == 2 else '单次'}")

    if body.status is not None and body.status in (0, 1):
        binding.status = body.status
        changed.append(f"状态={'运行' if body.status == 1 else '停止'}")

    if not changed:
        return {"success": False, "message": "未提供任何修改参数"}

    db.commit()
    db.refresh(binding)

    user = db.query(User).filter(User.id == binding.user_id).first()
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first() if user else None
    strategy = db.query(Strategy).filter(Strategy.code == binding.strategy_code).first()
    account = db.query(ExchangeAccount).filter(ExchangeAccount.id == binding.account_id).first()

    return {
        "success": True,
        "message": f"已修改: {', '.join(changed)}",
        "data": _binding_dict(binding, user=user, tenant=tenant, strategy=strategy, account=account),
    }


# ── 删除绑定 ─────────────────────────────────────────────────

@router.delete("/{binding_id}")
def delete_binding(
    binding_id: int,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员删除策略绑定（先停止再删除）"""
    binding = db.query(StrategyBinding).filter(StrategyBinding.id == binding_id).first()
    if not binding:
        return {"success": False, "message": "绑定不存在"}
    if binding.status == 1:
        return {"success": False, "message": "请先停止该绑定后再删除"}
    db.delete(binding)
    db.commit()
    return {"success": True, "message": "绑定已删除"}
