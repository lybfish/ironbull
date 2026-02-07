"""
用户行为分析

GET /api/user-analytics/overview     -> 用户概览（活跃度、留存、分层）
GET /api/user-analytics/ranking      -> 用户排行（交易量、盈亏、点卡）
GET /api/user-analytics/retention    -> 留存分析
GET /api/user-analytics/growth       -> 增长趋势
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, case, and_

from libs.member.models import User, StrategyBinding, ExchangeAccount
from libs.order_trade.models import Order, Fill
from libs.reward.models import ProfitPool

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/user-analytics", tags=["user-analytics"])


@router.get("/overview")
def user_overview(
    days: int = Query(30, ge=7, le=90),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """用户概览统计"""
    now = datetime.now()
    start = now - timedelta(days=days)

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.status == 1).scalar() or 0
    new_users_period = db.query(func.count(User.id)).filter(User.created_at >= start).scalar() or 0

    # 有策略绑定的用户数（活跃交易用户）
    trading_users = (
        db.query(func.count(func.distinct(StrategyBinding.user_id)))
        .filter(StrategyBinding.status == 1)
        .scalar() or 0
    )

    # 有点卡的用户
    funded_users = (
        db.query(func.count(User.id))
        .filter((User.point_card_self > 0) | (User.point_card_gift > 0))
        .scalar() or 0
    )

    # 市场节点数
    market_nodes = db.query(func.count(User.id)).filter(User.is_market_node == 1).scalar() or 0

    # 用户分层：按点卡余额
    tiers = []
    # 分层区间：无余额(<=0)，0-100(0,100]，100-1000(100,1000]，1000-10000(1000,10000]，10000+
    tier_ranges = [
        ("无余额", 0, 0),
        ("0-100", 0, 100),
        ("100-1000", 100, 1000),
        ("1000-10000", 1000, 10000),
        ("10000+", 10000, 999999999),
    ]
    total_card_expr = User.point_card_self + User.point_card_gift
    for label, low, high in tier_ranges:
        if low == 0 and high == 0:
            cnt = db.query(func.count(User.id)).filter(total_card_expr <= 0).scalar() or 0
        else:
            if high >= 999999999:
                cnt = db.query(func.count(User.id)).filter(total_card_expr >= low).scalar() or 0
            else:
                cnt = db.query(func.count(User.id)).filter(
                    and_(total_card_expr > low, total_card_expr <= high)
                ).scalar() or 0
        tiers.append({"label": label, "count": cnt})

    return {
        "success": True,
        "data": {
            "total_users": total_users,
            "active_users": active_users,
            "new_users_period": new_users_period,
            "trading_users": trading_users,
            "funded_users": funded_users,
            "market_nodes": market_nodes,
            "user_tiers": tiers,
            "period_days": days,
        },
    }


@router.get("/ranking")
def user_ranking(
    rank_by: str = Query("point_card", description="排行维度: point_card / reward / trade_count"),
    limit: int = Query(20, ge=5, le=100),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """用户排行榜"""
    if rank_by == "reward":
        users = (
            db.query(User)
            .filter(User.total_reward > 0)
            .order_by(User.total_reward.desc())
            .limit(limit)
            .all()
        )
        return {
            "success": True,
            "data": [
                {
                    "rank": i + 1,
                    "user_id": u.id,
                    "email": u.email,
                    "value": float(u.total_reward or 0),
                    "label": "累计奖励",
                }
                for i, u in enumerate(users)
            ],
        }
    elif rank_by == "trade_count":
        # 按成交笔数排行（按用户汇总：Fill -> ExchangeAccount -> User）
        rows = (
            db.query(User.id, User.email, func.count(Fill.id).label("cnt"))
            .join(ExchangeAccount, ExchangeAccount.user_id == User.id)
            .join(Fill, Fill.account_id == ExchangeAccount.id)
            .group_by(User.id, User.email)
            .order_by(func.count(Fill.id).desc())
            .limit(limit)
            .all()
        )
        return {
            "success": True,
            "data": [
                {
                    "rank": i + 1,
                    "user_id": r[0],
                    "email": r[1] or "",
                    "value": r[2],
                    "label": "成交笔数",
                }
                for i, r in enumerate(rows)
            ],
        }
    else:
        # 默认按点卡余额排行
        users = (
            db.query(User)
            .filter((User.point_card_self + User.point_card_gift) > 0)
            .order_by((User.point_card_self + User.point_card_gift).desc())
            .limit(limit)
            .all()
        )
        return {
            "success": True,
            "data": [
                {
                    "rank": i + 1,
                    "user_id": u.id,
                    "email": u.email,
                    "value": float((u.point_card_self or 0) + (u.point_card_gift or 0)),
                    "label": "点卡余额",
                }
                for i, u in enumerate(users)
            ],
        }


@router.get("/growth")
def user_growth(
    days: int = Query(30, ge=7, le=90),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """用户增长趋势（每日注册、累计）"""
    start = datetime.now() - timedelta(days=days)
    date_list = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]

    rows = (
        db.query(cast(User.created_at, Date).label("d"), func.count(User.id))
        .filter(User.created_at >= start)
        .group_by("d")
        .all()
    )
    daily_map = {str(r[0]): r[1] for r in rows}

    # 起始日之前的累计用户数
    base_count = db.query(func.count(User.id)).filter(User.created_at < start).scalar() or 0
    cumulative = []
    running = base_count
    for d in date_list:
        running += daily_map.get(d, 0)
        cumulative.append(running)

    return {
        "success": True,
        "data": {
            "dates": date_list,
            "daily_new": [daily_map.get(d, 0) for d in date_list],
            "cumulative": cumulative,
        },
    }
