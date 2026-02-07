"""
Execution Node - 子服务器执行端

接收中心 POST /api/execute，用请求中的凭证调交易所下单，同步返回执行结果。
不连数据库，不写库。
支持定时心跳：配置 center_url + node_code 后，节点启动时自动向中心发送心跳。
"""

import sys
import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
import httpx

from libs.core import get_config, get_logger, setup_logging
from libs.exchange.utils import to_canonical_symbol, normalize_symbol
from libs.exchange.market_service import contracts_to_coins_by_size
from libs.trading.live_trader import LiveTrader
from libs.trading.base import OrderSide, OrderType, OrderStatus

config = get_config()
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name="execution-node",
)
log = get_logger("execution-node")

# ---------- 心跳 ----------

# 中心 data-api 地址，如 http://192.168.1.1:8026；为空则不发心跳
CENTER_URL = config.get_str("center_url", "").strip().rstrip("/")
# 本节点编码，需与中心 dim_execution_node.node_code 一致
NODE_CODE = config.get_str("node_code", "").strip()
# 心跳间隔（秒），默认 60
HEARTBEAT_INTERVAL = config.get_int("heartbeat_interval", 60)
HEARTBEAT_TIMEOUT = config.get_float("heartbeat_timeout", 10.0)

_heartbeat_task: Optional[asyncio.Task] = None


async def _heartbeat_loop():
    """后台任务：定时向中心 POST /api/nodes/{node_code}/heartbeat"""
    url = f"{CENTER_URL}/api/nodes/{NODE_CODE}/heartbeat"
    secret = config.get_str("node_auth_secret", "").strip()
    headers = {}
    if secret:
        headers["X-Center-Token"] = secret
    log.info("heartbeat started", url=url, interval=HEARTBEAT_INTERVAL)
    while True:
        try:
            async with httpx.AsyncClient(timeout=HEARTBEAT_TIMEOUT) as client:
                resp = await client.post(url, headers=headers or None)
                if resp.status_code == 200:
                    log.debug("heartbeat ok")
                else:
                    log.warning("heartbeat response unexpected", status=resp.status_code, body=resp.text[:200])
        except Exception as e:
            log.warning("heartbeat failed", error=str(e))
        await asyncio.sleep(HEARTBEAT_INTERVAL)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """FastAPI lifespan：启动时开始心跳，关闭时取消"""
    global _heartbeat_task
    if CENTER_URL and NODE_CODE:
        _heartbeat_task = asyncio.create_task(_heartbeat_loop())
    else:
        log.info("heartbeat disabled (center_url or node_code not configured)")
    yield
    if _heartbeat_task and not _heartbeat_task.done():
        _heartbeat_task.cancel()
        try:
            await _heartbeat_task
        except asyncio.CancelledError:
            pass
        log.info("heartbeat stopped")


app = FastAPI(title="Execution Node", version="1.0", lifespan=lifespan)


def _allowed_ips_set():
    """解析 node_allowed_ips 为集合，空则返回 None（不校验 IP）"""
    raw = config.get_str("node_allowed_ips", "").strip()
    if not raw:
        return None
    return {ip.strip() for ip in raw.split(",") if ip.strip()}


async def verify_center_token(request: Request):
    """仅中心可调：校验 X-Center-Token 与可选 IP 白名单；未开启鉴权则放行"""
    if not config.get_bool("node_auth_enabled", False):
        return
    secret = config.get_str("node_auth_secret", "").strip()
    if not secret:
        return
    token = (request.headers.get("X-Center-Token") or "").strip()
    if token != secret:
        log.warning("center token mismatch or missing")
        raise HTTPException(status_code=401, detail="Unauthorized")
    allowed = _allowed_ips_set()
    if allowed:
        client_host = request.client.host if request.client else ""
        if client_host not in allowed:
            log.warning("center ip not allowed", client_host=client_host)
            raise HTTPException(status_code=401, detail="Unauthorized")


class TaskItem(BaseModel):
    account_id: int
    tenant_id: int
    user_id: int
    exchange: str
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None
    market_type: str = "future"  # future=合约（默认，会做双向持仓检测）, spot=现货
    amount_usdt: Optional[float] = None  # 该账户实际下单金额（按 ratio 缩放后），优先于 req.amount_usdt
    leverage: Optional[int] = None  # 该租户策略实例杠杆覆盖，空则用 signal.leverage


