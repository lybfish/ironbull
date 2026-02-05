import json
from dataclasses import asdict
from datetime import datetime
from threading import Lock
from typing import Dict, Optional
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from libs.contracts import ExecutionTask, ExecutionResult, NodeTask, NodeResult
from libs.core import get_config, get_logger, setup_logging, gen_id, time_now, AppError
from .node_registry import get_node_registry

# v1 Facts Layer (可选，失败不阻塞主流程)
try:
    from libs.facts import FactsRepository, AuditAction, SignalStatus, ExecutionStatus
    FACTS_ENABLED = True
except ImportError:
    FACTS_ENABLED = False

# v1 Queue Layer (可选)
try:
    from libs.core import init_redis, check_redis_connection
    from libs.queue import TaskQueue, TaskMessage, IdempotencyChecker, get_execution_queue
    QUEUE_ENABLED = True
except ImportError:
    QUEUE_ENABLED = False


class ExecutionSubmitRequest(BaseModel):
    signal_id: str
    account_id: int
    member_id: int
    platform: str
    exchange: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    credentials: Optional[dict] = None


class ExecutionSubmitResponse(BaseModel):
    task_id: str


class AsyncSubmitResponse(BaseModel):
    """异步提交响应"""
    task_id: str
    queued: bool
    message: str


class ExecutionResultResponse(BaseModel):
    result: dict


config = get_config()
service_name = "execution-dispatcher"
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name=service_name,
)
logger = get_logger(service_name)

app = FastAPI(title="execution-dispatcher")
results_store: Dict[str, ExecutionResult] = {}
store_lock = Lock()

# 初始化 Redis（如果可用）
if QUEUE_ENABLED:
    try:
        init_redis()
        if check_redis_connection():
            logger.info("redis connected for async queue")
        else:
            logger.warning("redis connection failed, async queue disabled")
            QUEUE_ENABLED = False
    except Exception as e:
        logger.warning("redis init failed", error=str(e))
        QUEUE_ENABLED = False


def _error_payload(code: str, message: str, detail: Optional[dict] = None, request_id: Optional[str] = None) -> dict:
    payload = {"code": code, "message": message, "detail": detail or {}}
    if request_id:
        payload["request_id"] = request_id
    return payload


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=422,
        content=_error_payload("VALIDATION_ERROR", "Validation failed", {"errors": exc.errors()}, request_id),
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=400,
        content=_error_payload(exc.code, exc.message, exc.detail, request_id),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", None)
    detail = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload("HTTP_ERROR", "HTTP error", detail, request_id),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.error("unhandled exception", request_id=request_id, error=str(exc))
    return JSONResponse(
        status_code=500,
        content=_error_payload("INTERNAL_ERROR", "Internal error", {"error": str(exc)}, request_id),
    )


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or gen_id("req_")
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/health")
def health():
    result = {"status": "ok", "service": service_name}
    
    # 添加队列状态
    if QUEUE_ENABLED:
        try:
            queue = get_execution_queue()
            result["queue"] = queue.stats()
        except Exception:
            result["queue"] = {"error": "unavailable"}
    
    return result


def _post_json(url: str, payload: dict, timeout: float = 5.0) -> dict:
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


def _build_node_task(task: ExecutionTask) -> NodeTask:
    creds = task.credentials or {}
    return NodeTask(
        task_id=task.task_id,
        symbol=task.symbol,
        side=task.side,
        order_type=task.order_type,
        quantity=task.quantity,
        price=task.price,
        stop_loss=task.stop_loss,
        take_profit=task.take_profit,
        api_key=creds.get("api_key", ""),
        api_secret=creds.get("api_secret", ""),
        passphrase=creds.get("passphrase"),
        exchange=task.exchange,
        timeout_ms=task.timeout_ms,
    )


