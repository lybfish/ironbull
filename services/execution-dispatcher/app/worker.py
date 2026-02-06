"""
Execution Worker - 执行任务消费者

从队列消费执行任务并处理
"""

import json
from dataclasses import asdict
from datetime import datetime
from typing import Dict, Any
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError

from libs.contracts import ExecutionTask, ExecutionResult, NodeTask, NodeResult
from libs.core import get_config, get_logger, setup_logging, gen_id, time_now, init_redis
from libs.queue import TaskQueue, TaskMessage, TaskWorker, TaskHandler, IdempotencyChecker, get_execution_queue

# Facts Layer (可选)
try:
    from libs.facts import FactsRepository, AuditAction, SignalStatus
    FACTS_ENABLED = True
except ImportError:
    FACTS_ENABLED = False

# 配置
config = get_config()
service_name = "execution-worker"
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name=service_name,
)
logger = get_logger(service_name)


def _post_json(url: str, payload: dict, timeout: float = 10.0) -> dict:
    """发送 JSON POST 请求"""
    data = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}


def _get_node_url(platform: str) -> str:
    """根据平台获取节点 URL"""
    if platform.lower() in ("crypto", "binance", "okx"):
        return f"http://127.0.0.1:{config.get_int('crypto_node_port', 8041)}"
    elif platform.lower() in ("mt5", "metatrader"):
        return f"http://127.0.0.1:{config.get_int('mt5_node_port', 8042)}"
    else:
        raise ValueError(f"Unknown platform: {platform}")


def _build_node_task(payload: dict, task_id: str) -> NodeTask:
    """构建节点任务"""
    creds = payload.get("credentials") or {}
    return NodeTask(
        task_id=task_id,
        symbol=payload["symbol"],
        side=payload["side"],
        order_type=payload["order_type"],
        quantity=payload["quantity"],
        price=payload.get("price"),
        stop_loss=payload.get("stop_loss"),
        take_profit=payload.get("take_profit"),
        api_key=creds.get("api_key", ""),
        api_secret=creds.get("api_secret", ""),
        passphrase=creds.get("passphrase"),
        exchange=payload.get("exchange", ""),
    )


