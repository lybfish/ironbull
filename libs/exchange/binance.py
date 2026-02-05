"""
Binance Client - Binance 交易所客户端

使用 ccxt 库访问 Binance API
"""

from typing import List, Optional, Dict, Any
import asyncio

try:
    import ccxt.async_support as ccxt_async
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

from .client import ExchangeClient, OHLCV, Ticker
from .utils import normalize_symbol, denormalize_symbol
from libs.core import get_logger

logger = get_logger("binance")


class BinanceClient(ExchangeClient):
    """
    Binance 交易所客户端
    
    支持：
    - 公开数据（K线、行情）- 无需 API Key
    - 可选 API Key 用于提高请求频率限制
    """
    
    # 支持的时间周期
    TIMEFRAMES = [
        "1m", "3m", "5m", "15m", "30m",
        "1h", "2h", "4h", "6h", "8h", "12h",
        "1d", "3d", "1w", "1M",
    ]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sandbox: bool = False,
        **kwargs,
    ):
        """
        Args:
            api_key: API Key（可选）
            api_secret: API Secret（可选）
            sandbox: 使用测试网（默认 False）
        """
        if not CCXT_AVAILABLE:
            raise ImportError("ccxt library not installed. Run: pip install ccxt")
        
        self._exchange = ccxt_async.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "sandbox": sandbox,
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",  # 现货市场
            },
            **kwargs,
        })
        
        logger.info("binance client initialized", sandbox=sandbox)
    
    @property
    def name(self) -> str:
        return "binance"
    
    @property
    def supported_timeframes(self) -> List[str]:
        return self.TIMEFRAMES.copy()
    
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "15m",
        limit: int = 100,
        since: Optional[int] = None,
    ) -> List[OHLCV]:
        """
        获取 K 线数据
        
        Args:
            symbol: 交易对（如 BTC/USDT 或 BTCUSDT）
            timeframe: 时间周期
            limit: 数量（最大 1000）
            since: 开始时间（毫秒）
        """
        # 标准化 symbol
        symbol = normalize_symbol(symbol, "binance")
        
        # 限制数量
        limit = min(limit, 1000)
        
        if timeframe not in self.TIMEFRAMES:
            timeframe = "15m"
        
        try:
            ohlcv_data = await self._exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                since=since,
            )
            
            result = []
            for item in ohlcv_data:
                # ccxt 返回格式: [timestamp, open, high, low, close, volume]
                result.append(OHLCV(
                    timestamp=int(item[0]),
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[5]),
                ))
            
            logger.info(
                "ohlcv fetched",
                exchange="binance",
                symbol=symbol,
                timeframe=timeframe,
                count=len(result),
            )
            
            return result
            
        except Exception as e:
            logger.error("ohlcv fetch failed", symbol=symbol, error=str(e))
            raise
    
    async def fetch_ticker(self, symbol: str) -> Ticker:
        """
        获取最新行情
        """
        symbol = normalize_symbol(symbol, "binance")
        
        try:
            ticker = await self._exchange.fetch_ticker(symbol)
            
            return Ticker(
                symbol=symbol,
                last=float(ticker.get("last", 0)),
                bid=float(ticker.get("bid", 0)),
                ask=float(ticker.get("ask", 0)),
                volume_24h=float(ticker.get("quoteVolume", 0)),
                timestamp=int(ticker.get("timestamp", 0)),
            )
            
        except Exception as e:
            logger.error("ticker fetch failed", symbol=symbol, error=str(e))
            raise
    
    async def fetch_tickers(self, symbols: Optional[List[str]] = None) -> Dict[str, Ticker]:
        """
        批量获取行情
        """
        try:
            if symbols:
                symbols = [normalize_symbol(s, "binance") for s in symbols]
            
            tickers = await self._exchange.fetch_tickers(symbols)
            
            result = {}
            for symbol, data in tickers.items():
                result[symbol] = Ticker(
                    symbol=symbol,
                    last=float(data.get("last", 0)),
                    bid=float(data.get("bid", 0)),
                    ask=float(data.get("ask", 0)),
                    volume_24h=float(data.get("quoteVolume", 0)),
                    timestamp=int(data.get("timestamp", 0)),
                )
            
            return result
            
        except Exception as e:
            logger.error("tickers fetch failed", error=str(e))
            raise
    
    async def fetch_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        获取订单簿
        """
        symbol = normalize_symbol(symbol, "binance")
        
        try:
            order_book = await self._exchange.fetch_order_book(symbol, limit=limit)
            return order_book
        except Exception as e:
            logger.error("order_book fetch failed", symbol=symbol, error=str(e))
            raise
    
    async def close(self):
        """关闭连接"""
        await self._exchange.close()
        logger.info("binance client closed")
