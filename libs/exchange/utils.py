"""
Exchange Utilities - 交易所工具函数
"""

from typing import Dict, Tuple

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


def denormalize_symbol(symbol: str, exchange: str = "binance") -> str:
    """
    反标准化交易对格式
    
    将 BASE/QUOTE 格式转换为交易所特定格式
    
    Examples (binance):
        "BTC/USDT" -> "BTCUSDT"
    Examples (okx):
        "BTC/USDT" -> "BTC-USDT"
    """
    if "/" not in symbol:
        return symbol
    
    base, quote = symbol.split("/")
    
    if exchange.lower() in ("binance", "bybit"):
        return f"{base}{quote}"
    elif exchange.lower() in ("okx", "okex"):
        return f"{base}-{quote}"
    else:
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
