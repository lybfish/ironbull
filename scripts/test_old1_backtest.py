#!/usr/bin/env python3
"""
使用old1的回测引擎运行回测
"""

import sys
import os
from datetime import datetime, timedelta

# 添加old1路径
old1_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "_legacy_readonly", "old1", "1.trade.7w1.top", "scripts"))
sys.path.insert(0, old1_path)

try:
    from backtest_engine import smc_backtest
except ImportError as e:
    print(f"❌ 无法导入old1回测引擎: {e}")
    print(f"   路径: {old1_path}")
    sys.exit(1)

import ccxt

# 配置
SYMBOL = "ETHUSD"
TIMEFRAME = "15m"
HTF_TIMEFRAME = "1h"

# 获取K线数据
print("📊 从交易所获取K线数据...")
exchange = ccxt.binance({"enableRateLimit": True})
ccxt_symbol = SYMBOL.replace("USD", "USDT")

# 获取小周期K线（15m）
since = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)
ltf_candles = []
current_since = since
while len(ltf_candles) < 35000:
    ohlcv = exchange.fetch_ohlcv(ccxt_symbol, TIMEFRAME, since=current_since, limit=1000)
    if not ohlcv:
        break
    for row in ohlcv:
        ltf_candles.append({
            "ts": int(row[0] / 1000),  # 转为秒
            "o": float(row[1]),
            "h": float(row[2]),
            "l": float(row[3]),
            "c": float(row[4]),
            "v": float(row[5]),
        })
    current_since = ohlcv[-1][0] + 1
    if len(ohlcv) < 1000:
        break

print(f"✅ 获取到 {len(ltf_candles)} 根{TIMEFRAME}K线")

# 获取大周期K线（1h）
htf_candles = []
current_since = since
while len(htf_candles) < 9000:
    ohlcv = exchange.fetch_ohlcv(ccxt_symbol, HTF_TIMEFRAME, since=current_since, limit=1000)
    if not ohlcv:
        break
    for row in ohlcv:
        htf_candles.append({
            "ts": int(row[0] / 1000),
            "o": float(row[1]),
            "h": float(row[2]),
            "l": float(row[3]),
            "c": float(row[4]),
            "v": float(row[5]),
        })
    current_since = ohlcv[-1][0] + 1
    if len(ohlcv) < 1000:
        break

print(f"✅ 获取到 {len(htf_candles)} 根{HTF_TIMEFRAME}K线")

# old1默认参数
params = {
    "symbol": SYMBOL,
    "timeframe": TIMEFRAME,
    "strategy": "smc_fibo",
    "entry_mode": "retest",
    "order_type": "limit",
    "rr": 2,
    "tif_bars": 20,
    "initial_cash": 10000,
    "fee_bps": 4,  # 0.04%
    "risk_cash": 100,  # 每单风险100 USDT
    "smc": {
        "fiboLevels": [0.5, 0.618, 0.705],
        "retestBars": 20,
        "minRr": 2,
        "pinbarRatio": 1.5,
        "allowEngulf": True,
        "stopBufferPct": 0.05,
        "stopSource": "auto",
        "tpMode": "swing",
        "bias": "with_trend",
        "structure": "both",
        "entry": "auto",
        "session": "all",
        "htfTimeframe": HTF_TIMEFRAME,
        "fiboFallback": True,
        "retestIgnoreStopTouch": False,
    },
}

print("\n🚀 开始old1回测...")
print(f"   参数: stopBufferPct={params['smc']['stopBufferPct']}, tpMode={params['smc']['tpMode']}, pinbarRatio={params['smc']['pinbarRatio']}")

try:
    result = smc_backtest(params, ltf_candles, htf_candles)
    
    # 提取结果
    trades = result.get("trades", [])
    equity_series = result.get("equity", [])
    
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if (t.get("pnl") or 0) > 0)
    losing_trades = sum(1 for t in trades if (t.get("pnl") or 0) < 0)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = sum(t.get("pnl", 0) for t in trades)
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
    avg_win = sum(t.get("pnl", 0) for t in trades if (t.get("pnl") or 0) > 0) / winning_trades if winning_trades > 0 else 0
    avg_loss = sum(t.get("pnl", 0) for t in trades if (t.get("pnl") or 0) < 0) / losing_trades if losing_trades > 0 else 0
    
    initial_balance = params.get("initial_cash", 10000)
    final_balance = equity_series[-1].get("equity", initial_balance) if equity_series else initial_balance
    total_return_pct = ((final_balance - initial_balance) / initial_balance * 100) if initial_balance > 0 else 0
    
    # 计算最大回撤
    max_drawdown = 0
    peak = initial_balance
    for eq in equity_series:
        equity = eq.get("equity", initial_balance)
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    max_drawdown_pct = (max_drawdown / peak * 100) if peak > 0 else 0
    
    print("\n" + "="*70)
    print("📈 Old1 回测结果")
    print("="*70)
    print(f"\n📊 交易统计:")
    print(f"  总交易次数: {total_trades}")
    print(f"  盈利交易: {winning_trades} ({winning_trades/total_trades*100:.1f}%)")
    print(f"  亏损交易: {losing_trades} ({losing_trades/total_trades*100:.1f}%)")
    print(f"  胜率: {win_rate:.2f}%")
    
    print(f"\n💰 收益统计:")
    print(f"  初始资金: ${initial_balance:,.2f}")
    print(f"  最终资金: ${final_balance:,.2f}")
    print(f"  总盈亏: ${total_pnl:,.2f}")
    print(f"  总收益率: {total_return_pct:.2f}%")
    print(f"  平均每笔: ${avg_pnl:,.2f}")
    print(f"  平均盈利: ${avg_win:,.2f}")
    print(f"  平均亏损: ${avg_loss:,.2f}")
    
    print(f"\n⚠️  风险统计:")
    print(f"  最大回撤: ${max_drawdown:,.2f}")
    print(f"  最大回撤率: {max_drawdown_pct:.2f}%")
    
    print("\n" + "="*70)
    
except Exception as e:
    print(f"\n❌ 回测失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