class ExecuteRequest(BaseModel):
    signal: Dict[str, Any]
    amount_usdt: float = 100.0  # 回退默认值，实际应由策略配置传入
    sandbox: bool = True
    tasks: List[TaskItem]

    # 注意：amount_usdt 的优先级为：task.amount_usdt > req.amount_usdt > signal.amount_usdt > 此默认值


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
            "unrealized_pnl": float(usdt.unrealized_pnl or 0),
            "margin_used": float(usdt.margin_used or 0),
            "margin_ratio": float(usdt.margin_ratio or 0),
            "equity": float(usdt.equity or usdt.total or 0),
            "error": None,
        }
    except Exception as e:
        try:
            await trader.close()
        except Exception:
            pass
        log.error("sync_balance error", account_id=task.account_id, error=str(e))
        return {
            "account_id": task.account_id,
            "tenant_id": task.tenant_id,
            "success": False,
            "balance": 0,
            "available": 0,
            "frozen": 0,
            "unrealized_pnl": 0,
            "margin_used": 0,
            "margin_ratio": 0,
            "equity": 0,
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
            # 统一转换：合约张数→币数量（Gate/OKX 有 contractSize，Binance=1 不变）
            contract_size = float(p.get("contractSize") or 0)
            coin_qty = contracts_to_coins_by_size(abs(qty), contract_size)
            if contract_size > 0 and contract_size != 1:
                log.debug("position contract→coin", contracts=qty, contract_size=contract_size, coin_qty=coin_qty)
            side = (p.get("side") or "long").lower()
            position_side = "LONG" if side == "long" else "SHORT"
            # 统一为规范 symbol（BTC/USDT），便于存储与跨所一致
            raw_sym = p.get("symbol") or ""
            sym = to_canonical_symbol(raw_sym, "future")
            # 提取杠杆/强平价/未实现盈亏：区分 None（未返回）和 0（有效值）
            _lev = p.get("leverage")
            _liq = p.get("liquidationPrice")
            _upnl = p.get("unrealizedPnl")
            # Binance 不直接返回 leverage，需从原始数据计算: notional / initialMargin
            info = p.get("info") or {}
            if _lev is None and info:
                try:
                    notional = float(info.get("notional") or 0)
                    initial_margin = float(info.get("initialMargin") or 0)
                    if initial_margin > 0:
                        _lev = round(notional / initial_margin)
                except (ValueError, ZeroDivisionError):
                    pass
            # Binance 全仓模式下 liquidationPrice='0'，CCXT 映射为 None
            # 从原始数据回填（0 = 全仓模式，无独立强平价）
            if _liq is None and info:
                try:
                    raw_liq = info.get("liquidationPrice")
                    if raw_liq is not None:
                        _liq = float(raw_liq)
                except (ValueError, TypeError):
                    pass
            out.append({
                "symbol": sym or raw_sym,
                "position_side": position_side,
                "quantity": coin_qty,
                "entry_price": float(p.get("entryPrice") or p.get("averagePrice") or 0),
                "unrealized_pnl": float(_upnl) if _upnl is not None else None,
                "leverage": int(_lev) if _lev is not None else None,
                "liquidation_price": float(_liq) if _liq is not None else None,
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
        log.error("sync_positions error", account_id=task.account_id, error=str(e))
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
    leverage: int = 0,
) -> Dict[str, Any]:
    # 统一为规范 symbol（BTC/USDT），LiveTrader 内部会转为 CCXT 合约格式
    symbol = to_canonical_symbol(normalize_symbol(symbol or "", "binance"), "future")
    if amount_usdt <= 0 or entry_price <= 0:
        return {"account_id": task.account_id, "success": False, "error": "invalid amount_usdt or entry_price"}
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
        # 传 amount_usdt 让 LiveTrader 内部统一换算数量（自动处理 contractSize、最小限制等）
        result = await trader.create_order(
            symbol=symbol,
            side=order_side,
            order_type=OrderType.MARKET,
            amount_usdt=amount_usdt,
            price=entry_price,
            leverage=leverage or None,
            signal_id=None,
        )
        ok = result.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)
        filled_qty = result.filled_quantity or 0
        filled_price = result.filled_price or entry_price
        exchange_order_id = str(result.exchange_order_id) if result.exchange_order_id else None
        # 不在交易所挂止盈止损单，由中心 position_monitor 自管到价平仓

        # 张数→币数量转换（Gate/OKX 合约以张为单位，需 × contractSize 得到真实币量）
        # 统一转换：张数→币数量
        coin_qty = filled_qty
        if filled_qty > 0 and (task.market_type or "future") == "future":
            try:
                ccxt_sym = trader._ccxt_symbol(symbol)
                market = trader.exchange.markets.get(ccxt_sym, {})
                cs = float(market.get("contractSize") or 0)
                coin_qty = contracts_to_coins_by_size(filled_qty, cs)
                if cs > 0 and cs != 1:
                    log.info("order contract→coin", contracts=filled_qty, contract_size=cs, coin_qty=coin_qty)
            except Exception as conv_err:
                log.warning("contract→coin conversion failed, using raw qty", error=str(conv_err))

        await trader.close()
        return {
            "account_id": task.account_id,
            "success": ok,
            "order_id": result.order_id,
            "exchange_order_id": exchange_order_id,
            "filled_quantity": coin_qty,
            "filled_price": filled_price,
            "error": None,
        }
    except Exception as e:
        try:
            await trader.close()
        except Exception:
            pass
        log.error("execute error", account_id=task.account_id, error=str(e))
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
def api_execute(req: ExecuteRequest, _: None = Depends(verify_center_token)):
    """执行信号：对 tasks 中每个账户下单，返回 results（同步）"""
    signal = req.signal or {}
    symbol = signal.get("symbol")
    if not symbol:
        raise HTTPException(status_code=400, detail="signal.symbol required")
    side = signal.get("side") or "BUY"
    entry_price = float(signal.get("entry_price") or 0)
    stop_loss = float(signal.get("stop_loss") or 0)
    take_profit = float(signal.get("take_profit") or 0)
    leverage = int(signal.get("leverage") or 0)  # 杠杆倍数（策略配置，随信号传入）
    if not entry_price:
        raise HTTPException(status_code=400, detail="signal.entry_price required")
    if not req.tasks:
        return {"success": True, "results": []}
    results = []
    for task in req.tasks:
        # 优先用 task 级别的 amount_usdt（按 binding ratio 缩放后），回退到 req 级别
        task_amount = task.amount_usdt if task.amount_usdt and task.amount_usdt > 0 else req.amount_usdt
        # 优先用 task 级别杠杆（租户策略实例覆盖），无则用 signal
        task_leverage = (task.leverage if task.leverage and task.leverage > 0 else None) or leverage
        r = asyncio.run(
            _run_one(
                task=task,
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                amount_usdt=task_amount,
                sandbox=req.sandbox,
                leverage=task_leverage,
            )
        )
        results.append(r)
    return {"success": True, "results": results}


async def _sync_trades_one(task: TaskItem, sandbox: bool, symbols: list = None, since_ms: int = None) -> Dict[str, Any]:
    """节点侧：查交易所最近成交记录，不写库，返回结果"""
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
        all_trades = []
        target_symbols = symbols or ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]
        # 加载市场信息，用于获取 contractSize 做张数→币数量转换
        await trader.exchange.load_markets()
        for sym in target_symbols:
            try:
                # 获取该 symbol 的 contractSize（Gate/OKX 合约用张数）
                market = trader.exchange.markets.get(sym, {})
                contract_size = float(market.get("contractSize") or 0)
                trades = await trader.exchange.fetch_my_trades(sym, since=since_ms, limit=100)
                for t in trades or []:
                    raw_sym = t.get("symbol") or sym
                    canonical = to_canonical_symbol(raw_sym, "future")
                    side = (t.get("side") or "buy").upper()
                    raw_qty = float(t.get("amount") or 0)
                    # 统一转换：张数→币数量
                    coin_qty = contracts_to_coins_by_size(raw_qty, contract_size)
                    if contract_size > 0 and contract_size != 1:
                        log.debug("trade contract→coin", symbol=sym, contracts=raw_qty,
                                  contract_size=contract_size, coin_qty=coin_qty)
                    all_trades.append({
                        "trade_id": str(t.get("id") or ""),
                        "order_id": str(t.get("order") or ""),
                        "symbol": canonical or raw_sym,
                        "side": side,
                        "price": float(t.get("price") or 0),
                        "quantity": coin_qty,
                        "cost": float(t.get("cost") or 0),
                        "fee": float((t.get("fee") or {}).get("cost", 0) or 0),
                        "fee_currency": (t.get("fee") or {}).get("currency", "USDT"),
                        "timestamp": t.get("timestamp"),
                        "datetime": t.get("datetime"),
                    })
            except Exception as e:
                log.warning("fetch_my_trades skip", symbol=sym, error=str(e))
        await trader.close()
        return {
            "account_id": task.account_id,
            "tenant_id": task.tenant_id,
            "success": True,
            "trades": all_trades,
            "error": None,
        }
    except Exception as e:
        try:
            await trader.close()
        except Exception:
            pass
        log.error("sync_trades error", account_id=task.account_id, error=str(e))
        return {
            "account_id": task.account_id,
            "tenant_id": task.tenant_id,
            "success": False,
            "trades": [],
            "error": str(e),
        }


