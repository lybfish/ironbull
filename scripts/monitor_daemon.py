#!/usr/bin/env python3
"""
Monitor Daemon - 监控巡检守护脚本

定时循环执行：
1. 服务健康检查
2. 节点心跳检查
3. DB/Redis 连通性检查

状态变更时通过 Telegram 告警。

用法：
    python scripts/monitor_daemon.py
    python scripts/monitor_daemon.py --interval 30
    python scripts/monitor_daemon.py --services data-api,merchant-api
"""

import sys
import os
import time
import signal
import argparse

# 项目根目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from libs.core import get_config, get_logger, init_database
from libs.core.database import get_db
from libs.monitor.health_checker import HealthChecker
from libs.monitor.node_checker import NodeChecker
from libs.monitor.db_checker import DbChecker
from libs.monitor.alerter import Alerter

log = get_logger("monitor-daemon")

# 优雅退出
_running = True


def _on_signal(sig, frame):
    global _running
    log.info("收到退出信号，准备停止...")
    _running = False


signal.signal(signal.SIGINT, _on_signal)
signal.signal(signal.SIGTERM, _on_signal)


def build_service_list(config, filter_names=None):
    """从配置构建服务列表"""
    services = config.get("monitor_services", None)
    if services:
        # YAML 配置了服务列表
        result = [{"name": s["name"], "url": s["url"]} for s in services]
    else:
        # 默认服务
        result = [
            {"name": "data-api", "url": "http://127.0.0.1:8026/health"},
            {"name": "merchant-api", "url": "http://127.0.0.1:8010/health"},
            {"name": "signal-monitor", "url": "http://127.0.0.1:8020/health"},
        ]

    if filter_names:
        allowed = set(filter_names)
        result = [s for s in result if s["name"] in allowed]

    return result


def run_once(health_checker, node_timeout, alerter):
    """执行一轮巡检"""
    # 1. 服务健康检查
    log.info("开始服务健康检查...")
    statuses = health_checker.check_all()
    for s in statuses:
        tag = "OK" if s.healthy else "FAIL"
        log.info(f"  {s.name}: {tag} ({s.latency_ms:.0f}ms)", error=s.error or "")
        alerter.process_service_status(s.name, s.healthy, s.error)

    # 2. 节点心跳检查
    log.info("开始节点心跳检查...")
    try:
        with get_db() as db:
            nc = NodeChecker(db, timeout_seconds=node_timeout)
            nodes = nc.check_all()
            for n in nodes:
                tag = "ONLINE" if n.online else "OFFLINE"
                log.info(f"  {n.node_code}: {tag}", last_hb=n.last_heartbeat or "无")
                alerter.process_node_status(n.node_code, n.online, n.seconds_since_heartbeat)
    except Exception as e:
        log.error("节点心跳检查失败", error=str(e))

    # 3. DB/Redis 检查
    log.info("开始 DB/Redis 检查...")
    dbc = DbChecker()
    db_status = dbc.check()
    log.info(f"  MySQL: {'OK' if db_status.mysql_ok else 'FAIL'} ({db_status.mysql_latency_ms:.0f}ms)")
    log.info(f"  Redis: {'OK' if db_status.redis_ok else 'FAIL'} ({db_status.redis_latency_ms:.0f}ms)")
    alerter.process_db_status("mysql", db_status.mysql_ok, db_status.mysql_error)
    alerter.process_db_status("redis", db_status.redis_ok, db_status.redis_error)

    log.info("本轮巡检完成")


def main():
    parser = argparse.ArgumentParser(description="IronBull Monitor Daemon")
    parser.add_argument("--interval", type=int, default=None, help="巡检间隔（秒），默认从配置读取")
    parser.add_argument("--services", type=str, default=None, help="逗号分隔的服务名筛选，如 data-api,merchant-api")
    args = parser.parse_args()

    config = get_config()

    # 是否启用监控
    enabled = config.get("monitor_enabled", True)
    if not enabled:
        log.info("监控已禁用 (monitor_enabled=false)，退出")
        return

    # 巡检间隔
    interval = args.interval or config.get_int("monitor_interval", 60)
    # 节点超时
    node_timeout = config.get_int("monitor_node_timeout", 180)
    # 告警冷却
    alert_cooldown = config.get_int("monitor_alert_cooldown", 300)

    # 初始化数据库
    init_database()

    # 构建服务列表
    filter_names = args.services.split(",") if args.services else None
    services = build_service_list(config, filter_names)

    log.info(
        "Monitor Daemon 启动",
        interval=interval,
        services=[s["name"] for s in services],
        node_timeout=node_timeout,
        alert_cooldown=alert_cooldown,
    )

    hc = HealthChecker(services)
    alerter = Alerter(cooldown_seconds=alert_cooldown)

    while _running:
        try:
            run_once(hc, node_timeout, alerter)
        except Exception as e:
            log.error("巡检异常", error=str(e))

        # 间隔等待，支持优雅退出
        for _ in range(interval):
            if not _running:
                break
            time.sleep(1)

    log.info("Monitor Daemon 已停止")


if __name__ == "__main__":
    main()
