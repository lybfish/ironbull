"""
Candle Cache - K 线数据缓存

使用 Redis 缓存 K 线数据，减少交易所 API 调用
支持 TTL 过期和增量更新
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
import json
import time

from libs.core import get_redis, get_logger

logger = get_logger("candle-cache")


@dataclass
class CachedCandle:
    """缓存的 K 线数据"""
    timestamp: int      # 秒级时间戳
    open: float
    high: float
    low: float
    close: float
    volume: float


class CandleCache:
    """
    K 线数据缓存
    
    缓存策略：
    - 每个 symbol + timeframe 组合一个 key
    - 使用 Redis Hash 存储，field 为时间戳
    - TTL 基于时间周期动态计算
    
    使用方式：
        cache = CandleCache()
        
        # 检查缓存
        candles = cache.get("BTC/USDT", "15m", limit=100)
        if not candles:
            # 从交易所获取
            candles = fetch_from_exchange(...)
            cache.set("BTC/USDT", "15m", candles)
    """
    
    KEY_PREFIX = "ironbull:candles"
    
    # 时间周期对应的 TTL（秒）
    # 较短周期缓存时间短，较长周期缓存时间长
    TTL_MAP = {
        "1m": 60,       # 1 分钟
        "3m": 180,      # 3 分钟
        "5m": 300,      # 5 分钟
        "15m": 900,     # 15 分钟
        "30m": 1800,    # 30 分钟
        "1h": 3600,     # 1 小时
        "2h": 7200,     # 2 小时
        "4h": 14400,    # 4 小时
        "6h": 21600,    # 6 小时
        "12h": 43200,   # 12 小时
        "1d": 86400,    # 1 天
        "1w": 604800,   # 1 周
    }
    
    def __init__(self, default_ttl: int = 900):
        """
        Args:
            default_ttl: 默认 TTL（秒），默认 15 分钟
        """
        self.default_ttl = default_ttl
    
    def _key(self, symbol: str, timeframe: str, exchange: str = "binance") -> str:
        """生成缓存 key"""
        # 标准化 symbol
        symbol = symbol.upper().replace("/", "")
        return f"{self.KEY_PREFIX}:{exchange}:{symbol}:{timeframe}"
    
    def _get_ttl(self, timeframe: str) -> int:
        """获取 TTL"""
        return self.TTL_MAP.get(timeframe, self.default_ttl)
    
    def get(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
        exchange: str = "binance",
    ) -> Optional[List[CachedCandle]]:
        """
        获取缓存的 K 线数据
        
        Returns:
            K 线列表，如果缓存不存在或过期返回 None
        """
        redis = get_redis()
        if not redis:
            return None
        
        key = self._key(symbol, timeframe, exchange)
        
        try:
            # 获取所有缓存数据
            data = redis.hgetall(key)
            if not data:
                logger.debug("cache miss", symbol=symbol, timeframe=timeframe)
                return None
            
            # 解析并排序
            candles = []
            for ts_str, candle_json in data.items():
                try:
                    ts = int(ts_str)
                    candle_data = json.loads(candle_json)
                    candles.append(CachedCandle(
                        timestamp=ts,
                        open=candle_data["o"],
                        high=candle_data["h"],
                        low=candle_data["l"],
                        close=candle_data["c"],
                        volume=candle_data["v"],
                    ))
                except (ValueError, KeyError, json.JSONDecodeError):
                    continue
            
            # 按时间排序并限制数量
            candles.sort(key=lambda x: x.timestamp)
            if len(candles) > limit:
                candles = candles[-limit:]
            
            if candles:
                logger.debug(
                    "cache hit",
                    symbol=symbol,
                    timeframe=timeframe,
                    count=len(candles),
                )
            
            return candles if candles else None
            
        except Exception as e:
            logger.warning("cache get failed", symbol=symbol, error=str(e))
            return None
    
    def set(
        self,
        symbol: str,
        timeframe: str,
        candles: List[CachedCandle],
        exchange: str = "binance",
    ) -> bool:
        """
        设置 K 线缓存
        
        Args:
            symbol: 交易对
            timeframe: 时间周期
            candles: K 线列表
            exchange: 交易所
        
        Returns:
            是否成功
        """
        redis = get_redis()
        if not redis or not candles:
            return False
        
        key = self._key(symbol, timeframe, exchange)
        ttl = self._get_ttl(timeframe)
        
        try:
            # 构建 Hash 数据
            mapping = {}
            for candle in candles:
                candle_data = {
                    "o": candle.open,
                    "h": candle.high,
                    "l": candle.low,
                    "c": candle.close,
                    "v": candle.volume,
                }
                mapping[str(candle.timestamp)] = json.dumps(candle_data)
            
            # 使用 pipeline 批量写入
            pipe = redis.pipeline()
            pipe.hset(key, mapping=mapping)
            pipe.expire(key, ttl)
            pipe.execute()
            
            logger.debug(
                "cache set",
                symbol=symbol,
                timeframe=timeframe,
                count=len(candles),
                ttl=ttl,
            )
            
            return True
            
        except Exception as e:
            logger.warning("cache set failed", symbol=symbol, error=str(e))
            return False
    
    def update_latest(
        self,
        symbol: str,
        timeframe: str,
        candle: CachedCandle,
        exchange: str = "binance",
    ) -> bool:
        """
        更新最新一根 K 线
        
        用于实时数据更新，只更新最后一根
        """
        redis = get_redis()
        if not redis:
            return False
        
        key = self._key(symbol, timeframe, exchange)
        ttl = self._get_ttl(timeframe)
        
        try:
            candle_data = {
                "o": candle.open,
                "h": candle.high,
                "l": candle.low,
                "c": candle.close,
                "v": candle.volume,
            }
            
            pipe = redis.pipeline()
            pipe.hset(key, str(candle.timestamp), json.dumps(candle_data))
            pipe.expire(key, ttl)
            pipe.execute()
            
            return True
            
        except Exception as e:
            logger.warning("cache update failed", symbol=symbol, error=str(e))
            return False
    
    def delete(self, symbol: str, timeframe: str, exchange: str = "binance") -> bool:
        """删除缓存"""
        redis = get_redis()
        if not redis:
            return False
        
        key = self._key(symbol, timeframe, exchange)
        
        try:
            redis.delete(key)
            return True
        except Exception:
            return False
    
    def get_stats(self, symbol: str, timeframe: str, exchange: str = "binance") -> Dict[str, Any]:
        """获取缓存统计"""
        redis = get_redis()
        if not redis:
            return {"exists": False}
        
        key = self._key(symbol, timeframe, exchange)
        
        try:
            count = redis.hlen(key)
            ttl = redis.ttl(key)
            
            return {
                "exists": count > 0,
                "count": count,
                "ttl": ttl,
                "key": key,
            }
        except Exception:
            return {"exists": False}


# 单例
_candle_cache: Optional[CandleCache] = None


def get_candle_cache() -> CandleCache:
    """获取 K 线缓存实例"""
    global _candle_cache
    if _candle_cache is None:
        _candle_cache = CandleCache()
    return _candle_cache
