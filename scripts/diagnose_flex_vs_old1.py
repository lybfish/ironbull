import time
import math
import random
import sys
import os
import json
from datetime import datetime, timedelta

# 添加项目根目录到 sys.path
sys.path.append(os.getcwd())
# old1 path - append the scripts folder directly
sys.path.append(os.path.join(os.getcwd(), "_legacy_readonly/old1/1.trade.7w1.top/scripts"))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy
from backtest_engine import smc_backtest  # old1 engine (imported directly from its directory)

# ======================== 伪数据生成 ========================

def generate_candles_old1_format(count=2000, interval="15m"):
    """生成 old1 格式的 K线数据 (dict list)"""
    candles = []
    price = 50000.0
    ts = int(datetime(2023, 1, 1).timestamp())
    
    # 解析 interval
    if interval == "15m":
        seconds = 900
        trend_step = 2.0
        wave_period = 30.0
        noise_amp = 80
    elif interval == "1h":
        seconds = 3600
        trend_step = 8.0     # 4x 15m
        wave_period = 30.0   # keep same pattern length in bars (was 7.5, too fast for swing detection)
        noise_amp = 160      # ~2x noise (sqrt(4))
    else:
        seconds = 900
        trend_step = 2.0
        wave_period = 30.0
        noise_amp = 80

    # 模拟强趋势 + 噪音
    for i in range(count):
        # 趋势项：正弦波 + 线性增长 (模拟大牛市)
        trend = i * trend_step  # 强线性趋势
        wave = math.sin(i / wave_period) * (400 if interval=="15m" else 1600)  # 波动幅度也放大
        noise = random.uniform(-noise_amp, noise_amp)   # 噪音
        
        close = price + trend + wave + noise
        high = close + random.uniform(0, noise_amp/1.5)
        low = close - random.uniform(0, noise_amp/1.5)
        open_ = close + random.uniform(-noise_amp/4, noise_amp/4)
        
        candles.append({
            "ts": ts + i * seconds,
            "o": open_,
            "h": max(high, open_, close),
            "l": min(low, open_, close),
            "c": close,
            "v": random.uniform(100, 1000)
        })
    return candles

def old1_to_flex_format(candles_old1):
    """转换 old1 格式 K线到 flex 格式"""
    out = []
    for c in candles_old1:
        out.append({
            "timestamp": datetime.fromtimestamp(c["ts"]).isoformat(),
            "open": c["o"],
            "high": c["h"],
            "low": c["l"],
            "close": c["c"],
            "volume": c["v"]
        })
    return out

# ======================== 运行 old1 ========================

def run_old1(candles_old1, realtime=False, timeframe="15m"):
    """运行 old1 回测引擎，返回结果字典"""
    # old1 需要的参数
    params = {
        "symbol": "BTCUSD",
        "realtime_mode": realtime,
        "timeframe": timeframe,
        "initial_cash": 10000.0,
        "risk_cash": 100.0,  # 每笔风险
        "commission_rate": 0.001,
        "strategy": "smc_fibo", # 指定使用 smc_backtest
        "smc": {
            "fiboLevels": "0.5,0.618,0.705", # old1 默认
            "minRr": 2.0,
            "stopBufferPct": 0.05,
            "tpMode": "rr",
            "bias": "with_trend",
            "structure": "both",
            "fiboFallback": True, # old1 默认开启
        }
    }
    
    t0 = time.time()
    result = smc_backtest(params, candles_old1, candles_old1) # Pass candles as htf_candles too
    elapsed = time.time() - t0
    
    trades = result.get("trades", [])
    signals = result.get("signals", [])
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    losses = sum(1 for t in trades if t.get("pnl", 0) <= 0)
    total_pnl = sum(t.get("pnl", 0) for t in trades)
    buy_trades = sum(1 for t in trades if t.get("side") in ("BUY", "多"))
    sell_trades = sum(1 for t in trades if t.get("side") in ("SELL", "空"))
    win_rate = (wins / len(trades) * 100) if trades else 0
    
    # 计算最大回撤（从 trades PnL 序列）
    equity = 10000.0
    peak = equity
    max_dd = 0.0
    for t in trades:
        equity += t.get("pnl", 0)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd:
            max_dd = dd
            
    # 平均盈亏
    avg_win = sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0) / max(1, wins)
    avg_loss = sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) <= 0) / max(1, losses)
    profit_factor = abs(sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0) / min(-0.01, sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) <= 0)))

    return {
        "name": "old1",
        "elapsed": elapsed,
        "candle_count": len(candles_old1),
        "signal_count": len(signals),
        "trade_count": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "max_drawdown": max_dd,
        "final_equity": equity,
        "buy_trades": buy_trades,
        "sell_trades": sell_trades,
    }


