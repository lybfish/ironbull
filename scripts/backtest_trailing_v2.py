#!/usr/bin/env python3
"""
移动止盈 vs 固定止盈 — 加上 MACD+量比+冷却 后的对比

T0: 基准 H8 固定止盈 (TP120%/SL40%)
T1: 无固定TP + 移动止损20%回撤, 激活0（立即）
T2: 无固定TP + 移动止损30%回撤, 激活20%后
T3: 无固定TP + 移动止损40%回撤, 激活30%后
T4: 无固定TP + 移动止损50%回撤, 激活20%后
T5: 固定TP120% + 移动止损30%回撤, 激活40%（两道保险）
T6: 固定TP150% + 移动止损30%回撤, 激活50%（宽TP+移动保护）
T7: 纯趋势 + 无固定TP + 移动30%, 激活20%
T8: 纯趋势 + 无固定TP + 移动50%, 激活30%

所有方案均含 MACD+量比+冷却5
"""

import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy

SYMBOL = "ETH/USDT"
TIMEFRAME = "1h"
LEVERAGE = 20
BALANCE = 2000
POS_VAL = 200


def load_candles():
    with open("/tmp/eth_usdt_1y_1h.json") as f:
        return json.load(f)


def run(candles, sc, ec):
    strategy = get_strategy("market_regime", sc)
    engine = BacktestEngine(**ec)
    result = engine.run(strategy=strategy, symbol=SYMBOL, timeframe=TIMEFRAME, candles=candles, lookback=100)
    return result


