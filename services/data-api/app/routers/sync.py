"""
中心同步 API：向执行节点拉取余额/持仓/成交并写回数据库。
- POST /api/sync/balance   - 同步余额（可选 node_id、sandbox）
- POST /api/sync/positions - 同步持仓（可选 node_id、sandbox）
- POST /api/sync/trades    - 同步成交流水（可选 node_id、sandbox）
- POST /api/sync/markets   - 同步市场信息到 dim_market_info（所有交易所）
- GET  /api/sync/markets   - 查询已同步的市场信息
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from libs.sync_node import sync_balance_from_nodes, sync_positions_from_nodes, sync_trades_from_nodes
from libs.exchange.market_service import MarketInfoService
from ..deps import get_db, get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/balance")
def post_sync_balance(
    node_id: Optional[int] = None,
    sandbox: Optional[bool] = None,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """向执行节点发起余额同步，并写回 fact_account。不传 node_id 则同步所有活跃节点。"""
    try:
        result = sync_balance_from_nodes(db, node_id=node_id, sandbox=sandbox)
        db.commit()
        return {"success": True, "data": result}
    except Exception as e:
        logger.exception("余额同步失败")
        raise HTTPException(status_code=500, detail=f"余额同步失败: {str(e)}")


@router.post("/positions")
def post_sync_positions(
    node_id: Optional[int] = None,
    sandbox: Optional[bool] = None,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """向执行节点发起持仓同步，并写回 fact_position。不传 node_id 则同步所有活跃节点。"""
    try:
        result = sync_positions_from_nodes(db, node_id=node_id, sandbox=sandbox)
        db.commit()
        return {"success": True, "data": result}
    except Exception as e:
        logger.exception("持仓同步失败")
        raise HTTPException(status_code=500, detail=f"持仓同步失败: {str(e)}")


@router.post("/trades")
def post_sync_trades(
    node_id: Optional[int] = None,
    sandbox: Optional[bool] = None,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """向执行节点发起成交同步，写入 fact_transaction。自动去重。"""
    try:
        result = sync_trades_from_nodes(db, node_id=node_id, sandbox=sandbox)
        db.commit()
        return {"success": True, "data": result}
    except Exception as e:
        logger.exception("成交同步失败")
        raise HTTPException(status_code=500, detail=f"成交同步失败: {str(e)}")


# ═══════════════════════════════════════════════════════════════
# 市场信息同步（dim_market_info）
# ═══════════════════════════════════════════════════════════════

SUPPORTED_EXCHANGES = ["binance", "gate", "okx"]


@router.post("/markets")
def post_sync_markets(
    exchange: Optional[str] = None,
    market_type: str = "swap",
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    从 ccxt load_markets 同步市场信息到 dim_market_info。

    - exchange: 指定交易所 (binance/gate/okx)，不传则同步所有
    - market_type: swap（永续合约）或 spot（现货）
    """
    svc = MarketInfoService(db)
    exchanges = [exchange] if exchange else SUPPORTED_EXCHANGES
    results = {}
    for ex in exchanges:
        try:
            r = svc.sync_from_ccxt(ex, market_type=market_type)
            results[ex] = r
        except Exception as e:
            logger.exception(f"市场信息同步失败: {ex}")
            results[ex] = {"error": str(e)}
    return {"success": True, "data": results}


@router.get("/markets")
def get_markets(
    exchange: Optional[str] = None,
    market_type: Optional[str] = None,
    symbol: Optional[str] = None,
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """查询已同步的市场信息"""
    svc = MarketInfoService(db)
    from libs.exchange.market_service import MarketInfo, _normalize_exchange
    from libs.exchange.utils import normalize_symbol
    q = db.query(MarketInfo).filter(MarketInfo.is_active == 1)
    if exchange:
        q = q.filter(MarketInfo.exchange == _normalize_exchange(exchange))
    if market_type:
        q = q.filter(MarketInfo.market_type == market_type)
    if symbol:
        canonical = normalize_symbol(symbol)
        q = q.filter(MarketInfo.canonical_symbol == canonical)
    markets = q.order_by(MarketInfo.exchange, MarketInfo.canonical_symbol).all()
    return {
        "success": True,
        "data": [m.to_dict() for m in markets],
        "total": len(markets),
    }
