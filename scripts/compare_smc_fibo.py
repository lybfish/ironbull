#!/usr/bin/env python3
"""
Compare old1 smc_backtest vs current SMCFiboStrategy.

Usage:
  PYTHONPATH=. python3 scripts/compare_smc_fibo.py \
    --candles ./tmp/candles.json \
    --params ./tmp/smc_params.json \
    --timeframe 15m \
    --htf-timeframe 1h

candles.json format (array):
  [{"timestamp": 1700000000, "open":..., "high":..., "low":..., "close":..., "volume":...}, ...]
params.json format:
  {"strategy": "smc_fibo", "risk_cash": 100, "rr": 2, "smc": {...}}
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# old1 smc_backtest (add old1 scripts to path)
OLD1_DIR = Path(__file__).resolve().parent.parent / "_legacy_readonly" / "old1" / "1.trade.7w1.top" / "scripts"
sys.path.insert(0, str(OLD1_DIR))
from backtest_engine import smc_backtest  # type: ignore

# current strategy
from libs.strategies.smc_fibo import SMCFiboStrategy


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--candles", required=True, help="Path to candles.json")
    p.add_argument("--params", required=True, help="Path to params.json")
    p.add_argument("--timeframe", default="15m")
    p.add_argument("--htf-timeframe", default="1h")
    p.add_argument("--max-bars", type=int, default=2000)
    return p.parse_args()


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def to_old1(candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for c in candles:
        out.append({
            "ts": int(c.get("timestamp")),
            "o": float(c.get("open")),
            "h": float(c.get("high")),
            "l": float(c.get("low")),
            "c": float(c.get("close")),
            "v": float(c.get("volume", 0)),
        })
    return out


def to_new(candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for c in candles:
        out.append({
            "time": c.get("timestamp"),
            "open": float(c.get("open")),
            "high": float(c.get("high")),
            "low": float(c.get("low")),
            "close": float(c.get("close")),
            "volume": float(c.get("volume", 0)),
        })
    return out


def tf_to_seconds(tf: str) -> int:
    t = tf.lower()
    if t.endswith("m"):
        return int(t[:-1]) * 60
    if t.endswith("h"):
        return int(t[:-1]) * 3600
    if t.endswith("d"):
        return int(t[:-1]) * 86400
    return 60


def aggregate_htf(candles: List[Dict[str, Any]], ltf: str, htf: str) -> List[Dict[str, Any]]:
    ltf_sec = tf_to_seconds(ltf)
    htf_sec = tf_to_seconds(htf)
    if htf_sec <= ltf_sec:
        return []
    step = htf_sec // ltf_sec
    out = []
    for i in range(0, len(candles) - step + 1, step):
        chunk = candles[i:i+step]
        out.append({
            "ts": chunk[0]["ts"],
            "o": chunk[0]["o"],
            "h": max(x["h"] for x in chunk),
            "l": min(x["l"] for x in chunk),
            "c": chunk[-1]["c"],
            "v": sum(x["v"] for x in chunk),
        })
    return out


def summarize_old1(result: Dict[str, Any]) -> Dict[str, Any]:
    signals = result.get("signals") or []
    orders = result.get("orders") or []
    trades = result.get("trades") or []
    return {
        "signals": len(signals),
        "orders": len(orders),
        "trades": len(trades),
        "last_signal": signals[-1] if signals else None,
    }


def summarize_new(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "signals": len(signals),
        "last_signal": signals[-1] if signals else None,
    }


def main() -> int:
    args = parse_args()
    candles_raw = load_json(args.candles)
    if isinstance(candles_raw, dict) and "candles" in candles_raw:
        candles_raw = candles_raw["candles"]
    params = load_json(args.params)

    candles_raw = candles_raw[: args.max_bars]

    # old1
    old1_candles = to_old1(candles_raw)
    htf = aggregate_htf(old1_candles, args.timeframe, args.htf_timeframe)
    old1_result = smc_backtest(params, old1_candles, htf_candles=htf)

    # new
    new_candles = to_new(candles_raw)
    strategy = SMCFiboStrategy(params)
    new_signals = []
    for i in range(len(new_candles)):
        window = new_candles[: i + 1]
        sig = strategy.analyze(symbol=params.get("symbol", ""), timeframe=args.timeframe, candles=window)
        if sig:
            new_signals.append({
                "index": i,
                "signal": sig.__dict__,
            })

    print("=== Old1 Summary ===")
    print(json.dumps(summarize_old1(old1_result), indent=2, ensure_ascii=False))
    print("\n=== New Summary ===")
    print(json.dumps(summarize_new(new_signals), indent=2, ensure_ascii=False))

    print("\n=== Old1 Last Signal ===")
    if (old1_result.get("signals") or []):
        print(json.dumps(old1_result.get("signals")[-1], indent=2, ensure_ascii=False))
    else:
        print("null")

    print("\n=== New Last Signal ===")
    if new_signals:
        print(json.dumps(new_signals[-1], indent=2, ensure_ascii=False))
    else:
        print("null")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
