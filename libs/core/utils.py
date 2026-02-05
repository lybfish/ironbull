"""
Utils - 通用工具函数

职责：
- 提供通用工具函数
- ID 生成、时间戳、类型转换等

不负责：
- 业务相关工具（由各 service 自行定义）
"""

import uuid
import time
from typing import Optional, Any
from decimal import Decimal, ROUND_DOWN


def generate_id(prefix: str = "") -> str:
    """
    生成唯一 ID
    
    Args:
        prefix: ID 前缀（如 sig_, ord_, task_）
    
    Returns:
        唯一 ID 字符串
    """
    uid = uuid.uuid4().hex[:16]
    return f"{prefix}{uid}" if prefix else uid


def gen_id(prefix: str = "") -> str:
    """生成唯一 ID（别名）"""
    return generate_id(prefix)


def now_timestamp() -> int:
    """
    获取当前 Unix 时间戳（秒）
    
    Returns:
        Unix 时间戳
    """
    return int(time.time())


def time_now() -> int:
    """获取当前 Unix 时间戳（秒）"""
    return now_timestamp()


def now_timestamp_ms() -> int:
    """
    获取当前 Unix 时间戳（毫秒）
    
    Returns:
        Unix 时间戳（毫秒）
    """
    return int(time.time() * 1000)


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    安全转换为浮点数
    
    Args:
        value: 任意值
        default: 默认值
    
    Returns:
        浮点数
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    安全转换为整数
    
    Args:
        value: 任意值
        default: 默认值
    
    Returns:
        整数
    """
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def truncate_decimal(value: float, precision: int) -> float:
    """
    截断小数位（向下取整，不四舍五入）
    
    Args:
        value: 数值
        precision: 小数位数
    
    Returns:
        截断后的数值
    """
    if precision < 0:
        return value
    d = Decimal(str(value))
    factor = Decimal(10) ** -precision
    return float(d.quantize(factor, rounding=ROUND_DOWN))


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    限制数值在范围内
    
    Args:
        value: 数值
        min_val: 最小值
        max_val: 最大值
    
    Returns:
        限制后的数值
    """
    return max(min_val, min(value, max_val))