@app.post("/api/execution/submit", response_model=ExecutionSubmitResponse)
def submit(req: ExecutionSubmitRequest, request: Request):
    task_id = gen_id("task_")
    task = ExecutionTask(
        task_id=task_id,
        signal_id=req.signal_id,
        account_id=req.account_id,
        member_id=req.member_id,
        platform=req.platform,
        exchange=req.exchange,
        symbol=req.symbol,
        side=req.side,
        order_type=req.order_type,
        quantity=req.quantity,
        price=req.price,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        credentials=req.credentials,
        created_at=time_now(),
    )

    registry = get_node_registry()
    node_url = registry.get(task.platform)
    if not node_url:
        raise HTTPException(status_code=400, detail="Unknown platform")

    node_task = _build_node_task(task)

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

    exec_result = ExecutionResult(
        task_id=task_id,
        signal_id=task.signal_id,
        success=node_result.success,
        exchange_order_id=node_result.exchange_order_id,
        filled_price=node_result.filled_price,
        filled_quantity=node_result.filled_quantity,
        error_code=node_result.error_code,
        error_message=node_result.error_message,
        executed_at=node_result.executed_at or time_now(),
    )

    with store_lock:
        results_store[task_id] = exec_result

    # v1: 记录 Trade + Ledger + SignalEvent（失败不阻塞）
    if FACTS_ENABLED:
        repo = FactsRepository()
        try:
            request_id = getattr(request.state, "request_id", None)
            
            # 1. 记录 Trade
            trade = repo.create_trade(
                signal_id=task.signal_id,
                task_id=task_id,
                account_id=task.account_id,
                member_id=task.member_id,
                symbol=task.symbol,
                side=task.side,
                trade_type="OPEN",  # v0 简化：默认 OPEN
                quantity=task.quantity,
                exchange=task.exchange,
                order_type=task.order_type,
                entry_price=task.price,
                filled_price=node_result.filled_price,
                filled_quantity=node_result.filled_quantity,
                stop_loss=task.stop_loss,
                take_profit=task.take_profit,
                fee=node_result.fee or 0,
                fee_currency=node_result.fee_currency,
                exchange_order_id=node_result.exchange_order_id,
                status="filled" if node_result.success else "failed",
                error_code=node_result.error_code,
                error_message=node_result.error_message,
                executed_at=datetime.utcnow() if node_result.success else None,
                request_id=request_id,
            )
            
            # 2. 记录 Ledger（手续费）
            if node_result.success and node_result.fee and node_result.fee > 0:
                repo.create_ledger(
                    account_id=task.account_id,
                    member_id=task.member_id,
                    ledger_type="TRADE_FEE",
                    amount=-node_result.fee,  # 费用为负
                    currency=node_result.fee_currency or "USDT",
                    trade_id=trade.id,
                    signal_id=task.signal_id,
                    description=f"Trade fee for {task.symbol}",
                    request_id=request_id,
                )
            
            # 3. 记录 SignalEvent
            new_status = SignalStatus.EXECUTED.value if node_result.success else SignalStatus.FAILED.value
            repo.create_signal_event(
                signal_id=task.signal_id,
                event_type="EXECUTED" if node_result.success else "FAILED",
                status=new_status,
                source_service="execution-dispatcher",
                task_id=task_id,
                account_id=task.account_id,
                detail={
                    "platform": task.platform,
                    "exchange": task.exchange,
                    "filled_price": node_result.filled_price,
                    "filled_quantity": node_result.filled_quantity,
                    "exchange_order_id": node_result.exchange_order_id,
                },
                error_code=node_result.error_code,
                error_message=node_result.error_message,
                request_id=request_id,
            )
            
            # 4. 审计日志
            repo.create_audit_log(
                action=AuditAction.EXEC_FILLED.value if node_result.success else AuditAction.EXEC_FAILED.value,
                source_service="execution-dispatcher",
                signal_id=task.signal_id,
                task_id=task_id,
                account_id=task.account_id,
                member_id=task.member_id,
                status_before=SignalStatus.PASSED.value,
                status_after=new_status,
                success=node_result.success,
                error_code=node_result.error_code,
                error_message=node_result.error_message,
                detail={
                    "platform": task.platform,
                    "exchange": task.exchange,
                    "symbol": task.symbol,
                    "side": task.side,
                    "filled_price": node_result.filled_price,
                    "filled_quantity": node_result.filled_quantity,
                    "exchange_order_id": node_result.exchange_order_id,
                },
                request_id=request_id,
            )
        except Exception as e:
            logger.warning("facts layer write failed", error=str(e))

    logger.info(
        "execution submitted",
        request_id=request.state.request_id,
        task_id=task_id,
        signal_id=task.signal_id,
        platform=task.platform,
    )

    return {"task_id": task_id}


