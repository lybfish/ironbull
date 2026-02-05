"""
Execution Node - 子服务器执行端

接收中心 POST /api/execute，用请求中的凭证调交易所下单，同步返回执行结果。
不连数据库，不写库。
"""

import sys
import os
import asyncio
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from libs.core import get_config, get_logger, setup_logging
from libs.trading.live_trader import LiveTrader
from libs.trading.base import OrderSide, OrderType, OrderStatus

config = get_config()
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name="execution-node",
)
log = get_logger("execution-node")

app = FastAPI(title="Execution Node", version="1.0")


class TaskItem(BaseModel):
    account_id: int
    tenant_id: int
    user_id: int
    exchange: str
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None
    market_type: str = "future"


class ExecuteRequest(BaseModel):
    signal: Dict[str, Any]
    amount_usdt: float = 100.0
    sandbox: bool = True
    tasks: List[TaskItem]


class SyncTasksRequest(BaseModel):
    """同步余额/持仓请求：仅 tasks + sandbox"""
    tasks: List[TaskItem]
    sandbox: bool = True


async def _sync_balance_one(task: TaskItem, sandbox: bool) -> Dict[str, Any]:
    """节点侧：查交易所余额，不写库，返回结果"""
    trader = LiveTrader(
        exchange=task.exchange or "binance",
        api_key=task.api_key,
        api_secret=task.api_secret,
        passphrase=task.passphrase,
        sandbox=sandbox,
        market_type=task.market_type or "future",
        settlement_service=None,
    )
    try:
        balances = await trader.get_balance("USDT")
        await trader.close()
        usdt = balances.get("USDT")
        if usdt is None:
            return {
                "account_id": task.account_id,
                "tenant_id": task.tenant_id,
                "success": True,
                "balance": 0,
                "available": 0,
                "frozen": 0,
                "error": None,
            }
        return {
            "account_id": task.account_id,
            "tenant_id": task.tenant_id,
            "success": True,
            "balance": float(usdt.total or 0),
            "available": float(usdt.free or 0),
            "frozen": float(usdt.locked or 0),
            "error": None,
        }
    except Exception as e:
        try:
            await trader.close()
        except Exception:
            pass
        log.error("sync_balance account_id=%s error=%s", task.account_id, e)
        return {
            "account_id": task.account_id,
            "tenant_id": task.tenant_id,
            "success": False,
            "balance": 0,
            "available": 0,
            "frozen": 0,
            "error": str(e),
        }


async def _sync_positions_one(task: TaskItem, sandbox: bool) -> Dict[str, Any]:
    """节点侧：查交易所持仓，不写库，返回结果"""
    trader = LiveTrader(
        exchange=task.exchange or "binance",
        api_key=task.api_key,
        api_secret=task.api_secret,
        passphrase=task.passphrase,
        sandbox=sandbox,
        market_type=task.market_type or "future",
        settlement_service=None,
    )
    try:
        # ccxt: fetch_positions() 返回当前持仓列表
        positions = await trader.exchange.fetch_positions()
        await trader.close()
        out = []
        for p in positions or []:
            qty = float(p.get("contracts", 0) or 0)
            if qty == 0:
                continue
            side = (p.get("side") or "long").lower()
            position_side = "LONG" if side == "long" else "SHORT"
            out.append({
                "symbol": p.get("symbol") or "",
                "position_side": position_side,
                "quantity": abs(qty),
                "entry_price": float(p.get("entryPrice") or p.get("averagePrice") or 0),
                "unrealized_pnl": float(p.get("unrealizedPnl") or 0),
                "leverage": int(p.get("leverage") or 0),
                "liquidation_price": float(p.get("liquidationPrice") or 0) if p.get("liquidationPrice") else None,
            })
        return {
            "account_id": task.account_id,
            "tenant_id": task.tenant_id,
            "success": True,
            "positions": out,
            "error": None,
        }
    except Exception as e:
        try:
            await trader.close()
        except Exception:
            pass
        log.error("sync_positions account_id=%s error=%s", task.account_id, e)
        return {
            "account_id": task.account_id,
            "tenant_id": task.tenant_id,
            "success": False,
            "positions": [],
            "error": str(e),
        }


