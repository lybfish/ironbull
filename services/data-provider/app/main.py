"""
Data Provider Service

提供 K 线数据和宏观事件数据的统一接口。

支持两种数据源模式：
- mock: Mock 数据（默认，用于测试）
- live: 真实交易所数据（通过 ccxt）

端点：
- GET /api/candles?symbol=...&timeframe=...&limit=...
- GET /api/mtf/candles?symbol=...&timeframes=...&limit=...
- GET /api/macro/events?from=...&to=...
- GET /api/exchanges - 列出支持的交易所
- GET /api/ticker?symbol=... - 获取最新行情
- WS /ws - WebSocket 实时行情推送
"""

import time
import math
import random
import asyncio
from typing import List, Optional, Dict, Any, Set

from fastapi import FastAPI, Request, Query, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from libs.core import get_config, get_logger, setup_logging, gen_id, AppError

# v1 Phase 5: 交易所数据接入
try:
    from libs.exchange import create_client, list_supported_exchanges, ExchangeClient
    EXCHANGE_AVAILABLE = True
except ImportError:
    EXCHANGE_AVAILABLE = False

# v1 Phase 5: 数据缓存
try:
    from libs.core import init_redis, check_redis_connection
    from libs.cache import CandleCache, TickerCache, CachedCandle, CachedTicker, get_candle_cache, get_ticker_cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

# v1 Phase 7: WebSocket 实时推送
try:
    from libs.ws import ConnectionManager, TickerStream, get_connection_manager, get_ticker_stream
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False


class Candle(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class CandlesResponse(BaseModel):
    symbol: str
    timeframe: str
    candles: List[Candle]


class MTFCandlesResponse(BaseModel):
    symbol: str
    timeframes: dict  # {timeframe: [candles]}


class MacroEvent(BaseModel):
    event_id: str
    timestamp: int
    event_type: str  # interest_rate, gdp, cpi, employment, etc.
    country: str
    title: str
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    impact: str  # high, medium, low


class MacroEventsResponse(BaseModel):
    events: List[MacroEvent]


config = get_config()
service_name = "data-provider"
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name=service_name,
)
logger = get_logger(service_name)

app = FastAPI(title="data-provider")

# 数据源模式: mock / live
DATA_SOURCE = config.get_str("data_source", "mock")
DEFAULT_EXCHANGE = config.get_str("default_exchange", "binance")
CACHE_ENABLED = config.get_bool("data_cache_enabled", True)

# 初始化 Redis 缓存
if CACHE_AVAILABLE and CACHE_ENABLED:
    try:
        init_redis()
        if check_redis_connection():
            logger.info("redis cache initialized")
        else:
            logger.warning("redis not available, cache disabled")
            CACHE_ENABLED = False
    except Exception as e:
        logger.warning("redis init failed", error=str(e))
        CACHE_ENABLED = False

# 交易所客户端缓存
_exchange_clients: Dict[str, ExchangeClient] = {}


def get_exchange_client(exchange: str = None) -> Optional[ExchangeClient]:
    """获取或创建交易所客户端"""
    if not EXCHANGE_AVAILABLE:
        return None
    
    exchange = exchange or DEFAULT_EXCHANGE
    
    if exchange not in _exchange_clients:
        try:
            _exchange_clients[exchange] = create_client(exchange)
            logger.info("exchange client created", exchange=exchange)
        except Exception as e:
            logger.error("failed to create exchange client", exchange=exchange, error=str(e))
            return None
    
    return _exchange_clients[exchange]


# 时间周期 -> 秒数
TIMEFRAME_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


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
        "data_source": DATA_SOURCE,
        "exchange_available": EXCHANGE_AVAILABLE,
        "default_exchange": DEFAULT_EXCHANGE,
        "cache_enabled": CACHE_ENABLED and CACHE_AVAILABLE,
        "websocket_available": WS_AVAILABLE,
    }


