"""
Data API - 持仓查询

GET /api/positions
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from libs.position import PositionService
from libs.position.contracts import PositionFilter

from ..deps import get_db, get_tenant_id, get_account_id_optional
from ..serializers import dto_to_dict

router = APIRouter(prefix="/api", tags=["positions"])


@router.get("/positions")
def list_positions(
    tenant_id: int = Depends(get_tenant_id),
    account_id: Optional[int] = Depends(get_account_id_optional),
    symbol: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    market_type: Optional[str] = Query(None),
    position_side: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    has_position: Optional[bool] = Query(None, description="True 仅返回 quantity>0"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """持仓列表（支持按租户、账户、标的、方向过滤）"""
    filt = PositionFilter(
        tenant_id=tenant_id,
        account_id=account_id,
        symbol=symbol,
        exchange=exchange,
        market_type=market_type,
        position_side=position_side,
        status=status,
        has_position=has_position,
        limit=limit,
        offset=offset,
    )
    svc = PositionService(db)
    positions = svc.list_positions(filt)
    return {"success": True, "data": [dto_to_dict(p) for p in positions], "total": len(positions)}
