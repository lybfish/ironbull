"""
Data API - 分析与绩效查询

GET /api/analytics/performance  - 绩效汇总与净值曲线
GET /api/analytics/risk        - 风险指标（最新）
GET /api/analytics/statistics  - 交易统计列表
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from libs.analytics import AnalyticsService, TradeStatisticsRepository

from ..deps import get_db, get_tenant_id
from ..serializers import dto_to_dict

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


@router.get("/performance")
def get_performance(
    tenant_id: int = Depends(get_tenant_id),
    account_id: int = Query(..., description="账户ID（必填）"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD，净值曲线起始"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD，净值曲线结束"),
    db: Session = Depends(get_db),
):
    """绩效汇总与净值曲线。不传 start_date/end_date 时仅返回汇总；传则同时返回 equity_curve。"""
    svc = AnalyticsService(db, tenant_id=tenant_id, account_id=account_id)
    summary = svc.get_performance_summary()
    out = {"summary": dto_to_dict(summary)}
    sd = _parse_date(start_date)
    ed = _parse_date(end_date)
    if sd is not None or ed is not None:
        curve = svc.get_equity_curve(start_date=sd, end_date=ed)
        out["equity_curve"] = dto_to_dict(curve)
    return {"success": True, "data": out}


@router.get("/risk")
def get_risk(
    tenant_id: int = Depends(get_tenant_id),
    account_id: int = Query(..., description="账户ID（必填）"),
    strategy_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """最新风险指标（夏普、回撤、VaR 等）"""
    svc = AnalyticsService(db, tenant_id=tenant_id, account_id=account_id)
    risk = svc.get_latest_risk_metrics(strategy_code=strategy_code)
    return {"success": True, "data": dto_to_dict(risk) if risk else None}


@router.get("/statistics")
def list_statistics(
    tenant_id: int = Depends(get_tenant_id),
    account_id: int = Query(..., description="账户ID（必填）"),
    period_type: Optional[str] = Query(None),
    strategy_code: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """交易统计列表（胜率、盈亏比、获利因子等）"""
    repo = TradeStatisticsRepository(db, tenant_id)
    stats = repo.list_statistics(
        account_id=account_id,
        period_type=period_type,
        strategy_code=strategy_code,
        symbol=symbol,
        limit=limit,
    )
    return {"success": True, "data": [dto_to_dict(s) for s in stats], "total": len(stats)}