class SyncTradesRequest(BaseModel):
    tasks: List[TaskItem]
    sandbox: bool = True
    symbols: List[str] = None
    since_ms: int = None


@app.post("/api/sync-trades")
def api_sync_trades(req: SyncTradesRequest, _: None = Depends(verify_center_token)):
    """同步成交：对 tasks 中每个账户查交易所成交记录，返回 results（不写库）"""
    if not req.tasks:
        return {"success": True, "results": []}
    results = []
    for task in req.tasks:
        r = asyncio.run(_sync_trades_one(
            task=task, sandbox=req.sandbox,
            symbols=req.symbols, since_ms=req.since_ms
        ))
        results.append(r)
    return {"success": True, "results": results}


@app.post("/api/sync-balance")
def api_sync_balance(req: SyncTasksRequest, _: None = Depends(verify_center_token)):
    """同步余额：对 tasks 中每个账户查交易所余额，返回 results（不写库）"""
    if not req.tasks:
        return {"success": True, "results": []}
    results = []
    for task in req.tasks:
        r = asyncio.run(_sync_balance_one(task=task, sandbox=req.sandbox))
        results.append(r)
    return {"success": True, "results": results}


@app.post("/api/sync-positions")
def api_sync_positions(req: SyncTasksRequest, _: None = Depends(verify_center_token)):
    """同步持仓：对 tasks 中每个账户查交易所持仓，返回 results（不写库）"""
    if not req.tasks:
        return {"success": True, "results": []}
    results = []
    for task in req.tasks:
        r = asyncio.run(_sync_positions_one(task=task, sandbox=req.sandbox))
        results.append(r)
    return {"success": True, "results": results}