def main():
    candles = load_candles()

    print("=" * 80)
    print("  移动止盈 vs 固定止盈 (ETH/USDT 1h, MACD+量比+冷却5)")
    print(f"  K线 {len(candles)} 根  |  本金 {BALANCE}  |  仓位 {POS_VAL}  |  杠杆 {LEVERAGE}X")
    print("=" * 80)

    base_s = {
        "sl_tp_mode": "margin_pct",
        "leverage": LEVERAGE,
        "max_position": 1000,
        "risk_pct": 0.01,
        "macd_filter": True,
        "volume_filter": True,
        "volume_min_ratio": 1.0,
        "cooldown_bars": 5,
    }
    base_e = {
        "initial_balance": BALANCE,
        "commission_rate": 0.0005,
        "amount_usdt": POS_VAL,
        "leverage": LEVERAGE,
        "margin_mode": "isolated",
    }

    configs = [
        # label, strategy_extra, engine_extra
        ("T0:固定TP120/SL40",
         {"tp_pct": 1.20, "sl_pct": 0.40}, {}),

        ("T1:移动20%即时",
         {"tp_pct": 0, "sl_pct": 0.40},
         {"trailing_stop_pct": 0.20, "trailing_activation_pct": 0.0}),

        ("T2:移动30%激活20%",
         {"tp_pct": 0, "sl_pct": 0.40},
         {"trailing_stop_pct": 0.30, "trailing_activation_pct": 0.20}),

        ("T3:移动40%激活30%",
         {"tp_pct": 0, "sl_pct": 0.40},
         {"trailing_stop_pct": 0.40, "trailing_activation_pct": 0.30}),

        ("T4:移动50%激活20%",
         {"tp_pct": 0, "sl_pct": 0.40},
         {"trailing_stop_pct": 0.50, "trailing_activation_pct": 0.20}),

        ("T5:TP120+移动30%激活40%",
         {"tp_pct": 1.20, "sl_pct": 0.40},
         {"trailing_stop_pct": 0.30, "trailing_activation_pct": 0.40}),

        ("T6:TP150+移动30%激活50%",
         {"tp_pct": 1.50, "sl_pct": 0.40},
         {"trailing_stop_pct": 0.30, "trailing_activation_pct": 0.50}),

        ("T7:趋势+移动30%激活20%",
         {"tp_pct": 0, "sl_pct": 0.40, "skip_ranging": True},
         {"trailing_stop_pct": 0.30, "trailing_activation_pct": 0.20, "hedge_mode": False}),

        ("T8:趋势+移动50%激活30%",
         {"tp_pct": 0, "sl_pct": 0.40, "skip_ranging": True},
         {"trailing_stop_pct": 0.50, "trailing_activation_pct": 0.30, "hedge_mode": False}),
    ]

    results = []
    for label, s_extra, e_extra in configs:
        sc = {**base_s, **s_extra}
        ec = {**base_e, **e_extra}
        r = run(candles, sc, ec)
        results.append((label, r))

        tp = sum(1 for t in r.trades if t.exit_reason == "TAKE_PROFIT")
        sl = sum(1 for t in r.trades if t.exit_reason == "STOP_LOSS")
        ts = sum(1 for t in r.trades if t.exit_reason == "TRAILING_STOP")
        sig = sum(1 for t in r.trades if t.exit_reason == "SIGNAL")

        print(f"\n  {'─' * 70}")
        print(f"  {label}")
        print(f"  交易{r.total_trades} 胜率{r.win_rate:.1f}% 盈亏比{r.risk_reward_ratio:.2f} "
              f"PnL{r.total_pnl:+.1f}({r.total_pnl_pct:+.1f}%) 回撤{r.max_drawdown_pct:.1f}% "
              f"期望{r.expectancy:+.2f} 因子{r.profit_factor:.2f}")
        print(f"  出场: 止盈{tp} 止损{sl} 移动止损{ts} 信号{sig}")

        # 移动止损的交易详情
        if ts > 0:
            ts_trades = [t for t in r.trades if t.exit_reason == "TRAILING_STOP"]
            ts_pnl = [t.pnl for t in ts_trades if t.pnl]
            avg_ts = sum(ts_pnl) / len(ts_pnl) if ts_pnl else 0
            win_ts = sum(1 for p in ts_pnl if p > 0)
            print(f"  移动止损详情: {ts}笔, 平均PnL{avg_ts:+.2f}, 盈利{win_ts}笔/亏损{ts-win_ts}笔")

    # ── 汇总 ──
    labels = [lb for lb, _ in results]
    all_r = [r for _, r in results]

    print(f"\n{'=' * 130}")
    print(f"  汇总对比")
    print(f"{'=' * 130}")

    hdr = f"{'指标':>10}"
    for lb in labels:
        hdr += f" {lb:>14}"
    print(hdr)
    print("─" * 130)

    def row(name, vals):
        line = f"{name:>10}"
        for v in vals:
            line += f" {v:>14}"
        print(line)

    row("总交易", [str(r.total_trades) for r in all_r])
    row("胜率", [f"{r.win_rate:.1f}%" for r in all_r])
    row("盈亏比", [f"{r.risk_reward_ratio:.2f}" for r in all_r])
    row("收益率", [f"{r.total_pnl_pct:+.1f}%" for r in all_r])
    row("盈利因子", [f"{r.profit_factor:.2f}" for r in all_r])
    row("期望值", [f"{r.expectancy:+.2f}" for r in all_r])
    row("回撤率", [f"{r.max_drawdown_pct:.1f}%" for r in all_r])
    row("最终资金", [f"{r.final_balance:.0f}" for r in all_r])
    row("收益/回撤", [f"{r.total_pnl_pct/r.max_drawdown_pct:.2f}" if r.max_drawdown_pct > 0 else "N/A" for r in all_r])

    # 出场分布
    print()
    for lb, r in results:
        tp = sum(1 for t in r.trades if t.exit_reason == "TAKE_PROFIT")
        sl = sum(1 for t in r.trades if t.exit_reason == "STOP_LOSS")
        ts = sum(1 for t in r.trades if t.exit_reason == "TRAILING_STOP")
        sig = sum(1 for t in r.trades if t.exit_reason == "SIGNAL")
        print(f"  {lb}: 止盈{tp} 止损{sl} 移动{ts} 信号{sig}")

    # 最优
    best = max(results, key=lambda x: x[1].total_pnl_pct)
    best_ratio = max(results, key=lambda x: x[1].total_pnl_pct / x[1].max_drawdown_pct if x[1].max_drawdown_pct > 0 else 0)
    print(f"\n  ★ 最高收益: {best[0]}  {best[1].total_pnl_pct:+.2f}%  回撤{best[1].max_drawdown_pct:.1f}%")
    print(f"  ★ 最优风险: {best_ratio[0]}  收益/回撤={best_ratio[1].total_pnl_pct/best_ratio[1].max_drawdown_pct:.2f}")
    print()


if __name__ == "__main__":
    main()
