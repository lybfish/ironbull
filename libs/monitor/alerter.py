"""
Alerter - 告警管理器

功能：
- 集成 TelegramNotifier.send_alert()
- 去重：同一告警 N 秒内不重复发送
- 恢复通知：服务恢复时发一条恢复消息
- 告警级别：critical / warning / info
"""

import time
from typing import Dict, Optional

from libs.core.logger import get_logger

log = get_logger("alerter")


class Alerter:
    """告警管理器"""

    def __init__(self, cooldown_seconds: int = 300):
        """
        Args:
            cooldown_seconds: 同一告警的去重冷却时间（秒）
        """
        self.cooldown = cooldown_seconds
        # key -> 上次告警时间
        self._last_alert_time: Dict[str, float] = {}
        # key -> 上次状态（True=正常, False=异常）
        self._last_status: Dict[str, bool] = {}

    def _should_send(self, key: str) -> bool:
        """判断是否应该发送（冷却去重）"""
        last = self._last_alert_time.get(key, 0)
        return (time.time() - last) >= self.cooldown

    def _record_sent(self, key: str) -> None:
        self._last_alert_time[key] = time.time()

    def _get_notifier(self):
        """惰性加载 TelegramNotifier，避免循环引入"""
        from libs.notify.telegram import get_telegram_notifier
        return get_telegram_notifier()

    def alert(self, key: str, message: str, level: str = "warning") -> bool:
        """
        发送告警。如果冷却期内已发过，则跳过。

        Args:
            key: 告警标识（如 "service:data-api"）
            message: 告警内容
            level: critical / warning / info

        Returns:
            True 如果实际发送了，False 如果被去重跳过
        """
        prev_ok = self._last_status.get(key, True)
        self._last_status[key] = False

        if not self._should_send(key):
            log.debug("告警被去重跳过", key=key)
            return False

        try:
            notifier = self._get_notifier()
            result = notifier.send_alert(
                alert_type="monitor",
                message=f"[{key}] {message}",
                level=level,
            )
            self._record_sent(key)
            if result.success:
                log.info("告警已发送", key=key, level=level)
            else:
                log.error("告警发送失败", key=key, error=result.error)
            return result.success
        except Exception as e:
            log.error("告警发送异常", key=key, error=str(e))
            return False

    def recover(self, key: str, message: str) -> bool:
        """
        发送恢复通知。仅当之前状态为异常时才发送。

        Args:
            key: 告警标识
            message: 恢复消息

        Returns:
            True 如果实际发送了
        """
        prev_ok = self._last_status.get(key, True)
        self._last_status[key] = True

        # 之前就是正常的，不需要发恢复通知
        if prev_ok:
            return False

        # 清除冷却记录（恢复通知总是发送）
        self._last_alert_time.pop(key, None)

        try:
            notifier = self._get_notifier()
            result = notifier.send_alert(
                alert_type="monitor",
                message=f"[{key}] {message}",
                level="info",
            )
            if result.success:
                log.info("恢复通知已发送", key=key)
            else:
                log.error("恢复通知发送失败", key=key, error=result.error)
            return result.success
        except Exception as e:
            log.error("恢复通知发送异常", key=key, error=str(e))
            return False

    def process_service_status(self, name: str, healthy: bool, error: Optional[str] = None) -> None:
        """
        处理服务状态变化，自动告警或恢复。

        Args:
            name: 服务名
            healthy: 是否健康
            error: 错误信息
        """
        key = f"service:{name}"
        if healthy:
            self.recover(key, f"服务 {name} 已恢复正常")
        else:
            self.alert(key, f"服务 {name} 异常: {error or '未知错误'}", level="critical")

    def process_node_status(self, node_code: str, online: bool, seconds_since: Optional[float] = None) -> None:
        """
        处理节点状态变化。

        Args:
            node_code: 节点编码
            online: 是否在线
            seconds_since: 距上次心跳秒数
        """
        key = f"node:{node_code}"
        if online:
            self.recover(key, f"节点 {node_code} 已恢复在线")
        else:
            detail = f"距上次心跳 {int(seconds_since)}s" if seconds_since is not None else "无心跳记录"
            self.alert(key, f"节点 {node_code} 离线: {detail}", level="warning")

    def process_db_status(self, component: str, ok: bool, error: Optional[str] = None) -> None:
        """
        处理 DB/Redis 状态变化。

        Args:
            component: "mysql" 或 "redis"
            ok: 是否正常
            error: 错误信息
        """
        key = f"db:{component}"
        if ok:
            self.recover(key, f"{component.upper()} 已恢复正常")
        else:
            self.alert(key, f"{component.upper()} 连接失败: {error or '未知'}", level="critical")
