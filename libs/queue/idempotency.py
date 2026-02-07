"""
Idempotency Checker - 幂等性检查

基于 Redis SETNX 实现的幂等性控制：
- 防止重复执行相同信号
- 支持 TTL 过期自动清理
- 提供执行状态查询
"""

from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from libs.core import get_redis, get_logger

logger = get_logger("idempotency")


class TaskState(str, Enum):
    """任务状态"""
    PENDING = "pending"       # 已接收，待处理
    PROCESSING = "processing" # 处理中
    COMPLETED = "completed"   # 完成
    FAILED = "failed"         # 失败


@dataclass
class IdempotencyRecord:
    """幂等性记录"""
    key: str                     # 幂等键
    state: TaskState             # 状态
    task_id: Optional[str] = None  # 任务ID
    result: Optional[Dict] = None  # 结果
    error: Optional[str] = None    # 错误信息
    created_at: str = ""
    updated_at: str = ""
    
    def to_json(self) -> str:
        data = asdict(self)
        data["state"] = self.state.value
        return json.dumps(data, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, data: str) -> "IdempotencyRecord":
        d = json.loads(data)
        d["state"] = TaskState(d["state"])
        return cls(**d)


class IdempotencyChecker:
    """
    幂等性检查器
    
    使用方式：
        checker = IdempotencyChecker()
        
        # 尝试获取执行权
        if checker.acquire(signal_id):
            try:
                result = execute_signal(signal_id)
                checker.complete(signal_id, result)
            except Exception as e:
                checker.fail(signal_id, str(e))
        else:
            # 重复请求，返回已有结果
            record = checker.get(signal_id)
    """
    
    KEY_PREFIX = "ironbull:idempotency"
    DEFAULT_TTL = 86400 * 7  # 7天过期
    
    def __init__(self, ttl_seconds: int = DEFAULT_TTL):
        self.ttl = ttl_seconds
    
    def _key(self, idempotency_key: str) -> str:
        """生成 Redis key"""
        return f"{self.KEY_PREFIX}:{idempotency_key}"
    
    def acquire(
        self,
        idempotency_key: str,
        task_id: Optional[str] = None,
    ) -> bool:
        """
        尝试获取执行权
        
        Args:
            idempotency_key: 幂等键（通常是 signal_id 或自定义唯一键）
            task_id: 可选的任务ID
        
        Returns:
            True 如果成功获取（可以执行）
            False 如果已存在（重复请求）
        """
        redis = get_redis()
        key = self._key(idempotency_key)
        now = datetime.now().isoformat()
        
        record = IdempotencyRecord(
            key=idempotency_key,
            state=TaskState.PROCESSING,
            task_id=task_id,
            created_at=now,
            updated_at=now,
        )
        
        # SETNX：仅当 key 不存在时设置
        acquired = redis.set(key, record.to_json(), nx=True, ex=self.ttl)
        
        if acquired:
            logger.info(
                "idempotency acquired",
                key=idempotency_key,
                task_id=task_id,
            )
            return True
        
        logger.warning(
            "idempotency rejected (duplicate)",
            key=idempotency_key,
            task_id=task_id,
        )
        return False
    
    def complete(
        self,
        idempotency_key: str,
        result: Optional[Dict] = None,
    ) -> None:
        """标记执行完成"""
        redis = get_redis()
        key = self._key(idempotency_key)
        
        existing = redis.get(key)
        if existing:
            record = IdempotencyRecord.from_json(existing)
        else:
            record = IdempotencyRecord(
                key=idempotency_key,
                state=TaskState.PENDING,
                created_at=datetime.now().isoformat(),
            )
        
        record.state = TaskState.COMPLETED
        record.result = result
        record.updated_at = datetime.now().isoformat()
        
        redis.setex(key, self.ttl, record.to_json())
        
        logger.info("idempotency completed", key=idempotency_key)
    
    def fail(
        self,
        idempotency_key: str,
        error: str,
    ) -> None:
        """标记执行失败"""
        redis = get_redis()
        key = self._key(idempotency_key)
        
        existing = redis.get(key)
        if existing:
            record = IdempotencyRecord.from_json(existing)
        else:
            record = IdempotencyRecord(
                key=idempotency_key,
                state=TaskState.PENDING,
                created_at=datetime.now().isoformat(),
            )
        
        record.state = TaskState.FAILED
        record.error = error
        record.updated_at = datetime.now().isoformat()
        
        redis.setex(key, self.ttl, record.to_json())
        
        logger.error("idempotency failed", key=idempotency_key, error=error)
    
    def get(self, idempotency_key: str) -> Optional[IdempotencyRecord]:
        """获取幂等性记录"""
        redis = get_redis()
        key = self._key(idempotency_key)
        
        data = redis.get(key)
        if data:
            return IdempotencyRecord.from_json(data)
        return None
    
    def exists(self, idempotency_key: str) -> bool:
        """检查是否已存在"""
        redis = get_redis()
        key = self._key(idempotency_key)
        return redis.exists(key) > 0
    
    def delete(self, idempotency_key: str) -> bool:
        """删除记录（慎用，仅用于测试）"""
        redis = get_redis()
        key = self._key(idempotency_key)
        return redis.delete(key) > 0


# 预定义检查器
_signal_checker: Optional[IdempotencyChecker] = None


def get_signal_idempotency() -> IdempotencyChecker:
    """获取信号幂等性检查器"""
    global _signal_checker
    if _signal_checker is None:
        _signal_checker = IdempotencyChecker()
    return _signal_checker
