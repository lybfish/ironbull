#!/usr/bin/env python3
"""
策略优化 v2b — 精调回测（基于 v2 发现去掉 RSI，聚焦 MACD+量比+冷却）

发现:
  - RSI 过滤在趋势行情中有害（过滤掉大行情）
  - MACD + 量比 + 冷却是最有效组合
  - 本轮精调这三个维度的参数

方案:
  H0: 基准 G0 (TP100/SL50, 无过滤)
  H1: MACD+量比 (无冷却)
  H2: MACD+量比+冷却3
  H3: MACD+量比+冷却5  ← 对应 v2 的 G5 但去掉 RSI
  H4: MACD+量比+冷却8
  H5: MACD+量比+冷却5+置信55
  H6: 纯趋势+MACD+量比+冷却5
  H7: 纯趋势+MACD+量比+冷却5+TP150/SL60
  H8: MACD+量比+冷却5+TP120/SL40 (更高盈亏比)
  H9: MACD+量比+冷却5+TP80/SL40 (适中止盈)
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy


SYMBOL = "ETH/USDT"
TIMEFRAME = "1h"
MAX_POSITION = 1000
RISK_PCT = 0.01
LEVERAGE = 20
MARGIN = MAX_POSITION * RISK_PCT
POS_VAL = MARGIN * LEVERAGE
BALANCE = 2000


def load_candles():
    path = "/tmp/eth_usdt_1y_1h.json"
    if not os.path.exists(path):
        print(f"未找到缓存数据 {path}，正在从 Binance 获取...")
        import ccxt
        from datetime import datetime, timedelta
        exchange = ccxt.binance({"enableRateLimit": True})
        since = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)
        all_ohlcv = []
        batch_since = since
        while True:
            ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, since=batch_since, limit=1000)
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
        print(f"已保存 {len(candles)} 根 K 线到 {path}")
        return candles
    with open(path) as f:
        return json.load(f)


def run(candles, strategy_config, engine_kwargs):
    strategy = get_strategy("market_regime", strategy_config)
    engine = BacktestEngine(**engine_kwargs)
    result = engine.run(strategy=strategy, symbol=SYMBOL, timeframe=TIMEFRAME, candles=candles, lookback=100)
    return result, strategy


def main():
    candles = load_candles()

    print("=" * 75)
    print("  策略优化 v2b — 精调 MACD+量比+冷却 (ETH/USDT 1h, 一年)")
    print(f"  K线: {len(candles)} 根  |  {candles[0]['timestamp'][:10]} ~ {candles[-1]['timestamp'][:10]}")
    print(f"  本金: {BALANCE}  |  仓位: {POS_VAL}  |  杠杆: {LEVERAGE}X  |  保证金: {MARGIN}")
    print("=" * 75)

    base_s = {
        "sl_tp_mode": "margin_pct",
        "leverage": LEVERAGE,
        "max_position": MAX_POSITION,
        "risk_pct": RISK_PCT,
        "tp_pct": 1.00,
        "sl_pct": 0.50,
    }
    base_e = {
        "initial_balance": BALANCE,
        "commission_rate": 0.0005,
        "amount_usdt": POS_VAL,
        "leverage": LEVERAGE,
        "margin_mode": "isolated",
    }

    # MACD+量比的基础（无 RSI）
    mv_filter = {"macd_filter": True, "volume_filter": True, "volume_min_ratio": 1.0}

    configs = [
        ("H0:基准", {**base_s}, {**base_e}),
        ("H1:MV无冷却", {**base_s, **mv_filter}, {**base_e}),
        ("H2:MV+冷却3", {**base_s, **mv_filter, "cooldown_bars": 3}, {**base_e}),
        ("H3:MV+冷却5", {**base_s, **mv_filter, "cooldown_bars": 5}, {**base_e}),
        ("H4:MV+冷却8", {**base_s, **mv_filter, "cooldown_bars": 8}, {**base_e}),
        ("H5:MV冷5信55", {**base_s, **mv_filter, "cooldown_bars": 5, "min_confidence": 55}, {**base_e}),
        ("H6:趋势MV冷5", {**base_s, **mv_filter, "cooldown_bars": 5, "skip_ranging": True}, {**base_e, "hedge_mode": False}),
        ("H7:趋势宽幅", {**base_s, **mv_filter, "cooldown_bars": 5, "skip_ranging": True, "tp_pct": 1.50, "sl_pct": 0.60}, {**base_e, "hedge_mode": False}),
        ("H8:MV冷5高比", {**base_s, **mv_filter, "cooldown_bars": 5, "tp_pct": 1.20, "sl_pct": 0.40}, {**base_e}),
        ("H9:MV冷5中比", {**base_s, **mv_filter, "cooldown_bars": 5, "tp_pct": 0.80, "sl_pct": 0.40}, {**base_e}),
    ]

    results = []
    for label, sc, ec in configs:
        r, st = run(candles, sc, ec)
        results.append((label, r, st))

        tp = sum(1 for t in r.trades if t.exit_reason == "TAKE_PROFIT")
        sl = sum(1 for t in r.trades if t.exit_reason == "STOP_LOSS")
        ts = sum(1 for t in r.trades if t.exit_reason == "TRAILING_STOP")
        sig = sum(1 for t in r.trades if t.exit_reason == "SIGNAL")

        print(f"\n{'─' * 65}")
        print(f"  {label}")
        print(f"{'─' * 65}")
        print(f"  交易: {r.total_trades} 笔 (赢 {r.winning_trades} / 亏 {r.losing_trades})")
        print(f"  胜率: {r.win_rate:.1f}%  |  盈亏比: {r.risk_reward_ratio:.2f}  |  盈利因子: {r.profit_factor:.2f}")
        print(f"  总PnL: {r.total_pnl:+.2f} ({r.total_pnl_pct:+.2f}%)  |  期望值: {r.expectancy:+.2f}/笔")
        print(f"  平均赢: {r.avg_win:+.2f}  |  平均亏: {r.avg_loss:+.2f}")
        print(f"  最大回撤: {r.max_drawdown:.2f} ({r.max_drawdown_pct:.2f}%)")
        print(f"  最终: {r.final_balance:.2f}  |  出场: 止盈{tp} 止损{sl} 移动{ts} 信号{sig}")

        if hasattr(st, 'filtered_by_rsi'):
            total_f = (st.filtered_by_rsi + st.filtered_by_macd + st.filtered_by_volume +
                      st.filtered_by_confidence + st.filtered_by_cooldown)
            if total_f > 0:
                print(f"  过滤: MACD:{st.filtered_by_macd} 量比:{st.filtered_by_volume} "
                      f"置信:{st.filtered_by_confidence} 冷却:{st.filtered_by_cooldown}")

    # ── 汇总 ──
    labels = [lb for lb, _, _ in results]
    all_r = [r for _, r, _ in results]

    print(f"\n{'=' * 140}")
    print(f"  汇总对比表")
    print(f"{'=' * 140}")

    hdr = f"{'指标':>10}"
    for lb in labels:
        hdr += f"  {lb:>12}"
    print(hdr)
    print("─" * 140)

    def row(name, vals):
        line = f"{name:>10}"
        for v in vals:
            line += f"  {v:>12}"
        print(line)

    row("总交易", [str(r.total_trades) for r in all_r])
    row("胜率", [f"{r.win_rate:.1f}%" for r in all_r])
    row("总PnL", [f"{r.total_pnl:+.1f}" for r in all_r])
    row("收益率", [f"{r.total_pnl_pct:+.1f}%" for r in all_r])
    row("盈亏比", [f"{r.risk_reward_ratio:.2f}" for r in all_r])
    row("盈利因子", [f"{r.profit_factor:.2f}" for r in all_r])
    row("期望值", [f"{r.expectancy:+.2f}" for r in all_r])
    row("回撤率", [f"{r.max_drawdown_pct:.1f}%" for r in all_r])
    row("最终资金", [f"{r.final_balance:.0f}" for r in all_r])
    
    # 收益/回撤比
    row("收益/回撤", [f"{r.total_pnl_pct / r.max_drawdown_pct:.2f}" if r.max_drawdown_pct > 0 else "N/A" for r in all_r])

    # 月度分布（top3 + 基准）
    sorted_r = sorted(results, key=lambda x: x[1].total_pnl_pct, reverse=True)
    show = [results[0]]
    for item in sorted_r[:3]:
        if item not in show:
            show.append(item)

    print(f"\n{'─' * 140}")
    print(f"  月度 PnL (前3 + 基准)")
    print(f"{'─' * 140}")
    for lb, r, _ in show:
        if not r.trades:
            continue
        monthly = {}
        for t in r.trades:
            if t.exit_time and t.pnl is not None:
                key = t.exit_time.strftime("%Y-%m") if hasattr(t.exit_time, 'strftime') else str(t.exit_time)[:7]
                monthly[key] = monthly.get(key, 0) + t.pnl
        if monthly:
            months = sorted(monthly.keys())
            pos_m = sum(1 for m in months if monthly[m] > 0)
            neg_m = sum(1 for m in months if monthly[m] <= 0)
            print(f"\n  {lb}: 盈利月{pos_m} / 亏损月{neg_m}")
            for m in months:
                bar = "█" * min(int(abs(monthly[m]) / 5), 50)
                print(f"    {m}: {monthly[m]:>+8.1f}  {bar}")

    # 最终推荐
    best = sorted_r[0]
    # 也找出最佳「收益/回撤比」
    best_ratio = max(results, key=lambda x: x[1].total_pnl_pct / x[1].max_drawdown_pct if x[1].max_drawdown_pct > 0 else 0)
    
    print(f"\n{'=' * 140}")
    print(f"  ★ 最高收益: {best[0]}  收益率 {best[1].total_pnl_pct:+.2f}%  "
          f"回撤 {best[1].max_drawdown_pct:.1f}%  盈利因子 {best[1].profit_factor:.2f}  "
          f"期望值 {best[1].expectancy:+.2f}/笔")
    print(f"  ★ 最优风险收益比: {best_ratio[0]}  "
          f"收益/回撤={best_ratio[1].total_pnl_pct / best_ratio[1].max_drawdown_pct:.2f}  "
          f"收益率 {best_ratio[1].total_pnl_pct:+.2f}%  回撤 {best_ratio[1].max_drawdown_pct:.1f}%")
    print(f"{'=' * 140}")
    print()


if __name__ == "__main__":
    main()