@app.get("/api/candles", response_model=CandlesResponse)
async def get_candles(
    request: Request,
    symbol: str = Query(..., description="交易对，如 BTCUSDT 或 BTC/USDT"),
    timeframe: str = Query("15m", description="时间周期，如 1m/5m/15m/1h/4h/1d"),
    limit: int = Query(100, ge=1, le=1000, description="K线数量"),
    exchange: str = Query(None, description="交易所（可选，默认使用配置）"),
    source: str = Query(None, description="数据源: mock/live（可选，默认使用配置）"),
    no_cache: bool = Query(False, description="是否跳过缓存"),
):
    """
    获取 K 线数据
    
    支持两种数据源：
    - mock: 返回模拟数据（用于测试）
    - live: 从交易所获取真实数据（支持缓存）
    """
    request_id = request.state.request_id
    use_source = source or DATA_SOURCE
    use_exchange = exchange or DEFAULT_EXCHANGE
    
    if timeframe not in TIMEFRAME_SECONDS:
        timeframe = "15m"
    
    candles = []
    cache_hit = False
    
    if use_source == "live" and EXCHANGE_AVAILABLE:
        # 1. 尝试从缓存获取
        if CACHE_ENABLED and CACHE_AVAILABLE and not no_cache:
            cache = get_candle_cache()
            cached = cache.get(symbol, timeframe, limit, use_exchange)
            if cached and len(cached) >= limit * 0.8:  # 缓存命中率 >= 80%
                candles = [
                    Candle(
                        timestamp=c.timestamp,
                        open=c.open,
                        high=c.high,
                        low=c.low,
                        close=c.close,
                        volume=c.volume,
                    )
                    for c in cached[-limit:]
                ]
                cache_hit = True
                logger.info(
                    "candles from cache",
                    request_id=request_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    count=len(candles),
                )
        
        # 2. 缓存未命中，从交易所获取
        if not candles:
            client = get_exchange_client(use_exchange)
            if client:
                try:
                    ohlcv_list = await client.fetch_ohlcv(symbol, timeframe, limit)
                    candles = [
                        Candle(
                            timestamp=ohlcv.timestamp // 1000,
                            open=ohlcv.open,
                            high=ohlcv.high,
                            low=ohlcv.low,
                            close=ohlcv.close,
                            volume=ohlcv.volume,
                        )
                        for ohlcv in ohlcv_list
                    ]
                    
                    # 3. 写入缓存
                    if CACHE_ENABLED and CACHE_AVAILABLE and candles:
                        cache = get_candle_cache()
                        cached_candles = [
                            CachedCandle(
                                timestamp=c.timestamp,
                                open=c.open,
                                high=c.high,
                                low=c.low,
                                close=c.close,
                                volume=c.volume,
                            )
                            for c in candles
                        ]
                        cache.set(symbol, timeframe, cached_candles, use_exchange)
                    
                    logger.info(
                        "live candles fetched",
                        request_id=request_id,
                        symbol=symbol,
                        timeframe=timeframe,
                        exchange=use_exchange,
                        count=len(candles),
                    )
                except Exception as e:
                    logger.warning(
                        "live data fetch failed, falling back to mock",
                        error=str(e),
                        symbol=symbol,
                    )
                    candles = generate_mock_candles(symbol, timeframe, limit)
            else:
                candles = generate_mock_candles(symbol, timeframe, limit)
    else:
        # 使用 mock 数据
        candles = generate_mock_candles(symbol, timeframe, limit)
        logger.info(
            "mock candles generated",
            request_id=request_id,
            symbol=symbol,
            timeframe=timeframe,
            count=len(candles),
        )
    
    return CandlesResponse(
        symbol=symbol,
        timeframe=timeframe,
        candles=candles,
    )


@app.get("/api/mtf/candles", response_model=MTFCandlesResponse)
def get_mtf_candles(
    request: Request,
    symbol: str = Query(..., description="交易对"),
    timeframes: str = Query("15m,1h,4h", description="时间周期列表，逗号分隔"),
    limit: int = Query(100, ge=1, le=500, description="每个周期的 K线数量"),
):
    """
    获取多时间周期 K 线数据
    
    v0: 从 1m mock 数据聚合生成
    """
    request_id = request.state.request_id
    
    tf_list = [tf.strip() for tf in timeframes.split(",")]
    result = {}
    
    for tf in tf_list:
        if tf not in TIMEFRAME_SECONDS:
            continue
        candles = generate_mock_candles(symbol, tf, limit)
        result[tf] = [c.dict() for c in candles]
    
    logger.info(
        "mtf candles fetched",
        request_id=request_id,
        symbol=symbol,
        timeframes=tf_list,
        counts={tf: len(result.get(tf, [])) for tf in tf_list},
    )
    
    return MTFCandlesResponse(symbol=symbol, timeframes=result)


