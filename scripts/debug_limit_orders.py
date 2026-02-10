#!/usr/bin/env python3
"""
调试限价单处理逻辑
"""

import json
import sys
sys.path.insert(0, '.')
from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy
from datetime import datetime

# 加载数据
with open("docs/eth_15m_1year.json", 'r') as f:
    data = json.load(f)
candles = data["candles"][-2000:]  # 最后2000根

# 转换时间戳
for c in candles:
    if isinstance(c.get("timestamp"), (int, float)):
        ts = c["timestamp"]
        if ts > 1e10:
            ts = ts / 1000
        c["timestamp"] = datetime.fromtimestamp(ts).isoformat()

strategy = get_strategy("smc_fibo_flex", {
    "preset_profile": "balanced",
    "require_retest": False,
    "require_htf_filter": False,
    "enable_signal_score": False,
    "min_rr": 1.0,
    "fibo_tolerance": 0.02,
    "allow_limit_orders": True,
    "signal_cooldown": 3,
})

engine = BacktestEngine(
    initial_balance=10000.0,
    commission_rate=0.001,
    risk_per_trade=100.0,
    min_rr=0.0,
)

# 统计
stats = {
    "signals_generated": 0,
    "limit_orders_created": 0,
    "limit_orders_touched": 0,
    "limit_orders_filled": 0,
    "market_orders": 0,
    "check_pending_calls": 0,
    "check_pending_results": {"None": 0, "StrategyOutput": 0, "waiting": 0, "other": 0},
    "pending_orders_expired": 0,
    "pending_orders_stop_touched": 0,
}

# 使用run方法，但添加钩子来追踪
original_check_pending = engine._check_pending_orders
original_handle_signal = engine._handle_signal

def tracked_check_pending(*args, **kwargs):
    pending_before = len(engine.pending_orders)
    result = original_check_pending(*args, **kwargs)
    
    # 检查是否有新的成交
    if len(engine.trades) > stats["limit_orders_filled"]:
        stats["limit_orders_filled"] = len(engine.trades)
        if stats["limit_orders_filled"] <= 5:
            last_trade = engine.trades[-1]
            current_price = args[2] if len(args) > 2 else "N/A"
            print(f"✅ 成交 {stats['limit_orders_filled']}: {last_trade.side} @ {last_trade.entry_price:.2f} (当前: {current_price})")
    
    # 检查是否有新的触达
    for order in engine.pending_orders:
        if order.get("touched") and not order.get("logged", False):
            order["logged"] = True
            stats["limit_orders_touched"] += 1
            if stats["limit_orders_touched"] <= 5:
                current_price = args[2] if len(args) > 2 else "N/A"
                print(f"📍 限价单触达 {stats['limit_orders_touched']}: {order['side']} @ {order['entry_price']:.2f} (当前: {current_price})")
    
    # 检查超时的限价单
    if len(engine.pending_orders) < pending_before:
        stats["pending_orders_expired"] += pending_before - len(engine.pending_orders)
    
    return result

def tracked_handle_signal(signal, current_price, current_time):
    if signal and signal.signal_type == "OPEN":
        stats["signals_generated"] += 1
        entry_price = signal.entry_price
        diff_pct = abs(entry_price - current_price) / current_price * 100
        
        if diff_pct > 0.01:
            stats["limit_orders_created"] += 1
            if stats["limit_orders_created"] <= 10:
                print(f"📝 创建限价单 {stats['limit_orders_created']}: {signal.side} @ {entry_price:.2f} (当前: {current_price:.2f}, 差异: {diff_pct:.3f}%)")
        else:
            stats["market_orders"] += 1
            if stats["market_orders"] <= 5:
                print(f"💰 市价单 {stats['market_orders']}: {signal.side} @ {entry_price:.2f} (当前: {current_price:.2f})")
    
    return original_handle_signal(signal, current_price, current_time)

engine._check_pending_orders = tracked_check_pending
engine._handle_signal = tracked_handle_signal

# 运行回测
result = engine.run(
    strategy=strategy,
    symbol="ETHUSDT",
    timeframe="15m",
    candles=candles,
    lookback=50
)

print(f"\n{'='*70}")
print("📊 限价单处理统计")
print(f"{'='*70}")
print(f"  生成信号: {stats['signals_generated']}")
print(f"  创建限价单: {stats['limit_orders_created']}")
print(f"  市价单: {stats['market_orders']}")
print(f"  限价单触达: {stats['limit_orders_touched']}")
print(f"  限价单成交: {stats['limit_orders_filled']}")
print(f"  限价单超时: {stats['pending_orders_expired']}")
print(f"  剩余限价单: {len(engine.pending_orders)}")
print(f"  最终交易数: {len(engine.trades)}")
print(f"\n_check_pending调用统计:")
for k, v in stats["check_pending_results"].items():
    if v > 0:
        print(f"  {k}: {v}")
