#!/usr/bin/env python3
"""
SMC Fibo Flex 参数快速优化器 (逐参数扫描)

策略：固定基线，每次只变一个参数，找出每个参数的最优值，然后组合。
速度：~20 次回测，约 1 分钟完成。

用法: python3 scripts/param_optimizer.py
"""

import time, math, random, sys, os, json
from datetime import datetime, timedelta

sys.path.append(os.getcwd())

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy


# ======================== 数据生成 (固定种子) ========================

def generate_candles(count=8760):
    candles = []
    price = 50000.0
    ts = datetime(2023, 1, 1)
    random.seed(42)
    for i in range(count):
        trend = i * 8.0
        wave = math.sin(i / 30.0) * 1600
        noise = random.uniform(-160, 160)
        close = price + trend + wave + noise
        high = close + random.uniform(0, 106)
        low = close - random.uniform(0, 106)
        open_ = close + random.uniform(-40, 40)
        candles.append({
            "timestamp": (ts + timedelta(hours=i)).isoformat(),
            "open": open_, "high": max(high, open_, close),
            "low": min(low, open_, close), "close": close,
            "volume": random.uniform(100, 1000)
        })
    return candles


# ======================== 回测运行 ========================

def run_once(candles, overrides):
    """运行一次回测，返回关键指标"""
    base = {
        "preset_profile": "none",
        "swing": 2,
        "max_loss": 100,
        "min_rr": 2.0,
        "fibo_levels": [0.5, 0.618, 0.705],
        "entry_mode": "retest",
        "require_retest": True,
        "retest_bars": 20,
        "entry_source": "auto",
        "require_htf_filter": False,
        "enable_signal_score": False,
        "duplicate_signal_filter_bars": 0,
        "stopBufferPct": 0.05,
        "bias": "with_trend",
        "structure": "both",
        "signal_cooldown": 0,
        "enable_session_filter": True,
        "allowed_sessions": ["london", "ny"],
        "amd_entry_mode": "off",
        "use_breaker": True,
    }
    base.update(overrides)
    
    try:
        strategy = get_strategy("smc_fibo_flex", base)
        engine = BacktestEngine(
            initial_balance=10000.0, commission_rate=0.001,
            risk_per_trade=100.0, max_drawdown_pct=100.0,
            max_consecutive_losses=0,
        )
        r = engine.run(strategy=strategy, symbol="BTCUSD", timeframe="1h",
                       candles=candles, lookback=50)
        return {
            "trades": r.total_trades, "win_rate": r.win_rate,
            "pf": r.profit_factor, "pnl": r.total_pnl,
            "max_dd": r.max_drawdown_pct, "equity": r.final_balance,
        }
    except Exception as e:
        return {"trades": 0, "win_rate": 0, "pf": 0, "pnl": 0, "max_dd": 0, "equity": 10000, "error": str(e)}


def score(r):
    """综合评分"""
    if r["trades"] < 5 or r["pf"] == 0 or r["pnl"] < 0:
        return 0.0
    s = r["pf"]
    if r["win_rate"] >= 50: s *= 1.0 + (r["win_rate"] - 50) * 0.02
    if r["max_dd"] > 20: s *= 0.7
    elif r["max_dd"] <= 10: s *= 1.1
    if r["trades"] < 10: s *= 0.7
    return round(s, 3)


# ======================== 主程序 ========================

