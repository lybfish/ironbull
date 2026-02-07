"""
Data API - 分析与绩效查询

GET /api/analytics/performance  - 绩效汇总与净值曲线
GET /api/analytics/risk        - 风险指标（最新）
GET /api/analytics/statistics  - 交易统计列表
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException

from sqlalchemy.orm import Session

from libs.analytics import AnalyticsService, TradeStatisticsRepository

from ..deps import get_db, get_tenant_id, get_current_admin
from ..serializers import dto_to_dict
from ..utils import parse_date

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/performance")
def get_performance(
    tenant_id: int = Depends(get_tenant_id),
    account_id: Optional[int] = Query(None, description="账户ID，不传时默认 1"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD，净值曲线起始"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD，净值曲线结束"),
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    """绩效汇总与净值曲线。不传 account_id 时默认 1；不传 start_date/end_date 时仅返回汇总。"""
    try:
        aid = account_id if account_id is not None else 1
        svc = AnalyticsService(db, tenant_id=tenant_id, account_id=aid)
        summary = svc.get_performance_summary()
        out = {"summary": dto_to_dict(summary)}
        sd = parse_date(start_date)
        ed = parse_date(end_date)
        if sd is not None or ed is not None:
            curve = svc.get_equity_curve(start_date=sd, end_date=ed)
            out["equity_curve"] = dto_to_dict(curve)
        return {"success": True, "data": out}
    except Exception as e:
        logger.exception("绩效查询失败")
        raise HTTPException(status_code=500, detail=f"绩效查询失败: {str(e)}")


@router.get("/risk")
def get_risk(
    tenant_id: int = Depends(get_tenant_id),
    account_id: Optional[int] = Query(None, description="账户ID，不传时默认 1"),
    strategy_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    """最新风险指标（夏普、回撤、VaR 等）"""
    try:
        aid = account_id if account_id is not None else 1
        svc = AnalyticsService(db, tenant_id=tenant_id, account_id=aid)
        risk = svc.get_latest_risk_metrics(strategy_code=strategy_code)
        return {"success": True, "data": dto_to_dict(risk) if risk else None}
    except Exception as e:
        logger.exception("风险指标查询失败")
        raise HTTPException(status_code=500, detail=f"风险指标查询失败: {str(e)}")


@router.get("/statistics")
def list_statistics(
    tenant_id: int = Depends(get_tenant_id),
    account_id: Optional[int] = Query(None, description="账户ID，不传时默认 1"),
    period_type: Optional[str] = Query(None),
    strategy_code: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    """交易统计列表（胜率、盈亏比、获利因子等）"""
    try:
        aid = account_id if account_id is not None else 1
        repo = TradeStatisticsRepository(db, tenant_id)
        stats = repo.list_statistics(
            account_id=aid,
            period_type=period_type,
            strategy_code=strategy_code,
            symbol=symbol,
            limit=limit,
        )
        return {"success": True, "data": [dto_to_dict(s) for s in stats], "total": len(stats)}
    except Exception as e:
        logger.exception("统计查询失败")
        raise HTTPException(status_code=500, detail=f"统计查询失败: {str(e)}")
