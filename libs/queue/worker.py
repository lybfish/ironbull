"""
Task Worker - 任务消费者

后台 Worker 进程，从队列消费任务并执行
支持优雅关闭和重试机制
"""

import signal
import time
from typing import Callable, Optional, Dict, Any
from abc import ABC, abstractmethod

from libs.core import get_logger
from .task_queue import TaskQueue, TaskMessage

logger = get_logger("task-worker")


class TaskHandler(ABC):
    """任务处理器基类"""
    
    @abstractmethod
    def handle(self, message: TaskMessage) -> Dict[str, Any]:
        """
        处理任务
        
        Args:
            message: 任务消息
        
        Returns:
            处理结果
        
        Raises:
            Exception: 处理失败时抛出异常
        """
        pass


class TaskWorker:
    """
    任务消费者 Worker
    
    使用方式：
        class MyHandler(TaskHandler):
            def handle(self, message: TaskMessage) -> Dict[str, Any]:
                # 处理任务
                return {"status": "ok"}
        
        worker = TaskWorker(
            queue=TaskQueue("my-queue"),
            handler=MyHandler(),
        )
        worker.run()
    """
    
    def __init__(
        self,
        queue: TaskQueue,
        handler: TaskHandler,
        poll_timeout: int = 5,
    ):
        """
        Args:
            queue: 任务队列
            handler: 任务处理器
            poll_timeout: 轮询超时（秒）
        """
        self.queue = queue
        self.handler = handler
        self.poll_timeout = poll_timeout
        self._running = False
        self._shutdown_requested = False
    
    def _setup_signals(self) -> None:
        """设置信号处理"""
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame) -> None:
        """处理关闭信号"""
        logger.info("shutdown signal received", signal=signum)
        self._shutdown_requested = True
    
    def run(self) -> None:
        """启动 Worker（阻塞）"""
        self._setup_signals()
        self._running = True
        
        logger.info(
            "worker started",
            queue=self.queue.name,
            handler=type(self.handler).__name__,
        )
        
        while self._running and not self._shutdown_requested:
            try:
                self._process_one()
            except Exception as e:
                logger.error("worker error", error=str(e))
                time.sleep(1)  # 发生错误时短暂等待
        
        logger.info("worker stopped", queue=self.queue.name)
    
    def _process_one(self) -> bool:
        """
        处理一个任务
        
        Returns:
            True 如果处理了任务，False 如果超时无任务
        """
        message = self.queue.pop(timeout=self.poll_timeout)
        
        if message is None:
            return False
        
        start_time = time.time()
        
        try:
            logger.info(
                "processing task",
                task_id=message.task_id,
                task_type=message.task_type,
                retry_count=message.retry_count,
            )
            
            result = self.handler.handle(message)
            
            # 确认完成
            self.queue.ack(message.task_id)
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(
                "task completed",
                task_id=message.task_id,
                elapsed_ms=round(elapsed, 2),
            )
            
            return True
            
        except Exception as e:
            # 任务失败，重试或死信
            error_msg = str(e)
            self.queue.nack(message, error=error_msg)
            
            elapsed = (time.time() - start_time) * 1000
            logger.error(
                "task failed",
                task_id=message.task_id,
                error=error_msg,
                elapsed_ms=round(elapsed, 2),
            )
            
            return True
    
    def stop(self) -> None:
        """请求停止 Worker"""
        self._running = False
    
    def run_once(self, timeout: int = 0) -> bool:
        """
        处理一个任务然后返回（用于测试）
        
        Returns:
            True 如果处理了任务
        """
        message = self.queue.pop(timeout=timeout)
        
        if message is None:
            return False
        
        try:
            self.handler.handle(message)
            self.queue.ack(message.task_id)
            return True
        except Exception as e:
            self.queue.nack(message, error=str(e))
            raise


class FunctionHandler(TaskHandler):
    """
    函数处理器（简化版）
    
    将普通函数包装为 TaskHandler
    
    使用方式：
        def process_task(message: TaskMessage) -> Dict:
            return {"ok": True}
        
        worker = TaskWorker(
            queue=TaskQueue("my-queue"),
            handler=FunctionHandler(process_task),
        )
    """
    
    def __init__(self, func: Callable[[TaskMessage], Dict[str, Any]]):
        self.func = func
    
    def handle(self, message: TaskMessage) -> Dict[str, Any]:
        return self.func(message)
