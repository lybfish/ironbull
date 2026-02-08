"""
Gate.io Client - Gate 交易所客户端

使用 ccxt 库访问 Gate.io API（K 线、行情等公开数据）
"""

from typing import List, Optional, Dict, Any

try:
    import ccxt.async_support as ccxt_async
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

from .client import ExchangeClient, OHLCV, Ticker
from .utils import normalize_symbol
from libs.core import get_logger

logger = get_logger("gate")


class GateClient(ExchangeClient):
    """
    Gate.io 交易所客户端

    支持：
    - 公开数据（K 线、行情）- 无需 API Key
    - 可选 API Key 用于提高请求频率限制
    """

    # 支持的时间周期（与 Gate 文档一致；不含 10s 以免部分标的不支持）
    TIMEFRAMES = [
        "1m", "5m", "15m", "30m",
        "1h", "2h", "4h", "8h", "1d",
        "7d", "30d",
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

        # CCXT 中 Gate 交易所类名为 gateio
        self._exchange = ccxt_async.gateio({
            "apiKey": api_key,
            "secret": api_secret,
            "sandbox": sandbox,
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
            },
            **kwargs,
        })

        logger.info("gate client initialized", sandbox=sandbox)

    @property
    def name(self) -> str:
        return "gate"

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
        """
        symbol = normalize_symbol(symbol, "gate")
        limit = min(limit, 1000)

        # 若请求周期不在 Gate 支持列表，使用 15m
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
                exchange="gate",
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
        symbol = normalize_symbol(symbol, "gate")

        try:
            ticker = await self._exchange.fetch_ticker(symbol)

            # 处理 timestamp：Gate 可能返回 None
            ticker_timestamp = ticker.get("timestamp")
            if ticker_timestamp is None:
                import time
                ticker_timestamp = int(time.time() * 1000)  # 使用当前时间（毫秒）
            else:
                ticker_timestamp = int(ticker_timestamp)

            return Ticker(
                symbol=symbol,
                last=float(ticker.get("last", 0)),
                bid=float(ticker.get("bid", 0)),
                ask=float(ticker.get("ask", 0)),
                volume_24h=float(ticker.get("quoteVolume", 0)),
                timestamp=ticker_timestamp,
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
                symbols = [normalize_symbol(s, "gate") for s in symbols]

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

    async def close(self):
        """关闭连接"""
        await self._exchange.close()
        logger.info("gate client closed")
