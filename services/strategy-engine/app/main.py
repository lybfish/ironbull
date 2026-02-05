"""
Strategy Engine Service

最小实现：
- 手动触发策略分析
- 输出 StrategyOutput
- POST 到 signal-hub
"""

import httpx
from dataclasses import asdict
from typing import Optional, List

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from libs.core import get_config, get_logger, setup_logging, gen_id, AppError
from libs.contracts import StrategyOutput
from libs.strategies import get_strategy, STRATEGY_REGISTRY


class CandleModel(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: float = 0
    timestamp: int = 0


class AnalyzeRequest(BaseModel):
    """手动触发分析请求（带 K 线数据）"""
    strategy_code: str
    symbol: str
    timeframe: str
    candles: List[CandleModel]
    config: Optional[dict] = None
    auto_submit: bool = True  # 是否自动提交到 signal-hub


class RunRequest(BaseModel):
    """自动获取数据并分析（从 data-provider）"""
    strategy_code: str
    symbol: str
    timeframe: str = "15m"
    limit: int = 100  # K 线数量
    config: Optional[dict] = None
    auto_submit: bool = True


class AnalyzeResponse(BaseModel):
    has_signal: bool
    strategy_output: Optional[dict] = None
    submitted: bool = False
    signal_id: Optional[str] = None
    error: Optional[str] = None


config = get_config()
service_name = "strategy-engine"
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name=service_name,
)
logger = get_logger(service_name)

app = FastAPI(title="strategy-engine")

# 服务 URL
SIGNAL_HUB_URL = config.get_str("signal_hub_url", "http://127.0.0.1:8001")
DATA_PROVIDER_URL = config.get_str("data_provider_url", "http://127.0.0.1:8005")


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


