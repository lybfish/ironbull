"""
Exchange Utilities - 交易所工具函数

Symbol 约定：
- 规范形式（canonical）：BASE/QUOTE，如 BTC/USDT，用于存储、展示、跨交易所一致。
- 各所格式：Binance 现货 BTCUSDT，OKX BTC-USDT，Gate BTC_USDT；合约在 CCXT 中多为 BASE/QUOTE:USDT。
"""

from typing import Dict, Tuple, Optional

# 时间周期映射（周期 -> 毫秒）
TIMEFRAME_MS: Dict[str, int] = {
    "1m": 60 * 1000,
    "3m": 3 * 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "30m": 30 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "2h": 2 * 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "6h": 6 * 60 * 60 * 1000,
    "8h": 8 * 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
    "3d": 3 * 24 * 60 * 60 * 1000,
    "1w": 7 * 24 * 60 * 60 * 1000,
    "1M": 30 * 24 * 60 * 60 * 1000,  # 近似值
}


def normalize_symbol(symbol: str, exchange: str = "binance") -> str:
    """
    标准化交易对格式
    
    将各种格式转换为统一的 BASE/QUOTE 格式
    
    Examples:
        "BTCUSDT" -> "BTC/USDT"
        "BTC-USDT" -> "BTC/USDT"
        "btc_usdt" -> "BTC/USDT"
    """
    symbol = symbol.upper().strip()
    
    # 已经是标准格式
    if "/" in symbol:
        return symbol
    
    # 处理分隔符
    for sep in ["-", "_"]:
        if sep in symbol:
            parts = symbol.split(sep)
            if len(parts) == 2:
                return f"{parts[0]}/{parts[1]}"
    
    # 无分隔符，尝试识别常见的 quote currency
    quote_currencies = ["USDT", "USDC", "BUSD", "USD", "BTC", "ETH", "BNB"]
    
    for quote in quote_currencies:
        if symbol.endswith(quote):
            base = symbol[:-len(quote)]
            if base:
                return f"{base}/{quote}"
    
    # 无法识别，原样返回
    return symbol


def to_canonical_symbol(symbol: str, market_type: str = "future") -> str:
    """
    将交易所返回的 symbol 转为规范形式 BASE/QUOTE，便于存储和跨所一致。

    - CCXT 合约多为 BTC/USDT:USDT，去掉 :USDT 得到 BTC/USDT。
    - 现货或已是 BASE/QUOTE 则先 normalize_symbol 后返回。
    """
    if not symbol:
        return symbol
    s = (symbol or "").strip().upper()
    # 合约后缀 :USDT / :USD
    for suffix in (":USDT", ":USD", ":BUSD"):
        if s.endswith(suffix):
            return s[: -len(suffix)]
    return normalize_symbol(s, "binance")


def symbol_for_ccxt_futures(canonical_symbol: str, settle: str = "USDT") -> str:
    """
    规范 symbol 转为 CCXT 合约格式（永续常用 BASE/QUOTE:USDT）。
    下单、查持仓等调用 CCXT 时，若为合约且传入的是规范形式，应先调用此函数。
    """
    canonical_symbol = normalize_symbol(canonical_symbol, "binance")
    if ":" in canonical_symbol:
        return canonical_symbol
    return f"{canonical_symbol}:{settle}"


def denormalize_symbol(symbol: str, exchange: str = "binance") -> str:
    """
    反标准化交易对格式
    
    将规范形式 BASE/QUOTE 转换为各交易所可识别的格式：
    - binance / bybit: BTCUSDT（无分隔）
    - okx: BTC-USDT（横线）
    - gate / gateio: BTC_USDT（下划线）
    """
    if "/" not in symbol:
        return symbol
    
    base, quote = symbol.split("/")
    
    ex = exchange.lower()
    if ex in ("binance", "bybit"):
        return f"{base}{quote}"
    if ex in ("okx", "okex"):
        return f"{base}-{quote}"
    if ex in ("gate", "gateio"):
        return f"{base}_{quote}"
    return f"{base}{quote}"


def parse_timeframe(timeframe: str) -> Tuple[int, str]:
    """
    解析时间周期字符串
    
    Returns:
        (value, unit) - 如 ("15m" -> (15, "m"), "4h" -> (4, "h"))
    """
    if not timeframe:
        return (15, "m")
    
    # 提取数字和单位
    value = ""
    unit = ""
    
    for char in timeframe:
        if char.isdigit():
            value += char
        else:
            unit += char
    
    if not value:
        value = "1"
    
    return (int(value), unit.lower())


def timeframe_to_ms(timeframe: str) -> int:
    """
    将时间周期转换为毫秒
    """
    return TIMEFRAME_MS.get(timeframe, 15 * 60 * 1000)


def timeframe_to_seconds(timeframe: str) -> int:
    """
    将时间周期转换为秒
    """
    return timeframe_to_ms(timeframe) // 1000


def ms_to_timestamp(ms: int) -> int:
    """
    毫秒转秒级时间戳
    """
    return ms // 1000


def timestamp_to_ms(ts: int) -> int:
    """
    秒级时间戳转毫秒
    """
    # 如果已经是毫秒级（13位），直接返回
    if ts > 10**12:
        return ts
    return ts * 1000