@app.get("/api/execution/result/{task_id}", response_model=ExecutionResultResponse)
def get_result(task_id: str):
    with store_lock:
        result = results_store.get(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"result": asdict(result)}


# ========== 异步队列 API (v1 Phase 3) ==========

@app.post("/api/execution/submit-async", response_model=AsyncSubmitResponse)
def submit_async(req: ExecutionSubmitRequest, request: Request):
    """
    异步提交执行任务
    
    任务会被放入队列，由 Worker 异步处理
    支持幂等性检查，同一 signal_id 不会重复执行
    """
    if not QUEUE_ENABLED:
        raise HTTPException(status_code=503, detail="Async queue not available")
    
    task_id = gen_id("task_")
    request_id = getattr(request.state, "request_id", None)
    
    # 幂等性检查
    idempotency_checker = IdempotencyChecker()
    idempotency_key = f"exec:{req.signal_id}"
    
    if not idempotency_checker.acquire(idempotency_key, task_id):
        # 重复请求，返回已有记录
        existing = idempotency_checker.get(idempotency_key)
        return AsyncSubmitResponse(
            task_id=existing.task_id if existing else "",
            queued=False,
            message="duplicate signal, already processing or completed",
        )
    
    # 构建任务消息
    message = TaskMessage(
        task_id=task_id,
        task_type="execution",
        signal_id=req.signal_id,
        account_id=req.account_id,
        request_id=request_id,
        payload={
            "signal_id": req.signal_id,
            "account_id": req.account_id,
            "member_id": req.member_id,
            "platform": req.platform,
            "exchange": req.exchange,
            "symbol": req.symbol,
            "side": req.side,
            "order_type": req.order_type,
            "quantity": req.quantity,
            "price": req.price,
            "stop_loss": req.stop_loss,
            "take_profit": req.take_profit,
            "credentials": req.credentials,
        },
    )
    
    # 放入队列
    queue = get_execution_queue()
    queue.push(message)
    
    logger.info(
        "execution queued",
        request_id=request_id,
        task_id=task_id,
        signal_id=req.signal_id,
        platform=req.platform,
    )
    
    # 记录审计（如果 Facts 可用），使用后台线程避免阻塞响应
    if FACTS_ENABLED:
        import threading
        def _write_facts():
            try:
                repo = FactsRepository()
                repo.create_signal_event(
                    signal_id=req.signal_id,
                    event_type="QUEUED",
                    status=SignalStatus.PASSED.value,
                    source_service="execution-dispatcher",
                    task_id=task_id,
                    account_id=req.account_id,
                    detail={"queue": "execution", "async": True},
                    request_id=request_id,
                )
                repo.create_audit_log(
                    action=AuditAction.EXEC_QUEUED.value if hasattr(AuditAction, 'EXEC_QUEUED') else "exec_queued",
                    source_service="execution-dispatcher",
                    signal_id=req.signal_id,
                    task_id=task_id,
                    account_id=req.account_id,
                    member_id=req.member_id,
                    status_before=SignalStatus.PASSED.value,
                    status_after=SignalStatus.PASSED.value,
                    success=True,
                    detail={"queue": "execution", "async": True},
                    request_id=request_id,
                )
            except Exception as e:
                logger.warning("facts write failed", error=str(e))
        threading.Thread(target=_write_facts, daemon=True).start()
    
    return AsyncSubmitResponse(
        task_id=task_id,
        queued=True,
        message="task queued for execution",
    )


@app.get("/api/execution/queue/stats")
def queue_stats():
    """获取队列状态"""
    if not QUEUE_ENABLED:
        raise HTTPException(status_code=503, detail="Async queue not available")
    
    queue = get_execution_queue()
    return queue.stats()


@app.get("/api/execution/idempotency/{signal_id}")
def check_idempotency(signal_id: str):
    """检查信号的幂等性状态"""
    if not QUEUE_ENABLED:
        raise HTTPException(status_code=503, detail="Async queue not available")
    
    checker = IdempotencyChecker()
    idempotency_key = f"exec:{signal_id}"
    record = checker.get(idempotency_key)
    
    if not record:
        return {"exists": False, "signal_id": signal_id}
    
    return {
        "exists": True,
        "signal_id": signal_id,
        "task_id": record.task_id,
        "state": record.state.value,
        "result": record.result,
        "error": record.error,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
