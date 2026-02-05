"""
Exchange Client - 交易所客户端基类
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from libs.core import get_logger

logger = get_logger("exchange")


@dataclass
class OHLCV:
    """K 线数据"""
    timestamp: int      # 毫秒时间戳
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Ticker:
    """行情数据"""
    symbol: str
    last: float
    bid: float
    ask: float
    volume_24h: float
    timestamp: int


class ExchangeClient(ABC):
    """
    交易所客户端基类
    
    所有交易所实现都需要继承此类
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """交易所名称"""
        pass
    
    @property
    @abstractmethod
    def supported_timeframes(self) -> List[str]:
        """支持的时间周期"""
        pass
    
    @abstractmethod
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
            symbol: 交易对（标准格式，如 BTC/USDT）
            timeframe: 时间周期
            limit: 数量
            since: 开始时间（毫秒）
        
        Returns:
            K 线列表
        """
        pass
    
    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> Ticker:
        """
        获取最新行情
        """
        pass
    
    @abstractmethod
    async def fetch_tickers(self, symbols: Optional[List[str]] = None) -> Dict[str, Ticker]:
        """
        批量获取行情
        """
        pass
    
    async def close(self):
        """关闭连接"""
        pass


# 支持的交易所列表
SUPPORTED_EXCHANGES = ["binance", "okx"]


def list_supported_exchanges() -> List[str]:
    """列出支持的交易所"""
    return SUPPORTED_EXCHANGES.copy()


def create_client(
    exchange: str,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    **kwargs
) -> ExchangeClient:
    """
    创建交易所客户端
    
    Args:
        exchange: 交易所名称 (binance, okx)
        api_key: API Key（可选，公开数据不需要）
        api_secret: API Secret（可选）
    
    Returns:
        ExchangeClient 实例
    """
    exchange = exchange.lower()
    
    if exchange == "binance":
        from .binance import BinanceClient
        return BinanceClient(api_key=api_key, api_secret=api_secret, **kwargs)
    elif exchange in ("okx", "okex"):
        from .okx import OKXClient
        return OKXClient(api_key=api_key, api_secret=api_secret, **kwargs)
    else:
        raise ValueError(f"Unsupported exchange: {exchange}. Supported: {SUPPORTED_EXCHANGES}")
