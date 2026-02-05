# IronBull v0 — Errors & Logging Spec

本规范用于统一各服务的日志字段与错误返回结构。

## 1) 日志规范

### 结构化日志（JSON）
示例：
```json
{
  "timestamp": "2026-02-05T20:44:04.538031Z",
  "level": "INFO",
  "service_name": "risk-control",
  "request_id": "req_xxxx",
  "logger": "risk-control",
  "message": "risk check passed",
  "extra": {
    "signal_id": "sig_xxx",
    "account_id": 123
  }
}
```

### 开发环境（简单格式）
```
2026-02-05 20:44:04 | INFO     | risk-control | req_xxxx | risk-control | risk check passed
```

### 使用方式
```python
from libs.core import get_logger, setup_logging

setup_logging(level="INFO", structured=True, service_name="xxx")
logger = get_logger("xxx")

logger.info("message", signal_id="xxx", account_id=123)
```

## 2) 错误码体系
定义于 `libs/core/exceptions.py`。

| 错误类 | 错误码 | 说明 |
| --- | --- | --- |
| AppError | INTERNAL_ERROR | 内部错误（基类） |
| ConfigError | CONFIG_ERROR | 配置错误 |
| ValidationError | VALIDATION_ERROR | 验证失败 |
| TimeoutError | TIMEOUT_ERROR | 操作超时 |
| RetryableError | RETRYABLE_ERROR | 可重试错误 |
| NotFoundError | NOT_FOUND | 资源不存在 |
| ConflictError | CONFLICT | 资源冲突 |
| AuthenticationError | AUTHENTICATION_ERROR | 认证失败 |
| PermissionError | PERMISSION_DENIED | 权限不足 |

## 3) 统一返回结构

### 成功响应
成功响应按业务返回：
- `/health`：`{"status": "ok", "service": "xxx"}`
- 业务接口：`{"signal": ...}` / `{"result": ...}` / `{"task_id": ...}` 等

### 错误响应
统一格式：
```json
{
  "code": "VALIDATION_ERROR",
  "message": "Validation failed",
  "detail": {
    "errors": [ ... ]
  },
  "request_id": "req_06818fb80c374aaf"
}
```

### HTTP 状态码映射
| 场景 | HTTP Status | code |
| --- | --- | --- |
| 参数验证失败 | 422 | VALIDATION_ERROR |
| 业务错误 (AppError) | 400 | 具体错误码 |
| HTTP 异常 | 对应状态码 | HTTP_ERROR |
| 未捕获异常 | 500 | INTERNAL_ERROR |

## 4) Request ID 链路追踪
- 从 `X-Request-Id` 读取；若不存在则自动生成
- 响应头写回 `X-Request-Id`
- 日志中自动携带 `request_id`

