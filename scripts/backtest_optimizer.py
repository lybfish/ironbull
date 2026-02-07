#!/usr/bin/env python3
"""
策略参数优化器 — 网格搜索

Phase 1: TP/SL 网格 (30组)
Phase 2: Top5 × ADX阈值 × 冷却 (80组)
Phase 3: 冠军精调 (仓位/杠杆/量比阈值)
"""

import sys, os, json, time
from itertools import product

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy

SYMBOL = "ETH/USDT"
TIMEFRAME = "1h"


def load_candles():
    with open("/tmp/eth_usdt_1y_1h.json") as f:
        return json.load(f)


def run_one(candles, strategy_cfg, engine_cfg):
    strategy = get_strategy("market_regime", strategy_cfg)
    engine = BacktestEngine(**engine_cfg)
    r = engine.run(strategy=strategy, symbol=SYMBOL, timeframe=TIMEFRAME, candles=candles, lookback=100)
    return r


def score(r):
    """综合评分: 收益率 × 盈利因子 / 回撤率（越高越好）"""
    if r.max_drawdown_pct <= 0 or r.profit_factor <= 0:
        return -999
    return r.total_pnl_pct * r.profit_factor / max(r.max_drawdown_pct, 1)


def main():
    candles = load_candles()
    t0 = time.time()

    print("=" * 90)
    print("  策略参数优化器 (ETH/USDT 1h)")
    print(f"  K线 {len(candles)} 根  |  {candles[0]['timestamp'][:10]} ~ {candles[-1]['timestamp'][:10]}")
    print("=" * 90)

    base_engine = {
        "initial_balance": 2000,
        "commission_rate": 0.0005,
        "amount_usdt": 200,
        "leverage": 20,
        "margin_mode": "isolated",
    }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Phase 1: TP / SL 网格搜索
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print(f"\n{'─' * 90}")
    print(f"  Phase 1: TP/SL 网格 (MACD+量比+冷却5 固定)")
    print(f"{'─' * 90}")

    tp_range = [0.60, 0.80, 1.00, 1.20, 1.50, 2.00]
    sl_range = [0.20, 0.30, 0.40, 0.50, 0.60, 0.80]

    phase1 = []
    total = len(tp_range) * len(sl_range)
    done = 0

    for tp, sl in product(tp_range, sl_range):
        sc = {
            "sl_tp_mode": "margin_pct", "leverage": 20,
            "max_position": 1000, "risk_pct": 0.01,
            "tp_pct": tp, "sl_pct": sl,
            "macd_filter": True, "volume_filter": True,
            "volume_min_ratio": 1.0, "cooldown_bars": 5,
        }
        r = run_one(candles, sc, base_engine)
        s = score(r)
        phase1.append({
            "tp": tp, "sl": sl, "pnl_pct": r.total_pnl_pct,
            "dd_pct": r.max_drawdown_pct, "rr": r.risk_reward_ratio,
            "pf": r.profit_factor, "wr": r.win_rate, "trades": r.total_trades,
            "score": s, "expect": r.expectancy,
        })
        done += 1
        if done % 6 == 0:
            print(f"    {done}/{total}...", flush=True)

    # 排序
    phase1.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n  Phase 1 Top 10:")
    print(f"  {'TP':>5} {'SL':>5} {'收益率':>8} {'回撤':>7} {'盈亏比':>7} {'盈利因子':>8} {'胜率':>7} {'交易':>5} {'期望值':>8} {'评分':>8}")
    print(f"  {'─' * 80}")
    for p in phase1[:10]:
        print(f"  {p['tp']:>5.2f} {p['sl']:>5.2f} {p['pnl_pct']:>+7.1f}% {p['dd_pct']:>6.1f}% "
              f"{p['rr']:>7.2f} {p['pf']:>8.2f} {p['wr']:>6.1f}% {p['trades']:>5} "
              f"{p['expect']:>+7.2f} {p['score']:>8.2f}")

    print(f"\n  Phase 1 Bottom 5:")
    for p in phase1[-5:]:
        print(f"  TP{p['tp']:.2f}/SL{p['sl']:.2f}  收益{p['pnl_pct']:+.1f}%  回撤{p['dd_pct']:.1f}%")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Phase 2: Top5 × ADX阈值 × 冷却
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print(f"\n{'─' * 90}")
    print(f"  Phase 2: Top5 × ADX阈值 × 冷却")
    print(f"{'─' * 90}")

    top5 = phase1[:5]
    adx_combos = [(25, 15), (30, 15), (35, 15), (35, 20), (40, 15), (40, 20)]
    cooldown_range = [0, 3, 5, 8, 12]
    skip_range = [False, True]

    phase2 = []
    total2 = len(top5) * len(adx_combos) * len(cooldown_range) * len(skip_range)
    done2 = 0

    for p1 in top5:
        for (adx_t, adx_r), cd, skip in product(adx_combos, cooldown_range, skip_range):
            sc = {
                "sl_tp_mode": "margin_pct", "leverage": 20,
                "max_position": 1000, "risk_pct": 0.01,
                "tp_pct": p1["tp"], "sl_pct": p1["sl"],
                "macd_filter": True, "volume_filter": True,
                "volume_min_ratio": 1.0, "cooldown_bars": cd,
                "adx_trend_threshold": adx_t,
                "adx_range_threshold": adx_r,
                "skip_ranging": skip,
            }
            ec = {**base_engine}
            if skip:
                ec["hedge_mode"] = False
            r = run_one(candles, sc, ec)
            s = score(r)
            phase2.append({
                "tp": p1["tp"], "sl": p1["sl"],
                "adx_t": adx_t, "adx_r": adx_r,
                "cd": cd, "skip": skip,
                "pnl_pct": r.total_pnl_pct, "dd_pct": r.max_drawdown_pct,
                "rr": r.risk_reward_ratio, "pf": r.profit_factor,
                "wr": r.win_rate, "trades": r.total_trades,
                "score": s, "expect": r.expectancy,
            })
            done2 += 1
            if done2 % 30 == 0:
                print(f"    {done2}/{total2}...", flush=True)

    phase2.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n  Phase 2 Top 15:")
    print(f"  {'TP':>5} {'SL':>5} {'ADX':>8} {'冷却':>4} {'模式':>6} {'收益率':>8} {'回撤':>7} {'盈亏比':>7} {'因子':>6} {'胜率':>6} {'笔':>4} {'期望':>7} {'评分':>8}")
    print(f"  {'─' * 95}")
    for p in phase2[:15]:
        mode = "趋势" if p["skip"] else "对冲"
        adx_s = f"{p['adx_t']}/{p['adx_r']}"
        print(f"  {p['tp']:>5.2f} {p['sl']:>5.2f} {adx_s:>8} {p['cd']:>4} {mode:>6} "
              f"{p['pnl_pct']:>+7.1f}% {p['dd_pct']:>6.1f}% {p['rr']:>7.2f} "
              f"{p['pf']:>6.2f} {p['wr']:>5.1f}% {p['trades']:>4} {p['expect']:>+6.2f} {p['score']:>8.2f}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Phase 3: 冠军精调（仓位大小 / 杠杆 / 量比阈值）
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    champ = phase2[0]
    print(f"\n{'─' * 90}")
    print(f"  Phase 3: 冠军精调 (TP{champ['tp']}/SL{champ['sl']} ADX{champ['adx_t']}/{champ['adx_r']} CD{champ['cd']})")
    print(f"{'─' * 90}")

    leverage_range = [10, 20, 50]
    pos_range = [100, 200, 400, 600]
    vol_range = [0.8, 1.0, 1.2, 1.5]

    phase3 = []
    for lev, pos, vol_min in product(leverage_range, pos_range, vol_range):
        margin = pos / lev
        sc = {
            "sl_tp_mode": "margin_pct", "leverage": lev,
            "max_position": 1000, "risk_pct": 0.01,
            "tp_pct": champ["tp"], "sl_pct": champ["sl"],
            "macd_filter": True, "volume_filter": True,
            "volume_min_ratio": vol_min, "cooldown_bars": champ["cd"],
            "adx_trend_threshold": champ["adx_t"],
            "adx_range_threshold": champ["adx_r"],
            "skip_ranging": champ["skip"],
        }
        ec = {
            "initial_balance": 2000,
            "commission_rate": 0.0005,
            "amount_usdt": pos,
            "leverage": lev,
            "margin_mode": "isolated",
        }
        if champ["skip"]:
            ec["hedge_mode"] = False
        r = run_one(candles, sc, ec)
        s = score(r)
        phase3.append({
            "lev": lev, "pos": pos, "vol_min": vol_min,
            "margin": margin,
            "pnl_pct": r.total_pnl_pct, "dd_pct": r.max_drawdown_pct,
            "rr": r.risk_reward_ratio, "pf": r.profit_factor,
            "wr": r.win_rate, "trades": r.total_trades,
            "score": s, "expect": r.expectancy,
            "final": r.final_balance, "pnl": r.total_pnl,
        })

    phase3.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n  Phase 3 Top 10:")
    print(f"  {'杠杆':>4} {'仓位':>5} {'保证金':>6} {'量比':>5} {'收益率':>8} {'净赚':>8} {'回撤':>7} {'因子':>6} {'交易':>4} {'期望':>7} {'评分':>8}")
    print(f"  {'─' * 80}")
    for p in phase3[:10]:
        print(f"  {p['lev']:>3}X {p['pos']:>5} {p['margin']:>6.0f} {p['vol_min']:>5.1f} "
              f"{p['pnl_pct']:>+7.1f}% {p['pnl']:>+7.0f} {p['dd_pct']:>6.1f}% "
              f"{p['pf']:>6.2f} {p['trades']:>4} {p['expect']:>+6.2f} {p['score']:>8.2f}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 最终推荐
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    best = phase3[0]
    # 也找收益率最高的
    best_pnl = max(phase3, key=lambda x: x["pnl_pct"])
    # 也找回撤最低的正收益
    pos_results = [p for p in phase3 if p["pnl_pct"] > 0]
    best_safe = min(pos_results, key=lambda x: x["dd_pct"]) if pos_results else best

    elapsed = time.time() - t0

    print(f"\n{'=' * 90}")
    print(f"  优化完成! 耗时 {elapsed:.0f}s")
    print(f"  Phase1: {len(phase1)}组  Phase2: {len(phase2)}组  Phase3: {len(phase3)}组")
    print(f"  合计测试: {len(phase1) + len(phase2) + len(phase3)} 组参数")
    print(f"{'=' * 90}")

    print(f"\n  ★ 综合最优:")
    print(f"    TP={champ['tp']:.2f}  SL={champ['sl']:.2f}  ADX趋势>{champ['adx_t']}  ADX震荡<{champ['adx_r']}")
    print(f"    冷却={champ['cd']}bar  模式={'纯趋势' if champ['skip'] else '对冲+趋势'}")
    print(f"    杠杆={best['lev']}X  仓位={best['pos']}  保证金={best['margin']:.0f}  量比>{best['vol_min']}")
    print(f"    收益率: {best['pnl_pct']:+.2f}%  净赚: {best['pnl']:+.0f} USDT")
    print(f"    回撤: {best['dd_pct']:.1f}%  盈亏比: {best['rr']:.2f}  盈利因子: {best['pf']:.2f}")

    print(f"\n  ★ 最高收益:")
    print(f"    杠杆={best_pnl['lev']}X  仓位={best_pnl['pos']}  量比>{best_pnl['vol_min']}")
    print(f"    收益率: {best_pnl['pnl_pct']:+.2f}%  净赚: {best_pnl['pnl']:+.0f}  回撤: {best_pnl['dd_pct']:.1f}%")

    print(f"\n  ★ 最稳健:")
    print(f"    杠杆={best_safe['lev']}X  仓位={best_safe['pos']}  量比>{best_safe['vol_min']}")
    print(f"    收益率: {best_safe['pnl_pct']:+.2f}%  净赚: {best_safe['pnl']:+.0f}  回撤: {best_safe['dd_pct']:.1f}%")

    print(f"\n{'=' * 90}\n")


if __name__ == "__main__":
    main()
