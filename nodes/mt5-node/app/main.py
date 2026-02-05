from dataclasses import asdict
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from libs.contracts import NodeTask, NodeResult
from libs.core import get_config, get_logger, setup_logging, gen_id, time_now, AppError


class NodeTaskModel(BaseModel):
    task_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    api_key: str = ""
    api_secret: str = ""
    passphrase: Optional[str] = None
    exchange: str = ""
    timeout_ms: int = 30000


class NodeResultResponse(BaseModel):
    result: dict


config = get_config()
service_name = "mt5-node"
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name=service_name,
)
logger = get_logger(service_name)

app = FastAPI(title="mt5-node")


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
    return {"status": "ok", "service": service_name}


@app.post("/api/node/execute", response_model=NodeResultResponse)
def execute(task: NodeTaskModel, request: Request):
    node_task = NodeTask(**task.dict())
    result = NodeResult(
        task_id=node_task.task_id,
        success=True,
        exchange_order_id=f"mock_{node_task.task_id}",
        filled_price=node_task.price,
        filled_quantity=node_task.quantity,
        executed_at=time_now(),
        execution_ms=1,
    )

    logger.info(
        "node executed",
        request_id=request.state.request_id,
        task_id=node_task.task_id,
        exchange=node_task.exchange,
    )

    return {"result": asdict(result)}
