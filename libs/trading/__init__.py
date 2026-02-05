"""
IronBull Trading Module

基于 ccxt 的交易封装，支持真实交易和模拟交易

组件：
- Trader: 交易执行器基类
- LiveTrader: 真实交易（ccxt）
- PaperTrader: 模拟交易
"""

from .base import Trader, OrderResult, OrderStatus, OrderSide, OrderType
from .live_trader import LiveTrader
from .paper_trader import PaperTrader

__all__ = [
    "Trader",
    "OrderResult",
    "OrderStatus",
    "OrderSide",
    "OrderType",
    "LiveTrader",
    "PaperTrader",
]