# ======================== 运行 flex ========================

def run_flex(candles_flex, timeframe="15m"):
    """运行 smc_fibo_flex 通过 BacktestEngine，返回结果字典"""
    
    strategy_config = {
        # 为了公平对比 old1，这里关闭预设，直接用显式参数
        "preset_profile": "none",
        "swing": 2,                    # 优化：从 3 改为 2，加快结构确认速度（只滞后2根）
        "max_loss": 100,
        "min_rr": 2.0,                 # 严格对齐 Old1：恢复默认 RR=2.0
        "fibo_levels": [0.5, 0.618, 0.705], # 严格对齐 Old1：去掉 0.236/0.382
        # 恢复 retest 模式，复刻 old1 的"宽区成交"逻辑
        "entry_mode": "retest",
        "require_retest": True,        # 开启回踩确认
        # 诊断脚本不提供 HTF K线，因此关闭 HTF 过滤
        "require_htf_filter": False,
        # 关闭信号评分和去重，最大化信号数量
        "enable_signal_score": False,
        "duplicate_signal_filter_bars": 0,
        "stopBufferPct": 0.05,
        "bias": "with_trend",
        "structure": "both",
        "signal_cooldown": 0,          # 允许连续信号
    }
    
    strategy = get_strategy("smc_fibo_flex", strategy_config)
    
    engine = BacktestEngine(
        initial_balance=10000.0,
        commission_rate=0.001,
        risk_per_trade=100.0,
        # 暂时放宽回撤保护，看完整交易数
        max_drawdown_pct=100.0,
        # 诊断阶段暂时不限制连续亏损次数
        max_consecutive_losses=0,
    )
    
    t0 = time.time()
    result = engine.run(
        strategy=strategy,
        symbol="BTCUSD",
        timeframe=timeframe,
        candles=candles_flex,
        lookback=50
    )
    elapsed = time.time() - t0
    
    # 提取 BacktestResult 数据
    trades = result.trades
    # 信号统计需要从 engine 内部拿，或者通过 strategy 内部计数
    # 这里我们只看 trades
    
    return {
        "name": "smc_fibo_flex",
        "elapsed": elapsed,
        "candle_count": len(candles_flex),
        "signal_count": strategy.signal_count, 
        "trade_count": result.total_trades,
        "wins": result.winning_trades,
        "losses": result.losing_trades,
        "win_rate": result.win_rate,
        "total_pnl": result.total_pnl,
        "avg_win": result.avg_win,
        "avg_loss": result.avg_loss,
        "profit_factor": result.profit_factor,
        "max_drawdown": result.max_drawdown_pct,
        "final_equity": result.final_balance,
        "buy_trades": result.long_trades,
        "sell_trades": result.short_trades,
    }

