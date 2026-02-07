#!/usr/bin/env python3
"""
策略优化 v2 — 全维度对比回测

优化维度:
  G0: 基准 — F1 最优参数 (TP 100% / SL 50%)
  G1: +RSI过滤 — 避免追涨杀跌 (BUY时RSI>70不进, SELL时RSI<30不进)
  G2: +MACD确认 — 趋势方向需MACD柱一致
  G3: +量比确认 — 趋势信号要求放量 (量比>1.0)
  G4: +全过滤 — RSI + MACD + 量比 三重过滤
  G5: +全过滤+冷却 — 三重过滤 + 止损后冷却5根K线
  G6: +全过滤+冷却+高置信 — 三重 + 冷却5 + 置信度>=60
  G7: 纯趋势+全过滤 — 跳过震荡 + 三重过滤 + 冷却5
  G8: 纯趋势+宽SL — 跳过震荡 + 三重过滤 + TP 150% / SL 80%
  G9: 分治+全过滤 — 震荡 TP70/SL50 + 趋势 TP120/SL40 + 三重过滤

模型: 逐仓 20X，保证金 10 USDT，仓位 200 USDT，本金 2000 USDT
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy


# ── 全局参数 ──
SYMBOL = "ETH/USDT"
TIMEFRAME = "1h"
MAX_POSITION = 1000
RISK_PCT = 0.01
LEVERAGE = 20
MARGIN = MAX_POSITION * RISK_PCT    # 10
POS_VAL = MARGIN * LEVERAGE          # 200
BALANCE = 2000


def load_candles():
    """加载缓存的一年 K 线数据"""
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
        candles = json.load(f)
    return candles


def run(candles, strategy_config, engine_kwargs):
    """运行单次回测，返回 (result, strategy)"""
    strategy = get_strategy("market_regime", strategy_config)
    engine = BacktestEngine(**engine_kwargs)
    result = engine.run(
        strategy=strategy,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        candles=candles,
        lookback=100,
    )
    return result, strategy


def print_detail(label, r, strategy=None):
    """打印单个方案详情"""
    tp = sum(1 for t in r.trades if t.exit_reason == "TAKE_PROFIT")
    sl = sum(1 for t in r.trades if t.exit_reason == "STOP_LOSS")
    ts = sum(1 for t in r.trades if t.exit_reason == "TRAILING_STOP")
    sig = sum(1 for t in r.trades if t.exit_reason == "SIGNAL")
    end = sum(1 for t in r.trades if t.exit_reason == "END")

    print(f"\n{'─' * 65}")
    print(f"  {label}")
    print(f"{'─' * 65}")
    print(f"  交易: {r.total_trades} 笔 (赢 {r.winning_trades} / 亏 {r.losing_trades})")
    print(f"  胜率: {r.win_rate:.1f}%")
    print(f"  总PnL: {r.total_pnl:+.2f} USDT ({r.total_pnl_pct:+.2f}%)")
    print(f"  平均赢: {r.avg_win:+.2f}  |  平均亏: {r.avg_loss:+.2f}")
    print(f"  盈亏比: {r.risk_reward_ratio:.2f}  |  盈利因子: {r.profit_factor:.2f}")
    print(f"  期望值: {r.expectancy:+.2f}/笔")
    print(f"  最大回撤: {r.max_drawdown:.2f} ({r.max_drawdown_pct:.2f}%)")
    print(f"  最终资金: {r.final_balance:.2f}")
    print(f"  多头: {r.long_trades}笔 PnL {r.long_pnl:+.2f}  |  空头: {r.short_trades}笔 PnL {r.short_pnl:+.2f}")
    print(f"  出场: 止盈{tp} 止损{sl} 移动止损{ts} 信号{sig} 到期{end}")

    # 显示过滤统计
    if strategy and hasattr(strategy, 'filtered_by_rsi'):
        filters = []
        if strategy.filtered_by_rsi > 0:
            filters.append(f"RSI拦截{strategy.filtered_by_rsi}")
        if strategy.filtered_by_macd > 0:
            filters.append(f"MACD拦截{strategy.filtered_by_macd}")
        if strategy.filtered_by_volume > 0:
            filters.append(f"量比拦截{strategy.filtered_by_volume}")
        if strategy.filtered_by_confidence > 0:
            filters.append(f"置信度拦截{strategy.filtered_by_confidence}")
        if strategy.filtered_by_cooldown > 0:
            filters.append(f"冷却拦截{strategy.filtered_by_cooldown}")
        if filters:
            print(f"  过滤: {', '.join(filters)}")


def main():
    candles = load_candles()

    print("=" * 75)
    print("  策略优化 v2 — 全维度对比回测 (ETH/USDT 1h, 一年)")
    print(f"  K线: {len(candles)} 根  |  {candles[0]['timestamp'][:10]} ~ {candles[-1]['timestamp'][:10]}")
    print(f"  本金: {BALANCE}  |  仓位: {POS_VAL}  |  杠杆: {LEVERAGE}X  |  保证金: {MARGIN}")
    print("=" * 75)

    # 基础策略参数（继承 F1 最优）
    base_strategy = {
        "sl_tp_mode": "margin_pct",
        "leverage": LEVERAGE,
        "max_position": MAX_POSITION,
        "risk_pct": RISK_PCT,
        "tp_pct": 1.00,       # F1 最优
        "sl_pct": 0.50,       # F1 最优
    }

    base_engine = {
        "initial_balance": BALANCE,
        "commission_rate": 0.0005,
        "amount_usdt": POS_VAL,
        "leverage": LEVERAGE,
        "margin_mode": "isolated",
    }

    results = []   # (label, result, strategy)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # G0: 基准 — F1 最优 (TP 100% / SL 50%)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s0 = {**base_strategy}
    e0 = {**base_engine}
    r0, st0 = run(candles, s0, e0)
    results.append(("G0:基准F1", r0, st0))
    print_detail("G0: 基准 — TP 100% / SL 50% (F1 对照组)", r0, st0)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # G1: +RSI 过滤
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s1 = {**base_strategy, "rsi_filter": True, "rsi_overbought": 70, "rsi_oversold": 30}
    e1 = {**base_engine}
    r1, st1 = run(candles, s1, e1)
    results.append(("G1:+RSI", r1, st1))
    print_detail("G1: +RSI 过滤 (>70不做多, <30不做空)", r1, st1)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # G2: +MACD 确认
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s2 = {**base_strategy, "macd_filter": True}
    e2 = {**base_engine}
    r2, st2 = run(candles, s2, e2)
    results.append(("G2:+MACD", r2, st2))
    print_detail("G2: +MACD 方向确认", r2, st2)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # G3: +量比确认
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s3 = {**base_strategy, "volume_filter": True, "volume_min_ratio": 1.0}
    e3 = {**base_engine}
    r3, st3 = run(candles, s3, e3)
    results.append(("G3:+量比", r3, st3))
    print_detail("G3: +量比过滤 (量比>1.0)", r3, st3)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # G4: 三重过滤 (RSI + MACD + 量比)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s4 = {
        **base_strategy,
        "rsi_filter": True, "rsi_overbought": 70, "rsi_oversold": 30,
        "macd_filter": True,
        "volume_filter": True, "volume_min_ratio": 1.0,
    }
    e4 = {**base_engine}
    r4, st4 = run(candles, s4, e4)
    results.append(("G4:三重过滤", r4, st4))
    print_detail("G4: 三重过滤 (RSI + MACD + 量比)", r4, st4)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # G5: 三重过滤 + 止损冷却 5 bar
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s5 = {
        **base_strategy,
        "rsi_filter": True, "rsi_overbought": 70, "rsi_oversold": 30,
        "macd_filter": True,
        "volume_filter": True, "volume_min_ratio": 1.0,
        "cooldown_bars": 5,
    }
    e5 = {**base_engine}
    r5, st5 = run(candles, s5, e5)
    results.append(("G5:+冷却5", r5, st5))
    print_detail("G5: 三重过滤 + 冷却 5 bar", r5, st5)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # G6: 三重过滤 + 冷却 + 高置信度 >= 60
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s6 = {
        **base_strategy,
        "rsi_filter": True, "rsi_overbought": 70, "rsi_oversold": 30,
        "macd_filter": True,
        "volume_filter": True, "volume_min_ratio": 1.0,
        "cooldown_bars": 5,
        "min_confidence": 60,
    }
    e6 = {**base_engine}
    r6, st6 = run(candles, s6, e6)
    results.append(("G6:+置信60", r6, st6))
    print_detail("G6: 三重过滤 + 冷却5 + 置信度>=60", r6, st6)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # G7: 纯趋势 + 三重过滤 + 冷却
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s7 = {
        **base_strategy,
        "skip_ranging": True,
        "rsi_filter": True, "rsi_overbought": 70, "rsi_oversold": 30,
        "macd_filter": True,
        "volume_filter": True, "volume_min_ratio": 1.0,
        "cooldown_bars": 5,
    }
    e7 = {**base_engine, "hedge_mode": False}
    r7, st7 = run(candles, s7, e7)
    results.append(("G7:趋势+过滤", r7, st7))
    print_detail("G7: 纯趋势 + 三重过滤 + 冷却5", r7, st7)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # G8: 纯趋势 + 三重过滤 + 宽 TP/SL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s8 = {
        **base_strategy,
        "skip_ranging": True,
        "tp_pct": 1.50,       # 更宽止盈
        "sl_pct": 0.80,       # 更宽止损
        "rsi_filter": True, "rsi_overbought": 70, "rsi_oversold": 30,
        "macd_filter": True,
        "volume_filter": True, "volume_min_ratio": 1.0,
        "cooldown_bars": 5,
    }
    e8 = {**base_engine, "hedge_mode": False}
    r8, st8 = run(candles, s8, e8)
    results.append(("G8:趋势宽幅", r8, st8))
    print_detail("G8: 纯趋势 + 三重过滤 + TP150%/SL80%", r8, st8)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # G9: 分治 + 三重过滤
    #     震荡: TP 70% / SL 50% (盈亏比 1.4)
    #     趋势: TP 120% / SL 40% (盈亏比 3.0)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s9 = {
        **base_strategy,
        "tp_pct": 1.00,
        "sl_pct": 0.50,
        "ranging_tp_pct": 0.70,
        "ranging_sl_pct": 0.50,
        "trending_tp_pct": 1.20,
        "trending_sl_pct": 0.40,
        "rsi_filter": True, "rsi_overbought": 70, "rsi_oversold": 30,
        "macd_filter": True,
        "volume_filter": True, "volume_min_ratio": 1.0,
        "cooldown_bars": 5,
    }
    e9 = {**base_engine}
    r9, st9 = run(candles, s9, e9)
    results.append(("G9:分治+过滤", r9, st9))
    print_detail("G9: 分治 震荡TP70/SL50 + 趋势TP120/SL40 + 三重过滤", r9, st9)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 汇总对比表
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    labels = [lb for lb, _, _ in results]
    all_r = [r for _, r, _ in results]

    print(f"\n{'=' * 130}")
    print(f"  汇总对比表")
    print(f"{'=' * 130}")

    hdr = f"{'指标':>12}"
    for lb in labels:
        hdr += f"  {lb:>12}"
    print(hdr)
    print("─" * 130)

    def row(name, vals):
        line = f"{name:>12}"
        for v in vals:
            line += f"  {v:>12}"
        print(line)

    row("总交易", [str(r.total_trades) for r in all_r])
    row("胜率", [f"{r.win_rate:.1f}%" for r in all_r])
    row("总PnL", [f"{r.total_pnl:+.1f}" for r in all_r])
    row("收益率", [f"{r.total_pnl_pct:+.1f}%" for r in all_r])
    row("盈亏比", [f"{r.risk_reward_ratio:.2f}" for r in all_r])
    row("盈利因子", [f"{r.profit_factor:.2f}" for r in all_r])
    row("期望值/笔", [f"{r.expectancy:+.2f}" for r in all_r])
    row("平均赢", [f"{r.avg_win:+.1f}" for r in all_r])
    row("平均亏", [f"{r.avg_loss:+.1f}" for r in all_r])
    row("最大回撤", [f"{r.max_drawdown:.0f}" for r in all_r])
    row("回撤率", [f"{r.max_drawdown_pct:.1f}%" for r in all_r])
    row("最终资金", [f"{r.final_balance:.0f}" for r in all_r])

    # 出场分布
    print()
    for lb, r, _ in results:
        tp = sum(1 for t in r.trades if t.exit_reason == "TAKE_PROFIT")
        sl = sum(1 for t in r.trades if t.exit_reason == "STOP_LOSS")
        ts = sum(1 for t in r.trades if t.exit_reason == "TRAILING_STOP")
        sig = sum(1 for t in r.trades if t.exit_reason == "SIGNAL")
        print(f"  {lb}: 止盈{tp} 止损{sl} 移动止损{ts} 信号{sig}")

    # 过滤统计
    print(f"\n{'─' * 130}")
    print(f"  过滤器拦截统计")
    print(f"{'─' * 130}")
    for lb, _, st in results:
        if not hasattr(st, 'filtered_by_rsi'):
            continue
        total_filtered = (st.filtered_by_rsi + st.filtered_by_macd +
                         st.filtered_by_volume + st.filtered_by_confidence +
                         st.filtered_by_cooldown)
        if total_filtered > 0:
            print(f"  {lb}: 共拦截 {total_filtered} 次 "
                  f"(RSI:{st.filtered_by_rsi} MACD:{st.filtered_by_macd} "
                  f"量比:{st.filtered_by_volume} 置信:{st.filtered_by_confidence} "
                  f"冷却:{st.filtered_by_cooldown})")

    # 月度分布（只看 top 3 + 基准）
    print(f"\n{'─' * 130}")
    print(f"  月度 PnL 分布 (前3名 + 基准)")
    print(f"{'─' * 130}")

    # 按收益率排序，取 top 3
    sorted_results = sorted(results, key=lambda x: x[1].total_pnl_pct, reverse=True)
    show_list = [results[0]]  # 基准
    for item in sorted_results[:3]:
        if item not in show_list:
            show_list.append(item)

    for lb, r, _ in show_list:
        if not r.trades:
            continue
        monthly = {}
        for t in r.trades:
            if t.exit_time and t.pnl is not None:
                key = t.exit_time.strftime("%Y-%m") if hasattr(t.exit_time, 'strftime') else str(t.exit_time)[:7]
                monthly[key] = monthly.get(key, 0) + t.pnl
        if monthly:
            months = sorted(monthly.keys())
            vals = [monthly[m] for m in months]
            pos_months = sum(1 for v in vals if v > 0)
            neg_months = sum(1 for v in vals if v <= 0)
            print(f"\n  {lb}: 盈利月{pos_months} / 亏损月{neg_months}")
            for m in months:
                bar_len = int(abs(monthly[m]) / 5)
                bar = "█" * min(bar_len, 50)
                print(f"    {m}: {monthly[m]:>+8.1f}  {bar}")

    # 最终推荐
    print(f"\n{'=' * 130}")
    best = sorted_results[0]
    print(f"  ★ 最佳方案: {best[0]}  收益率 {best[1].total_pnl_pct:+.2f}%  "
          f"回撤 {best[1].max_drawdown_pct:.1f}%  盈亏比 {best[1].risk_reward_ratio:.2f}  "
          f"胜率 {best[1].win_rate:.1f}%  共 {best[1].total_trades} 笔")
    print(f"{'=' * 130}")
    print()


if __name__ == "__main__":
    main()
