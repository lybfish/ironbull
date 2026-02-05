"""
IronBull Trading Module

基于 ccxt 的交易封装，支持真实交易和模拟交易

组件：
- Trader: 交易执行器基类
- LiveTrader: 真实交易（ccxt）
- PaperTrader: 模拟交易
- AutoTrader: 自动交易执行器（信号驱动）
- TradeSettlementService: 交易结算服务（OrderTrade → Position → Ledger）
"""

from .base import Trader, OrderResult, OrderStatus, OrderSide, OrderType, Balance
from .live_trader import LiveTrader
from .paper_trader import PaperTrader
from .auto_trader import AutoTrader, TradeMode, RiskLimits, TradeRecord
from .settlement import TradeSettlementService, SettlementResult

__all__ = [
    "Trader",
    "OrderResult",
    "OrderStatus",
    "OrderSide",
    "OrderType",
    "Balance",
    "LiveTrader",
    "PaperTrader",
    "AutoTrader",
    "TradeMode",
    "RiskLimits",
    "TradeRecord",
    "TradeSettlementService",
    "SettlementResult",
]
