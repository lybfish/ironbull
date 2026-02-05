"""
Ticker Cache - 行情数据缓存

使用 Redis 缓存最新行情，短 TTL
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
import json

from libs.core import get_redis, get_logger

logger = get_logger("ticker-cache")


@dataclass
class CachedTicker:
    """缓存的行情数据"""
    symbol: str
    last: float
    bid: float
    ask: float
    volume_24h: float
    timestamp: int


class TickerCache:
    """
    行情数据缓存
    
    特点：
    - 短 TTL（默认 5 秒）
    - 简单 key-value 存储
    """
    
    KEY_PREFIX = "ironbull:ticker"
    DEFAULT_TTL = 5  # 5 秒
    
    def __init__(self, ttl: int = DEFAULT_TTL):
        self.ttl = ttl
    
    def _key(self, symbol: str, exchange: str = "binance") -> str:
        """生成缓存 key"""
        symbol = symbol.upper().replace("/", "")
        return f"{self.KEY_PREFIX}:{exchange}:{symbol}"
    
    def get(self, symbol: str, exchange: str = "binance") -> Optional[CachedTicker]:
        """获取缓存的行情"""
        redis = get_redis()
        if not redis:
            return None
        
        key = self._key(symbol, exchange)
        
        try:
            data = redis.get(key)
            if not data:
                return None
            
            ticker_data = json.loads(data)
            return CachedTicker(
                symbol=ticker_data["symbol"],
                last=ticker_data["last"],
                bid=ticker_data["bid"],
                ask=ticker_data["ask"],
                volume_24h=ticker_data["volume_24h"],
                timestamp=ticker_data["timestamp"],
            )
            
        except Exception as e:
            logger.warning("ticker cache get failed", symbol=symbol, error=str(e))
            return None
    
    def set(self, ticker: CachedTicker, exchange: str = "binance") -> bool:
        """设置行情缓存"""
        redis = get_redis()
        if not redis:
            return False
        
        key = self._key(ticker.symbol, exchange)
        
        try:
            data = {
                "symbol": ticker.symbol,
                "last": ticker.last,
                "bid": ticker.bid,
                "ask": ticker.ask,
                "volume_24h": ticker.volume_24h,
                "timestamp": ticker.timestamp,
            }
            redis.setex(key, self.ttl, json.dumps(data))
            return True
            
        except Exception as e:
            logger.warning("ticker cache set failed", symbol=ticker.symbol, error=str(e))
            return False
    
    def delete(self, symbol: str, exchange: str = "binance") -> bool:
        """删除缓存"""
        redis = get_redis()
        if not redis:
            return False
        
        key = self._key(symbol, exchange)
        
        try:
            redis.delete(key)
            return True
        except Exception:
            return False


# 单例
_ticker_cache: Optional[TickerCache] = None


def get_ticker_cache() -> TickerCache:
    """获取行情缓存实例"""
    global _ticker_cache
    if _ticker_cache is None:
        _ticker_cache = TickerCache()
    return _ticker_cache