class ExecutionHandler(TaskHandler):
    """执行任务处理器"""
    
    def __init__(self):
        self.idempotency = IdempotencyChecker()
    
    def handle(self, message: TaskMessage) -> Dict[str, Any]:
        """处理执行任务"""
        payload = message.payload
        task_id = message.task_id
        signal_id = message.signal_id or payload.get("signal_id", "")
        request_id = message.request_id
        
        logger.info(
            "processing execution task",
            task_id=task_id,
            signal_id=signal_id,
            platform=payload.get("platform"),
        )
        
        # 记录开始处理
        if FACTS_ENABLED:
            self._record_dequeued(message)
        
        # 获取节点 URL
        platform = payload.get("platform", "crypto")
        try:
            node_url = _get_node_url(platform)
        except ValueError as e:
            self._fail_task(message, "INVALID_PLATFORM", str(e))
            raise
        
        # 构建节点任务
        node_task = _build_node_task(payload, task_id)
        
        # 调用节点执行
        try:
            node_resp = _post_json(f"{node_url}/api/node/execute", asdict(node_task))
            node_result = NodeResult(**node_resp.get("result", {}))
        except (URLError, HTTPError, ValueError) as exc:
            node_result = NodeResult(
                task_id=task_id,
                success=False,
                error_code="NODE_CALL_FAILED",
                error_message=str(exc),
                executed_at=time_now(),
                execution_ms=0,
            )
        
        # 构建执行结果
        exec_result = ExecutionResult(
            task_id=task_id,
            signal_id=signal_id,
            success=node_result.success,
            exchange_order_id=node_result.exchange_order_id,
            filled_price=node_result.filled_price,
            filled_quantity=node_result.filled_quantity,
            error_code=node_result.error_code,
            error_message=node_result.error_message,
            executed_at=node_result.executed_at or time_now(),
        )
        
        # 更新幂等性状态
        idempotency_key = f"exec:{signal_id}"
        if node_result.success:
            self.idempotency.complete(idempotency_key, asdict(exec_result))
        else:
            self.idempotency.fail(idempotency_key, node_result.error_message or "execution failed")
        
        # 记录 Facts
        if FACTS_ENABLED:
            self._record_result(message, payload, node_result, exec_result)
        
        logger.info(
            "execution task completed",
            task_id=task_id,
            signal_id=signal_id,
            success=node_result.success,
        )
        
        if not node_result.success:
            raise Exception(f"Execution failed: {node_result.error_message}")
        
        return asdict(exec_result)
    
    def _record_dequeued(self, message: TaskMessage) -> None:
        """记录任务出队"""
        try:
            repo = FactsRepository()
            repo.create_audit_log(
                action=AuditAction.EXEC_DEQUEUED.value,
                source_service=service_name,
                signal_id=message.signal_id,
                task_id=message.task_id,
                account_id=message.account_id,
                success=True,
                detail={"retry_count": message.retry_count},
                request_id=message.request_id,
            )
        except Exception as e:
            logger.warning("failed to record dequeued", error=str(e))
    
    def _record_result(
        self,
        message: TaskMessage,
        payload: dict,
        node_result: NodeResult,
        exec_result: ExecutionResult,
    ) -> None:
        """记录执行结果到 Facts"""
        try:
            repo = FactsRepository()
            
            # 1. 记录 Trade
            trade = repo.create_trade(
                signal_id=message.signal_id or "",
                task_id=message.task_id,
                account_id=payload.get("account_id", 0),
                user_id=payload.get("user_id", 0),
                symbol=payload.get("symbol", ""),
                side=payload.get("side", ""),
                trade_type="OPEN",
                quantity=payload.get("quantity", 0),
                exchange=payload.get("exchange", ""),
                order_type=payload.get("order_type", ""),
                entry_price=payload.get("price"),
                filled_price=node_result.filled_price,
                filled_quantity=node_result.filled_quantity,
                stop_loss=payload.get("stop_loss"),
                take_profit=payload.get("take_profit"),
                fee=node_result.fee or 0,
                fee_currency=node_result.fee_currency,
                exchange_order_id=node_result.exchange_order_id,
                status="filled" if node_result.success else "failed",
                error_code=node_result.error_code,
                error_message=node_result.error_message,
                executed_at=datetime.utcnow() if node_result.success else None,
                request_id=message.request_id,
            )
            
            # 2. 记录 Ledger（手续费）
            if node_result.success and node_result.fee and node_result.fee > 0:
                repo.create_ledger(
                    account_id=payload.get("account_id", 0),
                    user_id=payload.get("user_id", 0),
                    ledger_type="TRADE_FEE",
                    amount=-node_result.fee,
                    currency=node_result.fee_currency or "USDT",
                    trade_id=trade.id,
                    signal_id=message.signal_id,
                    description=f"Trade fee for {payload.get('symbol')}",
                    request_id=message.request_id,
                )
            
            # 3. 记录 SignalEvent
            new_status = SignalStatus.EXECUTED.value if node_result.success else SignalStatus.FAILED.value
            repo.create_signal_event(
                signal_id=message.signal_id or "",
                event_type="EXECUTED" if node_result.success else "FAILED",
                status=new_status,
                source_service=service_name,
                task_id=message.task_id,
                account_id=payload.get("account_id"),
                detail={
                    "platform": payload.get("platform"),
                    "exchange": payload.get("exchange"),
                    "filled_price": node_result.filled_price,
                    "filled_quantity": node_result.filled_quantity,
                    "exchange_order_id": node_result.exchange_order_id,
                    "async": True,
                },
                error_code=node_result.error_code,
                error_message=node_result.error_message,
                request_id=message.request_id,
            )
            
            # 4. 审计日志
            repo.create_audit_log(
                action=AuditAction.EXEC_FILLED.value if node_result.success else AuditAction.EXEC_FAILED.value,
                source_service=service_name,
                signal_id=message.signal_id,
                task_id=message.task_id,
                account_id=payload.get("account_id"),
                user_id=payload.get("user_id"),
                status_before=SignalStatus.PASSED.value,
                status_after=new_status,
                success=node_result.success,
                error_code=node_result.error_code,
                error_message=node_result.error_message,
                detail={
                    "platform": payload.get("platform"),
                    "exchange": payload.get("exchange"),
                    "symbol": payload.get("symbol"),
                    "filled_price": node_result.filled_price,
                    "filled_quantity": node_result.filled_quantity,
                    "exchange_order_id": node_result.exchange_order_id,
                    "retry_count": message.retry_count,
                },
                request_id=message.request_id,
            )
        except Exception as e:
            logger.warning("failed to record result", error=str(e))
    
    def _fail_task(self, message: TaskMessage, error_code: str, error_message: str) -> None:
        """记录任务失败"""
        idempotency_key = f"exec:{message.signal_id}"
        self.idempotency.fail(idempotency_key, error_message)
        
        if FACTS_ENABLED:
            try:
                repo = FactsRepository()
                repo.create_audit_log(
                    action=AuditAction.EXEC_FAILED.value,
                    source_service=service_name,
                    signal_id=message.signal_id,
                    task_id=message.task_id,
                    success=False,
                    error_code=error_code,
                    error_message=error_message,
                    request_id=message.request_id,
                )
            except Exception as e:
                logger.warning("failed to record failure", error=str(e))


def main():
    """启动 Worker"""
    logger.info("starting execution worker")
    
    # 初始化 Redis
    init_redis()
    
    # 创建队列和处理器
    queue = get_execution_queue()
    handler = ExecutionHandler()
    
    # 创建 Worker
    worker = TaskWorker(
        queue=queue,
        handler=handler,
        poll_timeout=5,
    )
    
    logger.info("execution worker started, waiting for tasks...")
    
    # 运行
    worker.run()


if __name__ == "__main__":
    main()