# ═══════════════════════════════════════════════════════════════
# 取消残留条件单（止损/止盈触发后清理另一侧）
# ═══════════════════════════════════════════════════════════════

class CancelConditionalsRequest(BaseModel):
    """取消指定 symbol 的残留条件单"""
    tasks: List[TaskItem]
    sandbox: bool = True
    symbols: List[str]  # 需要清理的交易对列表（canonical 格式: BTC/USDT）


async def _cancel_conditionals_one(
    task: TaskItem, sandbox: bool, symbols: List[str],
) -> Dict[str, Any]:
    """对单个账户，取消指定 symbol 的所有残留条件委托单"""
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
        await trader.exchange.load_markets()
        total_cancelled = 0
        total_errors = 0
        results_by_symbol = {}
        for sym in symbols:
            r = await trader.cancel_all_open_orders(sym)
            results_by_symbol[sym] = r
            total_cancelled += r.get("cancelled", 0)
            total_errors += r.get("errors", 0)
        await trader.close()
        return {
            "account_id": task.account_id,
            "success": True,
            "cancelled": total_cancelled,
            "errors": total_errors,
            "by_symbol": results_by_symbol,
        }
    except Exception as e:
        try:
            await trader.close()
        except Exception:
            pass
        log.error("cancel_conditionals error", account_id=task.account_id, error=str(e))
        return {
            "account_id": task.account_id,
            "success": False,
            "cancelled": 0,
            "errors": 1,
            "error": str(e),
        }


@app.post("/api/cancel-conditionals")
def api_cancel_conditionals(req: CancelConditionalsRequest, _: None = Depends(verify_center_token)):
    """取消指定交易对的残留条件委托单（止损/止盈）"""
    if not req.tasks or not req.symbols:
        return {"success": True, "results": []}
    results = []
    for task in req.tasks:
        r = asyncio.run(_cancel_conditionals_one(task=task, sandbox=req.sandbox, symbols=req.symbols))
        results.append(r)
    return {"success": True, "results": results}


# ========== 平仓端点（position_monitor 自管 SL/TP 触发）==========

