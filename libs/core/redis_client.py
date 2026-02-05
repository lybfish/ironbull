"""
Redis Client - Redis 连接管理

职责：
- 提供统一的 Redis 连接
- 支持连接池
- 提供常用操作封装

用途：
- 消息队列
- 幂等性检查（去重）
- 分布式锁
- 缓存
"""

from typing import Optional, Any, List
import json

import redis
from redis import Redis

from .config import get_config
from .logger import get_logger

logger = get_logger("redis")

_redis_client: Optional[Redis] = None


def get_redis_url() -> str:
    """获取 Redis 连接 URL"""
    config = get_config()
    
    # 直接 URL
    url = config.get_str("redis_url", "")
    if url:
        return url
    
    # 拼接方式
    host = config.get_str("redis_host", "127.0.0.1")
    port = config.get_int("redis_port", 6379)
    db = config.get_int("redis_db", 0)
    password = config.get_str("redis_password", "")
    
    if password:
        return f"redis://:{password}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"


def init_redis() -> Redis:
    """初始化 Redis 连接"""
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
    
    config = get_config()
    url = get_redis_url()
    
    # 连接池配置
    pool_size = config.get_int("redis_pool_size", 10)
    
    pool = redis.ConnectionPool.from_url(
        url,
        max_connections=pool_size,
        decode_responses=True,  # 自动解码为字符串
    )
    
    _redis_client = Redis(connection_pool=pool)
    
    # 测试连接
    _redis_client.ping()
    
    logger.info(
        "redis initialized",
        host=config.get_str("redis_host", "127.0.0.1"),
        port=config.get_int("redis_port", 6379),
        db=config.get_int("redis_db", 0),
    )
    
    return _redis_client


def get_redis() -> Redis:
    """获取 Redis 客户端"""
    global _redis_client
    if _redis_client is None:
        return init_redis()
    return _redis_client


def close_redis() -> None:
    """关闭 Redis 连接"""
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None
        logger.info("redis connection closed")


def check_redis_connection() -> bool:
    """检查 Redis 连接"""
    try:
        client = get_redis()
        client.ping()
        return True
    except Exception as e:
        logger.error("redis connection failed", error=str(e))
        return False


# ==================== 常用操作封装 ====================

def set_with_ttl(key: str, value: Any, ttl_seconds: int) -> bool:
    """设置带过期时间的值"""
    client = get_redis()
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return client.setex(key, ttl_seconds, value)


def get_json(key: str) -> Optional[Any]:
    """获取 JSON 值"""
    client = get_redis()
    value = client.get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return None


def set_if_not_exists(key: str, value: Any, ttl_seconds: int = 0) -> bool:
    """
    仅当 key 不存在时设置（用于幂等性检查）
    
    Returns:
        True 如果设置成功（key 不存在）
        False 如果 key 已存在
    """
    client = get_redis()
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    
    if ttl_seconds > 0:
        return client.set(key, value, nx=True, ex=ttl_seconds)
    return client.setnx(key, value)


def delete_key(key: str) -> bool:
    """删除 key"""
    client = get_redis()
    return client.delete(key) > 0


def push_to_queue(queue_name: str, message: Any) -> int:
    """
    推送消息到队列（LPUSH）
    
    Returns:
        队列长度
    """
    client = get_redis()
    if isinstance(message, (dict, list)):
        message = json.dumps(message, ensure_ascii=False)
    return client.lpush(queue_name, message)


def pop_from_queue(queue_name: str, timeout: int = 0) -> Optional[Any]:
    """
    从队列弹出消息（BRPOP，阻塞）
    
    Args:
        queue_name: 队列名
        timeout: 超时秒数，0 表示永久阻塞
    
    Returns:
        消息内容，超时返回 None
    """
    client = get_redis()
    result = client.brpop(queue_name, timeout=timeout)
    if result:
        _, message = result
        try:
            return json.loads(message)
        except json.JSONDecodeError:
            return message
    return None


def get_queue_length(queue_name: str) -> int:
    """获取队列长度"""
    client = get_redis()
    return client.llen(queue_name)
