"""
Monitor 模块单元测试

覆盖：
- HealthChecker：正常 / 异常 / 超时场景
- NodeChecker：在线 / 离线 / 无心跳记录
- DbChecker：MySQL + Redis 连通性
- Alerter：告警去重 / 恢复通知 / process_* 方法
"""

import os
import sys
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== HealthChecker ====================

class TestHealthChecker:
    """服务健康检查测试"""

    def test_check_healthy_service(self):
        """正常服务返回 healthy=True"""
        from libs.monitor.health_checker import HealthChecker

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}

        with patch("libs.monitor.health_checker.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            hc = HealthChecker([{"name": "test-svc", "url": "http://localhost:9999/health"}])
            results = hc.check_all()

            assert len(results) == 1
            assert results[0].name == "test-svc"
            assert results[0].healthy is True
            assert results[0].error is None

    def test_check_unhealthy_service(self):
        """HTTP 500 返回 healthy=False"""
        from libs.monitor.health_checker import HealthChecker

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {}

        with patch("libs.monitor.health_checker.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            hc = HealthChecker([{"name": "bad-svc", "url": "http://localhost:9999/health"}])
            results = hc.check_all()

            assert len(results) == 1
            assert results[0].healthy is False
            assert "500" in results[0].error

    def test_check_connection_refused(self):
        """连接被拒绝返回 healthy=False"""
        import httpx
        from libs.monitor.health_checker import HealthChecker

        with patch("libs.monitor.health_checker.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            hc = HealthChecker([{"name": "dead-svc", "url": "http://localhost:9999/health"}])
            results = hc.check_all()

            assert len(results) == 1
            assert results[0].healthy is False
            assert "连接被拒绝" in results[0].error

    def test_check_multiple_services_order(self):
        """多服务按原始顺序返回"""
        from libs.monitor.health_checker import HealthChecker

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}

        with patch("libs.monitor.health_checker.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            services = [
                {"name": "svc-a", "url": "http://localhost:1/health"},
                {"name": "svc-b", "url": "http://localhost:2/health"},
                {"name": "svc-c", "url": "http://localhost:3/health"},
            ]
            hc = HealthChecker(services)
            results = hc.check_all()

            assert [r.name for r in results] == ["svc-a", "svc-b", "svc-c"]

    def test_service_status_to_dict(self):
        """ServiceStatus.to_dict() 返回正确字典"""
        from libs.monitor.health_checker import ServiceStatus

        s = ServiceStatus(name="foo", url="http://x/health", healthy=True, latency_ms=12.345)
        d = s.to_dict()
        assert d["name"] == "foo"
        assert d["healthy"] is True
        assert d["latency_ms"] == 12.3  # 四舍五入到 1 位


# ==================== NodeChecker ====================

class TestNodeChecker:
    """节点心跳检测测试"""

    def _make_node(self, code, heartbeat_at=None, status=1):
        node = MagicMock()
        node.node_code = code
        node.name = code
        node.base_url = f"http://{code}:9000"
        node.status = status
        node.last_heartbeat_at = heartbeat_at
        node.id = hash(code)
        return node

    def test_online_node(self):
        """心跳在超时内的节点标记为在线"""
        from libs.monitor.node_checker import NodeChecker

        now = datetime.utcnow()
        node = self._make_node("node-1", heartbeat_at=now - timedelta(seconds=30))

        mock_db = MagicMock()
        query = MagicMock()
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = [node]
        mock_db.query.return_value = query

        nc = NodeChecker(mock_db, timeout_seconds=180)
        results = nc.check_all()

        assert len(results) == 1
        assert results[0].online is True

    def test_offline_node(self):
        """心跳超时的节点标记为离线"""
        from libs.monitor.node_checker import NodeChecker

        now = datetime.utcnow()
        node = self._make_node("node-2", heartbeat_at=now - timedelta(seconds=600))

        mock_db = MagicMock()
        query = MagicMock()
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = [node]
        mock_db.query.return_value = query

        nc = NodeChecker(mock_db, timeout_seconds=180)
        results = nc.check_all()

        assert len(results) == 1
        assert results[0].online is False

    def test_no_heartbeat_node(self):
        """从未有心跳的节点标记为离线"""
        from libs.monitor.node_checker import NodeChecker

        node = self._make_node("node-3", heartbeat_at=None)

        mock_db = MagicMock()
        query = MagicMock()
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = [node]
        mock_db.query.return_value = query

        nc = NodeChecker(mock_db, timeout_seconds=180)
        results = nc.check_all()

        assert len(results) == 1
        assert results[0].online is False
        assert results[0].last_heartbeat is None

    def test_node_status_to_dict(self):
        """NodeStatus.to_dict() 正确"""
        from libs.monitor.node_checker import NodeStatus

        ns = NodeStatus(
            node_code="n1", name="节点1", base_url="http://x",
            status=1, online=True, last_heartbeat="2026-01-01 00:00:00",
            seconds_since_heartbeat=42.7,
        )
        d = ns.to_dict()
        assert d["node_code"] == "n1"
        assert d["online"] is True
        assert d["seconds_since_heartbeat"] == 43.0


# ==================== DbChecker ====================

class TestDbChecker:
    """数据库/Redis 连通性测试"""

    def test_mysql_and_redis_ok(self):
        """MySQL 和 Redis 都正常"""
        from libs.monitor.db_checker import DbChecker

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_engine.connect.return_value = mock_conn

        with patch("libs.core.database.get_engine", return_value=mock_engine), \
             patch("libs.core.redis_client.check_redis_connection", return_value=True):
            dbc = DbChecker()
            status = dbc.check()

            assert status.mysql_ok is True
            assert status.redis_ok is True
            assert status.mysql_error is None
            assert status.redis_error is None

    def test_mysql_fail(self):
        """MySQL 连接失败"""
        from libs.monitor.db_checker import DbChecker

        with patch("libs.core.database.get_engine", side_effect=Exception("conn refused")), \
             patch("libs.core.redis_client.check_redis_connection", return_value=True):
            dbc = DbChecker()
            status = dbc.check()

            assert status.mysql_ok is False
            assert "conn refused" in status.mysql_error
            assert status.redis_ok is True

    def test_redis_fail(self):
        """Redis 连接失败"""
        from libs.monitor.db_checker import DbChecker

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_engine.connect.return_value = mock_conn

        with patch("libs.core.database.get_engine", return_value=mock_engine), \
             patch("libs.core.redis_client.check_redis_connection", return_value=False):
            dbc = DbChecker()
            status = dbc.check()

            assert status.mysql_ok is True
            assert status.redis_ok is False

    def test_db_status_to_dict(self):
        """DbStatus.to_dict() 正确"""
        from libs.monitor.db_checker import DbStatus

        s = DbStatus(mysql_ok=True, mysql_latency_ms=1.234, redis_ok=False, redis_latency_ms=5.678, redis_error="timeout")
        d = s.to_dict()
        assert d["mysql_ok"] is True
        assert d["mysql_latency_ms"] == 1.2
        assert d["redis_ok"] is False
        assert d["redis_error"] == "timeout"


# ==================== Alerter ====================

class TestAlerter:
    """告警管理器测试"""

    def test_alert_sends_first_time(self):
        """首次告警应发送"""
        from libs.monitor.alerter import Alerter

        alerter = Alerter(cooldown_seconds=300)
        mock_notifier = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_notifier.send_alert.return_value = mock_result

        with patch.object(alerter, "_get_notifier", return_value=mock_notifier):
            sent = alerter.alert("test:key", "something broke")
            assert sent is True
            mock_notifier.send_alert.assert_called_once()

    def test_alert_dedup_within_cooldown(self):
        """冷却期内不重复发送"""
        from libs.monitor.alerter import Alerter

        alerter = Alerter(cooldown_seconds=300)
        mock_notifier = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_notifier.send_alert.return_value = mock_result

        with patch.object(alerter, "_get_notifier", return_value=mock_notifier):
            alerter.alert("test:dup", "error1")
            sent2 = alerter.alert("test:dup", "error2")
            assert sent2 is False
            # 只调了一次
            assert mock_notifier.send_alert.call_count == 1

    def test_alert_sends_after_cooldown(self):
        """冷却期过后应再次发送"""
        from libs.monitor.alerter import Alerter

        alerter = Alerter(cooldown_seconds=1)
        mock_notifier = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_notifier.send_alert.return_value = mock_result

        with patch.object(alerter, "_get_notifier", return_value=mock_notifier):
            alerter.alert("test:cd", "err1")
            time.sleep(1.1)
            sent = alerter.alert("test:cd", "err2")
            assert sent is True
            assert mock_notifier.send_alert.call_count == 2

    def test_recover_sends_when_previously_down(self):
        """之前异常 → 恢复时发送恢复通知"""
        from libs.monitor.alerter import Alerter

        alerter = Alerter(cooldown_seconds=300)
        mock_notifier = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_notifier.send_alert.return_value = mock_result

        with patch.object(alerter, "_get_notifier", return_value=mock_notifier):
            # 先标记为异常
            alerter.alert("test:recover", "broken")
            # 然后恢复
            sent = alerter.recover("test:recover", "back online")
            assert sent is True
            assert mock_notifier.send_alert.call_count == 2  # 1 alert + 1 recover

    def test_recover_skips_when_already_ok(self):
        """之前就是正常的，恢复通知不发"""
        from libs.monitor.alerter import Alerter

        alerter = Alerter(cooldown_seconds=300)
        mock_notifier = MagicMock()

        with patch.object(alerter, "_get_notifier", return_value=mock_notifier):
            sent = alerter.recover("test:ok", "still ok")
            assert sent is False
            mock_notifier.send_alert.assert_not_called()

    def test_process_service_status_healthy(self):
        """process_service_status healthy → recover 逻辑"""
        from libs.monitor.alerter import Alerter

        alerter = Alerter(cooldown_seconds=300)
        with patch.object(alerter, "recover") as mock_recover:
            alerter.process_service_status("data-api", True)
            mock_recover.assert_called_once()

    def test_process_service_status_unhealthy(self):
        """process_service_status unhealthy → alert 逻辑"""
        from libs.monitor.alerter import Alerter

        alerter = Alerter(cooldown_seconds=300)
        with patch.object(alerter, "alert") as mock_alert:
            alerter.process_service_status("data-api", False, "connection refused")
            mock_alert.assert_called_once()

    def test_process_node_status(self):
        """process_node_status 离线触发告警"""
        from libs.monitor.alerter import Alerter

        alerter = Alerter(cooldown_seconds=300)
        with patch.object(alerter, "alert") as mock_alert:
            alerter.process_node_status("node-1", False, 300.0)
            mock_alert.assert_called_once()
            assert "node-1" in mock_alert.call_args[0][1]

    def test_process_db_status(self):
        """process_db_status MySQL 异常触发告警"""
        from libs.monitor.alerter import Alerter

        alerter = Alerter(cooldown_seconds=300)
        with patch.object(alerter, "alert") as mock_alert:
            alerter.process_db_status("mysql", False, "cannot connect")
            mock_alert.assert_called_once()
            assert "MYSQL" in mock_alert.call_args[0][1]
