"""
Ticker Stream - 实时行情流

从交易所订阅实时行情，推送给 WebSocket 客户端
"""

import asyncio
from typing import Dict, Set, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime

from libs.core import get_logger

logger = get_logger("ticker-stream")


@dataclass
class TickerData:
    """行情数据"""
    symbol: str
    last: float
    bid: float
    ask: float
    volume_24h: float
    change_24h: float
    change_pct_24h: float
    timestamp: int
    
    def to_dict(self) -> dict:
        return {
            "type": "ticker",
            "symbol": self.symbol,
            "last": self.last,
            "bid": self.bid,
            "ask": self.ask,
            "volume_24h": self.volume_24h,
            "change_24h": self.change_24h,
            "change_pct_24h": self.change_pct_24h,
            "timestamp": self.timestamp,
        }


class TickerStream:
    """
    实时行情流
    
    功能：
    - 订阅交易所 WebSocket
    - 解析并转发行情数据
    - 管理订阅的交易对
    
    使用示例：
        stream = TickerStream(exchange="binance")
        stream.set_callback(on_ticker)
        
        await stream.subscribe("BTC/USDT")
        await stream.start()
    """
    
    def __init__(self, exchange: str = "binance"):
        self.exchange = exchange
        self._subscriptions: Set[str] = set()
        self._callback: Optional[Callable[[TickerData], Any]] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._ccxt_ws = None
        
    def set_callback(self, callback: Callable[[TickerData], Any]):
        """设置行情回调"""
        self._callback = callback
    
    async def subscribe(self, symbol: str):
        """订阅交易对"""
        self._subscriptions.add(symbol)
        logger.info("subscribed to ticker", symbol=symbol, exchange=self.exchange)
    
    async def unsubscribe(self, symbol: str):
        """取消订阅"""
        self._subscriptions.discard(symbol)
        logger.info("unsubscribed from ticker", symbol=symbol)
    
    async def start(self):
        """启动行情流"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("ticker stream started", exchange=self.exchange)
    
    async def stop(self):
        """停止行情流"""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self._ccxt_ws:
            try:
                await self._ccxt_ws.close()
            except Exception:
                pass
        
        logger.info("ticker stream stopped")
    
    async def _run_loop(self):
        """主循环 - 从交易所获取行情"""
        try:
            # 动态导入 ccxt
            import ccxt.pro as ccxtpro
            
            # 交易所名 -> CCXT 类名（gate -> gateio）
            ccxt_id = "gateio" if self.exchange == "gate" else self.exchange
            exchange_class = getattr(ccxtpro, ccxt_id)
            self._ccxt_ws = exchange_class({
                'enableRateLimit': True,
            })
            
            logger.info("connected to exchange ws", exchange=self.exchange)
            
            while self._running:
                if not self._subscriptions:
                    await asyncio.sleep(1)
                    continue
                
                try:
                    # 监听所有订阅的交易对
                    for symbol in list(self._subscriptions):
                        try:
                            ticker = await asyncio.wait_for(
                                self._ccxt_ws.watch_ticker(symbol),
                                timeout=5.0
                            )
                            
                            # 转换为 TickerData
                            data = TickerData(
                                symbol=ticker['symbol'],
                                last=ticker.get('last', 0) or 0,
                                bid=ticker.get('bid', 0) or 0,
                                ask=ticker.get('ask', 0) or 0,
                                volume_24h=ticker.get('baseVolume', 0) or 0,
                                change_24h=ticker.get('change', 0) or 0,
                                change_pct_24h=ticker.get('percentage', 0) or 0,
                                timestamp=ticker.get('timestamp', 0) or 0,
                            )
                            
                            # 回调
                            if self._callback:
                                try:
                                    result = self._callback(data)
                                    if asyncio.iscoroutine(result):
                                        await result
                                except Exception as e:
                                    logger.warning("callback error", error=str(e))
                                    
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            logger.warning("watch ticker error", symbol=symbol, error=str(e))
                            await asyncio.sleep(1)
                            
                except Exception as e:
                    logger.error("stream error", error=str(e))
                    await asyncio.sleep(5)
                    
        except ImportError:
            logger.warning("ccxt.pro not available, using mock stream")
            await self._run_mock_loop()
        except Exception as e:
            logger.error("stream fatal error", error=str(e))
        finally:
            if self._ccxt_ws:
                try:
                    await self._ccxt_ws.close()
                except Exception:
                    pass
    
    async def _run_mock_loop(self):
        """模拟行情流（用于测试）"""
        import random
        
        # 模拟价格
        prices = {
            "BTC/USDT": 98000,
            "ETH/USDT": 3200,
            "BNB/USDT": 680,
        }
        
        while self._running:
            if not self._subscriptions:
                await asyncio.sleep(1)
                continue
            
            for symbol in list(self._subscriptions):
                # 随机波动
                base_price = prices.get(symbol, 100)
                change = random.uniform(-0.002, 0.002)
                new_price = base_price * (1 + change)
                prices[symbol] = new_price
                
                data = TickerData(
                    symbol=symbol,
                    last=round(new_price, 2),
                    bid=round(new_price * 0.9999, 2),
                    ask=round(new_price * 1.0001, 2),
                    volume_24h=random.uniform(1000, 10000),
                    change_24h=round(new_price * change, 2),
                    change_pct_24h=round(change * 100, 4),
                    timestamp=int(datetime.now().timestamp() * 1000),
                )
                
                if self._callback:
                    try:
                        result = self._callback(data)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        logger.warning("callback error", error=str(e))
            
            # 模拟延迟
            await asyncio.sleep(1)
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def subscriptions(self) -> Set[str]:
        return self._subscriptions.copy()


# 单例
_ticker_stream: Optional[TickerStream] = None


def get_ticker_stream(exchange: str = "binance") -> TickerStream:
    """获取行情流实例"""
    global _ticker_stream
    if _ticker_stream is None:
        _ticker_stream = TickerStream(exchange)
    return _ticker_stream