@app.get("/api/strategies")
def list_strategies():
    """列出所有可用策略"""
    strategies = []
    for code, cls in STRATEGY_REGISTRY.items():
        instance = cls()
        strategies.append({
            "code": code,
            "name": instance.name,
            "version": instance.version,
        })
    return {"strategies": strategies}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest, request: Request):
    """
    手动触发策略分析
    
    1. 加载策略
    2. 执行 analyze()
    3. 如果有信号且 auto_submit=True，POST 到 signal-hub
    """
    request_id = request.state.request_id
    
    # 1. 获取策略
    try:
        strategy = get_strategy(req.strategy_code, req.config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # 2. 转换 candles
    candles = [c.dict() for c in req.candles]
    
    logger.info(
        "analyze started",
        request_id=request_id,
        strategy_code=req.strategy_code,
        symbol=req.symbol,
        timeframe=req.timeframe,
        candles_count=len(candles),
    )
    
    # 3. 执行分析
    output: Optional[StrategyOutput] = strategy.analyze(
        symbol=req.symbol,
        timeframe=req.timeframe,
        candles=candles,
    )
    
    if output is None:
        logger.info(
            "no signal",
            request_id=request_id,
            strategy_code=req.strategy_code,
            symbol=req.symbol,
        )
        return AnalyzeResponse(has_signal=False)
    
    logger.info(
        "signal generated",
        request_id=request_id,
        strategy_code=req.strategy_code,
        symbol=req.symbol,
        side=output.side,
        signal_type=output.signal_type,
    )
    
    output_dict = asdict(output)
    
    # 4. 提交到 signal-hub
    if req.auto_submit:
        try:
            signal_id = await submit_to_signal_hub(
                strategy_code=req.strategy_code,
                timeframe=req.timeframe,
                output=output,
                request_id=request_id,
            )
            logger.info(
                "signal submitted",
                request_id=request_id,
                signal_id=signal_id,
            )
            return AnalyzeResponse(
                has_signal=True,
                strategy_output=output_dict,
                submitted=True,
                signal_id=signal_id,
            )
        except Exception as e:
            logger.error(
                "submit failed",
                request_id=request_id,
                error=str(e),
            )
            return AnalyzeResponse(
                has_signal=True,
                strategy_output=output_dict,
                submitted=False,
                error=str(e),
            )
    
    return AnalyzeResponse(
        has_signal=True,
        strategy_output=output_dict,
        submitted=False,
    )


@app.post("/api/run", response_model=AnalyzeResponse)
async def run_strategy(req: RunRequest, request: Request):
    """
    自动获取数据并运行策略
    
    1. 从 data-provider 获取 K 线
    2. 执行策略分析
    3. 提交到 signal-hub
    """
    request_id = request.state.request_id
    
    # 1. 获取策略
    try:
        strategy = get_strategy(req.strategy_code, req.config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # 2. 从 data-provider 获取 K 线
    try:
        candles = await fetch_candles_from_provider(
            req.symbol, req.timeframe, req.limit, request_id
        )
    except Exception as e:
        logger.error(
            "fetch candles failed",
            request_id=request_id,
            error=str(e),
        )
        raise HTTPException(status_code=502, detail=f"Failed to fetch candles: {e}")
    
    logger.info(
        "run started",
        request_id=request_id,
        strategy_code=req.strategy_code,
        symbol=req.symbol,
        timeframe=req.timeframe,
        candles_count=len(candles),
    )
    
    # 3. 执行分析
    output: Optional[StrategyOutput] = strategy.analyze(
        symbol=req.symbol,
        timeframe=req.timeframe,
        candles=candles,
    )
    
    if output is None:
        logger.info(
            "no signal",
            request_id=request_id,
            strategy_code=req.strategy_code,
            symbol=req.symbol,
        )
        return AnalyzeResponse(has_signal=False)
    
    logger.info(
        "signal generated",
        request_id=request_id,
        strategy_code=req.strategy_code,
        symbol=req.symbol,
        side=output.side,
        signal_type=output.signal_type,
    )
    
    output_dict = asdict(output)
    
    # 4. 提交到 signal-hub
    if req.auto_submit:
        try:
            signal_id = await submit_to_signal_hub(
                strategy_code=req.strategy_code,
                timeframe=req.timeframe,
                output=output,
                request_id=request_id,
            )
            logger.info(
                "signal submitted",
                request_id=request_id,
                signal_id=signal_id,
            )
            return AnalyzeResponse(
                has_signal=True,
                strategy_output=output_dict,
                submitted=True,
                signal_id=signal_id,
            )
        except Exception as e:
            logger.error(
                "submit failed",
                request_id=request_id,
                error=str(e),
            )
            return AnalyzeResponse(
                has_signal=True,
                strategy_output=output_dict,
                submitted=False,
                error=str(e),
            )
    
    return AnalyzeResponse(
        has_signal=True,
        strategy_output=output_dict,
        submitted=False,
    )


async def fetch_candles_from_provider(
    symbol: str,
    timeframe: str,
    limit: int,
    request_id: str,
) -> List[dict]:
    """
    从 data-provider 获取 K 线数据
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{DATA_PROVIDER_URL}/api/candles",
            params={"symbol": symbol, "timeframe": timeframe, "limit": limit},
            headers={"X-Request-Id": request_id},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candles"]


async def submit_to_signal_hub(
    strategy_code: str,
    timeframe: str,
    output: StrategyOutput,
    request_id: str,
) -> str:
    """
    提交 StrategyOutput 到 signal-hub
    
    Returns:
        signal_id
    """
    payload = {
        "strategy_code": strategy_code,
        "timeframe": timeframe,
        "strategy_output": {
            "symbol": output.symbol,
            "signal_type": output.signal_type,
            "side": output.side,
            "entry_price": output.entry_price,
            "stop_loss": output.stop_loss,
            "take_profit": output.take_profit,
            "confidence": output.confidence,
            "reason": output.reason,
            "indicators": output.indicators,
            "bar_data": output.bar_data,
        },
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SIGNAL_HUB_URL}/api/signals",
            json=payload,
            headers={"X-Request-Id": request_id},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["signal"]["signal_id"]
