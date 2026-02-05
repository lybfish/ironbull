"""
Follow Service

跟单服务 - 处理 Leader 信号广播给 Follower。

v0 最小实现：
- 内存存储跟单关系
- 收到信号后为每个 Follower 生成 FollowTask
- 调用 execution-dispatcher 执行
"""

import httpx
from dataclasses import asdict
from typing import List, Optional, Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from libs.core import get_config, get_logger, setup_logging, gen_id, AppError
from libs.contracts import FollowTask, FollowTaskResult, Signal


# ============== Pydantic Models ==============

class FollowRelation(BaseModel):
    """跟单关系"""
    relation_id: int
    leader_id: int
    follower_id: int
    follower_account_id: int
    follow_mode: str  # ratio / fixed_amount / fixed_quantity
    follow_value: float
    platform: str  # crypto / mt5
    exchange: str  # binance / okx / mt5_broker
    enabled: bool = True


class CreateRelationRequest(BaseModel):
    leader_id: int
    follower_id: int
    follower_account_id: int
    follow_mode: str
    follow_value: float
    platform: str
    exchange: str


class SignalModel(BaseModel):
    """信号（来自 signal-hub）"""
    signal_id: str
    strategy_code: str
    symbol: str
    canonical_symbol: str
    side: str
    signal_type: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    quantity: Optional[float] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    timeframe: str = ""
    timestamp: int = 0
    status: str = "pending"


class BroadcastRequest(BaseModel):
    """广播信号请求"""
    leader_id: int
    signal: SignalModel


class BroadcastResponse(BaseModel):
    """广播响应"""
    signal_id: str
    tasks_created: int
    tasks: List[dict]


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    order_id: Optional[str] = None
    error: Optional[str] = None


# ============== Service Setup ==============

config = get_config()
service_name = "follow-service"
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name=service_name,
)
logger = get_logger(service_name)

app = FastAPI(title="follow-service")

# 服务 URL
DISPATCHER_URL = config.get_str("dispatcher_url", "http://127.0.0.1:8003")


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

# ============== In-Memory Storage ==============
# v0: 内存存储，后续可替换为 DB

# 跟单关系: {relation_id: FollowRelation}
_relations: Dict[int, FollowRelation] = {}
_relation_counter = 0

# 跟单任务: {task_id: FollowTask}
_tasks: Dict[str, FollowTask] = {}

# Leader -> Relations 索引
_leader_relations: Dict[int, List[int]] = {}


# ============== Middleware ==============

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or gen_id("req_")
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


# ============== Endpoints ==============

@app.get("/health")
def health():
    return {"status": "ok", "service": service_name}


@app.post("/api/relations")
def create_relation(req: CreateRelationRequest):
    """创建跟单关系"""
    global _relation_counter
    _relation_counter += 1
    relation_id = _relation_counter
    
    relation = FollowRelation(
        relation_id=relation_id,
        leader_id=req.leader_id,
        follower_id=req.follower_id,
        follower_account_id=req.follower_account_id,
        follow_mode=req.follow_mode,
        follow_value=req.follow_value,
        platform=req.platform,
        exchange=req.exchange,
        enabled=True,
    )
    
    _relations[relation_id] = relation
    
    # 更新索引
    if req.leader_id not in _leader_relations:
        _leader_relations[req.leader_id] = []
    _leader_relations[req.leader_id].append(relation_id)
    
    logger.info(
        "relation created",
        relation_id=relation_id,
        leader_id=req.leader_id,
        follower_id=req.follower_id,
    )
    
    return {"relation_id": relation_id, "relation": relation.dict()}


@app.get("/api/relations")
def list_relations(leader_id: Optional[int] = None):
    """列出跟单关系"""
    if leader_id is not None:
        relation_ids = _leader_relations.get(leader_id, [])
        relations = [_relations[rid].dict() for rid in relation_ids if rid in _relations]
    else:
        relations = [r.dict() for r in _relations.values()]
    return {"relations": relations}


@app.delete("/api/relations/{relation_id}")
def delete_relation(relation_id: int):
    """删除跟单关系"""
    if relation_id not in _relations:
        raise HTTPException(status_code=404, detail="Relation not found")
    
    relation = _relations.pop(relation_id)
    
    # 更新索引
    if relation.leader_id in _leader_relations:
        _leader_relations[relation.leader_id] = [
            rid for rid in _leader_relations[relation.leader_id] if rid != relation_id
        ]
    
    logger.info("relation deleted", relation_id=relation_id)
    return {"deleted": True}


