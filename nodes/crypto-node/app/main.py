from dataclasses import asdict
from typing import Optional, Dict, Any
import asyncio

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from libs.contracts import NodeTask, NodeResult
from libs.core import get_config, get_logger, setup_logging, gen_id, time_now, AppError
from libs.trading import LiveTrader, PaperTrader, OrderSide, OrderType, OrderStatus


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
    exchange: str = "binance"
    timeout_ms: int = 30000


class NodeResultResponse(BaseModel):
    result: dict


class BalanceRequest(BaseModel):
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None
    exchange: str = "binance"
    asset: Optional[str] = None


config = get_config()
service_name = "crypto-node"
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name=service_name,
)
logger = get_logger(service_name)

# 交易模式: live / paper
TRADING_MODE = config.get_str("trading_mode", "paper")

# 模拟交易器（单例）
_paper_trader: Optional[PaperTrader] = None

def get_paper_trader() -> PaperTrader:
    """获取模拟交易器"""
    global _paper_trader
    if _paper_trader is None:
        _paper_trader = PaperTrader(
            initial_balance={"USDT": 10000, "BTC": 0, "ETH": 0},
            commission_rate=0.001,
        )
    return _paper_trader


app = FastAPI(title="crypto-node")


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
    return {
        "status": "ok",
        "service": service_name,
        "trading_mode": TRADING_MODE,
        "supported_exchanges": LiveTrader.SUPPORTED_EXCHANGES,
    }


@app.post("/api/node/execute", response_model=NodeResultResponse)
async def execute(task: NodeTaskModel, request: Request):
    """
    执行交易任务
    
    支持两种模式：
    - paper: 模拟交易（默认，不需要 API Key）
    - live: 真实交易（需要 API Key）
    """
    node_task = NodeTask(**task.dict())
    request_id = request.state.request_id
    
    # 确定交易模式
    use_live = TRADING_MODE == "live" and task.api_key and task.api_secret
    
    import time
    start_time = time.time()
    
    try:
        # 解析订单参数
        side = OrderSide.BUY if task.side.upper() == "BUY" else OrderSide.SELL
        order_type = OrderType.MARKET if task.order_type.upper() == "MARKET" else OrderType.LIMIT
        
        if use_live:
            # 真实交易
            trader = LiveTrader(
                exchange=task.exchange or "binance",
                api_key=task.api_key,
                api_secret=task.api_secret,
                passphrase=task.passphrase,
            )
            
            try:
                order_result = await trader.create_order(
                    symbol=task.symbol,
                    side=side,
                    order_type=order_type,
                    quantity=task.quantity,
                    price=task.price,
                )
            finally:
                await trader.close()
        else:
            # 模拟交易
            trader = get_paper_trader()
            
            # 如果有价格，设置模拟价格
            if task.price:
                trader.set_price(task.symbol, task.price)
            
            order_result = await trader.create_order(
                symbol=task.symbol,
                side=side,
                order_type=order_type,
                quantity=task.quantity,
                price=task.price,
            )
        
        end_time = time.time()
        execution_ms = int((end_time - start_time) * 1000)
        
        # 构建 NodeResult
        result = NodeResult(
            task_id=node_task.task_id,
            success=order_result.is_success,
            exchange_order_id=order_result.exchange_order_id or "",
            filled_price=order_result.filled_price,
            filled_quantity=order_result.filled_quantity,
            executed_at=time_now(),
            execution_ms=execution_ms,
            error_code=order_result.error_code,
            error_message=order_result.error_message,
        )
        
        logger.info(
            "node executed",
            request_id=request_id,
            task_id=node_task.task_id,
            exchange=node_task.exchange,
            mode="live" if use_live else "paper",
            success=result.success,
            order_id=order_result.exchange_order_id,
            filled_price=order_result.filled_price,
            execution_ms=execution_ms,
        )
        
        return {"result": asdict(result)}
        
    except Exception as e:
        logger.error(
            "node execution failed",
            request_id=request_id,
            task_id=node_task.task_id,
            error=str(e),
        )
        
        result = NodeResult(
            task_id=node_task.task_id,
            success=False,
            exchange_order_id="",
            filled_price=0,
            filled_quantity=0,
            executed_at=time_now(),
            execution_ms=0,
            error_code="EXECUTION_ERROR",
            error_message=str(e),
        )
        
        return {"result": asdict(result)}


@app.post("/api/node/balance")
async def get_balance(req: BalanceRequest, request: Request):
    """
    查询账户余额
    
    - paper 模式: 返回模拟余额
    - live 模式: 查询真实余额
    """
    use_live = TRADING_MODE == "live" and req.api_key and req.api_secret
    
    try:
        if use_live:
            trader = LiveTrader(
                exchange=req.exchange,
                api_key=req.api_key,
                api_secret=req.api_secret,
                passphrase=req.passphrase,
            )
            
            try:
                balances = await trader.get_balance(req.asset)
            finally:
                await trader.close()
        else:
            trader = get_paper_trader()
            balances = await trader.get_balance(req.asset)
        
        return {
            "mode": "live" if use_live else "paper",
            "balances": {
                k: {"asset": v.asset, "free": v.free, "locked": v.locked, "total": v.total}
                for k, v in balances.items()
            },
        }
        
    except Exception as e:
        logger.error("get balance failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/node/paper/balance")
async def get_paper_balance():
    """查询模拟账户余额"""
    trader = get_paper_trader()
    balances = await trader.get_balance()
    
    return {
        "mode": "paper",
        "balances": {
            k: {"asset": v.asset, "free": v.free, "locked": v.locked, "total": v.total}
            for k, v in balances.items()
        },
    }


@app.post("/api/node/paper/reset")
async def reset_paper_balance(balance: Dict[str, float] = None):
    """重置模拟账户余额"""
    global _paper_trader
    _paper_trader = PaperTrader(
        initial_balance=balance or {"USDT": 10000, "BTC": 0, "ETH": 0},
        commission_rate=0.001,
    )
    
    return {"status": "ok", "message": "Paper balance reset"}
