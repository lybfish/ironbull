"""
Strategy Runner Service

定时运行策略的服务，提供 HTTP API 管理策略任务。
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from libs.runner import StrategyRunner, StrategyTask
from libs.strategies import list_strategies
from libs.core import get_config, get_logger, setup_logging, gen_id, AppError

# 配置
config = get_config()
DATA_PROVIDER_URL = os.getenv(
    "DATA_PROVIDER_URL",
    config.get_str("data_provider_url", "http://127.0.0.1:8005"),
)
SIGNAL_HUB_URL = os.getenv(
    "SIGNAL_HUB_URL",
    config.get_str("signal_hub_url", "http://127.0.0.1:8001"),
)

# 日志
service_name = "strategy-runner"
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name=service_name,
)
logger = get_logger(service_name)

# 全局 Runner 实例
runner: Optional[StrategyRunner] = None
runner_task: Optional[asyncio.Task] = None


# ============ Pydantic Models ============

class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    task_id: str = Field(..., description="任务唯一标识")
    strategy_code: str = Field(..., description="策略代码")
    symbol: str = Field(..., description="交易对")
    timeframe: str = Field(..., description="时间周期")
    interval_seconds: int = Field(60, description="运行间隔（秒）")
    candle_limit: int = Field(100, description="K 线数量")
    auto_submit: bool = Field(True, description="自动提交信号")
    enabled: bool = Field(True, description="是否启用")
    strategy_config: dict = Field(default_factory=dict, description="策略配置")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    strategy_code: str
    symbol: str
    timeframe: str
    interval_seconds: int
    enabled: bool
    run_count: int
    signal_count: int
    error_count: int
    last_run: Optional[str] = None
    last_error: Optional[str] = None


class RunOnceResponse(BaseModel):
    """单次运行响应"""
    task_id: str
    has_signal: bool
    signal: Optional[dict] = None


class StatsResponse(BaseModel):
    """统计响应"""
    running: bool
    task_count: int
    enabled_tasks: int
    total_runs: int
    total_signals: int
    total_errors: int
    tasks: List[dict]


# ============ Lifespan ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global runner, runner_task
    
    # 启动时初始化 Runner
    runner = StrategyRunner(
        data_provider_url=DATA_PROVIDER_URL,
        signal_hub_url=SIGNAL_HUB_URL,
    )
    logger.info(f"StrategyRunner initialized (data: {DATA_PROVIDER_URL}, signal: {SIGNAL_HUB_URL})")
    
    yield
    
    # 关闭时停止 Runner
    if runner and runner.is_running():
        await runner.stop()
    logger.info("StrategyRunner shutdown")


# ============ FastAPI App ============

app = FastAPI(
    title="IronBull Strategy Runner",
    description="定时运行策略的服务",
    version="0.1.0",
    lifespan=lifespan,
)


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


# ============ Endpoints ============

@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "service": "strategy-runner",
        "runner_active": runner.is_running() if runner else False,
    }


@app.get("/api/strategies")
async def get_strategies():
    """获取可用策略列表"""
    return {"strategies": list_strategies()}


@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(req: CreateTaskRequest):
    """创建策略任务"""
    if not runner:
        raise HTTPException(500, "Runner not initialized")
    
    # 检查任务是否已存在
    if runner.get_task(req.task_id):
        raise HTTPException(400, f"Task already exists: {req.task_id}")
    
    # 创建任务
    task = StrategyTask(
        task_id=req.task_id,
        strategy_code=req.strategy_code,
        strategy_config=req.strategy_config,
        symbol=req.symbol,
        timeframe=req.timeframe,
        interval_seconds=req.interval_seconds,
        candle_limit=req.candle_limit,
        auto_submit=req.auto_submit,
        enabled=req.enabled,
    )
    
    try:
        runner.add_task(task)
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    return TaskResponse(
        task_id=task.task_id,
        strategy_code=task.strategy_code,
        symbol=task.symbol,
        timeframe=task.timeframe,
        interval_seconds=task.interval_seconds,
        enabled=task.enabled,
        run_count=task.run_count,
        signal_count=task.signal_count,
        error_count=task.error_count,
    )


@app.get("/api/tasks", response_model=List[TaskResponse])
async def list_tasks():
    """列出所有任务"""
    if not runner:
        raise HTTPException(500, "Runner not initialized")
    
    tasks = runner.list_tasks()
    return [
        TaskResponse(
            task_id=t.task_id,
            strategy_code=t.strategy_code,
            symbol=t.symbol,
            timeframe=t.timeframe,
            interval_seconds=t.interval_seconds,
            enabled=t.enabled,
            run_count=t.run_count,
            signal_count=t.signal_count,
            error_count=t.error_count,
            last_run=str(t.last_run) if t.last_run else None,
            last_error=t.last_error,
        )
        for t in tasks
    ]


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """获取单个任务"""
    if not runner:
        raise HTTPException(500, "Runner not initialized")
    
    task = runner.get_task(task_id)
    if not task:
        raise HTTPException(404, f"Task not found: {task_id}")
    
    return TaskResponse(
        task_id=task.task_id,
        strategy_code=task.strategy_code,
        symbol=task.symbol,
        timeframe=task.timeframe,
        interval_seconds=task.interval_seconds,
        enabled=task.enabled,
        run_count=task.run_count,
        signal_count=task.signal_count,
        error_count=task.error_count,
        last_run=str(task.last_run) if task.last_run else None,
        last_error=task.last_error,
    )


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    if not runner:
        raise HTTPException(500, "Runner not initialized")
    
    if not runner.remove_task(task_id):
        raise HTTPException(404, f"Task not found: {task_id}")
    
    return {"message": f"Task deleted: {task_id}"}


@app.post("/api/tasks/{task_id}/enable")
async def enable_task(task_id: str):
    """启用任务"""
    if not runner:
        raise HTTPException(500, "Runner not initialized")
    
    task = runner.get_task(task_id)
    if not task:
        raise HTTPException(404, f"Task not found: {task_id}")
    
    task.enabled = True
    return {"message": f"Task enabled: {task_id}"}


@app.post("/api/tasks/{task_id}/disable")
async def disable_task(task_id: str):
    """禁用任务"""
    if not runner:
        raise HTTPException(500, "Runner not initialized")
    
    task = runner.get_task(task_id)
    if not task:
        raise HTTPException(404, f"Task not found: {task_id}")
    
    task.enabled = False
    return {"message": f"Task disabled: {task_id}"}


@app.post("/api/tasks/{task_id}/run", response_model=RunOnceResponse)
async def run_task_once(task_id: str):
    """手动运行一次任务"""
    if not runner:
        raise HTTPException(500, "Runner not initialized")
    
    try:
        output = await runner.run_once(task_id)
        
        signal_dict = None
        if output:
            signal_dict = {
                "symbol": output.symbol,
                "signal_type": output.signal_type,
                "side": output.side,
                "entry_price": output.entry_price,
                "stop_loss": output.stop_loss,
                "take_profit": output.take_profit,
                "confidence": output.confidence,
                "reason": output.reason,
            }
        
        return RunOnceResponse(
            task_id=task_id,
            has_signal=output is not None,
            signal=signal_dict,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/runner/start")
async def start_runner(background_tasks: BackgroundTasks):
    """启动 Runner 调度循环"""
    global runner_task
    
    if not runner:
        raise HTTPException(500, "Runner not initialized")
    
    if runner.is_running():
        return {"message": "Runner already running"}
    
    # 在后台启动
    async def _start():
        await runner.start()
    
    runner_task = asyncio.create_task(_start())
    
    return {"message": "Runner started"}


@app.post("/api/runner/stop")
async def stop_runner():
    """停止 Runner 调度循环"""
    if not runner:
        raise HTTPException(500, "Runner not initialized")
    
    if not runner.is_running():
        return {"message": "Runner not running"}
    
    await runner.stop()
    
    return {"message": "Runner stopped"}


@app.get("/api/runner/stats", response_model=StatsResponse)
async def get_stats():
    """获取运行统计"""
    if not runner:
        raise HTTPException(500, "Runner not initialized")
    
    stats = runner.get_stats()
    return StatsResponse(**stats)


# ============ Main ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
