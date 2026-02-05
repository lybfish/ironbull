#!/usr/bin/env python3
"""
简单回测测试 - 不依赖 HTTP 服务

直接测试回测引擎核心功能。
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy


def generate_mock_candles(count: int = 500, base_price: float = 50000.0):
    """生成模拟K线数据（带趋势）"""
    
    candles = []
    current_time = datetime.now() - timedelta(minutes=15 * count)
    
    for i in range(count):
        # 生成带趋势的价格
        trend = i * 2  # 上涨趋势
        noise = (hash(i) % 100) - 50  # 随机波动
        
        open_price = base_price + trend + noise
        close_price = open_price + ((hash(i * 2) % 100) - 50)
        high_price = max(open_price, close_price) + abs(hash(i * 3) % 50)
        low_price = min(open_price, close_price) - abs(hash(i * 4) % 50)
        
        candles.append({
            "timestamp": current_time.isoformat(),
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": 100.0 + (hash(i * 5) % 50),
        })
        
        current_time += timedelta(minutes=15)
    
    return candles


def main():
    print("=" * 60)
    print("回测引擎简单测试")
    print("=" * 60)
    print()
    
    # 1. 生成测试数据
    print("1️⃣  生成模拟K线数据...")
    candles = generate_mock_candles(count=500, base_price=50000.0)
    print(f"✅ 生成 {len(candles)} 根K线")
    print(f"   时间范围: {candles[0]['timestamp']} ~ {candles[-1]['timestamp']}")
    print(f"   价格范围: {candles[0]['close']:.2f} ~ {candles[-1]['close']:.2f}")
    print()
    
    # 2. 加载策略
    print("2️⃣  加载策略...")
    strategy = get_strategy("ma_cross", {"fast_ma": 5, "slow_ma": 20})
    print(f"✅ 策略加载成功: {strategy.name}")
    print()
    
    # 3. 创建回测引擎
    print("3️⃣  创建回测引擎...")
    engine = BacktestEngine(
        initial_balance=10000.0,
        commission_rate=0.001,
    )
    print(f"✅ 引擎创建成功")
    print(f"   初始资金: {engine.initial_balance} USDT")
    print(f"   手续费率: {engine.commission_rate * 100}%")
    print()
    
    # 4. 运行回测
    print("4️⃣  运行回测...")
    result = engine.run(
        strategy=strategy,
        symbol="BTCUSDT",
        timeframe="15m",
        candles=candles,
        lookback=50,
    )
    print(f"✅ 回测完成")
    print()
    
    # 5. 显示结果
    print("=" * 60)
    print("📊 回测结果")
    print("=" * 60)
    print()
    
    print(f"策略: {result.strategy_code}")
    print(f"交易对: {result.symbol}")
    print(f"周期: {result.timeframe}")
    print(f"时间范围: {result.start_time} ~ {result.end_time}")
    print()
    
    print("📈 交易统计")
    print(f"  总交易次数: {result.total_trades}")
    print(f"  盈利次数: {result.winning_trades}")
    print(f"  亏损次数: {result.losing_trades}")
    print(f"  胜率: {result.win_rate:.2f}%")
    print()
    
    print("💰 收益统计")
    print(f"  总盈亏: {result.total_pnl:.2f} USDT")
    print(f"  总收益率: {result.total_pnl_pct:.2f}%")
    print(f"  平均盈亏: {result.avg_pnl:.2f} USDT")
    print(f"  平均盈利: {result.avg_win:.2f} USDT")
    print(f"  平均亏损: {result.avg_loss:.2f} USDT")
    print()
    
    print("⚠️  风险统计")
    print(f"  最大回撤: {result.max_drawdown:.2f} USDT")
    print(f"  最大回撤率: {result.max_drawdown_pct:.2f}%")
    print()
    
    print("💼 账户统计")
    print(f"  初始资金: {result.initial_balance:.2f} USDT")
    print(f"  最终资金: {result.final_balance:.2f} USDT")
    print(f"  最高资金: {result.peak_balance:.2f} USDT")
    print()
    
    if result.trades:
        print("📝 交易记录（前5笔）")
        for trade in result.trades[:5]:
            print(f"  [{trade.trade_id}] {trade.side} @ {trade.entry_price:.2f} "
                  f"→ {trade.exit_price:.2f} | "
                  f"PnL: {trade.pnl:.2f} ({trade.pnl_pct:.2f}%) | "
                  f"{trade.exit_reason}")
        
        if len(result.trades) > 5:
            print(f"  ... 还有 {len(result.trades) - 5} 笔交易")
    else:
        print("📝 无交易记录")
    
    print()
    print("=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