@app.post("/api/broadcast", response_model=BroadcastResponse)
async def broadcast_signal(req: BroadcastRequest, request: Request):
    """
    广播信号给所有 Follower
    
    1. 查找 Leader 的所有 Follower
    2. 为每个 Follower 创建 FollowTask
    3. 调用 dispatcher 执行
    """
    request_id = request.state.request_id
    leader_id = req.leader_id
    signal = req.signal
    
    # 获取该 Leader 的所有跟单关系
    relation_ids = _leader_relations.get(leader_id, [])
    if not relation_ids:
        logger.info(
            "no followers",
            request_id=request_id,
            leader_id=leader_id,
            signal_id=signal.signal_id,
        )
        return BroadcastResponse(
            signal_id=signal.signal_id,
            tasks_created=0,
            tasks=[],
        )
    
    tasks = []
    for rid in relation_ids:
        relation = _relations.get(rid)
        if not relation or not relation.enabled:
            continue
        
        # 计算跟单数量
        quantity = calculate_follow_quantity(
            mode=relation.follow_mode,
            value=relation.follow_value,
            leader_quantity=signal.quantity or 0.01,
            entry_price=signal.entry_price or 0,
        )
        
        # 创建 FollowTask
        task = FollowTask(
            task_id=gen_id("ftask_"),
            signal_id=signal.signal_id,
            leader_id=leader_id,
            relation_id=rid,
            follower_id=relation.follower_id,
            follower_account_id=relation.follower_account_id,
            follow_mode=relation.follow_mode,
            follow_value=relation.follow_value,
            symbol=signal.symbol,
            side=signal.side,
            quantity=quantity,
            status="queued",
        )
        
        _tasks[task.task_id] = task
        
        # 提交到 dispatcher
        try:
            result = await submit_to_dispatcher(
                task=task,
                relation=relation,
                signal=signal,
                request_id=request_id,
            )
            # dispatcher v0 返回 task_id，无 success 字段
            task.status = "submitted" if result.get("task_id") else "failed"
        except Exception as e:
            logger.error(
                "dispatch failed",
                request_id=request_id,
                task_id=task.task_id,
                error=str(e),
            )
            task.status = "failed"
        
        tasks.append(asdict(task))
    
    logger.info(
        "broadcast completed",
        request_id=request_id,
        leader_id=leader_id,
        signal_id=signal.signal_id,
        tasks_created=len(tasks),
    )
    
    return BroadcastResponse(
        signal_id=signal.signal_id,
        tasks_created=len(tasks),
        tasks=tasks,
    )


@app.get("/api/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    """查询跟单任务状态"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = _tasks[task_id]
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        order_id=None,  # v0 暂不跟踪
        error=None,
    )


# ============== Helper Functions ==============

def calculate_follow_quantity(
    mode: str,
    value: float,
    leader_quantity: float,
    entry_price: float,
) -> float:
    """
    计算跟单数量
    
    Args:
        mode: ratio / fixed_amount / fixed_quantity
        value: 跟单值
        leader_quantity: Leader 下单数量
        entry_price: 入场价
    
    Returns:
        计算后的数量
    """
    if mode == "ratio":
        # 按比例跟单
        return round(leader_quantity * value, 8)
    elif mode == "fixed_amount":
        # 固定金额
        if entry_price > 0:
            return round(value / entry_price, 8)
        return 0.01
    elif mode == "fixed_quantity":
        # 固定数量
        return value
    else:
        return 0.01


async def submit_to_dispatcher(
    task: FollowTask,
    relation: FollowRelation,
    signal: SignalModel,
    request_id: str,
) -> dict:
    """
    提交跟单任务到 execution-dispatcher
    """
    payload = {
        "signal_id": task.signal_id,
        "account_id": relation.follower_account_id,
        "member_id": relation.follower_id,
        "platform": relation.platform,
        "exchange": relation.exchange,
        "symbol": task.symbol,
        "side": task.side,
        "order_type": "MARKET",
        "quantity": task.quantity,
        "price": signal.entry_price,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{DISPATCHER_URL}/api/execution/submit",
            json=payload,
            headers={"X-Request-Id": request_id},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()
