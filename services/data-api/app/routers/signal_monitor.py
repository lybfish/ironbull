"""
信号监控状态代理（供管理后台展示）
- GET  /api/signal-monitor/status         - signal-monitor 运行状态
- POST /api/signal-monitor/trigger-scan   - 手动触发持仓监控扫描
- GET  /api/signal-monitor/realtime-prices - 批量获取实时价格
"""

from typing import List, Optional, Dict, Any, Tuple

from fastapi import APIRouter, Depends, Query
import httpx

from libs.core import get_config

from ..deps import get_current_admin

router = APIRouter(prefix="/api", tags=["signal-monitor"])
config = get_config()
SIGNAL_MONITOR_URL = config.get_str("signal_monitor_url", "http://127.0.0.1:8020").rstrip("/")
DATA_PROVIDER_URL = config.get_str("data_provider_url", "http://127.0.0.1:8005").rstrip("/")


@router.get("/signal-monitor/status")
def signal_monitor_status():
    """获取 signal-monitor 运行状态（running、last_signal、total_signals 等）"""
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{SIGNAL_MONITOR_URL}/api/status")
            r.raise_for_status()
            return r.json()
    except Exception as e:
        return {
            "running": False,
            "error": str(e),
            "message": "无法连接 signal-monitor 服务，请确认已启动",
        }


@router.post("/signal-monitor/trigger-scan")
def trigger_position_monitor_scan(
    _admin: Dict[str, Any] = Depends(get_current_admin),
):
    """
    手动触发一次持仓监控扫描（检查 SL/TP 是否触发）。
    仅管理员可调用。会立即执行一次扫描并返回结果。
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(f"{SIGNAL_MONITOR_URL}/api/position-monitor/scan")
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        return {"success": False, "error": "无法连接 signal-monitor 服务"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/signal-monitor/realtime-prices")
def get_realtime_prices(
    symbols: str = Query(..., description="逗号分隔的交易对，如 BTCUSDT,ETHUSDT"),
    exchange_symbols: Optional[str] = Query(
        None,
        description="按交易所分组的币对，格式: exchange:symbol,...  如 gate:ETH/USDT,okx:BTC/USDT。"
                    "优先使用此参数；未传时回退到 symbols 参数（使用默认交易所）。",
    ),
    _admin: Dict[str, Any] = Depends(get_current_admin),
):
    """
    批量获取实时价格（代理到 data-provider 的 /api/ticker）。

    返回格式:
      - prices: {symbol: {last, bid, ask}}  （旧格式，向后兼容）
      - exchange_prices: {"exchange:symbol": {last, bid, ask, exchange}}  （按交易所区分）
    """
    results = {}          # 旧格式: symbol → price
    exchange_results = {} # 新格式: exchange:symbol → price

    # ── 解析请求：优先 exchange_symbols，回退 symbols ──
    # 去重列表: [(exchange_or_none, ccxt_symbol, original_key)]
    query_items: List[tuple] = []
    seen_keys = set()

    if exchange_symbols:
        for item in exchange_symbols.split(","):
            item = item.strip()
            if not item:
                continue
            if ":" in item:
                ex, sym = item.split(":", 1)
                ex = ex.strip().lower()
                sym = sym.strip()
            else:
                ex = None
                sym = item.strip()
            # 规范化 symbol
            ccxt_sym = sym
            if "/" not in sym and "USDT" in sym:
                ccxt_sym = sym.replace("USDT", "/USDT")
            key = f"{ex}:{ccxt_sym}" if ex else ccxt_sym
            if key not in seen_keys:
                seen_keys.add(key)
                query_items.append((ex, ccxt_sym, sym))
    else:
        for sym in symbols.split(","):
            sym = sym.strip()
            if not sym:
                continue
            ccxt_sym = sym
            if "/" not in sym and "USDT" in sym:
                ccxt_sym = sym.replace("USDT", "/USDT")
            if ccxt_sym not in seen_keys:
                seen_keys.add(ccxt_sym)
                query_items.append((None, ccxt_sym, sym))

    try:
        with httpx.Client(timeout=10.0) as client:
            for exchange, ccxt_sym, orig_sym in query_items:
                try:
                    params: dict = {"symbol": ccxt_sym}
                    if exchange:
                        params["exchange"] = exchange
                    r = client.get(f"{DATA_PROVIDER_URL}/api/ticker", params=params)
                    if r.status_code == 200:
                        data = r.json()
                        price_info = {
                            "last": data.get("last"),
                            "bid": data.get("bid"),
                            "ask": data.get("ask"),
                            "volume_24h": data.get("volume_24h"),
                            "exchange": data.get("exchange") or exchange or "",
                        }
                    else:
                        price_info = {"last": None, "error": f"HTTP {r.status_code}"}
                    # 旧格式（按 symbol）
                    results[orig_sym] = price_info
                    # 新格式（按 exchange:symbol）
                    ex_key = f"{exchange}:{orig_sym}" if exchange else orig_sym
                    exchange_results[ex_key] = price_info
                except Exception as e:
                    err = {"last": None, "error": str(e)}
                    results[orig_sym] = err
                    ex_key = f"{exchange}:{orig_sym}" if exchange else orig_sym
                    exchange_results[ex_key] = err
    except Exception as e:
        return {"success": False, "error": str(e), "prices": {}, "exchange_prices": {}}

    return {"success": True, "prices": results, "exchange_prices": exchange_results}