class ClosePositionRequest(BaseModel):
    account_id: int
    tenant_id: int
    exchange: str
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None
    market_type: str = "future"
    symbol: str
    side: str  # "BUY" or "SELL"（反向平仓方向）
    amount_usdt: float  # 用 USDT 金额（= 币数量 × 当前价），LiveTrader 自动换算合约张数
    trigger_type: str = "SL"  # "SL" or "TP"
    position_side: Optional[str] = None  # 被平仓位方向 LONG/SHORT，必传否则会按开仓推导成反向


async def _close_position_one(req: ClosePositionRequest, sandbox: bool) -> Dict[str, Any]:
    """在节点侧执行平仓市价单"""
    symbol = to_canonical_symbol(normalize_symbol(req.symbol or "", "binance"), "future")
    order_side = OrderSide.BUY if (req.side or "SELL").upper() == "BUY" else OrderSide.SELL
    trader = LiveTrader(
        exchange=req.exchange or "binance",
        api_key=req.api_key,
        api_secret=req.api_secret,
        passphrase=req.passphrase or "",
        sandbox=sandbox,
        market_type=req.market_type or "future",
        settlement_service=None,
    )
    try:
        await trader.exchange.load_markets()
        # 获取当前价格作为参考
        ccxt_sym = trader._ccxt_symbol(symbol)
        ticker = await trader.exchange.fetch_ticker(ccxt_sym)
        current_price = float(ticker.get("last") or ticker.get("close") or 0)

        # 用 amount_usdt 让 LiveTrader 内部统一换算（处理合约张数、精度等）
        # position_side 必传：平的是当前持仓方向，否则 create_order 会按 side 推导成开反向仓
        pos_side = (req.position_side or "").strip().upper() or ("LONG" if order_side == OrderSide.SELL else "SHORT")
        result = await trader.create_order(
            symbol=symbol,
            side=order_side,
            order_type=OrderType.MARKET,
            amount_usdt=req.amount_usdt,
            price=current_price,
            signal_id=f"PM_{req.trigger_type}",
            trade_type="CLOSE",
            close_reason=req.trigger_type,
            position_side=pos_side,
        )
        ok = result.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)
        filled_qty = result.filled_quantity or 0
        filled_price = result.filled_price or current_price

        # 张数→币数量转换
        coin_qty = filled_qty
        if filled_qty > 0 and (req.market_type or "future") == "future":
            try:
                market = trader.exchange.markets.get(ccxt_sym, {})
                cs = float(market.get("contractSize") or 0)
                coin_qty = contracts_to_coins_by_size(filled_qty, cs)
            except Exception:
                pass

        await trader.close()
        log.info(f"[NODE] {req.trigger_type}平仓{'成功' if ok else '失败'}",
                 account_id=req.account_id, symbol=symbol,
                 filled_qty=coin_qty, filled_price=filled_price)
        return {
            "account_id": req.account_id,
            "success": ok,
            "filled_quantity": coin_qty,
            "filled_price": filled_price,
            "trigger_type": req.trigger_type,
            "error": None,
        }
    except Exception as e:
        try:
            await trader.close()
        except Exception:
            pass
        log.error(f"[NODE] {req.trigger_type}平仓异常",
                  account_id=req.account_id, symbol=req.symbol, error=str(e))
        return {
            "account_id": req.account_id,
            "success": False,
            "filled_quantity": 0,
            "filled_price": 0,
            "trigger_type": req.trigger_type,
            "error": str(e),
        }


@app.post("/api/close-position")
def api_close_position(req: ClosePositionRequest, _: None = Depends(verify_center_token)):
    """
    接收中心 position_monitor 的平仓指令（自管 SL/TP 到价触发）。
    在节点侧用用户 API key 发市价反向单平仓。
    """
    sandbox = config.get_bool("exchange_sandbox", True)
    result = asyncio.run(_close_position_one(req, sandbox))
    return result


@app.get("/health")
def health():
    heartbeat_info = {}
    if CENTER_URL and NODE_CODE:
        heartbeat_info = {
            "heartbeat_enabled": True,
            "center_url": CENTER_URL,
            "node_code": NODE_CODE,
            "heartbeat_interval": HEARTBEAT_INTERVAL,
        }
    else:
        heartbeat_info = {"heartbeat_enabled": False}
    return {"status": "ok", "service": "execution-node", **heartbeat_info}


if __name__ == "__main__":
    import uvicorn
    port = config.get_int("execution_node_port", 9101)
    uvicorn.run(app, host="0.0.0.0", port=port)
