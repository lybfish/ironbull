#!/usr/bin/env python3
"""
从回测结果中取真实交易举例，展示完整生命周期
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy

SYMBOL = "ETH/USDT"
TIMEFRAME = "1h"


def load_candles():
    with open("/tmp/eth_usdt_1y_1h.json") as f:
        return json.load(f)


def main():
    candles = load_candles()

    # 用 H8 方案（1h 最优）
    strategy_config = {
        "sl_tp_mode": "margin_pct",
        "leverage": 20,
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
        "initial_balance": 2000,
        "commission_rate": 0.0005,
        "amount_usdt": 200,
        "leverage": 20,
        "margin_mode": "isolated",
    }

    strategy = get_strategy("market_regime", strategy_config)
    engine = BacktestEngine(**engine_kwargs)
    result = engine.run(strategy=strategy, symbol=SYMBOL, timeframe=TIMEFRAME, candles=candles, lookback=100)

    trades = result.trades

    print("=" * 90)
    print(f"  H8 方案真实交易举例 (ETH/USDT 1h, TP120%/SL40%, MACD+量比+冷却5)")
    print(f"  共 {len(trades)} 笔交易  |  本金 2000 USDT  |  每笔仓位 200 USDT  |  保证金 10 USDT")
    print("=" * 90)

    # ── 举例1: 前几笔交易（展示开头）──
    print(f"\n{'━' * 90}")
    print(f"  【前 10 笔交易】")
    print(f"{'━' * 90}")
    for t in trades[:10]:
        _print_trade(t)

    # ── 举例2: 找几笔止盈的 ──
    tp_trades = [t for t in trades if t.exit_reason == "TAKE_PROFIT"]
    print(f"\n{'━' * 90}")
    print(f"  【止盈案例】共 {len(tp_trades)} 笔止盈，挑 5 笔：")
    print(f"{'━' * 90}")
    for t in tp_trades[:5]:
        _print_trade(t)

    # ── 举例3: 找几笔止损的 ──
    sl_trades = [t for t in trades if t.exit_reason == "STOP_LOSS"]
    print(f"\n{'━' * 90}")
    print(f"  【止损案例】共 {len(sl_trades)} 笔止损，挑 5 笔：")
    print(f"{'━' * 90}")
    for t in sl_trades[:5]:
        _print_trade(t)

    # ── 举例4: 信号平仓的（策略方向切换）──
    sig_trades = [t for t in trades if t.exit_reason == "SIGNAL"]
    print(f"\n{'━' * 90}")
    print(f"  【信号平仓案例】共 {len(sig_trades)} 笔（策略方向切换导致平仓），挑 5 笔：")
    print(f"{'━' * 90}")
    for t in sig_trades[:5]:
        _print_trade(t)

    # ── 举例5: 最赚的 5 笔 ──
    best = sorted(trades, key=lambda t: t.pnl or 0, reverse=True)
    print(f"\n{'━' * 90}")
    print(f"  【最赚的 5 笔】")
    print(f"{'━' * 90}")
    for t in best[:5]:
        _print_trade(t)

    # ── 举例6: 最亏的 5 笔 ──
    worst = sorted(trades, key=lambda t: t.pnl or 0)
    print(f"\n{'━' * 90}")
    print(f"  【最亏的 5 笔】")
    print(f"{'━' * 90}")
    for t in worst[:5]:
        _print_trade(t)

    # ── 对冲配对举例（找相邻的多+空）──
    print(f"\n{'━' * 90}")
    print(f"  【对冲配对举例】找同时开的多+空：")
    print(f"{'━' * 90}")
    pairs_shown = 0
    for i in range(len(trades) - 1):
        t1 = trades[i]
        t2 = trades[i + 1]
        # 同一时间入场，一多一空
        if (t1.entry_time == t2.entry_time and
            t1.side != t2.side and
            abs(t1.entry_price - t2.entry_price) < 0.01):
            print(f"\n  ┌── 对冲组 @ {_fmt_time(t1.entry_time)}  入场价 {t1.entry_price:.2f}")
            _print_trade(t1, indent="  │ ")
            _print_trade(t2, indent="  │ ")
            net = (t1.pnl or 0) + (t2.pnl or 0)
            print(f"  └── 对冲净损益: {net:+.2f} USDT")
            pairs_shown += 1
            if pairs_shown >= 5:
                break

    print(f"\n{'=' * 90}")
    print(f"  总结: {result.total_trades}笔, 胜率{result.win_rate:.1f}%, "
          f"总PnL {result.total_pnl:+.2f}, 盈亏比{result.risk_reward_ratio:.2f}")
    print(f"{'=' * 90}\n")


def _fmt_time(t):
    if hasattr(t, 'strftime'):
        return t.strftime("%Y-%m-%d %H:%M")
    return str(t)[:16]


def _print_trade(t, indent="  "):
    side = "做多 ↑" if t.side == "BUY" else "做空 ↓"
    pnl_s = f"{t.pnl:+.2f}" if t.pnl is not None else "N/A"
    pnl_pct_s = f"{t.pnl_pct:+.1f}%" if t.pnl_pct is not None else ""
    result_emoji = "✅" if t.pnl and t.pnl > 0 else "❌"

    entry_t = _fmt_time(t.entry_time)
    exit_t = _fmt_time(t.exit_time) if t.exit_time else "持仓中"
    exit_p = f"{t.exit_price:.2f}" if t.exit_price else "—"

    # 持仓时长
    if t.entry_time and t.exit_time:
        if hasattr(t.exit_time, 'timestamp'):
            hours = (t.exit_time.timestamp() - t.entry_time.timestamp()) / 3600
        else:
            hours = 0
        duration = f"{hours:.0f}h" if hours < 48 else f"{hours/24:.1f}天"
    else:
        duration = "—"

    sl_s = f"{t.stop_loss:.2f}" if t.stop_loss else "无"
    tp_s = f"{t.take_profit:.2f}" if t.take_profit else "无"

    reason_map = {
        "TAKE_PROFIT": "止盈 💰",
        "STOP_LOSS": "止损 🛑",
        "TRAILING_STOP": "移动止损",
        "SIGNAL": "策略切换 🔄",
        "END": "到期平仓",
    }
    reason = reason_map.get(t.exit_reason, t.exit_reason or "—")

    print(f"{indent}[#{t.trade_id:>3}] {side}  {entry_t} → {exit_t}  ({duration})")
    print(f"{indent}       入场 {t.entry_price:.2f}  →  出场 {exit_p}  |  SL:{sl_s}  TP:{tp_s}")
    print(f"{indent}       数量 {t.quantity:.6f} ETH  |  名义 {t.entry_price * t.quantity:.1f} USDT")
    print(f"{indent}       {result_emoji} PnL: {pnl_s} USDT ({pnl_pct_s})  |  出场原因: {reason}")


if __name__ == "__main__":
    main()
