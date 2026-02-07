#!/usr/bin/env python3
"""
多币种回测对比 — H8 方案 (MACD+量比+冷却5, TP120%/SL40%)

币种: ETH, BTC, SOL, DOGE, XRP, BNB, AVAX, LINK
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy


TIMEFRAME = "1h"
LEVERAGE = 20
BALANCE = 2000
POS_VAL = 200

SYMBOLS = [
    "ETH/USDT",
    "BTC/USDT",
    "SOL/USDT",
    "DOGE/USDT",
    "XRP/USDT",
    "BNB/USDT",
    "AVAX/USDT",
    "LINK/USDT",
]


def load_candles(symbol):
    """加载/下载 K 线数据"""
    safe_name = symbol.replace("/", "_").lower()
    path = f"/tmp/{safe_name}_1y_1h.json"

    if not os.path.exists(path):
        print(f"  下载 {symbol} 1h 数据...", end="", flush=True)
        import ccxt
        from datetime import datetime, timedelta
        exchange = ccxt.binance({"enableRateLimit": True})
        since = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)
        all_ohlcv = []
        batch_since = since
        while True:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, since=batch_since, limit=1000)
            except Exception as e:
                print(f" 失败: {e}")
                return None
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            batch_since = ohlcv[-1][0] + 1
            if len(ohlcv) < 1000:
                break
        candles = []
        for row in all_ohlcv:
            candles.append({
                "timestamp": datetime.fromtimestamp(row[0] / 1000).isoformat(),
                "open": row[1], "high": row[2], "low": row[3], "close": row[4], "volume": row[5],
            })
        with open(path, "w") as f:
            json.dump(candles, f)
        print(f" {len(candles)} 根")
        return candles

    with open(path) as f:
        return json.load(f)


def run_backtest(candles, symbol):
    """用 H8 方案跑单个币种"""
    strategy_config = {
        "sl_tp_mode": "margin_pct",
        "leverage": LEVERAGE,
        "max_position": 1000,
        "risk_pct": 0.01,
        "tp_pct": 1.20,
        "sl_pct": 0.40,
        "macd_filter": True,
        "volume_filter": True,
        "volume_min_ratio": 1.0,
        "cooldown_bars": 5,
    }
    engine_kwargs = {
        "initial_balance": BALANCE,
        "commission_rate": 0.0005,
        "amount_usdt": POS_VAL,
        "leverage": LEVERAGE,
        "margin_mode": "isolated",
    }
    strategy = get_strategy("market_regime", strategy_config)
    engine = BacktestEngine(**engine_kwargs)
    result = engine.run(strategy=strategy, symbol=symbol, timeframe=TIMEFRAME, candles=candles, lookback=100)
    return result


def main():
    print("=" * 90)
    print("  多币种回测 — H8 方案 (TP120%/SL40%, MACD+量比+冷却5, 20X逐仓)")
    print(f"  本金 {BALANCE} USDT  |  每笔仓位 {POS_VAL} USDT  |  保证金 {POS_VAL/LEVERAGE:.0f} USDT")
    print("=" * 90)

    # 下载所有数据
    print(f"\n  准备数据...")
    all_data = {}
    for sym in SYMBOLS:
        candles = load_candles(sym)
        if candles and len(candles) > 200:
            all_data[sym] = candles

    # 逐个回测
    results = {}
    for sym, candles in all_data.items():
        print(f"\n  回测 {sym}...", end="", flush=True)
        r = run_backtest(candles, sym)
        results[sym] = r

        start_p = candles[100]["close"]
        end_p = candles[-1]["close"]
        buy_hold = ((end_p - start_p) / start_p) * 100

        tp = sum(1 for t in r.trades if t.exit_reason == "TAKE_PROFIT")
        sl = sum(1 for t in r.trades if t.exit_reason == "STOP_LOSS")
        sig = sum(1 for t in r.trades if t.exit_reason == "SIGNAL")

        print(f" 完成")
        print(f"    交易 {r.total_trades}笔  胜率 {r.win_rate:.1f}%  盈亏比 {r.risk_reward_ratio:.2f}")
        print(f"    PnL {r.total_pnl:+.2f} ({r.total_pnl_pct:+.2f}%)  回撤 {r.max_drawdown_pct:.1f}%")
        print(f"    止盈{tp} 止损{sl} 信号{sig}  |  买入持有: {buy_hold:+.1f}%")

    # ── 汇总表 ──
    print(f"\n{'=' * 110}")
    print(f"  多币种汇总对比")
    print(f"{'=' * 110}")

    hdr = f"{'币种':>12} {'交易':>6} {'胜率':>7} {'盈亏比':>7} {'收益率':>9} {'回撤':>7} {'盈利因子':>8} {'期望值':>8} {'最终资金':>9} {'买入持有':>9}"
    print(hdr)
    print("─" * 110)

    total_pnl = 0
    for sym in SYMBOLS:
        if sym not in results:
            continue
        r = results[sym]
        candles = all_data[sym]
        start_p = candles[100]["close"]
        end_p = candles[-1]["close"]
        buy_hold = ((end_p - start_p) / start_p) * 100
        total_pnl += r.total_pnl

        line = (f"{sym:>12} {r.total_trades:>6} {r.win_rate:>6.1f}% {r.risk_reward_ratio:>7.2f} "
                f"{r.total_pnl_pct:>+8.1f}% {r.max_drawdown_pct:>6.1f}% {r.profit_factor:>8.2f} "
                f"{r.expectancy:>+7.2f} {r.final_balance:>9.0f} {buy_hold:>+8.1f}%")
        print(line)

    # 组合统计
    print("─" * 110)
    combined_balance = sum(r.final_balance for r in results.values())
    combined_capital = BALANCE * len(results)
    combined_pct = (total_pnl / combined_capital) * 100

    print(f"{'合计':>12} {'':>6} {'':>7} {'':>7} {combined_pct:>+8.1f}% {'':>7} {'':>8} {'':>8} {combined_balance:>9.0f}")

    # 月度分布（每个币种）
    print(f"\n{'─' * 110}")
    print(f"  各币种月度PnL")
    print(f"{'─' * 110}")

    for sym in SYMBOLS:
        if sym not in results:
            continue
        r = results[sym]
        monthly = {}
        for t in r.trades:
            if t.exit_time and t.pnl is not None:
                key = t.exit_time.strftime("%Y-%m") if hasattr(t.exit_time, 'strftime') else str(t.exit_time)[:7]
                monthly[key] = monthly.get(key, 0) + t.pnl
        if monthly:
            months = sorted(monthly.keys())
            pos_m = sum(1 for m in months if monthly[m] > 0)
            neg_m = sum(1 for m in months if monthly[m] <= 0)
            total = sum(monthly.values())
            print(f"\n  {sym}: 盈利月{pos_m}/亏损月{neg_m}  合计{total:+.1f}")
            for m in months:
                bar = "█" * min(int(abs(monthly[m]) / 5), 50)
                sign = "+" if monthly[m] >= 0 else "-"
                print(f"    {m}: {monthly[m]:>+8.1f}  {bar}")

    # 如果全部同时跑（组合）
    print(f"\n{'=' * 110}")
    print(f"  💡 多币种组合效果")
    print(f"{'=' * 110}")
    n = len(results)
    print(f"  币种数: {n}")
    print(f"  每个币种本金: {BALANCE} USDT × {n} = {BALANCE * n} USDT")
    print(f"  合计净赚: {total_pnl:+.2f} USDT")
    print(f"  组合收益率: {combined_pct:+.2f}%")

    # 最好 & 最差
    best_sym = max(results.items(), key=lambda x: x[1].total_pnl_pct)
    worst_sym = min(results.items(), key=lambda x: x[1].total_pnl_pct)
    print(f"  最佳币种: {best_sym[0]}  {best_sym[1].total_pnl_pct:+.2f}%")
    print(f"  最差币种: {worst_sym[0]}  {worst_sym[1].total_pnl_pct:+.2f}%")

    # 组合月度PnL
    combo_monthly = {}
    for sym, r in results.items():
        for t in r.trades:
            if t.exit_time and t.pnl is not None:
                key = t.exit_time.strftime("%Y-%m") if hasattr(t.exit_time, 'strftime') else str(t.exit_time)[:7]
                combo_monthly[key] = combo_monthly.get(key, 0) + t.pnl
    if combo_monthly:
        months = sorted(combo_monthly.keys())
        pos_m = sum(1 for m in months if combo_monthly[m] > 0)
        neg_m = sum(1 for m in months if combo_monthly[m] <= 0)
        print(f"\n  组合月度PnL: 盈利月{pos_m} / 亏损月{neg_m}")
        for m in months:
            bar = "█" * min(int(abs(combo_monthly[m]) / 10), 60)
            print(f"    {m}: {combo_monthly[m]:>+8.1f}  {bar}")

    print(f"\n{'=' * 110}\n")


if __name__ == "__main__":
    main()
