"""
信号监控状态代理（供管理后台展示）
- GET  /api/signal-monitor/status         - signal-monitor 运行状态
- POST /api/signal-monitor/trigger-scan   - 手动触发持仓监控扫描
- GET  /api/signal-monitor/realtime-prices - 批量获取实时价格
"""

from typing import List, Optional, Dict, Any

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
    _admin: Dict[str, Any] = Depends(get_current_admin),
):
    """
    批量获取实时价格（代理到 data-provider 的 /api/ticker）。
    返回 {symbol: {last, bid, ask}} 的映射。
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    results = {}
    try:
        with httpx.Client(timeout=10.0) as client:
            for sym in symbol_list:
                try:
                    # ccxt 格式：BTCUSDT → BTC/USDT
                    ccxt_sym = sym
                    if "/" not in sym and "USDT" in sym:
                        ccxt_sym = sym.replace("USDT", "/USDT")
                    r = client.get(f"{DATA_PROVIDER_URL}/api/ticker", params={"symbol": ccxt_sym})
                    if r.status_code == 200:
                        data = r.json()
                        results[sym] = {
                            "last": data.get("last"),
                            "bid": data.get("bid"),
                            "ask": data.get("ask"),
                            "volume_24h": data.get("volume_24h"),
                        }
                    else:
                        results[sym] = {"last": None, "error": f"HTTP {r.status_code}"}
                except Exception as e:
                    results[sym] = {"last": None, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e), "prices": {}}

    return {"success": True, "prices": results}
