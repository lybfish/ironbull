"""
IronBull Queue Module (v1 Phase 3)

消息队列模块 - 支持异步执行和可靠投递

组件：
- TaskQueue: 任务队列（生产者/消费者）
- TaskMessage: 任务消息
- IdempotencyChecker: 幂等性检查
- TaskWorker: 任务消费者
- TaskHandler: 任务处理器基类
- FunctionHandler: 函数处理器
"""

from .task_queue import (
    TaskQueue,
    TaskMessage,
    EXECUTION_QUEUE,
    NOTIFICATION_QUEUE,
    NODE_EXECUTE_QUEUE,
    get_execution_queue,
    get_notification_queue,
    get_node_execute_queue,
)
from .idempotency import IdempotencyChecker, TaskState, IdempotencyRecord, get_signal_idempotency
from .worker import TaskWorker, TaskHandler, FunctionHandler

__all__ = [
    # Queue
    "TaskQueue",
    "TaskMessage",
    "EXECUTION_QUEUE",
    "NOTIFICATION_QUEUE",
    "NODE_EXECUTE_QUEUE",
    "get_execution_queue",
    "get_notification_queue",
    "get_node_execute_queue",
    # Idempotency
    "IdempotencyChecker",
    "TaskState",
    "IdempotencyRecord",
    "get_signal_idempotency",
    # Worker
    "TaskWorker",
    "TaskHandler",
    "FunctionHandler",
]
