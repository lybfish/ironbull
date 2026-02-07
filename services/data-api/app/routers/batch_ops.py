"""
批量操作 API

POST /api/batch/toggle-users     -> 批量启用/禁用用户
POST /api/batch/recharge-users   -> 批量充值点卡
POST /api/batch/bind-strategy    -> 批量绑定策略
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from libs.member.models import User, StrategyBinding
from libs.pointcard.service import PointCardService

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/batch", tags=["batch-ops"])


class BatchToggleBody(BaseModel):
    user_ids: List[int]
    status: int = 1  # 1=启用, 0=禁用


class BatchRechargeBody(BaseModel):
    user_ids: List[int]
    amount: float
    card_type: str = "self"  # self=充值, gift=赠送


class BatchBindStrategyBody(BaseModel):
    user_ids: List[int]
    strategy_id: int
    capital: Optional[float] = None
    leverage: Optional[int] = None


@router.post("/toggle-users")
def batch_toggle_users(
    body: BatchToggleBody,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """批量启用/禁用用户"""
    if not body.user_ids:
        raise HTTPException(status_code=400, detail="请选择用户")
    if len(body.user_ids) > 200:
        raise HTTPException(status_code=400, detail="单次最多操作200个用户")

    users = db.query(User).filter(User.id.in_(body.user_ids)).all()
    if not users:
        raise HTTPException(status_code=404, detail="未找到用户")

    updated = 0
    skipped = 0
    for u in users:
        if u.is_root:
            skipped += 1
            continue
        u.status = body.status
        updated += 1

    db.commit()
    label = "启用" if body.status == 1 else "禁用"
    return {
        "success": True,
        "message": f"已{label} {updated} 个用户" + (f"，跳过 {skipped} 个（根用户不可操作）" if skipped else ""),
        "data": {"updated": updated, "skipped": skipped},
    }


@router.post("/recharge-users")
def batch_recharge_users(
    body: BatchRechargeBody,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """批量充值点卡"""
    if not body.user_ids:
        raise HTTPException(status_code=400, detail="请选择用户")
    if len(body.user_ids) > 100:
        raise HTTPException(status_code=400, detail="单次最多操作100个用户")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="金额必须大于0")

    users = db.query(User).filter(User.id.in_(body.user_ids)).all()
    if not users:
        raise HTTPException(status_code=404, detail="未找到用户")

    svc = PointCardService(db)
    use_self = body.card_type != "gift"
    success_count = 0
    fail_count = 0
    errors = []

    for u in users:
        try:
            ok, err, _ = svc.recharge_user(u.tenant_id, u.id, Decimal(str(body.amount)), use_self)
            if ok:
                success_count += 1
            else:
                fail_count += 1
                errors.append({"user_id": u.id, "error": err})
        except Exception as e:
            fail_count += 1
            errors.append({"user_id": u.id, "error": str(e)})

    db.commit()
    return {
        "success": True,
        "message": f"充值完成：成功 {success_count}，失败 {fail_count}",
        "data": {"success_count": success_count, "fail_count": fail_count, "errors": errors[:10]},
    }


@router.post("/bind-strategy")
def batch_bind_strategy(
    body: BatchBindStrategyBody,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """批量绑定策略"""
    if not body.user_ids:
        raise HTTPException(status_code=400, detail="请选择用户")
    if len(body.user_ids) > 100:
        raise HTTPException(status_code=400, detail="单次最多操作100个用户")

    from libs.member.models import Strategy
    strategy = db.query(Strategy).filter(Strategy.id == body.strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    users = db.query(User).filter(User.id.in_(body.user_ids)).all()
    created = 0
    skipped = 0

    for u in users:
        # 检查是否已绑定
        existing = db.query(StrategyBinding).filter(
            StrategyBinding.user_id == u.id,
            StrategyBinding.strategy_id == body.strategy_id,
            StrategyBinding.status == 1,
        ).first()
        if existing:
            skipped += 1
            continue

        binding = StrategyBinding(
            tenant_id=u.tenant_id,
            user_id=u.id,
            strategy_id=body.strategy_id,
            strategy_code=strategy.code,
            capital=body.capital or float(strategy.amount_usdt or 0),
            leverage=body.leverage or strategy.leverage or 1,
            risk_mode=strategy.risk_mode or "isolated",
            status=1,
        )
        db.add(binding)
        created += 1

    db.commit()
    return {
        "success": True,
        "message": f"绑定完成：新增 {created}，跳过 {skipped}（已绑定）",
        "data": {"created": created, "skipped": skipped},
    }
