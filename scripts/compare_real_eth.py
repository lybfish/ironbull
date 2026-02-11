#!/usr/bin/env python3
"""
对比: confirm_after_fill=True vs False

目的: 用数据对比"成交后确认过滤"和"成交直接设SL/TP"哪个更好
"""

import time, json, sys, os
from datetime import datetime

sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "_legacy_readonly/old1/1.trade.7w1.top/scripts"))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy
from backtest_engine import smc_backtest


def load_eth_data():
    with open("docs/eth_15m_1year.json", "r") as f:
        return json.load(f)["candles"]

def to_old1_fmt(c):
    return [{"ts": x["timestamp"], "o": x["open"], "h": x["high"],
             "l": x["low"], "c": x["close"], "v": x["volume"]} for x in c]

def to_flex_fmt(c):
    return [{"timestamp": datetime.fromtimestamp(x["timestamp"]).isoformat(),
             "open": x["open"], "high": x["high"], "low": x["low"],
             "close": x["close"], "volume": x["volume"]} for x in c]


def run_old1(candles_old1, tf="15m", commission=0.0004):
    params = {
        "symbol": "ETHUSD", "realtime_mode": True, "timeframe": tf,
        "initial_cash": 10000.0, "risk_cash": 100.0, "commission_rate": commission,
        "strategy": "smc_fibo", "entry_mode": "retest", "order_type": "limit",
        "rr": 2, "tif_bars": 20,
        "smc": {"fiboLevels": [0.5, 0.618, 0.705], "retestBars": 20, "minRr": 2,
                "pinbarRatio": 1.5, "allowEngulf": True, "stopBufferPct": 0.05,
                "stopSource": "auto", "tpMode": "swing", "bias": "with_trend",
                "structure": "both", "entry": "auto", "session": "all",
                "fiboFallback": True, "retestIgnoreStopTouch": False}
    }
    t0 = time.time()
    result = smc_backtest(params, candles_old1, candles_old1)
    elapsed = time.time() - t0
    trades = result.get("trades", [])
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    losses = sum(1 for t in trades if t.get("pnl", 0) <= 0)
    total_pnl = sum(t.get("pnl", 0) for t in trades)
    equity, peak, max_dd = 10000.0, 10000.0, 0.0
    for t in trades:
        equity += t.get("pnl", 0)
        if equity > peak: peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd: max_dd = dd
    gross_profit = sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0)
    gross_loss = sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) <= 0)
    pf = abs(gross_profit / min(-0.01, gross_loss))
    return {
        "name": f"old1", "elapsed": elapsed,
        "signal_count": len(result.get("signals", [])), "trade_count": len(trades),
        "wins": wins, "losses": losses,
        "win_rate": (wins / len(trades) * 100) if trades else 0,
        "total_pnl": total_pnl,
        "avg_win": gross_profit / max(1, wins),
        "avg_loss": gross_loss / max(1, losses),
        "profit_factor": pf, "max_drawdown": max_dd,
        "final_equity": equity,
    }


def run_flex(candles_flex, tf="15m", config_ov=None, engine_ov=None):
    cfg = {
        "preset_profile": "none", "swing": 3, "max_loss": 100,
        "min_rr": 1.5, "fibo_levels": [0.5, 0.618, 0.705],
        "entry_mode": "limit", "require_retest": True, "retest_bars": 20,
        "entry_source": "auto", "require_htf_filter": False,
        "enable_signal_score": False, "duplicate_signal_filter_bars": 0,
        "stopBufferPct": 1.0, "bias": "with_trend", "structure": "both",
        "signal_cooldown": 20, "fibo_fallback": False, "tp_mode": "swing",
        "enable_session_filter": False, "amd_entry_mode": "off",
        "use_breaker": False, "auto_profile": "off",
        "confirm_after_fill": True, "post_fill_confirm_bars": 3,
    }
    if config_ov:
        cfg.update(config_ov)
    
    eng_params = {
        "initial_balance": 10000.0, "commission_rate": 0.0004,
        "risk_per_trade": 100.0, "max_drawdown_pct": 100.0,
        "max_consecutive_losses": 0, "slippage_pct": 0.05,
    }
    post_attrs = {}
    if engine_ov:
        for key in ("dd_scale_levels", "strict_single_position"):
            if key in engine_ov:
                post_attrs[key] = engine_ov.pop(key)
        eng_params.update(engine_ov)
    
    strategy = get_strategy("smc_fibo_flex", cfg)
    engine = BacktestEngine(**eng_params)
    for attr, val in post_attrs.items():
        setattr(engine, attr, val)
    
    t0 = time.time()
    result = engine.run(strategy=strategy, symbol="ETHUSDT", timeframe=tf,
                        candles=candles_flex, lookback=50)
    elapsed = time.time() - t0
    
    confirmed = getattr(strategy, "_debug_post_fill_confirmed", 0)
    unconfirmed = getattr(strategy, "_debug_post_fill_unconfirmed", 0)
    total_cf = confirmed + unconfirmed
    cf_rate = confirmed / total_cf * 100 if total_cf > 0 else 0
    
    return {
        "name": cfg.get("_label", f"flex_{tf}"),
        "trade_count": result.total_trades,
        "wins": result.winning_trades, "losses": result.losing_trades,
        "win_rate": result.win_rate,
        "total_pnl": result.total_pnl,
        "avg_win": result.avg_win, "avg_loss": result.avg_loss,
        "profit_factor": result.profit_factor,
        "max_drawdown": result.max_drawdown_pct,
        "final_equity": result.final_balance,
        "cf_rate": cf_rate,
        "_confirmed": confirmed,
        "_unconfirmed": unconfirmed,
    }


