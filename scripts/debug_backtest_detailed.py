#!/usr/bin/env python3
"""
详细调试回测过程
"""

import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy
from datetime import datetime

# 加载数据
with open("docs/eth_15m_1year.json", 'r') as f:
    data = json.load(f)
candles = data["candles"][-1000:]  # 最后1000根

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
    "min_rr": 1.2,
    "fibo_tolerance": 0.01,
    "signal_cooldown": 0,
})

engine = BacktestEngine(
    initial_balance=10000.0,
    commission_rate=0.001,
    risk_per_trade=100.0,
    min_rr=0.0,
)

# 统计
stats = {
    "total_candles": 0,
    "signals_generated": 0,
    "signals_passed_rr": 0,
    "signals_handled": 0,
    "positions_opened": 0,
    "positions_closed": 0,
    "pending_orders_created": 0,
    "same_side_ignored": 0,
    "reverse_side_switched": 0,
}

# 手动模拟回测过程
lookback = 50
for i in range(lookback, len(candles)):
    stats["total_candles"] += 1
    history = candles[:i+1]
    current_candle = history[-1]
    current_price = current_candle["close"]
    current_time = engine._parse_time(current_candle["timestamp"])
    
    # 检查限价单
    prev_candle = history[-2] if len(history) >= 2 else None
    prev2_candle = history[-3] if len(history) >= 3 else None
    engine._check_pending_orders(
        current_candle["high"],
        current_candle["low"],
        current_price,
        current_time,
        current_candle,
        prev_candle,
        prev2_candle,
    )
    
    # 构建持仓信息
    positions = engine._build_positions_info()
    
    # 调用策略
    signal = strategy.analyze("ETHUSDT", "15m", history, positions)
    
    if signal and signal.signal_type == "OPEN":
        stats["signals_generated"] += 1
        
        # 检查RR
        if engine._check_min_rr(signal, current_price):
            stats["signals_passed_rr"] += 1
            
            # 检查是否有持仓
            has_position = engine.position is not None
            is_same_side = has_position and signal.side == engine.position.side
            is_reverse_side = has_position and signal.side != engine.position.side
            
            if is_same_side:
                stats["same_side_ignored"] += 1
                if stats["same_side_ignored"] <= 3:
                    print(f"[{i}] 同方向信号被忽略: {signal.side} @ {current_price:.2f} (已有持仓: {engine.position.side})")
            elif is_reverse_side:
                stats["reverse_side_switched"] += 1
                if stats["reverse_side_switched"] <= 3:
                    print(f"[{i}] 反向信号切换: {signal.side} @ {current_price:.2f} (平仓: {engine.position.side})")
            else:
                if stats["positions_opened"] <= 3:
                    print(f"[{i}] 开新仓: {signal.side} @ {current_price:.2f}")
            
            # 检查开仓前状态
            had_position_before = engine.position is not None
            
            # 处理信号
            engine._handle_signal(signal, current_price, current_time)
            stats["signals_handled"] += 1
            
            # 检查是否开仓（通过检查position是否从None变为有值）
            if not had_position_before and engine.position:
                stats["positions_opened"] += 1
                if stats["positions_opened"] <= 10:
                    print(f"  -> 开仓成功: {engine.position.side} @ {engine.position.entry_price:.2f}, SL={engine.position.stop_loss:.2f}, TP={engine.position.take_profit:.2f}")
    
    # 检查止损止盈
    position_before = engine.position
    if engine.position:
        is_long = engine.position.side == "BUY"
        engine._check_position_sl_tp(
            engine.position,
            current_candle["high"],
            current_candle["low"],
            current_time,
            is_long
        )
        if engine.position is None and position_before:
            stats["positions_closed"] += 1
            if stats["positions_closed"] <= 5:
                last_trade = engine.trades[-1] if engine.trades else None
                if last_trade and last_trade.exit_time == current_time:
                    print(f"[{i}] 平仓: {last_trade.exit_reason} @ {last_trade.exit_price:.2f}, PnL={last_trade.pnl:.2f}")
    
    # 更新权益曲线
    engine._update_equity(current_price, current_time)
    
    # 检查是否平仓
    if engine.position is None and stats["positions_opened"] > stats["positions_closed"]:
        stats["positions_closed"] += 1

# 强制平仓
last_candle = candles[-1]
last_price = last_candle["close"]
last_time = engine._parse_time(last_candle["timestamp"])
engine._close_all_positions(last_price, last_time, "END")

print("\n" + "=" * 60)
print("详细统计")
print("=" * 60)
print(f"总K线数: {stats['total_candles']}")
print(f"策略产生的信号: {stats['signals_generated']}")
print(f"通过RR检查: {stats['signals_passed_rr']}")
print(f"处理的信号: {stats['signals_handled']}")
print(f"开仓次数: {stats['positions_opened']}")
print(f"平仓次数: {stats['positions_closed']}")
print(f"同方向信号被忽略: {stats['same_side_ignored']}")
print(f"反向信号切换: {stats['reverse_side_switched']}")
print(f"限价单创建: {stats['pending_orders_created']}")
print(f"\n实际交易数（平仓记录）: {len(engine.trades)}")
if engine.trades:
    print(f"第一笔交易: {engine.trades[0].side} @ {engine.trades[0].entry_price:.2f} -> {engine.trades[0].exit_price:.2f} ({engine.trades[0].exit_reason})")
    print(f"最后一笔交易: {engine.trades[-1].side} @ {engine.trades[-1].entry_price:.2f} -> {engine.trades[-1].exit_price:.2f} ({engine.trades[-1].exit_reason})")
print("=" * 60)
