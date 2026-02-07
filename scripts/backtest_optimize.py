#!/usr/bin/env python3
"""
策略优化回测对比

方案:
  F0: 基准 — 固定 TP 45% / SL 70%（对照组）
  F1: 正盈亏比 — TP 100% / SL 50%（赢10亏5，需>33%胜率）
  F2: 对称盈亏 — TP 70% / SL 70%（赢7亏7，需>50%胜率）
  F3: 分治模式 — 震荡用 TP 70% / SL 50%，趋势用移动止损（无固定TP，保本+30%跟踪）
  F4: 纯趋势 — 关掉对冲，只做趋势单边（TP 100% / SL 50%）

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
    """运行单次回测"""
    strategy = get_strategy("market_regime", strategy_config)
    engine = BacktestEngine(**engine_kwargs)
    result = engine.run(
        strategy=strategy,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        candles=candles,
        lookback=100,
    )
    return result


def print_detail(label, r):
    """打印单个方案详情"""
    tp = sum(1 for t in r.trades if t.exit_reason == "TAKE_PROFIT")
    sl = sum(1 for t in r.trades if t.exit_reason == "STOP_LOSS")
    ts = sum(1 for t in r.trades if t.exit_reason == "TRAILING_STOP")
    sig = sum(1 for t in r.trades if t.exit_reason == "SIGNAL")
    end = sum(1 for t in r.trades if t.exit_reason == "END")

    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")
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

    if r.trades:
        print(f"  前5笔:")
        for t in r.trades[:5]:
            side = "多" if t.side == "BUY" else "空"
            pnl_s = f"{t.pnl:+.2f}" if t.pnl else "N/A"
            exit_s = f"{t.exit_price:.2f}" if t.exit_price else "N/A"
            print(f"    [{t.trade_id:>3}] {side} @ {t.entry_price:.2f} -> {exit_s}  PnL={pnl_s}  {t.exit_reason}")


def main():
    candles = load_candles()

    print("=" * 70)
    print("  策略优化回测对比 (ETH/USDT 1h, 一年)")
    print(f"  K线: {len(candles)} 根  |  {candles[0]['timestamp'][:10]} ~ {candles[-1]['timestamp'][:10]}")
    print(f"  本金: {BALANCE}  |  仓位: {POS_VAL}  |  杠杆: {LEVERAGE}X  |  保证金: {MARGIN}")
    print("=" * 70)

    # 基础策略参数
    base_strategy = {
        "sl_tp_mode": "margin_pct",
        "leverage": LEVERAGE,
        "max_position": MAX_POSITION,
        "risk_pct": RISK_PCT,
    }

    base_engine = {
        "initial_balance": BALANCE,
        "commission_rate": 0.0005,
        "amount_usdt": POS_VAL,
        "leverage": LEVERAGE,
        "margin_mode": "isolated",
    }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # F0: 基准 — 固定 TP 45% / SL 70%
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s0 = {**base_strategy, "tp_pct": 0.45, "sl_pct": 0.70}
    e0 = {**base_engine}
    r0 = run(candles, s0, e0)
    print_detail("F0: 基准 — TP 45% / SL 70% (盈亏比 0.64)", r0)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # F1: 正盈亏比 — TP 100% / SL 50% (赢10亏5)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s1 = {**base_strategy, "tp_pct": 1.00, "sl_pct": 0.50}
    e1 = {**base_engine}
    r1 = run(candles, s1, e1)
    print_detail("F1: 正盈亏比 — TP 100% / SL 50% (赢10亏5)", r1)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # F2: 对称盈亏 — TP 70% / SL 70% (赢7亏7)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s2 = {**base_strategy, "tp_pct": 0.70, "sl_pct": 0.70}
    e2 = {**base_engine}
    r2 = run(candles, s2, e2)
    print_detail("F2: 对称盈亏 — TP 70% / SL 70% (赢7亏7)", r2)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # F3: 分治模式 — 震荡: TP 70% / SL 50%, 趋势: 保本+移动止损30%
    #     震荡盈亏比 1.4:1, 趋势让利润奔跑
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s3 = {
        **base_strategy,
        "tp_pct": 0.70,       # 默认（回退用）
        "sl_pct": 0.50,
        "ranging_tp_pct": 0.70,    # 震荡: TP 70%
        "ranging_sl_pct": 0.50,    # 震荡: SL 50%
        "trending_tp_pct": 0,      # 趋势: 无固定TP（靠移动止损出场）
        "trending_sl_pct": 0.50,   # 趋势: 初始SL 50%
    }
    e3 = {
        **base_engine,
        "trailing_stop_pct": 0.30,           # 移动止损 30% margin
        "trailing_activation_pct": 0.20,     # 浮盈 >= 20% margin 后激活
    }
    r3 = run(candles, s3, e3)
    print_detail("F3: 分治 — 震荡 TP70%/SL50% + 趋势 保本+移动30%", r3)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # F4: 纯趋势 — 关掉对冲，只做趋势单边 TP 100% / SL 50%
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    s4 = {
        **base_strategy,
        "tp_pct": 1.00,
        "sl_pct": 0.50,
        "skip_ranging": True,   # 跳过震荡行情
    }
    e4 = {**base_engine, "hedge_mode": False}  # 单向模式
    r4 = run(candles, s4, e4)
    print_detail("F4: 纯趋势 — 只做单边 TP 100% / SL 50%", r4)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 汇总对比
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    labels = [
        "F0:基准45/70",
        "F1:正比100/50",
        "F2:对称70/70",
        "F3:分治+移动",
        "F4:纯趋势",
    ]
    all_r = [r0, r1, r2, r3, r4]

    print(f"\n{'=' * 95}")
    print(f"  汇总对比")
    print(f"{'=' * 95}")

    hdr = f"{'':>14}"
    for lb in labels:
        hdr += f"  {lb:>14}"
    print(hdr)

    def row(name, vals):
        line = f"{name:>14}"
        for v in vals:
            line += f"  {v:>14}"
        print(line)

    row("总交易", [str(r.total_trades) for r in all_r])
    row("胜率", [f"{r.win_rate:.1f}%" for r in all_r])
    row("总PnL", [f"{r.total_pnl:+.1f}" for r in all_r])
    row("收益率", [f"{r.total_pnl_pct:+.2f}%" for r in all_r])
    row("盈亏比", [f"{r.risk_reward_ratio:.2f}" for r in all_r])
    row("盈利因子", [f"{r.profit_factor:.2f}" for r in all_r])
    row("期望值/笔", [f"{r.expectancy:+.2f}" for r in all_r])
    row("平均赢", [f"{r.avg_win:+.2f}" for r in all_r])
    row("平均亏", [f"{r.avg_loss:+.2f}" for r in all_r])
    row("最大回撤", [f"{r.max_drawdown:.0f}" for r in all_r])
    row("回撤率", [f"{r.max_drawdown_pct:.1f}%" for r in all_r])
    row("最终资金", [f"{r.final_balance:.0f}" for r in all_r])

    # 出场分布
    print()
    for lb, r in zip(labels, all_r):
        tp = sum(1 for t in r.trades if t.exit_reason == "TAKE_PROFIT")
        sl = sum(1 for t in r.trades if t.exit_reason == "STOP_LOSS")
        ts = sum(1 for t in r.trades if t.exit_reason == "TRAILING_STOP")
        sig = sum(1 for t in r.trades if t.exit_reason == "SIGNAL")
        print(f"  {lb}: 止盈{tp} 止损{sl} 移动止损{ts} 信号{sig}")

    # 月度分布（看稳定性）
    print(f"\n{'─' * 95}")
    print(f"  月度 PnL 分布")
    print(f"{'─' * 95}")
    for lb, r in zip(labels, all_r):
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
                bar_len = int(abs(monthly[m]) / 10)
                bar = "█" * min(bar_len, 40)
                sign = "+" if monthly[m] >= 0 else "-"
                print(f"    {m}: {monthly[m]:>+8.1f}  {bar}")

    print()


if __name__ == "__main__":
    main()