def pr(results, title):
    """打印对比表格"""
    if not results: return
    print(f"\n{'='*110}")
    print(f"  {title}")
    print(f"{'='*110}")
    cols = "".join(f"{r['name']:>16}" for r in results)
    print(f"  {'':>14}{cols}")
    print(f"  {'-'*14}" + "-" * (16 * len(results)))
    
    def row(lbl, key, fmt=".0f"):
        vals = "".join(f"{r[key]:>16{fmt}}" for r in results)
        print(f"  {lbl:>14}{vals}")
    
    row("交易数", "trade_count")
    row("胜率(%)", "win_rate", ".1f")
    row("PF", "profit_factor", ".2f")
    row("PnL($)", "total_pnl", ".0f")
    row("均赢($)", "avg_win", ".1f")
    row("均亏($)", "avg_loss", ".1f")
    row("回撤(%)", "max_drawdown", ".1f")
    row("终值($)", "final_equity", ".0f")
    
    # 确认率
    has_cf = any(r.get("cf_rate", 0) > 0 for r in results)
    if has_cf:
        vals = "".join(f"{r.get('cf_rate', 0):>16.1f}" for r in results)
        print(f"  {'确认率(%)':>14}{vals}")
        vals2 = "".join(f"{r.get('_confirmed', 0):>16.0f}" for r in results)
        print(f"  {'确认通过':>14}{vals2}")
        vals3 = "".join(f"{r.get('_unconfirmed', 0):>16.0f}" for r in results)
        print(f"  {'确认失败':>14}{vals3}")
    
    print(f"  {'-'*14}" + "-" * (16 * len(results)))
    
    for r in results:
        if r["trade_count"] == 0:
            print(f"  ❌ {r['name']}: 无交易")
            continue
        ico = "🏆" if r["profit_factor"] >= 1.5 else "✅" if r["profit_factor"] >= 1.2 else "⚠️" if r["profit_factor"] >= 1.0 else "❌"
        print(f"  {ico} {r['name']}: T={r['trade_count']}, WR={r['win_rate']:.1f}%, PF={r['profit_factor']:.2f}, PnL=${r['total_pnl']:.0f}, DD={r['max_drawdown']:.1f}%")


