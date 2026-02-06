"""
IronBull Exchange Module (v1 Phase 5)

交易所数据接口 - 统一封装 ccxt 访问

组件：
- ExchangeClient: 交易所客户端基类
- BinanceClient / OKXClient / GateClient: 各交易所数据客户端
- 通用工具函数
"""

from .client import (
    ExchangeClient,
    create_client,
    list_supported_exchanges,
)
from .binance import BinanceClient
from .okx import OKXClient
from .gate import GateClient
from .utils import (
    normalize_symbol,
    to_canonical_symbol,
    symbol_for_ccxt_futures,
    denormalize_symbol,
    parse_timeframe,
    timeframe_to_ms,
)

__all__ = [
    # 客户端
    "ExchangeClient",
    "BinanceClient",
    "OKXClient",
    "GateClient",
    "create_client",
    "list_supported_exchanges",
    # 工具函数
    "normalize_symbol",
    "to_canonical_symbol",
    "symbol_for_ccxt_futures",
    "denormalize_symbol",
    "parse_timeframe",
    "timeframe_to_ms",
]
