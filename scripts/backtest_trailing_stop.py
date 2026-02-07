#!/usr/bin/env python3
"""
移动止损回测对比

方案:
  E0: 基准 — 固定 45% TP / 70% SL（对照组）
  E1: 纯移动止损 30% margin（价格回撤 1.5%），立即激活，无固定 TP
  E2: 纯移动止损 50% margin（价格回撤 2.5%），立即激活，无固定 TP
  E3: 保本+移动 — 初始 SL 70%，浮盈 >= 20% margin 后 SL 移到成本价，之后 30% margin 跟踪
  E4: 保本+移动 — 初始 SL 70%，浮盈 >= 20% margin 后 SL 移到成本价，之后 50% margin 跟踪

模型: 逐仓 20X，保证金 10 USDT，仓位 200 USDT，投入本金 2000 USDT
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
TP_PCT = 0.45
SL_PCT = 0.70
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


def run(candles, label, strategy_config, engine_kwargs):
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
    
    # 显示前 5 笔交易
    if r.trades:
        print(f"  前5笔:")
        for t in r.trades[:5]:
            side = "多" if t.side == "BUY" else "空"
            pnl_s = f"{t.pnl:+.2f}" if t.pnl else "N/A"
            exit_s = f"{t.exit_price:.2f}" if t.exit_price else "N/A"
            print(f"    [{t.trade_id:>3}] {side} @ {t.entry_price:.2f} -> {exit_s}  PnL={pnl_s}  {t.exit_reason}")


def main():
    candles = load_candles()
    
    print("=" * 60)
    print("  移动止损回测对比 (ETH/USDT 1h, 一年)")
    print(f"  K线: {len(candles)} 根  |  {candles[0]['timestamp'][:10]} ~ {candles[-1]['timestamp'][:10]}")
    print(f"  本金: {BALANCE}  |  仓位: {POS_VAL}  |  杠杆: {LEVERAGE}X  |  保证金: {MARGIN}")
    print("=" * 60)
    
    # 通用策略参数（保证金百分比模式）
    base_strategy = {
        "sl_tp_mode": "margin_pct",
        "leverage": LEVERAGE,
        "tp_pct": TP_PCT,
        "sl_pct": SL_PCT,
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
    
    # ── E0: 基准 (固定 45% TP / 70% SL) ──
    r0 = run(candles, "E0", base_strategy, base_engine)
    print_detail("E0: 基准 — 固定 TP 45% / SL 70%", r0)
    
    # ── E1: 纯移动止损 30% margin，立即激活，无 TP ──
    s1 = {**base_strategy, "tp_pct": 0, "sl_pct": SL_PCT}  # 无固定 TP, 保留初始 SL
    e1 = {**base_engine, "trailing_stop_pct": 0.30, "trailing_activation_pct": 0.0}
    r1 = run(candles, "E1", s1, e1)
    print_detail("E1: 纯移动止损 30% margin (回撤 1.5%), 立即激活", r1)
    
    # ── E2: 纯移动止损 50% margin，立即激活，无 TP ──
    s2 = {**base_strategy, "tp_pct": 0, "sl_pct": SL_PCT}
    e2 = {**base_engine, "trailing_stop_pct": 0.50, "trailing_activation_pct": 0.0}
    r2 = run(candles, "E2", s2, e2)
    print_detail("E2: 纯移动止损 50% margin (回撤 2.5%), 立即激活", r2)
    
    # ── E3: 保本 + 移动止损 30%，激活阈值 20% ──
    s3 = {**base_strategy, "tp_pct": 0, "sl_pct": SL_PCT}  # 无固定 TP
    e3 = {**base_engine, "trailing_stop_pct": 0.30, "trailing_activation_pct": 0.20}
    r3 = run(candles, "E3", s3, e3)
    print_detail("E3: 保本+移动 30% (浮盈>=20% margin后激活)", r3)
    
    # ── E4: 保本 + 移动止损 50%，激活阈值 20% ──
    s4 = {**base_strategy, "tp_pct": 0, "sl_pct": SL_PCT}
    e4 = {**base_engine, "trailing_stop_pct": 0.50, "trailing_activation_pct": 0.20}
    r4 = run(candles, "E4", s4, e4)
    print_detail("E4: 保本+移动 50% (浮盈>=20% margin后激活)", r4)
    
    # ── 汇总对比 ──
    labels = [
        "E0:固定TP/SL",
        "E1:移动30%即时",
        "E2:移动50%即时",
        "E3:保本+移30%",
        "E4:保本+移50%",
    ]
    all_r = [r0, r1, r2, r3, r4]
    
    print(f"\n{'=' * 90}")
    print(f"  汇总对比")
    print(f"{'=' * 90}")
    
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
    
    print()


if __name__ == "__main__":
    main()
