"""
Old1 SMC + Fibonacci backtest engine ported into current codebase.

Notes:
- Logic is copied 1:1 from old1 backtest_engine.py (smc_backtest).
- No IO/DB; pure computation on candles.
- Keep behavior identical for alignment.
"""

from __future__ import annotations

from typing import Any
import math


def detect_rejection(
    bar: dict[str, Any],
    prev: dict[str, Any] | None,
    prev2: dict[str, Any] | None,
    side: str,
    zone_low: float,
    zone_high: float,
    include_stars: bool,
    allow_engulf: bool,
    pinbar_ratio: float,
) -> dict[str, bool]:
    o = bar["o"]
    c = bar["c"]
    h = bar["h"]
    l = bar["l"]
    body = max(1e-8, abs(c - o))
    upper = h - max(o, c)
    lower = min(o, c) - l
    engulf = False
    if allow_engulf and prev:
        if side == "BUY":
            engulf = c > o and prev["c"] < prev["o"] and c >= prev["o"] and o <= prev["c"]
        else:
            engulf = c < o and prev["c"] > prev["o"] and o >= prev["c"] and c <= prev["o"]

    if side == "BUY":
        close_reject = c > zone_high and c > o
        pinbar = lower >= pinbar_ratio * body and lower >= upper * 1.2
    else:
        close_reject = c < zone_low and c < o
        pinbar = upper >= pinbar_ratio * body and upper >= lower * 1.2

    morning_star = False
    evening_star = False
    if include_stars and prev and prev2:
        c1o, c1c = prev2["o"], prev2["c"]
        c2o, c2c = prev["o"], prev["c"]
        c3o, c3c = bar["o"], bar["c"]
        body1 = abs(c1c - c1o)
        body2 = abs(c2c - c2o)
        body3 = abs(c3c - c3o)
        if side == "BUY":
            if c1c < c1o and body1 > 0:
                if body2 < body1 * 0.5:
                    if c3c > c3o and body3 > 0 and c3c >= (c1o + c1c) / 2.0:
                        morning_star = True
        else:
            if c1c > c1o and body1 > 0:
                if body2 < body1 * 0.5:
                    if c3c < c3o and body3 > 0 and c3c <= (c1o + c1c) / 2.0:
                        evening_star = True

    return {
        "close_reject": close_reject,
        "pinbar": pinbar,
        "engulf": engulf,
        "morning_star": morning_star,
        "evening_star": evening_star,
    }


def in_session(ts: int, session: str) -> bool:
    if session == "all":
        return True
    # ts is UTC seconds; convert to UTC+8 for session bucketing
    t = (ts + 8 * 3600) % 86400
    hour = t // 3600
    if session == "asia":
        return 0 <= hour < 8
    if session == "london":
        return 15 <= hour < 23
    if session == "ny":
        return hour >= 20 or hour < 4
    return True


