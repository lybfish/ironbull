"""
信号监控状态代理（供管理后台展示）
- GET /api/signal-monitor/status - 转发至 signal-monitor 的 /api/status
"""

from fastapi import APIRouter
import httpx
from libs.core import get_config

router = APIRouter(prefix="/api", tags=["signal-monitor"])
config = get_config()
SIGNAL_MONITOR_URL = config.get_str("signal_monitor_url", "http://127.0.0.1:8020").rstrip("/")


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
