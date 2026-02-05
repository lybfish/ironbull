"""
Signal Standardization
"""

from libs.contracts import Signal, StrategyOutput
from libs.core import gen_id, time_now


def canonicalize_symbol(symbol: str) -> str:
    if not symbol:
        return symbol
    if "/" in symbol:
        return symbol
    upper = symbol.upper()
    for quote in ("USDT", "USD", "BTC", "ETH"):
        if upper.endswith(quote) and len(upper) > len(quote):
            base = upper[: -len(quote)]
            return f"{base}/{quote}"
    return upper


def standardize_signal(
    output: StrategyOutput,
    strategy_code: str,
    timeframe: str,
) -> Signal:
    return Signal(
        signal_id=gen_id("sig_"),
        strategy_code=strategy_code,
        symbol=output.symbol,
        canonical_symbol=canonicalize_symbol(output.symbol),
        side=output.side or "",
        signal_type=output.signal_type,
        entry_price=output.entry_price,
        stop_loss=output.stop_loss,
        take_profit=output.take_profit,
        quantity=None,
        confidence=output.confidence,
        reason=output.reason,
        timeframe=timeframe,
        timestamp=time_now(),
        status="pending",
    )
