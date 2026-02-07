#!/usr/bin/env python3
"""
15m 快速优化器 — 精简版
Phase 1: TP/SL 重点组合 (16组)
Phase 2: Top3 × 冷却+ADX (36组)
"""

import sys, os, json, time
from itertools import product

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy

SYMBOL = "ETH/USDT"
TIMEFRAME = "15m"


def load_candles():
    with open("/tmp/eth_usdt_1y_15m.json") as f:
        return json.load(f)


def run_one(candles, sc, ec):
    s = get_strategy("market_regime", sc)
    e = BacktestEngine(**ec)
    return e.run(strategy=s, symbol=SYMBOL, timeframe=TIMEFRAME, candles=candles, lookback=100)


def score(r):
    if r.max_drawdown_pct <= 0 or r.profit_factor <= 0:
        return -999
    return r.total_pnl_pct * r.profit_factor / max(r.max_drawdown_pct, 1)


def main():
    candles = load_candles()
    t0 = time.time()
    print(f"15m 快速优化 | K线 {len(candles)} 根\n")

    ec = {"initial_balance": 2000, "commission_rate": 0.0005, "amount_usdt": 200, "leverage": 20, "margin_mode": "isolated"}

    # Phase 1: TP/SL 重点 (精简到16组)
    combos = [
        (0.40, 0.20), (0.40, 0.30), (0.50, 0.25), (0.50, 0.40),
        (0.60, 0.20), (0.60, 0.30), (0.60, 0.40), (0.80, 0.20),
        (0.80, 0.30), (0.80, 0.40), (1.00, 0.25), (1.00, 0.30),
        (1.00, 0.40), (1.20, 0.30), (1.20, 0.40), (1.50, 0.40),
    ]

    print(f"Phase 1: {len(combos)} 组 TP/SL (冷却20, MACD+量比)")
    print(f"{'TP':>5} {'SL':>5} {'收益':>8} {'回撤':>7} {'盈亏比':>7} {'因子':>6} {'胜率':>6} {'笔':>5} {'评分':>7}")
    print(f"{'─'*62}")

    p1 = []
    for tp, sl in combos:
        sc = {
            "sl_tp_mode": "margin_pct", "leverage": 20, "max_position": 1000, "risk_pct": 0.01,
            "tp_pct": tp, "sl_pct": sl, "macd_filter": True, "volume_filter": True,
            "volume_min_ratio": 1.0, "cooldown_bars": 20,
        }
        r = run_one(candles, sc, ec)
        s = score(r)
        p1.append({"tp": tp, "sl": sl, "pnl_pct": r.total_pnl_pct, "dd_pct": r.max_drawdown_pct,
                    "rr": r.risk_reward_ratio, "pf": r.profit_factor, "wr": r.win_rate,
                    "trades": r.total_trades, "score": s})
        print(f"{tp:>5.2f} {sl:>5.2f} {r.total_pnl_pct:>+7.1f}% {r.max_drawdown_pct:>6.1f}% "
              f"{r.risk_reward_ratio:>7.2f} {r.profit_factor:>6.2f} {r.win_rate:>5.1f}% {r.total_trades:>5} {s:>7.2f}")

    p1.sort(key=lambda x: x["score"], reverse=True)
    top3 = p1[:3]

    # Phase 2: Top3 × 冷却 × ADX (36组)
    cds = [12, 20, 30, 48]
    adxs = [(25, 15), (35, 15), (35, 20)]

    print(f"\nPhase 2: Top3 × 冷却 × ADX ({len(top3)*len(cds)*len(adxs)} 组)")
    print(f"{'TP':>5} {'SL':>5} {'ADX':>8} {'冷却':>4} {'收益':>8} {'回撤':>7} {'盈亏比':>7} {'因子':>6} {'胜率':>6} {'笔':>5} {'评分':>7}")
    print(f"{'─'*72}")

    p2 = []
    for t in top3:
        for (at, ar), cd in product(adxs, cds):
            sc = {
                "sl_tp_mode": "margin_pct", "leverage": 20, "max_position": 1000, "risk_pct": 0.01,
                "tp_pct": t["tp"], "sl_pct": t["sl"], "macd_filter": True, "volume_filter": True,
                "volume_min_ratio": 1.0, "cooldown_bars": cd, "adx_trend_threshold": at, "adx_range_threshold": ar,
            }
            r = run_one(candles, sc, ec)
            s = score(r)
            p2.append({"tp": t["tp"], "sl": t["sl"], "adx_t": at, "adx_r": ar, "cd": cd,
                        "pnl_pct": r.total_pnl_pct, "dd_pct": r.max_drawdown_pct, "rr": r.risk_reward_ratio,
                        "pf": r.profit_factor, "wr": r.win_rate, "trades": r.total_trades, "score": s})
            adx_s = f"{at}/{ar}"
            print(f"{t['tp']:>5.2f} {t['sl']:>5.2f} {adx_s:>8} {cd:>4} {r.total_pnl_pct:>+7.1f}% "
                  f"{r.max_drawdown_pct:>6.1f}% {r.risk_reward_ratio:>7.2f} {r.profit_factor:>6.2f} "
                  f"{r.win_rate:>5.1f}% {r.total_trades:>5} {s:>7.2f}")

    p2.sort(key=lambda x: x["score"], reverse=True)
    c = p2[0]

    # 仓位快速测试
    print(f"\nPhase 3: 冠军仓位 (TP{c['tp']}/SL{c['sl']} ADX{c['adx_t']}/{c['adx_r']} CD{c['cd']})")
    print(f"{'仓位':>5} {'保证金':>6} {'收益':>8} {'净赚':>8} {'回撤':>7} {'因子':>6}")
    print(f"{'─'*48}")
    for pos in [100, 200, 400, 600]:
        sc = {
            "sl_tp_mode": "margin_pct", "leverage": 20, "max_position": 1000, "risk_pct": 0.01,
            "tp_pct": c["tp"], "sl_pct": c["sl"], "macd_filter": True, "volume_filter": True,
            "volume_min_ratio": 1.0, "cooldown_bars": c["cd"],
            "adx_trend_threshold": c["adx_t"], "adx_range_threshold": c["adx_r"],
        }
        ec2 = {**ec, "amount_usdt": pos}
        r = run_one(candles, sc, ec2)
        print(f"{pos:>5} {pos/20:>6.0f} {r.total_pnl_pct:>+7.1f}% {r.total_pnl:>+7.0f} "
              f"{r.max_drawdown_pct:>6.1f}% {r.profit_factor:>6.2f}")

    elapsed = time.time() - t0
    print(f"\n{'='*72}")
    print(f"  15m 最优: TP={c['tp']:.2f} SL={c['sl']:.2f} ADX>{c['adx_t']} CD={c['cd']}bar({c['cd']*15}min)")
    print(f"  收益: {c['pnl_pct']:+.1f}%  回撤: {c['dd_pct']:.1f}%  盈亏比: {c['rr']:.2f}  因子: {c['pf']:.2f}")
    print(f"  耗时: {elapsed:.0f}s  合计: {len(p1)+len(p2)+4} 组")
    print(f"{'='*72}")


if __name__ == "__main__":
    main()
