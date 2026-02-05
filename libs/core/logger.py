"""
Logger - 结构化日志

职责：
- 提供统一的日志接口
- 支持结构化日志输出（JSON）
- 支持日志级别控制

不负责：
- 业务字段定义（由调用方传入 extra）
- 日志持久化（由部署层配置）
"""

import logging
import json
import sys
from typing import Optional, Dict, Any
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """结构化日志格式器（JSON 输出）"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service_name": getattr(record, "service_name", "-"),
            "request_id": getattr(record, "request_id", "-"),
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # 添加 extra 字段
        if hasattr(record, "extra") and record.extra:
            log_data["extra"] = record.extra
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class SimpleFormatter(logging.Formatter):
    """简单日志格式器（开发环境）"""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(service_name)s | %(request_id)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


class ContextFilter(logging.Filter):
    """为日志记录补齐 service_name / request_id"""

    def __init__(self, service_name: str = "-"):
        super().__init__()
        self.service_name = service_name or "-"

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "service_name"):
            record.service_name = self.service_name
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


class StructuredLogger:
    """结构化日志封装"""
    
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
    
    def _log(self, level: int, msg: str, extra: Optional[Dict[str, Any]] = None):
        """内部日志方法"""
        record = self._logger.makeRecord(
            self._logger.name,
            level,
            "(unknown)",
            0,
            msg,
            (),
            None
        )
        if extra:
            record.extra = extra
            if "service_name" in extra:
                record.service_name = extra["service_name"]
            if "request_id" in extra:
                record.request_id = extra["request_id"]
        self._logger.handle(record)
    
    def debug(self, msg: str, **extra):
        self._log(logging.DEBUG, msg, extra if extra else None)
    
    def info(self, msg: str, **extra):
        self._log(logging.INFO, msg, extra if extra else None)
    
    def warning(self, msg: str, **extra):
        self._log(logging.WARNING, msg, extra if extra else None)
    
    def error(self, msg: str, **extra):
        self._log(logging.ERROR, msg, extra if extra else None)
    
    def critical(self, msg: str, **extra):
        self._log(logging.CRITICAL, msg, extra if extra else None)


_loggers: Dict[str, StructuredLogger] = {}
_initialized: bool = False


def setup_logging(
    level: str = "INFO",
    structured: bool = False,
    service_name: str = "-"
) -> None:
    """
    初始化日志系统
    
    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        structured: 是否使用 JSON 格式（生产环境建议开启）
    """
    global _initialized
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 清除已有 handler
    root_logger.handlers.clear()
    
    # 添加控制台 handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        StructuredFormatter() if structured else SimpleFormatter()
    )
    handler.addFilter(ContextFilter(service_name=service_name))
    root_logger.addHandler(handler)
    
    _initialized = True


def get_logger(name: str) -> StructuredLogger:
    """
    获取日志实例
    
    Args:
        name: 日志名称（通常为模块名）
    
    Returns:
        StructuredLogger 实例
    """
    global _initialized
    
    if not _initialized:
        setup_logging()
    
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    
    return _loggers[name]
