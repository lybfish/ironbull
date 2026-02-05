"""
IronBull Exchange Module (v1 Phase 5)

交易所数据接口 - 统一封装 ccxt 访问

组件：
- ExchangeClient: 交易所客户端基类
- BinanceClient: Binance 数据客户端
- OKXClient: OKX 数据客户端
- 通用工具函数
"""

from .client import (
    ExchangeClient,
    create_client,
    list_supported_exchanges,
)
from .binance import BinanceClient
from .okx import OKXClient
from .utils import (
    normalize_symbol,
    parse_timeframe,
    timeframe_to_ms,
)

__all__ = [
    # 客户端
    "ExchangeClient",
    "BinanceClient",
    "OKXClient",
    "create_client",
    "list_supported_exchanges",
    # 工具函数
    "normalize_symbol",
    "parse_timeframe",
    "timeframe_to_ms",
]