def main():
    print("=" * 110)
    print("  🎯 对比: confirm_after_fill = True vs False")
    print("  基线参数: stopBufferPct=1.0%, signal_cooldown=20, maker 0.04%, SL滑点 0.05%")
    print("=" * 110)
    
    raw_15m = load_eth_data()
    flex_data = to_flex_fmt(raw_15m)
    old1_data = to_old1_fmt(raw_15m)
    print(f"  15m K线: {len(raw_15m)}")
    
    # old1 基准
    r_old1 = run_old1(old1_data)
    r_old1["cf_rate"] = 0
    r_old1["_confirmed"] = 0
    r_old1["_unconfirmed"] = 0
    
    eng_base = {"strict_single_position": True}
    cfg_base = {"signal_cooldown": 20, "stopBufferPct": 1.0}
    
    results = [r_old1]
    
    # ════════════════════════════════════════════════════════════════
    # 方案 A: confirm_after_fill = False (成交直接设SL/TP)
    # ════════════════════════════════════════════════════════════════
    print("\n  测试 A: 不确认(成交直接设SL/TP)...")
    r_no_confirm = run_flex(flex_data, "15m",
        {**cfg_base, "_label": "不确认(直接SL/TP)",
         "confirm_after_fill": False},
        {**eng_base})
    results.append(r_no_confirm)
    print(f"    T={r_no_confirm['trade_count']}, WR={r_no_confirm['win_rate']:.1f}%, PF={r_no_confirm['profit_factor']:.2f}, DD={r_no_confirm['max_drawdown']:.1f}%")
    
    # ════════════════════════════════════════════════════════════════
    # 方案 B: confirm_after_fill = True, post_fill_confirm_bars = 3
    # ════════════════════════════════════════════════════════════════
    print("  测试 B: 确认3根K线...")
    r_confirm_3 = run_flex(flex_data, "15m",
        {**cfg_base, "_label": "确认3根K线",
         "confirm_after_fill": True, "post_fill_confirm_bars": 3},
        {**eng_base})
    results.append(r_confirm_3)
    print(f"    T={r_confirm_3['trade_count']}, WR={r_confirm_3['win_rate']:.1f}%, PF={r_confirm_3['profit_factor']:.2f}, DD={r_confirm_3['max_drawdown']:.1f}%")
    
    # ════════════════════════════════════════════════════════════════
    # 方案 C: confirm_after_fill = True, post_fill_confirm_bars = 2
    # ════════════════════════════════════════════════════════════════
    print("  测试 C: 确认2根K线...")
    r_confirm_2 = run_flex(flex_data, "15m",
        {**cfg_base, "_label": "确认2根K线",
         "confirm_after_fill": True, "post_fill_confirm_bars": 2},
        {**eng_base})
    results.append(r_confirm_2)
    print(f"    T={r_confirm_2['trade_count']}, WR={r_confirm_2['win_rate']:.1f}%, PF={r_confirm_2['profit_factor']:.2f}, DD={r_confirm_2['max_drawdown']:.1f}%")
    
    # ════════════════════════════════════════════════════════════════
    # 方案 D: confirm_after_fill = True, post_fill_confirm_bars = 5
    # ════════════════════════════════════════════════════════════════
    print("  测试 D: 确认5根K线...")
    r_confirm_5 = run_flex(flex_data, "15m",
        {**cfg_base, "_label": "确认5根K线",
         "confirm_after_fill": True, "post_fill_confirm_bars": 5},
        {**eng_base})
    results.append(r_confirm_5)
    print(f"    T={r_confirm_5['trade_count']}, WR={r_confirm_5['win_rate']:.1f}%, PF={r_confirm_5['profit_factor']:.2f}, DD={r_confirm_5['max_drawdown']:.1f}%")
    
    # ════════════════════════════════════════════════════════════════
    # 方案 E: confirm_after_fill = True, post_fill_confirm_bars = 1
    # ════════════════════════════════════════════════════════════════
    print("  测试 E: 确认1根K线...")
    r_confirm_1 = run_flex(flex_data, "15m",
        {**cfg_base, "_label": "确认1根K线",
         "confirm_after_fill": True, "post_fill_confirm_bars": 1},
        {**eng_base})
    results.append(r_confirm_1)
    print(f"    T={r_confirm_1['trade_count']}, WR={r_confirm_1['win_rate']:.1f}%, PF={r_confirm_1['profit_factor']:.2f}, DD={r_confirm_1['max_drawdown']:.1f}%")
    
    # ════════════════════════════════════════════════════════════════
    # 汇总
    # ════════════════════════════════════════════════════════════════
    pr(results, "📊 confirm_after_fill 对比: 成交后是否需要确认?")
    
    # 找最佳
    flex_results = results[1:]  # 排除 old1
    best = max(flex_results, key=lambda x: x["profit_factor"])
    
    print(f"\n  🏆 最佳方案: {best['name']}")
    print(f"     PF={best['profit_factor']:.2f}, WR={best['win_rate']:.1f}%, DD={best['max_drawdown']:.1f}%, PnL=${best['total_pnl']:.0f}")
    
    if best.get("cf_rate", 0) > 0:
        print(f"     确认率={best['cf_rate']:.1f}% (通过{best['_confirmed']}, 失败{best['_unconfirmed']})")
    
    print()


if __name__ == "__main__":
    main()
