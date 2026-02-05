"""
Task Queue - 任务队列

基于 Redis List 实现的简单可靠队列：
- LPUSH 入队（生产者）
- BRPOP 出队（消费者，阻塞）
- 支持死信队列（失败重试）
"""

import json
import time
from dataclasses import dataclass, asdict, field
from typing import Optional, Any, Dict
from datetime import datetime

from libs.core import get_redis, get_logger, gen_id

logger = get_logger("task-queue")


@dataclass
class TaskMessage:
    """
    任务消息
    """
    task_id: str                          # 任务ID
    task_type: str                        # 任务类型（execution/notification/...）
    payload: Dict[str, Any]               # 任务数据
    
    # 元数据
    signal_id: Optional[str] = None       # 关联信号ID
    account_id: Optional[int] = None      # 关联账户ID
    request_id: Optional[str] = None      # 请求追踪ID
    
    # 重试信息
    retry_count: int = 0                  # 已重试次数
    max_retries: int = 3                  # 最大重试次数
    
    # 时间
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    scheduled_at: Optional[str] = None    # 预定执行时间
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, data: str) -> "TaskMessage":
        return cls(**json.loads(data))
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskMessage":
        return cls(**data)


class TaskQueue:
    """
    任务队列
    
    队列命名规范：
    - ironbull:queue:{name}         主队列
    - ironbull:queue:{name}:dead    死信队列
    - ironbull:queue:{name}:processing  处理中队列
    """
    
    QUEUE_PREFIX = "ironbull:queue"
    
    def __init__(self, name: str):
        self.name = name
        self.queue_key = f"{self.QUEUE_PREFIX}:{name}"
        self.dead_key = f"{self.QUEUE_PREFIX}:{name}:dead"
        self.processing_key = f"{self.QUEUE_PREFIX}:{name}:processing"
    
    def push(self, message: TaskMessage) -> str:
        """
        推送任务到队列
        
        Returns:
            任务ID
        """
        redis = get_redis()
        redis.lpush(self.queue_key, message.to_json())
        
        logger.info(
            "task pushed",
            queue=self.name,
            task_id=message.task_id,
            task_type=message.task_type,
            signal_id=message.signal_id,
        )
        
        return message.task_id
    
    def pop(self, timeout: int = 0) -> Optional[TaskMessage]:
        """
        从队列弹出任务（阻塞）
        
        Args:
            timeout: 超时秒数，0 表示永久阻塞
        
        Returns:
            TaskMessage 或 None（超时）
        """
        redis = get_redis()
        result = redis.brpop(self.queue_key, timeout=timeout)
        
        if result:
            _, data = result
            message = TaskMessage.from_json(data)
            
            # 加入处理中队列
            redis.hset(self.processing_key, message.task_id, data)
            
            logger.info(
                "task popped",
                queue=self.name,
                task_id=message.task_id,
            )
            
            return message
        
        return None
    
    def ack(self, task_id: str) -> bool:
        """
        确认任务完成（从处理中队列移除）
        """
        redis = get_redis()
        removed = redis.hdel(self.processing_key, task_id)
        
        if removed:
            logger.info("task acked", queue=self.name, task_id=task_id)
        
        return removed > 0
    
    def nack(self, message: TaskMessage, error: Optional[str] = None) -> bool:
        """
        任务失败，重新入队或进入死信队列
        
        Returns:
            True 如果重新入队，False 如果进入死信队列
        """
        redis = get_redis()
        
        # 从处理中队列移除
        redis.hdel(self.processing_key, message.task_id)
        
        message.retry_count += 1
        
        if message.retry_count <= message.max_retries:
            # 重新入队（延迟重试，这里简化为立即重试）
            redis.lpush(self.queue_key, message.to_json())
            
            logger.warning(
                "task requeued",
                queue=self.name,
                task_id=message.task_id,
                retry_count=message.retry_count,
                error=error,
            )
            return True
        else:
            # 进入死信队列
            redis.lpush(self.dead_key, message.to_json())
            
            logger.error(
                "task moved to dead queue",
                queue=self.name,
                task_id=message.task_id,
                retry_count=message.retry_count,
                error=error,
            )
            return False
    
    def length(self) -> int:
        """获取队列长度"""
        redis = get_redis()
        return redis.llen(self.queue_key)
    
    def dead_length(self) -> int:
        """获取死信队列长度"""
        redis = get_redis()
        return redis.llen(self.dead_key)
    
    def processing_count(self) -> int:
        """获取处理中任务数"""
        redis = get_redis()
        return redis.hlen(self.processing_key)
    
    def stats(self) -> Dict[str, int]:
        """获取队列统计"""
        return {
            "pending": self.length(),
            "processing": self.processing_count(),
            "dead": self.dead_length(),
        }


# 预定义队列
EXECUTION_QUEUE = "execution"      # 执行任务队列
NOTIFICATION_QUEUE = "notification" # 通知队列
NODE_EXECUTE_QUEUE = "node-execute" # 按节点下发的执行队列（Phase 5）


def get_execution_queue() -> TaskQueue:
    """获取执行任务队列"""
    return TaskQueue(EXECUTION_QUEUE)


def get_notification_queue() -> TaskQueue:
    """获取通知队列"""
    return TaskQueue(NOTIFICATION_QUEUE)


def get_node_execute_queue() -> TaskQueue:
    """获取节点执行队列（中心投递，worker 消费并 POST 到各节点）"""
    return TaskQueue(NODE_EXECUTE_QUEUE)