def main():
    print("=" * 80)
    print("  ⚡ SMC Fibo Flex 快速参数优化器 (逐参数扫描)")
    print("=" * 80)
    
    print("\n📊 生成 8760 根 1H K线...")
    candles = generate_candles(8760)
    
    # ===== 定义要扫描的参数 =====
    scan_params = {
        "min_rr":                [1.5, 2.0, 2.5, 3.0],
        "fibo_levels":           [
            [0.5, 0.618, 0.705],
            [0.382, 0.5, 0.618, 0.705],
            [0.382, 0.5, 0.618],
        ],
        "entry_source":          ["auto", "ob"],
        "require_retest":        [True, False],
        "bias":                  ["with_trend", "both"],
        "enable_session_filter": [True, False],
        "amd_entry_mode":        ["off", "basic"],
        "use_breaker":           [True, False],
        "swing":                 [2, 3, 5],
        "structure":             ["both", "bos", "choch"],
    }
    
    total_tests = sum(len(v) for v in scan_params.values())
    print(f"   扫描参数: {len(scan_params)} 个, 共 {total_tests} 次测试")
    print(f"   预计耗时: ~{total_tests * 3}秒\n")
    
    # ===== Step 1: 跑基线 =====
    print("── 基线测试 ──")
    t0 = time.time()
    baseline = run_once(candles, {})
    bl_score = score(baseline)
    print(f"   基线: PF={baseline['pf']:.2f}  WR={baseline['win_rate']:.1f}%  "
          f"T={baseline['trades']}  PnL=${baseline['pnl']:.0f}  DD={baseline['max_dd']:.1f}%  "
          f"Score={bl_score:.2f}  ({time.time()-t0:.1f}s)")
    
    # ===== Step 2: 逐参数扫描 =====
    best_values = {}  # 记录每个参数的最优值
    
    print("\n── 逐参数扫描 ──\n")
    
    for param_name, values in scan_params.items():
        print(f"  📌 {param_name}:")
        best_score = -1
        best_val = values[0]
        
        for val in values:
            t0 = time.time()
            r = run_once(candles, {param_name: val})
            s = score(r)
            elapsed = time.time() - t0
            
            # 显示值
            val_str = str(val) if not isinstance(val, list) else f"[{','.join(str(v) for v in val)}]"
            bar = "█" * max(1, int(s * 3))
            marker = " 🏆" if s > bl_score * 1.05 else (" ⚠️" if s < bl_score * 0.5 else "")
            
            print(f"     {val_str:>35}  PF={r['pf']:>5.2f}  WR={r['win_rate']:>5.1f}%  "
                  f"T={r['trades']:>3}  PnL=${r['pnl']:>8.0f}  DD={r['max_dd']:>5.1f}%  "
                  f"Score={s:>5.2f} {bar}{marker}  ({elapsed:.1f}s)")
            
            if s > best_score:
                best_score = s
                best_val = val
        
        best_values[param_name] = best_val
        print(f"     ✅ 最优: {param_name} = {best_val}\n")
    
    # ===== Step 3: 组合最优参数，跑一次验证 =====
    print("\n" + "=" * 80)
    print("  🏆 组合最优参数验证")
    print("=" * 80)
    
    t0 = time.time()
    combined = run_once(candles, best_values)
    cs = score(combined)
    print(f"\n  组合最优: PF={combined['pf']:.2f}  WR={combined['win_rate']:.1f}%  "
          f"T={combined['trades']}  PnL=${combined['pnl']:.0f}  DD={combined['max_dd']:.1f}%  "
          f"Score={cs:.2f}  ({time.time()-t0:.1f}s)")
    print(f"  基线对比: PF={baseline['pf']:.2f}  WR={baseline['win_rate']:.1f}%  "
          f"T={baseline['trades']}  PnL=${baseline['pnl']:.0f}  DD={baseline['max_dd']:.1f}%  "
          f"Score={bl_score:.2f}")
    
    improvement = ((cs - bl_score) / max(0.01, bl_score)) * 100
    print(f"\n  📈 提升: {improvement:+.1f}%")
    
    # ===== 输出最终推荐配置 =====
    print("\n" + "=" * 80)
    print("  📋 推荐配置 (可直接使用)")
    print("=" * 80)
    
    final_config = {
        "preset_profile": "none",
        "max_loss": 100,
        "retest_bars": 20,
        "require_htf_filter": False,
        "enable_signal_score": False,
        "duplicate_signal_filter_bars": 0,
        "stopBufferPct": 0.05,
        "signal_cooldown": 0,
        "allowed_sessions": ["london", "ny"],
    }
    final_config.update(best_values)
    
    print(json.dumps(final_config, indent=2, ensure_ascii=False, default=str))
    
    print(f"\n  预期年化表现:")
    print(f"    盈亏比 (PF): {combined['pf']:.2f}")
    print(f"    胜率:        {combined['win_rate']:.1f}%")
    print(f"    年交易数:    {combined['trades']} 单")
    print(f"    年盈利:      ${combined['pnl']:.0f}")
    print(f"    最大回撤:    {combined['max_dd']:.1f}%")
    print(f"\n完成! 🎉")


if __name__ == "__main__":
    main()