@app.get("/api/macro/events", response_model=MacroEventsResponse)
def get_macro_events(
    request: Request,
    from_ts: int = Query(None, alias="from", description="开始时间戳"),
    to_ts: int = Query(None, alias="to", description="结束时间戳"),
    country: str = Query(None, description="国家代码，如 US/EU/JP"),
    impact: str = Query(None, description="影响级别，如 high/medium/low"),
):
    """
    获取宏观经济事件
    
    v0: 返回 mock 事件数据
    """
    request_id = request.state.request_id
    
    now = int(time.time())
    if from_ts is None:
        from_ts = now - 86400 * 7  # 默认过去 7 天
    if to_ts is None:
        to_ts = now + 86400 * 7  # 默认未来 7 天
    
    events = generate_mock_macro_events(from_ts, to_ts, country, impact)
    
    logger.info(
        "macro events fetched",
        request_id=request_id,
        from_ts=from_ts,
        to_ts=to_ts,
        count=len(events),
    )
    
    return MacroEventsResponse(events=events)


def generate_mock_candles(symbol: str, timeframe: str, limit: int) -> List[Candle]:
    """
    生成 mock K 线数据
    
    基于 symbol 生成稳定的伪随机序列，保证同一 symbol 返回一致的数据。
    """
    # 根据 symbol 确定基础价格
    base_prices = {
        "BTCUSDT": 42000,
        "ETHUSDT": 2500,
        "XAUUSD": 2000,
        "EURUSD": 1.08,
    }
    base_price = base_prices.get(symbol, 100)
    
    # 根据 symbol 生成稳定的随机种子
    seed = sum(ord(c) for c in symbol)
    rng = random.Random(seed)
    
    interval = TIMEFRAME_SECONDS.get(timeframe, 900)
    now = int(time.time())
    # 对齐到时间周期
    aligned_now = (now // interval) * interval
    
    candles = []
    price = base_price
    
    for i in range(limit):
        ts = aligned_now - (limit - 1 - i) * interval
        
        # 生成 OHLC
        volatility = base_price * 0.005  # 0.5% 波动
        change = rng.gauss(0, volatility)
        
        open_price = price
        close_price = price + change
        high_price = max(open_price, close_price) + abs(rng.gauss(0, volatility * 0.5))
        low_price = min(open_price, close_price) - abs(rng.gauss(0, volatility * 0.5))
        
        volume = rng.uniform(1000, 5000) * (base_price / 100)
        
        candles.append(Candle(
            timestamp=ts,
            open=round(open_price, 8),
            high=round(high_price, 8),
            low=round(low_price, 8),
            close=round(close_price, 8),
            volume=round(volume, 2),
        ))
        
        price = close_price
    
    return candles


def generate_mock_macro_events(
    from_ts: int,
    to_ts: int,
    country: Optional[str],
    impact: Optional[str],
) -> List[MacroEvent]:
    """
    生成 mock 宏观事件数据
    """
    event_templates = [
        ("US", "interest_rate", "Fed Interest Rate Decision", "high"),
        ("US", "employment", "Non-Farm Payrolls", "high"),
        ("US", "cpi", "CPI (YoY)", "high"),
        ("US", "gdp", "GDP Growth Rate (QoQ)", "medium"),
        ("EU", "interest_rate", "ECB Interest Rate Decision", "high"),
        ("EU", "cpi", "Eurozone CPI (YoY)", "medium"),
        ("JP", "interest_rate", "BoJ Interest Rate Decision", "high"),
        ("JP", "gdp", "Japan GDP (QoQ)", "medium"),
        ("CN", "cpi", "China CPI (YoY)", "medium"),
        ("CN", "pmi", "China Manufacturing PMI", "medium"),
    ]
    
    events = []
    rng = random.Random(42)  # 固定种子保证稳定
    
    # 每天生成 2-3 个事件
    days = (to_ts - from_ts) // 86400
    for day in range(max(1, days)):
        day_ts = from_ts + day * 86400
        num_events = rng.randint(2, 3)
        
        for _ in range(num_events):
            template = rng.choice(event_templates)
            ev_country, ev_type, ev_title, ev_impact = template
            
            # 过滤条件
            if country and ev_country != country:
                continue
            if impact and ev_impact != impact:
                continue
            
            event_ts = day_ts + rng.randint(0, 86400)
            if event_ts < from_ts or event_ts > to_ts:
                continue
            
            actual = round(rng.uniform(-2, 5), 2) if rng.random() > 0.3 else None
            forecast = round(rng.uniform(-2, 5), 2)
            previous = round(rng.uniform(-2, 5), 2)
            
            events.append(MacroEvent(
                event_id=gen_id("ev_"),
                timestamp=event_ts,
                event_type=ev_type,
                country=ev_country,
                title=ev_title,
                actual=actual,
                forecast=forecast,
                previous=previous,
                impact=ev_impact,
            ))
    
    # 按时间排序
    events.sort(key=lambda e: e.timestamp)
    
    return events


# ========== v1 Phase 5: 真实数据 API ==========

@app.get("/api/exchanges")
def list_exchanges():
    """列出支持的交易所"""
    exchanges = list_supported_exchanges() if EXCHANGE_AVAILABLE else []
    return {
        "exchanges": exchanges,
        "default": DEFAULT_EXCHANGE,
        "exchange_available": EXCHANGE_AVAILABLE,
    }


class TickerResponse(BaseModel):
    symbol: str
    last: float
    bid: float
    ask: float
    volume_24h: float
    timestamp: int
    exchange: str


@app.get("/api/ticker", response_model=TickerResponse)
async def get_ticker(
    request: Request,
    symbol: str = Query(..., description="交易对，如 BTC/USDT"),
    exchange: str = Query(None, description="交易所（可选）"),
):
    """
    获取最新行情
    
    仅在 live 模式下可用
    """
    if not EXCHANGE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Exchange module not available")
    
    client = get_exchange_client(exchange)
    if not client:
        raise HTTPException(status_code=503, detail="Failed to create exchange client")
    
    try:
        ticker = await client.fetch_ticker(symbol)
        # 处理 timestamp：可能为 None 或毫秒时间戳
        ticker_timestamp = ticker.timestamp
        if ticker_timestamp is None:
            import time
            ticker_timestamp = int(time.time() * 1000)  # 使用当前时间
        elif ticker_timestamp > 1e10:  # 如果是毫秒时间戳（> 10位数字）
            ticker_timestamp = ticker_timestamp // 1000  # 转换为秒
        # 如果已经是秒级时间戳，直接使用
        
        return TickerResponse(
            symbol=ticker.symbol,
            last=ticker.last,
            bid=ticker.bid,
            ask=ticker.ask,
            volume_24h=ticker.volume_24h,
            timestamp=int(ticker_timestamp),
            exchange=exchange or DEFAULT_EXCHANGE,
        )
    except Exception as e:
        logger.error("ticker fetch failed", symbol=symbol, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/source")
def get_data_source():
    """获取当前数据源配置"""
    return {
        "source": DATA_SOURCE,
        "exchange_available": EXCHANGE_AVAILABLE,
        "default_exchange": DEFAULT_EXCHANGE,
        "cache_enabled": CACHE_ENABLED and CACHE_AVAILABLE,
    }


# ========== 缓存管理 API ==========

@app.get("/api/cache/stats")
def get_cache_stats(
    symbol: str = Query(..., description="交易对"),
    timeframe: str = Query("15m", description="时间周期"),
    exchange: str = Query(None, description="交易所"),
):
    """获取缓存统计"""
    if not CACHE_AVAILABLE or not CACHE_ENABLED:
        return {"cache_enabled": False}
    
    cache = get_candle_cache()
    stats = cache.get_stats(symbol, timeframe, exchange or DEFAULT_EXCHANGE)
    stats["cache_enabled"] = True
    return stats


@app.delete("/api/cache")
def clear_cache(
    symbol: str = Query(..., description="交易对"),
    timeframe: str = Query("15m", description="时间周期"),
    exchange: str = Query(None, description="交易所"),
):
    """清除指定缓存"""
    if not CACHE_AVAILABLE or not CACHE_ENABLED:
        return {"deleted": False, "reason": "cache not enabled"}
    
    cache = get_candle_cache()
    deleted = cache.delete(symbol, timeframe, exchange or DEFAULT_EXCHANGE)
    
    return {"deleted": deleted, "symbol": symbol, "timeframe": timeframe}


# ========== WebSocket 实时行情 ==========

# 行情流实例
_ticker_stream: Optional[TickerStream] = None
_stream_task: Optional[asyncio.Task] = None


async def _on_ticker_update(ticker_data):
    """行情更新回调 - 广播到所有订阅者"""
    if not WS_AVAILABLE:
        return
    
    manager = get_connection_manager()
    channel = f"ticker:{ticker_data.symbol}"
    await manager.broadcast(channel, ticker_data.to_dict())


async def _start_ticker_stream():
    """启动行情流"""
    global _ticker_stream
    if not WS_AVAILABLE:
        return
    
    _ticker_stream = get_ticker_stream(DEFAULT_EXCHANGE)
    _ticker_stream.set_callback(_on_ticker_update)
    await _ticker_stream.start()


@app.on_event("startup")
async def startup_event():
    """启动时初始化行情流"""
    global _stream_task
    if WS_AVAILABLE:
        _stream_task = asyncio.create_task(_start_ticker_stream())
        logger.info("ticker stream task started")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 实时行情端点
    
    消息格式：
    
    订阅:
    { "action": "subscribe", "symbol": "BTC/USDT" }
    
    取消订阅:
    { "action": "unsubscribe", "symbol": "BTC/USDT" }
    
    查询订阅:
    { "action": "list" }
    
    推送格式:
    {
        "channel": "ticker:BTC/USDT",
        "type": "ticker",
        "symbol": "BTC/USDT",
        "last": 98000.5,
        "bid": 97999.0,
        "ask": 98001.0,
        "volume_24h": 12345.67,
        "change_24h": 150.5,
        "change_pct_24h": 0.15,
        "timestamp": 1234567890000
    }
    """
    if not WS_AVAILABLE:
        await websocket.close(code=1003, reason="WebSocket not available")
        return
    
    manager = get_connection_manager()
    client_id = await manager.connect(websocket)
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            action = data.get("action", "")
            
            if action == "subscribe":
                symbol = data.get("symbol")
                if symbol:
                    channel = f"ticker:{symbol}"
                    manager.subscribe(client_id, channel)
                    
                    # 确保行情流订阅了该交易对
                    if _ticker_stream:
                        await _ticker_stream.subscribe(symbol)
                    
                    await manager.send_to_client(client_id, {
                        "type": "subscribed",
                        "channel": channel,
                        "symbol": symbol,
                    })
                    
                    logger.info("client subscribed", client_id=client_id, symbol=symbol)
            
            elif action == "unsubscribe":
                symbol = data.get("symbol")
                if symbol:
                    channel = f"ticker:{symbol}"
                    manager.unsubscribe(client_id, channel)
                    
                    await manager.send_to_client(client_id, {
                        "type": "unsubscribed",
                        "channel": channel,
                        "symbol": symbol,
                    })
            
            elif action == "list":
                channels = manager.get_subscribed_channels(client_id)
                await manager.send_to_client(client_id, {
                    "type": "subscriptions",
                    "channels": list(channels),
                })
            
            elif action == "ping":
                await manager.send_to_client(client_id, {"type": "pong"})
            
            else:
                await manager.send_to_client(client_id, {
                    "type": "error",
                    "message": f"Unknown action: {action}",
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("client disconnected", client_id=client_id)
    except Exception as e:
        logger.error("websocket error", client_id=client_id, error=str(e))
        manager.disconnect(websocket)


@app.get("/api/ws/stats")
def get_ws_stats():
    """获取 WebSocket 统计信息"""
    if not WS_AVAILABLE:
        return {"available": False}
    
    manager = get_connection_manager()
    stats = manager.get_stats()
    
    stream_info = {}
    if _ticker_stream:
        stream_info = {
            "running": _ticker_stream.is_running,
            "subscriptions": list(_ticker_stream.subscriptions),
        }
    
    return {
        "available": True,
        "connections": stats,
        "stream": stream_info,
    }


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理连接"""
    # 停止行情流
    if _ticker_stream:
        await _ticker_stream.stop()
    
    # 关闭交易所客户端
    for exchange, client in _exchange_clients.items():
        try:
            await client.close()
            logger.info("exchange client closed", exchange=exchange)
        except Exception as e:
            logger.warning("failed to close exchange client", exchange=exchange, error=str(e))
