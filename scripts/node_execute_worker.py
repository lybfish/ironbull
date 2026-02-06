#!/usr/bin/env python3
"""
Node Execute Worker - 消费 NODE_EXECUTE_QUEUE，向执行节点 POST /api/execute，并在中心写库与结算。

用法（在项目根目录）:
  PYTHONPATH=. python3 scripts/node_execute_worker.py
  # 或指定轮询间隔（秒）
  NODE_EXECUTE_POLL_TIMEOUT=15 PYTHONPATH=. python3 scripts/node_execute_worker.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx
from libs.core import get_config, get_logger, setup_logging
from libs.core.database import get_session
from libs.member import ExecutionTarget
from libs.queue import get_node_execute_queue
from libs.execution_node.apply_results import apply_remote_results

config = get_config()
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name="node-execute-worker",
)
log = get_logger("node-execute-worker")

POLL_TIMEOUT = int(os.environ.get("NODE_EXECUTE_POLL_TIMEOUT", "30"))


def run():
    queue = get_node_execute_queue()
    log.info("node execute worker started", poll_timeout=POLL_TIMEOUT)

    while True:
        msg = queue.pop(timeout=POLL_TIMEOUT)
        if msg is None:
            continue
        task_id = msg.task_id
        payload = msg.payload or {}
        node_id = payload.get("node_id")
        base_url = (payload.get("base_url") or "").rstrip("/")
        signal = payload.get("signal") or {}
        amount_usdt = payload.get("amount_usdt", 0)
        sandbox = payload.get("sandbox", True)
        tasks = payload.get("tasks") or []

        if not base_url or not tasks:
            log.warning("invalid payload missing base_url or tasks", task_id=task_id, node_id=node_id)
            queue.nack(msg, "missing base_url or tasks")
            continue

        # 重建 ExecutionTarget 供 apply_remote_results 使用
        targets_by_account = {}
        for t in tasks:
            try:
                target = ExecutionTarget(
                    tenant_id=int(t["tenant_id"]),
                    account_id=int(t["account_id"]),
                    user_id=int(t["user_id"]),
                    exchange=t.get("exchange", "binance"),
                    api_key=t.get("api_key", ""),
                    api_secret=t.get("api_secret", ""),
                    passphrase=t.get("passphrase"),
                    market_type=t.get("market_type", "future"),
                    binding_id=int(t.get("binding_id", 0)),
                    strategy_code=t.get("strategy_code", ""),
                    ratio=int(t.get("ratio", 100)),
                    execution_node_id=t.get("execution_node_id"),
                )
                targets_by_account[target.account_id] = target
            except Exception as e:
                log.warning("skip invalid task", task_id=task_id, account_id=t.get("account_id"), error=str(e))

        if not targets_by_account:
            log.warning("no valid targets", task_id=task_id)
            queue.nack(msg, "no valid targets")
            continue

        # 发给节点的 body 与 signal-monitor 一致；保留每 task 的 amount_usdt/leverage（租户实例覆盖）
        post_body = {
            "signal": signal,
            "amount_usdt": amount_usdt,
            "sandbox": sandbox,
            "tasks": [
                {
                    "account_id": t["account_id"],
                    "tenant_id": t["tenant_id"],
                    "user_id": t["user_id"],
                    "exchange": t.get("exchange", "binance"),
                    "api_key": t.get("api_key", ""),
                    "api_secret": t.get("api_secret", ""),
                    "passphrase": t.get("passphrase"),
                    "market_type": t.get("market_type", "future"),
                    "amount_usdt": t.get("amount_usdt"),
                    "leverage": t.get("leverage"),
                }
                for t in tasks
            ],
        }

        node_headers = {}
        secret = config.get_str("node_auth_secret", "").strip()
        if secret:
            node_headers["X-Center-Token"] = secret
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(f"{base_url}/api/execute", json=post_body, headers=node_headers or None)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            log.warning("node execute POST failed", task_id=task_id, node_id=node_id, error=str(e))
            queue.nack(msg, str(e))
            continue

        response_results = data.get("results") or []
        session = get_session()
        try:
            apply_remote_results(session, signal, targets_by_account, response_results)
            session.commit()
            queue.ack(task_id)
            log.info("node execute done", task_id=task_id, node_id=node_id, results=len(response_results))
        except Exception as e:
            session.rollback()
            log.error("apply_remote_results failed", task_id=task_id, error=str(e))
            queue.nack(msg, str(e))
        finally:
            session.close()


if __name__ == "__main__":
    run()