def print_comparison(res1, res2, title_suffix=""):
    print("="*72)
    print(f"  回测对比: {res1['name']} vs {res2['name']}  ({title_suffix})")
    print("="*72)
    print(f"{'指标':<30} {res1['name']:>12} {res2['name']:>12}")
    print("-" * 72)
    print(f"  {'耗时':<30} {res1['elapsed']:>12.3f}s {res2['elapsed']:>12.3f}s")
    print(f"  {'信号数':<30} {res1['signal_count']:>12} {res2['signal_count']:>12}")
    print(f"  {'交易数 (下单)':<30} {res1['trade_count']:>12} {res2['trade_count']:>12}")
    print(f"    {'BUY':<30} {res1['buy_trades']:>12} {res2['buy_trades']:>12}")
    print(f"    {'SELL':<30} {res1['sell_trades']:>12} {res2['sell_trades']:>12}")
    print(f"  {'胜率':<30} {res1['win_rate']:>11.1f}% {res2['win_rate']:>11.1f}%")
    print(f"  {'盈利笔数':<30} {res1['wins']:>12} {res2['wins']:>12}")
    print(f"  {'亏损笔数':<30} {res1['losses']:>12} {res2['losses']:>12}")
    print(f"  {'总盈亏':<30} ${res1['total_pnl']:>11.2f} ${res2['total_pnl']:>11.2f}")
    print(f"  {'平均盈利':<30} ${res1['avg_win']:>11.2f} ${res2['avg_win']:>11.2f}")
    print(f"  {'平均亏损':<30} ${res1['avg_loss']:>11.2f} ${res2['avg_loss']:>11.2f}")
    print(f"  {'盈亏比(PF)':<30} {res1['profit_factor']:>12.2f} {res2['profit_factor']:>12.2f}")
    print(f"  {'最大回撤':<30} {res1['max_drawdown']:>11.2f}% {res2['max_drawdown']:>11.2f}%")
    print(f"  {'最终权益':<30} ${res1['final_equity']:>11.2f} ${res2['final_equity']:>11.2f}")
    print("-" * 72)
    
    # 简单的胜出判断
    best_pnl = res1['name'] if res1['total_pnl'] > res2['total_pnl'] else res2['name']
    best_wr = res1['name'] if res1['win_rate'] > res2['win_rate'] else res2['name']
    best_dd = res1['name'] if res1['max_drawdown'] < res2['max_drawdown'] else res2['name']
    speed_diff = res2['elapsed'] / res1['elapsed'] if res1['elapsed'] > 0 else 0
    
    print(f"\n  总结:")
    print(f"    PnL 更优: {best_pnl}")
    print(f"    胜率更优: {best_wr}")
    print(f"    回撤更优: {best_dd}")
    print(f"    速度差异: flex = {speed_diff:.1f}x old1 (架构差异: 逐步引擎 vs 批量)")
    print("\n")


def main():
    # 1. Run Standard 15m Test (35040 candles)
    size = 35040
    print(f"正在生成 {size} 根 15m K线数据 (≈1年)...")
    candles_old1 = generate_candles_old1_format(size, interval="15m")
    candles_flex = old1_to_flex_format(candles_old1)
    
    print(f"运行 old1 (lookahead, 15m)...")
    old1_res = run_old1(candles_old1, realtime=False, timeframe="15m")
    
    print(f"运行 smc_fibo_flex (15m)...")
    flex_res = run_flex(candles_flex, timeframe="15m")

    print_comparison(old1_res, flex_res, f"{size} 根 K线, 15m")
    
    # 2. Run 1H Test (8760 candles = 1 year)
    size_1h = 8760
    print("\n\n" + "="*72)
    print(f"  SWITCHING TO 1H TIMEFRAME (Same Duration, fewer candles)")
    print("="*72)
    print(f"正在生成 {size_1h} 根 1H K线数据 (≈1年)...")
    candles_old1_1h = generate_candles_old1_format(size_1h, interval="1h")
    candles_flex_1h = old1_to_flex_format(candles_old1_1h)
    
    print(f"运行 old1 (lookahead, 1h)...")
    old1_res_1h = run_old1(candles_old1_1h, realtime=False, timeframe="1h")
    
    print(f"运行 smc_fibo_flex (1h)...")
    flex_res_1h = run_flex(candles_flex_1h, timeframe="1h")
    
    print_comparison(old1_res_1h, flex_res_1h, f"{size_1h} 根 K线, 1H")

if __name__ == "__main__":
    main()
