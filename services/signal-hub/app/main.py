from dataclasses import asdict
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from libs.contracts import StrategyOutput, Signal
from libs.core import get_config, get_logger, setup_logging, gen_id, AppError
from .signal_standard import standardize_signal
from .signal_service import SignalService

# v1 Facts Layer (可选，失败不阻塞主流程)
try:
    from libs.facts import FactsRepository, AuditAction, SignalStatus
    FACTS_ENABLED = True
except ImportError:
    FACTS_ENABLED = False


class StrategyOutputModel(BaseModel):
    symbol: str
    signal_type: str
    side: Optional[str] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    indicators: Optional[dict] = None
    bar_data: Optional[dict] = None


class CreateSignalRequest(BaseModel):
    strategy_code: str
    timeframe: str
    strategy_output: StrategyOutputModel


class CreateSignalResponse(BaseModel):
    signal: dict


config = get_config()
service_name = "signal-hub"
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name=service_name,
)
logger = get_logger(service_name)

app = FastAPI(title="signal-hub")
service = SignalService()


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


@app.post("/api/signals", response_model=CreateSignalResponse)
def create_signal(req: CreateSignalRequest, request: Request):
    output = StrategyOutput(**req.strategy_output.dict())
    signal = standardize_signal(output, req.strategy_code, req.timeframe)
    service.create_signal(signal)
    
    # v1: 记录信号创建事件 + 审计日志（失败不阻塞）
    if FACTS_ENABLED:
        try:
            repo = FactsRepository()
            # 信号事件
            repo.create_signal_event(
                signal_id=signal.signal_id,
                event_type="CREATED",
                status=SignalStatus.PENDING.value,
                source_service="signal-hub",
                detail={
                    "strategy_code": signal.strategy_code,
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "signal_type": signal.signal_type,
                    "entry_price": signal.entry_price,
                    "confidence": signal.confidence,
                },
                request_id=request.state.request_id,
            )
            # 审计日志
            repo.create_audit_log(
                action=AuditAction.SIGNAL_CREATED.value,
                source_service="signal-hub",
                signal_id=signal.signal_id,
                status_before=None,
                status_after=SignalStatus.PENDING.value,
                detail={
                    "strategy_code": signal.strategy_code,
                    "symbol": signal.symbol,
                    "side": signal.side,
                },
                request_id=request.state.request_id,
            )
        except Exception as e:
            logger.warning("facts layer write failed", error=str(e))
    
    logger.info(
        "signal created",
        request_id=request.state.request_id,
        signal_id=signal.signal_id,
        strategy_code=signal.strategy_code,
    )
    return {"signal": asdict(signal)}


@app.get("/api/signals/{signal_id}")
def get_signal(signal_id: str):
    """获取信号详情"""
    signal = service.get_signal(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return {"signal": asdict(signal)}


@app.get("/api/signals/{signal_id}/chain")
def get_signal_chain(signal_id: str):
    """
    v1: 获取信号完整链路
    
    返回信号在整个执行链路中的所有事件、交易记录和账本流水
    """
    if not FACTS_ENABLED:
        raise HTTPException(status_code=501, detail="Facts layer not enabled")
    
    try:
        repo = FactsRepository()
        chain = repo.get_full_signal_chain(signal_id)
        return chain
    except Exception as e:
        logger.error("get signal chain failed", signal_id=signal_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/signals/{signal_id}/audit")
def get_signal_audit(signal_id: str):
    """
    v1 Phase 2: 获取信号完整链路（包含审计日志）
    
    返回：events + trades + ledgers + audit_logs
    """
    if not FACTS_ENABLED:
        raise HTTPException(status_code=501, detail="Facts layer not enabled")
    
    try:
        repo = FactsRepository()
        chain = repo.get_full_signal_chain_with_audit(signal_id)
        return chain
    except Exception as e:
        logger.error("get signal audit failed", signal_id=signal_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