def _coerce_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def smc_backtest(params: dict[str, Any], candles: list[dict[str, Any]], htf_candles: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    fee_rate = (float(params.get("fee_bps", 0)) or 0.0) / 10000.0
    spread_points = max(0.0, float(params.get("spread_points", 0) or 0))
    price_digits = int(params.get("price_digits", 5) or 5)
    price_digits = max(0, min(10, price_digits))
    order_type = (params.get("order_type") or "limit").lower()

    def fmt_price(v: float) -> str:
        return f"{v:.{price_digits}f}"

    point = 10 ** (-price_digits) if price_digits > 0 else 1.0
    spread = spread_points * point
    half_spread = spread / 2.0
    rr = max(0.1, float(params.get("rr", 2) or 2))
    risk_pct = max(0.1, float(params.get("risk_pct", 1) or 1)) / 100.0
    risk_cash_fixed = float(params.get("risk_cash", 0) or 0)
    max_leverage = max(1.0, float(params.get("max_leverage", 10) or 10))
    initial_cash = float(params.get("initial_cash", 10000) or 10000)
    max_notional = initial_cash * max_leverage
    symbol = (params.get("symbol") or "").upper()
    fx_meta = {
        "XAUUSD": {"tick_size": 0.01, "tick_value": 1, "contract": 100},
        "EURUSD": {"tick_size": 0.0001, "tick_value": 10, "contract": 100000},
        "GBPUSD": {"tick_size": 0.0001, "tick_value": 10, "contract": 100000},
        "USDJPY": {"tick_size": 0.01, "tick_value": 10, "contract": 100000},
    }
    crypto_meta = {
        "BTCUSD": {"qty_step": 0.01, "min_qty": 0.01},
        "ETHUSD": {"qty_step": 0.01, "min_qty": 0.01},
    }
    tif_bars = max(1, int(params.get("tif_bars", 20) or 20))
    direction = (params.get("direction") or "both").lower()
    cooldown_bars = max(0, int(params.get("cooldown_bars", 0) or 0))

    smc = params.get("smc") or {}
    structure = (smc.get("structure") or "both").lower()
    smc_swing_raw = smc.get("swing", 3)
    smc_swing_auto = str(smc_swing_raw).lower() == "auto"
    swing = max(1, int(smc_swing_raw or 3)) if not smc_swing_auto else 3
    auto_profile = (smc.get("autoProfile") or "medium").lower()
    entry_source = (smc.get("entry") or "ob").lower()
    bias = (smc.get("bias") or "with_trend").lower()
    liquidity = (smc.get("liquidity") or "external").lower()
    ob_type = (smc.get("obType") or "reversal").lower()
    wick_ob = bool(smc.get("wickOb", True))
    use_ob_raw = smc.get("useOb", True)
    use_ob = "auto" if str(use_ob_raw).lower() == "auto" else bool(use_ob_raw)
    ob_lookback = max(2, int(smc.get("obLookback", 20) or 20))
    use_fvg_raw = smc.get("useFvg", True)
    use_fvg = "auto" if str(use_fvg_raw).lower() == "auto" else bool(use_fvg_raw)
    fvg_min_pct = float(smc.get("fvgMinPct", 0.15) or 0.15) / 100.0
    use_sweep_raw = smc.get("useSweep", True)
    use_sweep = "auto" if str(use_sweep_raw).lower() == "auto" else bool(use_sweep_raw)
    sweep_len = max(1, int(smc.get("sweepLen", 5) or 5))
    limit_offset_pct = float(smc.get("limitOffsetPct", 20) or 20) / 100.0
    limit_tol_atr = float(smc.get("limitTolAtr", 0.2) or 0.2)
    atr_period = max(2, int(smc.get("atrPeriod", 14) or 14))
    stop_buffer_pct = float(smc.get("stopBufferPct", 0.05) or 0.05) / 100.0
    stop_source = (smc.get("stopSource") or "auto").lower()
    tp_mode = (smc.get("tpMode") or "swing").lower()
    min_rr_raw = smc.get("minRr", 2)
    min_rr_auto = str(min_rr_raw).lower() == "auto"
    min_rr = max(0.1, float(min_rr_raw or 2)) if not min_rr_auto else 2.0
    retest_raw = smc.get("retestBars", 20)
    retest_auto = str(retest_raw).lower() == "auto"
    retest_bars = max(1, int(retest_raw or 20)) if not retest_auto else 20
    retest_cancel_order = bool(smc.get("retestCancelOrder", False))
    retest_ignore_stop_touch = bool(smc.get("retestIgnoreStopTouch", False))
    pinbar_ratio = max(1.0, float(smc.get("pinbarRatio", 2) or 2))
    allow_engulf = bool(smc.get("allowEngulf", True))
    market_reject = bool(smc.get("marketReject", True))
    market_max_dev_atr = float(smc.get("marketMaxDevAtr", 0.3) or 0.3)
    fibo_levels_raw = smc.get("fiboLevels")
    confirm_mode = (params.get("entry_mode") or "limit").lower()
    htf_swing_raw = smc.get("htfSwing", 3)
    htf_swing_auto = str(htf_swing_raw).lower() == "auto"
    htf_swing = max(1, int(htf_swing_raw or 3)) if not htf_swing_auto else 3
    session = (smc.get("session") or "all").lower()
    fibo_mode = params.get("strategy") == "smc_fibo"
    fibo_fallback = bool(smc.get("fiboFallback", True))

    if fibo_mode and confirm_mode == "market":
        confirm_mode = "limit"
    entry_mode = confirm_mode

    equity = float(params.get("initial_cash", 10000) or 10000)
    cash = equity
    pos = 0.0
    pending_orders: list[dict[str, Any]] = []

    signals: list[dict[str, Any]] = []
    orders: list[dict[str, Any]] = []
    fills: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    markers: list[dict[str, Any]] = []
    order_zones: list[dict[str, Any]] = []
    equity_series: list[dict[str, Any]] = []

    signal_index: dict[int, int] = {}
    signal_seq = 0
    order_seq = 0

    open_order = None
    open_trade = None

    def price_with_spread(base: float, side: str) -> float:
        if half_spread <= 0:
            return base
        return base + half_spread if side == "BUY" else base - half_spread

    def spread_cost(qty: float) -> float:
        if half_spread <= 0:
            return 0.0
        return abs(qty) * half_spread

    last_entry_i = -10**9

    swing_high = None
    swing_low = None
    trend = None
    pending = None  # {side, entry, stop, tp, zone_low, zone_high, expireI}

    realtime_mode = _coerce_bool(params.get("realtime_mode") if "realtime_mode" in params else params.get("realtimeMode"))

    def compute_swings(
        src: list[dict[str, Any]],
        n: int,
        realtime: bool = False,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        highs = []
        lows = []
        if len(src) < n * 2 + 1:
            return highs, lows
        if realtime:
            for i in range(n, len(src)):
                hi = src[i]["h"]
                lo = src[i]["l"]
                if all(hi >= src[j]["h"] for j in range(i - n, i + 1)):
                    highs.append({"i": i, "ts": src[i]["ts"], "price": hi})
                if all(lo <= src[j]["l"] for j in range(i - n, i + 1)):
                    lows.append({"i": i, "ts": src[i]["ts"], "price": lo})
        else:
            for i in range(n, len(src) - n):
                hi = src[i]["h"]
                lo = src[i]["l"]
                if all(hi >= src[j]["h"] for j in range(i - n, i + n + 1)):
                    highs.append({"i": i, "ts": src[i]["ts"], "price": hi})
                if all(lo <= src[j]["l"] for j in range(i - n, i + n + 1)):
                    lows.append({"i": i, "ts": src[i]["ts"], "price": lo})
        return highs, lows

    def parse_fibo_levels(raw: Any) -> list[float]:
        levels: list[float] = []
        items: list[Any]
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, str):
            items = [x.strip() for x in raw.split(",")]
        else:
            items = []
        for item in items:
            try:
                val = float(item)
            except (TypeError, ValueError):
                continue
            if 0.0 < val < 1.0:
                levels.append(round(val, 4))
        if not levels:
            levels = [0.5, 0.618, 0.705]
        levels = sorted(set(levels))
        return levels

    fibo_levels = parse_fibo_levels(fibo_levels_raw)

    avg_pct = None
    if candles:
        sample = candles[-min(800, len(candles)):]
        avg_pct = sum(((c["h"] - c["l"]) / max(1e-8, c["c"])) for c in sample) / max(1, len(sample)) * 100.0

    atr_values = []
    if candles:
        tr_values = []
        prev_close = None
        for c in candles:
            high = c["h"]
            low = c["l"]
            if prev_close is None:
                tr = high - low
            else:
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_values.append(tr)
            prev_close = c["c"]
        for i in range(len(tr_values)):
            if i < atr_period:
                atr_values.append(None)
            else:
                window = tr_values[i - atr_period + 1 : i + 1]
                atr_values.append(sum(window) / max(1, len(window)))

    profile = auto_profile if auto_profile in ("conservative", "medium", "aggressive") else "medium"
    if profile == "conservative":
        swing_steps = (0.25, 0.5, 0.9, 1.5)
        min_rr_steps = (0.4, 0.8, 1.2)
        min_rr_vals = (2.0, 2.5, 3.0, 3.5)
        retest_steps = (0.4, 0.8, 1.2)
        retest_vals = (32, 24, 16, 10)
        entry_steps = (0.6, 1.2)
        fvg_on = 0.5
        sweep_on = 0.9
    elif profile == "aggressive":
        swing_steps = (0.1, 0.2, 0.4, 0.8)
        min_rr_steps = (0.2, 0.4, 0.8)
        min_rr_vals = (1.2, 1.6, 2.0, 2.5)
        retest_steps = (0.2, 0.5, 0.9)
        retest_vals = (20, 14, 10, 6)
        entry_steps = (0.2, 0.5)
        fvg_on = 0.2
        sweep_on = 0.4
    else:
        swing_steps = (0.15, 0.3, 0.6, 1.0)
        min_rr_steps = (0.25, 0.6, 1.0)
        min_rr_vals = (1.5, 2.0, 2.5, 3.0)
        retest_steps = (0.25, 0.6, 1.0)
        retest_vals = (28, 20, 12, 8)
        entry_steps = (0.3, 0.8)
        fvg_on = 0.3
        sweep_on = 0.6

    if smc_swing_auto and avg_pct is not None:
        if avg_pct < swing_steps[0]:
            swing = 2
        elif avg_pct < swing_steps[1]:
            swing = 3
        elif avg_pct < swing_steps[2]:
            swing = 4
        elif avg_pct < swing_steps[3]:
            swing = 5
        else:
            swing = 6

    if liquidity == "auto":
        liquidity = "external" if htf_candles else "internal"

    if confirm_mode == "auto":
        if avg_pct is None:
            confirm_mode = "limit"
        elif avg_pct < entry_steps[0]:
            confirm_mode = "limit"
        elif avg_pct < entry_steps[1]:
            confirm_mode = "market"
        else:
            confirm_mode = "retest"
    if fibo_mode and confirm_mode == "market":
        confirm_mode = "limit"

    if min_rr_auto and avg_pct is not None:
        if avg_pct < min_rr_steps[0]:
            min_rr = min_rr_vals[0]
        elif avg_pct < min_rr_steps[1]:
            min_rr = min_rr_vals[1]
        elif avg_pct < min_rr_steps[2]:
            min_rr = min_rr_vals[2]
        else:
            min_rr = min_rr_vals[3]

    if retest_auto and avg_pct is not None:
        if avg_pct < retest_steps[0]:
            retest_bars = retest_vals[0]
        elif avg_pct < retest_steps[1]:
            retest_bars = retest_vals[1]
        elif avg_pct < retest_steps[2]:
            retest_bars = retest_vals[2]
        else:
            retest_bars = retest_vals[3]

    if realtime_mode and session == "auto":
        session = "all"
    if session == "auto" and candles:
        candidates = ["asia", "london", "ny"]
        best = ("all", 0.0)
        for name in candidates:
            rng = []
            for c in candles[-min(1500, len(candles)):]:
                if in_session(c["ts"], name):
                    rng.append((c["h"] - c["l"]) / max(1e-8, c["c"]))
            if rng:
                score = sum(rng) / max(1, len(rng))
                if score > best[1]:
                    best = (name, score)
        session = best[0] if best[1] > 0 else "all"

    if avg_pct is not None:
        if use_ob == "auto":
            use_ob = True
        if use_fvg == "auto":
            use_fvg = avg_pct >= fvg_on
        if use_sweep == "auto":
            use_sweep = avg_pct >= sweep_on
    if use_ob == "auto":
        use_ob = True
    if use_fvg == "auto":
        use_fvg = True
    if use_sweep == "auto":
        use_sweep = True

    if smc_swing_auto and candles:
        sample = candles[-min(500, len(candles)):]
        avg_pct = sum(((c["h"] - c["l"]) / max(1e-8, c["c"])) for c in sample) / max(1, len(sample)) * 100.0
        if avg_pct < 0.15:
            swing = 2
        elif avg_pct < 0.3:
            swing = 3
        elif avg_pct < 0.6:
            swing = 4
        elif avg_pct < 1.0:
            swing = 5
        else:
            swing = 6

    htf_highs, htf_lows = ([], [])
    if htf_candles:
        if htf_swing_auto:
            sample = htf_candles[-min(300, len(htf_candles)):]
            avg_pct = sum(((c["h"] - c["l"]) / max(1e-8, c["c"])) for c in sample) / max(1, len(sample)) * 100.0
            if avg_pct < 0.15:
                htf_swing = 2
            elif avg_pct < 0.3:
                htf_swing = 3
            elif avg_pct < 0.6:
                htf_swing = 4
            elif avg_pct < 1.0:
                htf_swing = 5
            else:
                htf_swing = 6
        htf_highs, htf_lows = compute_swings(htf_candles, htf_swing, realtime_mode)
    htf_hi_idx = 0
    htf_lo_idx = 0
    last_htf_high = None
    last_htf_low = None
    htf_trend = None

    def quantize_qty(qty: float, step: float, min_qty: float) -> float:
        if qty is None or not math.isfinite(qty):
            return 0.0
        if step is None or not math.isfinite(step) or step <= 0:
            return qty
        if min_qty is None or not math.isfinite(min_qty):
            min_qty = 0.0
        floored = math.floor(qty / step) * step
        if floored + 1e-12 < min_qty:
            return 0.0
        return round(floored, 8)

    def calc_qty(entry: float, stop: float, side: str) -> float:
        risk_cash = risk_cash_fixed if risk_cash_fixed > 0 else equity * risk_pct
        meta = fx_meta.get(symbol)
        if meta:
            tick = meta["tick_size"]
            tick_value = meta["tick_value"]
            contract = meta["contract"]
            stop_points = abs(entry - stop) / max(1e-12, tick)
            loss_per_lot = max(1e-9, stop_points * tick_value)
            lot = risk_cash / loss_per_lot
            lot = round(max(lot, 0.01), 2)
            qty = int(round(lot * contract))
            if qty <= 0:
                return 0.0
            cap_qty = math.floor(max_notional / max(1e-8, entry))
            if cap_qty > 0:
                qty = min(qty, cap_qty)
            return float(max(0, int(qty)))
        else:
            if side == "BUY":
                entry_fill = price_with_spread(entry, "BUY")
                exit_fill = price_with_spread(stop, "SELL")
                unit_loss = max(1e-8, entry_fill - exit_fill)
                unit_loss += entry_fill * fee_rate + exit_fill * fee_rate
            else:
                entry_fill = price_with_spread(entry, "SELL")
                exit_fill = price_with_spread(stop, "BUY")
                unit_loss = max(1e-8, exit_fill - entry_fill)
                unit_loss += entry_fill * fee_rate + exit_fill * fee_rate
            qty = risk_cash / unit_loss
            cap_qty = max_notional / max(1e-8, entry)
            if cap_qty > 0:
                qty = min(qty, cap_qty)
            cmeta = crypto_meta.get(symbol)
            if cmeta:
                return quantize_qty(qty, cmeta["qty_step"], cmeta["min_qty"])
            qty = math.floor(qty)
            return float(max(0, int(qty)))

    def allow_side(side: str) -> bool:
        if direction == "both":
            return True
        if direction == "long":
            return side == "BUY"
        if direction == "short":
            return side == "SELL"
        return True

    def rr_net_calc(side: str, entry_price: float, stop_price: float, tp_price: float) -> float:
        if side == "BUY":
            entry_fill = price_with_spread(entry_price, "BUY")
            tp_fill = price_with_spread(tp_price, "SELL")
            stop_fill = price_with_spread(stop_price, "SELL")
            unit_gain = (tp_fill - entry_fill) - (entry_fill * fee_rate + tp_fill * fee_rate)
            unit_loss = (entry_fill - stop_fill) + (entry_fill * fee_rate + stop_fill * fee_rate)
        else:
            entry_fill = price_with_spread(entry_price, "SELL")
            tp_fill = price_with_spread(tp_price, "BUY")
            stop_fill = price_with_spread(stop_price, "BUY")
            unit_gain = (entry_fill - tp_fill) - (entry_fill * fee_rate + tp_fill * fee_rate)
            unit_loss = (stop_fill - entry_fill) + (entry_fill * fee_rate + stop_fill * fee_rate)
        return unit_gain / max(1e-8, unit_loss)

    def create_signal(
        side: str,
        reason: str,
        entry_intent: float,
        i: int,
        bar_ts: int,
        status: str = "已触发",
        swing_high: dict | None = None,
        swing_low: dict | None = None,
        fibo_level: float | None = None,
        bar_ohlc: dict | None = None,
    ) -> int:
        nonlocal signal_seq
        signal_seq += 1
        signals.append(
            {
                "signal_id": signal_seq,
                "i": i,
                "ts": bar_ts,
                "bar_ts": bar_ts,
                "side": side,
                "reason": reason,
                "entry_intent": entry_intent,
                "status": status,
                "order_id": None,
                "trade_id": None,
                "swing_high": swing_high,
                "swing_low": swing_low,
                "fibo_level": fibo_level,
                "bar_ohlc": bar_ohlc,
            }
        )
        signal_index[signal_seq] = len(signals) - 1
        return signal_seq

    def update_signal(signal_id: int | None, status: str, trade_id: int | None = None, order_id: int | None = None, cancel_reason: str | None = None) -> None:
        if not signal_id:
            return
        idx = signal_index.get(signal_id)
        if idx is None:
            return
        signals[idx]["status"] = status
        if trade_id is not None:
            signals[idx]["trade_id"] = trade_id
        if order_id is not None:
            signals[idx]["order_id"] = order_id
        if cancel_reason is not None:
            signals[idx]["cancel_reason"] = cancel_reason

    def next_order_id() -> int:
        nonlocal order_seq
        order_seq += 1
        return order_seq

    def ensure_min_rr(side: str, entry_price: float, stop_price: float, tp_price: float) -> tuple[float, float]:
        rr_value = rr_net_calc(side, entry_price, stop_price, tp_price)
        if rr_value >= min_rr:
            return tp_price, rr_value
        target_rr = max(min_rr * 1.2, min_rr + 0.3)
        for _ in range(5):
            if side == "BUY":
                tp_price = entry_price + target_rr * (entry_price - stop_price)
            else:
                tp_price = entry_price - target_rr * (stop_price - entry_price)
            rr_value = rr_net_calc(side, entry_price, stop_price, tp_price)
            if rr_value >= min_rr:
                return tp_price, rr_value
            target_rr *= 1.35
        return tp_price, rr_value

    def pick_stop(side: str, base_stop: float, entry_price: float) -> tuple[float, bool]:
        use_swing = stop_source in ("auto", "swing", "swing_high_low")
        if use_swing:
            if side == "BUY" and swing_low:
                candidate = swing_low["price"] * (1 - stop_buffer_pct)
                if candidate < entry_price:
                    return candidate, True
            if side == "SELL" and swing_high:
                candidate = swing_high["price"] * (1 + stop_buffer_pct)
                if candidate > entry_price:
                    return candidate, True
            if stop_source == "swing":
                return base_stop, False
        return base_stop, False

    for i, bar in enumerate(candles):
        mark_price = bar["c"]
        if open_trade:
            if open_trade["side"] == "BUY":
                unreal = (mark_price - open_trade["entryPrice"]) * open_trade["qty"]
            else:
                unreal = (open_trade["entryPrice"] - mark_price) * open_trade["qty"]
            equity = cash + unreal
        else:
            equity = cash
        equity_series.append({"i": i, "equity": equity})
        swing_hi_candidate = None
        swing_lo_candidate = None

        if not open_order and pending_orders:
            for idx, pending in enumerate(pending_orders):
                if pending.get("place_i") == i:
                    pending_orders.pop(idx)
                    open_order = pending
                    order_id = next_order_id()
                    if order_type == "market" and not open_trade and pos == 0:
                        entry_base = bar.get("o", bar["c"])
                        entry_price = price_with_spread(entry_base, open_order["side"])
                        notional = abs(open_order["qty"] * entry_price)
                        fee_in = notional * fee_rate
                        spread_fee = spread_cost(open_order["qty"])
                        pos = open_order["qty"] if open_order["side"] == "BUY" else -open_order["qty"]
                        cash -= fee_in
                        fills.append(
                            {
                                "i": i,
                                "ts": bar["ts"],
                                "bar_ts": bar["ts"],
                                "side": open_order["side"],
                                "price": entry_price,
                                "fee": fee_in,
                                "spread": spread_fee,
                                "signal_id": open_order.get("signal_id"),
                                "order_id": order_id,
                            }
                        )
                        markers.append({"i": i, "bar_ts": bar["ts"], "side": open_order["side"], "price": entry_price, "label": "市价入场"})
                        orders.append(
                            {
                                "i": i,
                                "ts": bar["ts"],
                                "bar_ts": bar["ts"],
                                "side": open_order["side"],
                                "price": open_order["price"],
                                "tif": tif_bars,
                                "status": "已成交",
                                "signal_id": open_order.get("signal_id"),
                                "order_id": order_id,
                                "order_type": "market",
                            }
                        )
                        update_signal(open_order.get("signal_id"), "已成交", order_id=order_id)
                        open_trade = {
                            "side": open_order["side"],
                            "entryI": i,
                            "entryPrice": entry_price,
                            "entryTs": bar["ts"],
                            "entryReason": open_order.get("entry_reason", "demo_signal"),
                            "stop": open_order["stop"],
                            "tp": open_order["tp"],
                            "qty": open_order["qty"],
                            "feeIn": fee_in,
                            "signal_id": open_order.get("signal_id"),
                            "order_id": order_id,
                        }
                        open_order = None
                    else:
                        open_order["order_id"] = order_id
                        open_order["order_i"] = i
                        open_order["order_ts"] = bar["ts"]
                        update_signal(open_order.get("signal_id"), "已下单", order_id=order_id)
                    break

        if i >= swing and (realtime_mode or i < len(candles) - swing):
            hi = bar["h"]
            lo = bar["l"]
            if realtime_mode:
                is_hi = all(hi >= candles[j]["h"] for j in range(i - swing, i + 1))
                is_lo = all(lo <= candles[j]["l"] for j in range(i - swing, i + 1))
            else:
                is_hi = all(hi >= candles[j]["h"] for j in range(i - swing, i + swing + 1))
                is_lo = all(lo <= candles[j]["l"] for j in range(i - swing, i + swing + 1))
            if is_hi:
                swing_hi_candidate = {"i": i, "price": hi}
            if is_lo:
                swing_lo_candidate = {"i": i, "price": lo}
            if not realtime_mode:
                if swing_hi_candidate:
                    swing_high = swing_hi_candidate
                if swing_lo_candidate:
                    swing_low = swing_lo_candidate

        if htf_candles and (htf_highs or htf_lows):
            while htf_hi_idx < len(htf_highs) and htf_highs[htf_hi_idx]["ts"] <= bar["ts"]:
                last_htf_high = htf_highs[htf_hi_idx]
                htf_hi_idx += 1
            while htf_lo_idx < len(htf_lows) and htf_lows[htf_lo_idx]["ts"] <= bar["ts"]:
                last_htf_low = htf_lows[htf_lo_idx]
                htf_lo_idx += 1
            if last_htf_high and bar["c"] > last_htf_high["price"]:
                htf_trend = "bull"
            if last_htf_low and bar["c"] < last_htf_low["price"]:
                htf_trend = "bear"

        if open_trade:
            side = open_trade["side"]
            stop = open_trade["stop"]
            tp = open_trade["tp"]
            hit_stop = bar["l"] <= stop if side == "BUY" else bar["h"] >= stop
            hit_tp = bar["h"] >= tp if side == "BUY" else bar["l"] <= tp

            exit_price = None
            reason = None
            if hit_stop and hit_tp:
                if params.get("intrabar_rule") == "tp_first":
                    exit_price = tp
                    reason = "同K线冲突：先止盈"
                else:
                    exit_price = stop
                    reason = "同K线冲突：先止损"
            elif hit_stop:
                exit_price = stop
                reason = "止损"
            elif hit_tp:
                exit_price = tp
                reason = "止盈"

            if exit_price is not None:
                exit_side = "SELL" if side == "BUY" else "BUY"
                exit_price = price_with_spread(exit_price, exit_side)
                notional = abs(open_trade["qty"] * exit_price)
                fee_out = notional * fee_rate
                spread_fee = spread_cost(open_trade["qty"])
                if side == "BUY":
                    pnl = (exit_price - open_trade["entryPrice"]) * open_trade["qty"] - open_trade["feeIn"] - fee_out
                else:
                    pnl = (open_trade["entryPrice"] - exit_price) * open_trade["qty"] - open_trade["feeIn"] - fee_out
                cash += pnl
                pos = 0.0
                fills.append(
                    {
                        "i": i,
                        "ts": bar["ts"],
                        "bar_ts": bar["ts"],
                        "side": "SELL" if side == "BUY" else "BUY",
                        "price": exit_price,
                        "fee": fee_out,
                        "spread": spread_fee,
                        "signal_id": open_trade.get("signal_id"),
                        "order_id": open_trade.get("order_id"),
                    }
                )
                markers.append({"i": i, "bar_ts": bar["ts"], "side": "SELL" if side == "BUY" else "BUY", "price": exit_price, "label": reason})
                trade_id = len(trades) + 1
                trades.append(
                    {
                        "trade_id": trade_id,
                        "i": i,
                        "ts": bar["ts"],
                        "bar_ts": bar["ts"],
                        "exit_ts": bar["ts"],
                        "entry_ts": open_trade.get("entryTs", bar["ts"]),
                        "entry_reason": open_trade.get("entryReason", "demo_signal"),
                        "side": "多" if side == "BUY" else "空",
                        "entry": open_trade["entryPrice"],
                        "stop": open_trade["stop"],
                        "tp": open_trade["tp"],
                        "qty": open_trade["qty"],
                        "pnl": pnl,
                        "reason": reason,
                        "signal_id": open_trade.get("signal_id"),
                        "order_id": open_trade.get("order_id"),
                        "order_type": order_type,
                        "entry_mode": entry_mode,
                    }
                )
                update_signal(open_trade.get("signal_id"), "已完结", trade_id)
                open_trade = None

        if open_order:
            if i > open_order["expireI"]:
                orders.append(
                    {
                        "i": open_order.get("order_i", i),
                        "ts": open_order.get("order_i", i),
                        "bar_ts": open_order.get("order_ts", bar["ts"]),
                        "side": open_order["side"],
                        "price": open_order["price"],
                        "tif": tif_bars,
                        "status": "已撤单",
                        "signal_id": open_order.get("signal_id"),
                        "order_id": open_order.get("order_id"),
                        "order_type": "limit",
                    }
                )
                reason = f"挂单超时：未触达价 {fmt_price(open_order['price'])}（当K高/低 {fmt_price(bar['h'])}/{fmt_price(bar['l'])}）"
                update_signal(open_order.get("signal_id"), "已撤单", cancel_reason=reason)
                open_order = None
            else:
                hit = bar["l"] <= open_order["price"] if open_order["side"] == "BUY" else bar["h"] >= open_order["price"]
                if hit and not open_trade and pos == 0:
                    entry_price = price_with_spread(open_order["price"], open_order["side"])
                    notional = abs(open_order["qty"] * entry_price)
                    fee_in = notional * fee_rate
                    spread_fee = spread_cost(open_order["qty"])

                    pos = open_order["qty"] if open_order["side"] == "BUY" else -open_order["qty"]
                    cash -= fee_in
                    fills.append(
                        {
                            "i": i,
                            "ts": open_order.get("order_ts", bar["ts"]),
                            "bar_ts": bar["ts"],
                            "side": open_order["side"],
                            "price": entry_price,
                            "fee": fee_in,
                            "spread": spread_fee,
                            "signal_id": open_order.get("signal_id"),
                            "order_id": open_order.get("order_id"),
                        }
                    )
                    markers.append({"i": i, "bar_ts": bar["ts"], "side": open_order["side"], "price": entry_price, "label": "入场成交"})

                    open_trade = {
                        "side": open_order["side"],
                        "entryI": i,
                        "entryPrice": entry_price,
                        "entryTs": bar["ts"],
                        "entryReason": open_order.get("entry_reason", "demo_signal"),
                        "stop": open_order["stop"],
                        "tp": open_order["tp"],
                        "qty": open_order["qty"],
                        "feeIn": fee_in,
                        "signal_id": open_order.get("signal_id"),
                        "order_id": open_order.get("order_id"),
                    }
                    orders.append(
                        {
                            "i": open_order.get("order_i", i),
                            "ts": open_order.get("order_i", i),
                            "bar_ts": open_order.get("order_ts", bar["ts"]),
                            "side": open_order["side"],
                            "price": open_order["price"],
                            "tif": tif_bars,
                            "status": "已成交",
                            "signal_id": open_order.get("signal_id"),
                            "order_id": open_order.get("order_id"),
                            "order_type": "limit",
                        }
                    )
                    update_signal(open_order.get("signal_id"), "已成交")
                    open_order = None

        if pending and i <= pending.get("expireI", -1) and not open_trade and pos == 0:
            if "zone_low" not in pending or "zone_high" not in pending:
                pending = None
                continue
            prev = candles[i - 1] if i > 0 else None
            prev2 = candles[i - 2] if i > 1 else None
            zone_low = pending["zone_low"]
            zone_high = pending["zone_high"]
            side = pending["side"]
            stop = pending.get("stop")

            if stop is not None and not retest_ignore_stop_touch:
                if side == "BUY" and bar["l"] <= stop:
                    reason = f"回踩触及止损：低点 {fmt_price(bar['l'])} <= 止损 {fmt_price(stop)}"
                    update_signal(pending.get("signal_id"), "已撤单", cancel_reason=reason)
                    pending = None
                    continue
                if side == "SELL" and bar["h"] >= stop:
                    reason = f"回踩触及止损：高点 {fmt_price(bar['h'])} >= 止损 {fmt_price(stop)}"
                    update_signal(pending.get("signal_id"), "已撤单", cancel_reason=reason)
                    pending = None
                    continue

            touched = bar["l"] <= zone_high and bar["h"] >= zone_low
            if touched and not pending.get("touched"):
                pending["touched"] = True
                pending["touch_i"] = i

            if pending.get("touched"):
                rej = detect_rejection(
                    bar,
                    prev,
                    prev2,
                    side,
                    zone_low,
                    zone_high,
                    True,
                    allow_engulf,
                    pinbar_ratio,
                )
                if rej["close_reject"] and (rej["pinbar"] or rej["engulf"] or rej["morning_star"] or rej["evening_star"]):
                    side = pending["side"]
                    entry = pending["entry"]
                    stop = pending["stop"]
                    tp = pending["tp"]
                    qty = calc_qty(entry, stop, side)
                    if qty > 0:
                        order_id = next_order_id()
                        update_signal(pending.get("signal_id"), "已成交", order_id=order_id)
                        entry_fill = price_with_spread(entry, side)
                        notional = abs(qty * entry_fill)
                        fee_in = notional * fee_rate
                        spread_fee = spread_cost(qty)
                        pos = qty if side == "BUY" else -qty
                        cash -= fee_in
                        fills.append(
                            {
                                "i": i,
                                "ts": bar["ts"],
                                "bar_ts": bar["ts"],
                                "side": side,
                                "price": entry_fill,
                                "fee": fee_in,
                                "spread": spread_fee,
                                "signal_id": pending.get("signal_id"),
                                "order_id": order_id,
                            }
                        )
                        markers.append({"i": i, "bar_ts": bar["ts"], "side": side, "price": entry_fill, "label": "入场成交"})
                        orders.append(
                            {
                                "i": i,
                                "ts": bar["ts"],
                                "bar_ts": bar["ts"],
                                "side": side,
                                "price": entry,
                                "tif": tif_bars,
                                "status": "已成交",
                                "signal_id": pending.get("signal_id"),
                                "order_id": order_id,
                                "order_type": "market" if order_type == "market" else "limit",
                            }
                        )
                        open_trade = {
                            "side": side,
                            "entryI": i,
                            "entryPrice": entry_fill,
                            "entryTs": bar["ts"],
                            "entryReason": pending.get("entry_reason", "SMC+RETEST"),
                            "stop": stop,
                            "tp": tp,
                            "qty": qty,
                            "feeIn": fee_in,
                            "signal_id": pending.get("signal_id"),
                            "order_id": order_id,
                        }
                        if not pending.get("zone_id"):
                            order_zones.append({"i": i, "bar_ts": bar["ts"], "side": side, "entry": entry, "stop": stop, "tp": tp, "expireI": i + tif_bars})
                        pending = None
            if pending and i >= pending["expireI"]:
                if retest_cancel_order:
                    orders.append(
                        {
                            "i": i,
                            "ts": bar["ts"],
                            "bar_ts": bar["ts"],
                            "side": pending["side"],
                            "price": pending["entry"],
                            "tif": retest_bars,
                            "status": "已撤单",
                            "signal_id": pending.get("signal_id"),
                            "order_id": pending.get("order_id"),
                            "order_type": "market" if order_type == "market" else "limit",
                        }
                    )
                if pending.get("zone_low") is not None and pending.get("zone_high") is not None:
                    reason = f"回踩超时：未触达区间[{fmt_price(pending['zone_low'])},{fmt_price(pending['zone_high'])}]"
                else:
                    reason = "回踩超时：未触达确认区间"
                update_signal(pending.get("signal_id"), "已撤单", cancel_reason=reason)
                pending = None

        if not open_order and not open_trade and pos == 0 and not pending and swing_high and swing_low and in_session(bar["ts"], session):
            if cooldown_bars and (i - last_entry_i) < cooldown_bars:
                continue
            use_wick_break = fibo_mode
            up_break = bar["h"] > swing_high["price"] if use_wick_break else bar["c"] > swing_high["price"]
            down_break = bar["l"] < swing_low["price"] if use_wick_break else bar["c"] < swing_low["price"]

            bos = None
            if up_break:
                bos = "BUY"
                trend = "bull"
            elif down_break:
                bos = "SELL"
                trend = "bear"

            choch = None
            if trend == "bull" and down_break:
                choch = "SELL"
                trend = "bear"
            elif trend == "bear" and up_break:
                choch = "BUY"
                trend = "bull"

            side = None
            if structure == "bos":
                side = bos
            elif structure == "choch":
                side = choch
            else:
                side = bos or choch
            fibo_side_fallback = False
            if fibo_mode and fibo_fallback and not side:
                trend_base = htf_trend or trend
                if trend_base == "bull":
                    side = "BUY"
                    fibo_side_fallback = True
                elif trend_base == "bear":
                    side = "SELL"
                    fibo_side_fallback = True

            if not side:
                continue
            bias_trend = htf_trend or trend
            if bias == "with_trend":
                if bias_trend == "bull" and side != "BUY":
                    continue
                if bias_trend == "bear" and side != "SELL":
                    continue
            elif bias == "counter":
                if bias_trend == "bull" and side != "SELL":
                    continue
                if bias_trend == "bear" and side != "BUY":
                    continue

            if not allow_side(side):
                continue

            if fibo_mode:
                if not swing_high or not swing_low:
                    continue
                swing_range = swing_high["price"] - swing_low["price"]
                if swing_range <= 0:
                    continue
                mid_price = (swing_high["price"] + swing_low["price"]) / 2.0
                if fibo_side_fallback:
                    if side == "BUY" and bar["l"] > mid_price:
                        continue
                    if side == "SELL" and bar["h"] < mid_price:
                        continue
                fib_candidates = []
                for level in fibo_levels:
                    if side == "BUY":
                        entry = swing_high["price"] - swing_range * level
                        if entry > mid_price:
                            continue
                        base_stop = swing_low["price"] * (1 - stop_buffer_pct)
                        tp = swing_high["price"]
                    else:
                        entry = swing_low["price"] + swing_range * level
                        if entry < mid_price:
                            continue
                        base_stop = swing_high["price"] * (1 + stop_buffer_pct)
                        tp = swing_low["price"]
                    stop, stop_used_swing = pick_stop(side, base_stop, entry)
                    if entry == stop:
                        continue
                    tp, rr_value = ensure_min_rr(side, entry, stop, tp)
                    if rr_value < min_rr:
                        continue
                    fib_candidates.append((rr_value, entry, stop, tp, level, stop_used_swing))
                if not fib_candidates:
                    entry = mid_price
                    if side == "BUY":
                        base_stop = swing_low["price"] * (1 - stop_buffer_pct)
                        tp = swing_high["price"]
                    else:
                        base_stop = swing_high["price"] * (1 + stop_buffer_pct)
                        tp = swing_low["price"]
                    stop, stop_used_swing = pick_stop(side, base_stop, entry)
                    if entry != stop:
                        tp, rr_value = ensure_min_rr(side, entry, stop, tp)
                        if rr_value >= min_rr:
                            fib_candidates.append((rr_value, entry, stop, tp, 0.5, stop_used_swing))
                if not fib_candidates:
                    continue
                fib_candidates.sort(key=lambda x: x[0], reverse=True)
                rr_value, entry, stop, tp, level, stop_used_swing = fib_candidates[0]
                if rr_value < min_rr:
                    tp, rr_value = ensure_min_rr(side, entry, stop, tp)
                    if rr_value < min_rr:
                        continue
                zone_low = min(entry, stop)
                zone_high = max(entry, stop)

                structure_label = "结构突破" if bos and side == bos else ("结构反转" if choch and side == choch else "结构信号")
                bias_label = "顺势" if bias == "with_trend" else ("逆势" if bias == "counter" else "不限制")
                confirm_label = "回踩确认" if confirm_mode == "retest" else "限价挂单"
                discount_label = "折价区" if side == "BUY" else "溢价区"
                entry_label = f"{discount_label}｜FIB {level:.3f}".rstrip("0").rstrip(".")
                stop_label = "止损:前高/前低" if stop_used_swing else "止损:结构"
                entry_reason = f"{bias_label}｜{structure_label}｜{entry_label}｜{confirm_label}｜{stop_label}"

                if confirm_mode == "retest":
                    signal_id = create_signal(
                        side,
                        entry_reason,
                        entry,
                        i,
                        bar["ts"],
                        status="等待确认",
                        swing_high=swing_high,
                        swing_low=swing_low,
                        fibo_level=level,
                        bar_ohlc=bar,
                    )
                    pending = {
                        "side": side,
                        "entry": entry,
                        "stop": stop,
                        "tp": tp,
                        "zone_low": zone_low,
                        "zone_high": zone_high,
                        "expireI": i + retest_bars,
                        "entry_reason": entry_reason,
                        "zone_id": f"pending_{i}_{side}",
                        "signal_id": signal_id,
                    }
                    order_zones.append({"i": i, "bar_ts": bar["ts"], "side": side, "entry": entry, "stop": stop, "tp": tp, "expireI": i + retest_bars, "entry_reason": entry_reason, "zone_id": pending["zone_id"]})
                    markers.append({"i": i, "bar_ts": bar["ts"], "side": side, "price": entry, "label": "挂单生成", "reason": entry_reason})
                    last_entry_i = i
                    continue

                qty = calc_qty(entry, stop, side)
                if qty <= 0:
                    continue
                signal_id = create_signal(
                    side,
                    entry_reason,
                    entry,
                    i,
                    bar["ts"],
                    swing_high=swing_high,
                    swing_low=swing_low,
                    fibo_level=level,
                    bar_ohlc=bar,
                )
                order_draft = {
                    "side": side,
                    "price": entry,
                    "stop": stop,
                    "tp": tp,
                    "qty": qty,
                    "expireI": i + 1 + tif_bars,
                    "entry_reason": entry_reason,
                    "signal_id": signal_id,
                }
                pending_orders.append({**order_draft, "place_i": i + 1})
                order_zones.append({"i": i, "bar_ts": bar["ts"], "side": side, "entry": entry, "stop": stop, "tp": tp, "expireI": order_draft["expireI"], "entry_reason": entry_reason})
                markers.append({"i": i, "bar_ts": bar["ts"], "side": side, "price": entry, "label": "挂单生成", "reason": entry_reason})
                last_entry_i = i

            ob = None
            if use_ob:
                for k in range(i - 1, max(-1, i - ob_lookback - 1), -1):
                    if k < 0:
                        break
                    c = candles[k]
                    if side == "BUY":
                        if ob_type == "reversal" and c["c"] < c["o"]:
                            ob = c
                            break
                        if ob_type == "continuation" and c["c"] > c["o"]:
                            ob = c
                            break
                    if side == "SELL":
                        if ob_type == "reversal" and c["c"] > c["o"]:
                            ob = c
                            break
                        if ob_type == "continuation" and c["c"] < c["o"]:
                            ob = c
                            break

            fvg = None
            if use_fvg and i >= 2:
                c0 = candles[i - 2]
                c2 = candles[i]
                if side == "BUY":
                    gap = c2["l"] - c0["h"]
                    if gap > 0 and (gap / c2["c"]) >= fvg_min_pct:
                        fvg = {"low": c0["h"], "high": c2["l"]}
                else:
                    gap = c0["l"] - c2["h"]
                    if gap > 0 and (gap / c2["c"]) >= fvg_min_pct:
                        fvg = {"low": c2["h"], "high": c0["l"]}

            sweep = None
            if use_sweep:
                allow_internal = liquidity in ("internal", "both", "none")
                allow_external = liquidity in ("external", "both", "none")
                if side == "BUY" and allow_internal and swing_low and i - swing_low["i"] <= sweep_len:
                    if bar["l"] < swing_low["price"] and bar["c"] > swing_low["price"]:
                        sweep = {"price": bar["l"]}
                if side == "SELL" and allow_internal and swing_high and i - swing_high["i"] <= sweep_len:
                    if bar["h"] > swing_high["price"] and bar["c"] < swing_high["price"]:
                        sweep = {"price": bar["h"]}
                if not sweep and allow_external:
                    if side == "BUY" and last_htf_low and bar["l"] < last_htf_low["price"] and bar["c"] > last_htf_low["price"]:
                        sweep = {"price": bar["l"]}
                    if side == "SELL" and last_htf_high and bar["h"] > last_htf_high["price"] and bar["c"] < last_htf_high["price"]:
                        sweep = {"price": bar["h"]}

            candidates = []
            allow_all = entry_source in ("auto", "any")
            require_confluence = entry_source == "confluence"
            if (allow_all or entry_source in ("ob", "confluence")) and ob and use_ob:
                if wick_ob:
                    entry = ob["l"] if side == "BUY" else ob["h"]
                else:
                    entry = ob["o"]
                stop = ob["l"] if side == "BUY" else ob["h"]
                candidates.append(("ob", entry, stop, ob["l"], ob["h"]))
            if (allow_all or entry_source in ("fvg", "confluence")) and fvg and use_fvg:
                entry = (fvg["low"] + fvg["high"]) / 2.0
                stop = fvg["low"] if side == "BUY" else fvg["high"]
                candidates.append(("fvg", entry, stop, fvg["low"], fvg["high"]))
            if (allow_all or entry_source in ("sweep", "confluence")) and sweep and use_sweep:
                entry = bar["c"]
                stop = sweep["price"]
                zone_low = min(entry, stop)
                zone_high = max(entry, stop)
                candidates.append(("sweep", entry, stop, zone_low, zone_high))

            if require_confluence and len(candidates) < 2:
                continue

            if not candidates:
                continue

            source, entry, base_stop, zone_low, zone_high = candidates[0]
            if confirm_mode == "limit" and source in ("ob", "fvg") and zone_high > zone_low:
                offset = min(max(limit_offset_pct, 0.0), 0.8)
                if side == "BUY":
                    entry = zone_low + (zone_high - zone_low) * offset
                else:
                    entry = zone_high - (zone_high - zone_low) * offset
            structure_label = "结构突破" if bos and side == bos else ("结构反转" if choch and side == choch else "结构信号")
            entry_label = {"ob": "订单块", "fvg": "FVG 缺口", "sweep": "流动性扫荡"}.get(source, source.upper())
            confirm_label = "市价入场" if confirm_mode == "market" else ("回踩确认" if confirm_mode == "retest" else "限价挂单")
            bias_label = "顺势" if bias == "with_trend" else ("逆势" if bias == "counter" else "不限制")
            liquidity_label = {
                "external": "外部流动性",
                "internal": "内部流动性",
                "both": "内外流动性",
                "none": "不限流动性",
            }.get(liquidity, "流动性过滤")
            stop, stop_used_swing = pick_stop(side, base_stop, entry)
            stop_label = "止损:前高/前低" if stop_used_swing else "止损:结构"
            entry_reason = f"{bias_label}｜{structure_label}｜{entry_label}｜{liquidity_label}｜{confirm_label}｜{stop_label}"
            if entry == stop:
                continue
            if tp_mode == "swing":
                if side == "BUY" and swing_high:
                    tp = swing_high["price"]
                elif side == "SELL" and swing_low:
                    tp = swing_low["price"]
                else:
                    continue
            else:
                tp = entry + rr * (entry - stop) if side == "BUY" else entry - rr * (stop - entry)

            rr_net = rr_net_calc(side, entry, stop, tp)
            if rr_net < min_rr:
                continue
            if confirm_mode == "retest":
                signal_id = create_signal(side, entry_reason, entry, i, bar["ts"], status="等待确认")
                pending = {
                    "side": side,
                    "entry": entry,
                    "stop": stop,
                    "tp": tp,
                    "zone_low": min(zone_low, zone_high),
                    "zone_high": max(zone_low, zone_high),
                    "expireI": i + retest_bars,
                    "entry_reason": entry_reason,
                    "zone_id": f"pending_{i}_{side}",
                    "signal_id": signal_id,
                }
                order_zones.append({"i": i, "bar_ts": bar["ts"], "side": side, "entry": entry, "stop": stop, "tp": tp, "expireI": i + retest_bars, "entry_reason": entry_reason, "zone_id": pending["zone_id"]})
                markers.append({"i": i, "bar_ts": bar["ts"], "side": side, "price": entry, "label": "挂单生成", "reason": entry_reason})
                last_entry_i = i

            elif confirm_mode == "market":
                signal_entry = entry
                if market_reject:
                    prev = candles[i - 1] if i > 0 else None
                    rej = detect_rejection(
                        bar,
                        prev,
                        None,
                        side,
                        zone_low,
                        zone_high,
                        False,
                        allow_engulf,
                        pinbar_ratio,
                    )
                    if not (rej["close_reject"] and (rej["pinbar"] or rej["engulf"])):
                        continue
                entry = bar["c"]
                if atr_values and i < len(atr_values):
                    atr = atr_values[i]
                    if atr is not None and market_max_dev_atr > 0:
                        if abs(entry - signal_entry) > atr * market_max_dev_atr:
                            continue
                stop, stop_used_swing = pick_stop(side, base_stop, entry)
                if entry == stop:
                    continue
                if tp_mode == "swing":
                    if side == "BUY" and swing_high:
                        tp = swing_high["price"]
                    elif side == "SELL" and swing_low:
                        tp = swing_low["price"]
                    else:
                        continue
                    if (side == "BUY" and tp <= entry) or (side == "SELL" and tp >= entry):
                        tp = entry + rr * (entry - stop) if side == "BUY" else entry - rr * (stop - entry)
                else:
                    tp = entry + rr * (entry - stop) if side == "BUY" else entry - rr * (stop - entry)
                rr_net = rr_net_calc(side, entry, stop, tp)
                if rr_net < min_rr:
                    target_rr = max(min_rr, rr) * 1.1
                    tp = entry + target_rr * (entry - stop) if side == "BUY" else entry - target_rr * (stop - entry)
                    rr_net = rr_net_calc(side, entry, stop, tp)
                if rr_net < min_rr:
                    continue
                qty = calc_qty(entry, stop, side)
                if qty <= 0:
                    continue
                signal_id = create_signal(side, entry_reason, signal_entry, i, bar["ts"])
                order_id = next_order_id()
                update_signal(signal_id, "已成交", order_id=order_id)
                entry_fill = price_with_spread(entry, side)
                notional = abs(qty * entry_fill)
                fee_in = notional * fee_rate
                spread_fee = spread_cost(qty)
                pos = qty if side == "BUY" else -qty
                cash -= fee_in
                fills.append(
                    {
                        "i": i,
                        "ts": open_order.get("order_ts", last_bar["ts"]),
                        "bar_ts": bar["ts"],
                        "side": side,
                        "price": entry_fill,
                        "fee": fee_in,
                        "spread": spread_fee,
                        "signal_id": signal_id,
                        "order_id": order_id,
                    }
                )
                markers.append({"i": i, "bar_ts": bar["ts"], "side": side, "price": entry_fill, "label": "市价入场"})
                orders.append(
                    {
                        "i": i,
                        "ts": open_order.get("order_ts", last_bar["ts"]),
                        "bar_ts": bar["ts"],
                        "side": side,
                        "price": entry,
                        "tif": tif_bars,
                        "status": "已成交",
                        "signal_id": signal_id,
                        "order_id": order_id,
                        "order_type": "market",
                    }
                )
                open_trade = {
                    "side": side,
                    "entryI": i,
                    "entryPrice": entry_fill,
                    "entryTs": bar["ts"],
                    "entryReason": entry_reason,
                    "stop": stop,
                    "tp": tp,
                    "qty": qty,
                    "feeIn": fee_in,
                    "signal_id": signal_id,
                    "order_id": order_id,
                }
                order_zones.append({"i": i, "bar_ts": bar["ts"], "side": side, "entry": entry, "stop": stop, "tp": tp, "expireI": i + tif_bars})
                last_entry_i = i
            else:
                qty = calc_qty(entry, stop, side)
                if qty <= 0:
                    continue
                signal_id = create_signal(side, entry_reason, entry, i, bar["ts"])
                order_draft = {
                    "side": side,
                    "price": entry,
                    "stop": stop,
                    "tp": tp,
                    "qty": qty,
                    "expireI": i + 1 + tif_bars,
                    "entry_reason": entry_reason,
                    "signal_id": signal_id,
                }
                pending_orders.append({**order_draft, "place_i": i + 1})
                order_zones.append({"i": i, "bar_ts": bar["ts"], "side": side, "entry": entry, "stop": stop, "tp": tp, "expireI": order_draft["expireI"], "entry_reason": entry_reason})
                markers.append({"i": i, "bar_ts": bar["ts"], "side": side, "price": entry, "label": "挂单生成", "reason": entry_reason})
                last_entry_i = i

        if realtime_mode:
            if swing_hi_candidate:
                swing_high = swing_hi_candidate
            if swing_lo_candidate:
                swing_low = swing_lo_candidate

    if open_order and candles:
        last_bar = candles[-1]
        orders.append(
            {
                "i": open_order.get("order_i", len(candles) - 1),
                "ts": open_order.get("order_i", len(candles) - 1),
                "bar_ts": open_order.get("order_ts", last_bar["ts"]),
                "side": open_order["side"],
                "price": open_order["price"],
                "tif": tif_bars,
                "status": "已撤单",
                "signal_id": open_order.get("signal_id"),
                "order_id": open_order.get("order_id"),
                "order_type": "limit",
            }
        )
        reason = f"挂单超时：未触达价 {fmt_price(open_order['price'])}（当K高/低 {fmt_price(last_bar['h'])}/{fmt_price(last_bar['l'])}）"
        update_signal(open_order.get("signal_id"), "已撤单", cancel_reason=reason)
        open_order = None

    end_equity = equity_series[-1]["equity"] if equity_series else float(params.get("initial_cash", 0) or 0)
    total_return = (end_equity / (float(params.get("initial_cash", 1) or 1))) - 1.0
    peak = -1e18
    mdd = 0.0
    for p in equity_series:
        peak = max(peak, p["equity"])
        dd = (peak - p["equity"]) / peak if peak > 0 else 0.0
        mdd = max(mdd, dd)
    wins = sum(1 for t in trades if t["pnl"] > 0)
    win_rate = (wins / len(trades)) if trades else 0.0

    return {
        "equitySeries": equity_series,
        "signals": signals,
        "orders": orders,
        "fills": fills,
        "trades": trades,
        "markers": markers,
        "orderZones": order_zones,
        "metrics": {"totalReturn": total_return, "mdd": mdd, "trades": len(trades), "winRate": win_rate},
    }
