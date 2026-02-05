"""
IronBull Core Library

基础能力库，为所有 services / nodes 提供统一基础设施。

模块：
- config: 统一配置加载
- logger: 结构化日志
- exceptions: 基础异常
- utils: 通用工具
- database: MySQL 数据库连接 (v1)
"""

from .config import Config, get_config
from .logger import get_logger, setup_logging
from .exceptions import (
    AppError,
    IronBullError,
    ConfigError,
    ValidationError,
    TimeoutError,
    RetryableError,
)
from .utils import (
    generate_id,
    gen_id,
    now_timestamp,
    time_now,
    safe_float,
    safe_int,
)
from .database import (
    Base,
    init_database,
    get_engine,
    get_session,
    get_db,
    create_tables,
    check_connection,
    close_database,
)
from .redis_client import (
    init_redis,
    get_redis,
    close_redis,
    check_redis_connection,
    set_with_ttl,
    get_json,
    set_if_not_exists,
    delete_key,
    push_to_queue,
    pop_from_queue,
    get_queue_length,
)

__all__ = [
    # Config
    "Config",
    "get_config",
    
    # Logger
    "get_logger",
    "setup_logging",
    
    # Exceptions
    "AppError",
    "IronBullError",
    "ConfigError",
    "ValidationError",
    "TimeoutError",
    "RetryableError",
    
    # Utils
    "generate_id",
    "gen_id",
    "now_timestamp",
    "time_now",
    "safe_float",
    "safe_int",
    
    # Database (v1)
    "Base",
    "init_database",
    "get_engine",
    "get_session",
    "get_db",
    "create_tables",
    "check_connection",
    "close_database",
    
    # Redis (v1 Phase 3)
    "init_redis",
    "get_redis",
    "close_redis",
    "check_redis_connection",
    "set_with_ttl",
    "get_json",
    "set_if_not_exists",
    "delete_key",
    "push_to_queue",
    "pop_from_queue",
    "get_queue_length",
]