async def _run_one(
    task: TaskItem,
    symbol: str,
    side: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    amount_usdt: float,
    sandbox: bool,
) -> Dict[str, Any]:
    quantity = round(amount_usdt / entry_price, 6) if entry_price else 0
    if quantity <= 0:
        return {"account_id": task.account_id, "success": False, "error": "quantity<=0"}
    order_side = OrderSide.BUY if (side or "BUY").upper() == "BUY" else OrderSide.SELL
    trader = LiveTrader(
        exchange=task.exchange or "binance",
        api_key=task.api_key,
        api_secret=task.api_secret,
        passphrase=task.passphrase,
        sandbox=sandbox,
        market_type=task.market_type or "future",
        settlement_service=None,
    )
    try:
        result = await trader.create_order(
            symbol=symbol,
            side=order_side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            signal_id=None,
        )
        ok = result.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)
        filled_qty = result.filled_quantity or 0
        filled_price = result.filled_price or entry_price
        exchange_order_id = str(result.exchange_order_id) if result.exchange_order_id else None
        if ok and (stop_loss or take_profit) and filled_qty > 0:
            try:
                await trader.set_sl_tp(
                    symbol=symbol,
                    side=order_side,
                    quantity=filled_qty,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )
            except Exception as e:
                log.warning("set_sl_tp failed account_id=%s: %s", task.account_id, e)
        await trader.close()
        return {
            "account_id": task.account_id,
            "success": ok,
            "order_id": result.order_id,
            "exchange_order_id": exchange_order_id,
            "filled_quantity": filled_qty,
            "filled_price": filled_price,
            "error": None,
        }
    except Exception as e:
        try:
            await trader.close()
        except Exception:
            pass
        log.error("execute account_id=%s error=%s", task.account_id, e)
        return {
            "account_id": task.account_id,
            "success": False,
            "order_id": None,
            "exchange_order_id": None,
            "filled_quantity": 0,
            "filled_price": 0,
            "error": str(e),
        }


@app.post("/api/execute")
def api_execute(req: ExecuteRequest):
    """执行信号：对 tasks 中每个账户下单，返回 results（同步）"""
    signal = req.signal or {}
    symbol = signal.get("symbol") or "BTC/USDT"
    side = signal.get("side") or "BUY"
    entry_price = float(signal.get("entry_price") or 0)
    stop_loss = float(signal.get("stop_loss") or 0)
    take_profit = float(signal.get("take_profit") or 0)
    if not entry_price:
        raise HTTPException(status_code=400, detail="signal.entry_price required")
    if not req.tasks:
        return {"success": True, "results": []}
    results = []
    for task in req.tasks:
        r = asyncio.run(
            _run_one(
                task=task,
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                amount_usdt=req.amount_usdt,
                sandbox=req.sandbox,
            )
        )
        results.append(r)
    return {"success": True, "results": results}


@app.post("/api/sync-balance")
def api_sync_balance(req: SyncTasksRequest):
    """同步余额：对 tasks 中每个账户查交易所余额，返回 results（不写库）"""
    if not req.tasks:
        return {"success": True, "results": []}
    results = []
    for task in req.tasks:
        r = asyncio.run(_sync_balance_one(task=task, sandbox=req.sandbox))
        results.append(r)
    return {"success": True, "results": results}


@app.post("/api/sync-positions")
def api_sync_positions(req: SyncTasksRequest):
    """同步持仓：对 tasks 中每个账户查交易所持仓，返回 results（不写库）"""
    if not req.tasks:
        return {"success": True, "results": []}
    results = []
    for task in req.tasks:
        r = asyncio.run(_sync_positions_one(task=task, sandbox=req.sandbox))
        results.append(r)
    return {"success": True, "results": results}


@app.get("/health")
def health():
    return {"status": "ok", "service": "execution-node"}


if __name__ == "__main__":
    import uvicorn
    port = config.get_int("execution_node_port", 9101)
    uvicorn.run(app, host="0.0.0.0", port=port)
