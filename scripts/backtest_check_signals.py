#!/usr/bin/env python3
"""
ETHUSDT SMC Fibo Flex 回测 - 检查是否应该有信号
"""
import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies.smc_fibo_flex.strategy import SMCFiboFlexStrategy

# 获取最近 30 天的 ETHUSDT K线 (从线上 data-provider)
import httpx

def fetch_ethusdt_candles(timeframe="1h", limit=720):
    """从 data-provider 获取 ETHUSDT K线 (使用 SSH 隧道或服务器 IP)"""
    # 服务器 IP
    server_ip = "54.255.160.210"
    url = f"http://{server_ip}:8005/api/candles"
    resp = httpx.get(url, params={"symbol": "ETHUSDT", "timeframe": timeframe, "limit": limit})
    data = resp.json()
    return data.get("candles", [])

def run_backtest():
    print("=" * 60)
    print("ETHUSDT SMC Fibo Flex 回测")
    print("=" * 60)
    
    # 获取最近 30 天的 1h K线
    candles = fetch_ethusdt_candles("1h", 720)
    print(f"\n📊 获取到 {len(candles)} 根 K线")
    print(f"   时间范围: {datetime.fromtimestamp(candles[0]['timestamp'])} ~ {datetime.fromtimestamp(candles[-1]['timestamp'])}")
    
    if not candles:
        print("❌ 没有获取到数据")
        return
    
    # 策略配置 (balanced 预设)
    strategy_config = {
        "preset_profile": "balanced",
        "max_loss": 100,      # 每单最大亏损 100 USDT
        "min_rr": 1.8,        # 最小盈亏比
        "fibo_levels": [0.382, 0.5, 0.618, 0.705],
        "require_retest": False,  # 回测先关闭，方便看到更多信号
        "require_htf_filter": False,  # 关闭 HTF 过滤
        "enable_signal_score": False,
        "use_ob": True,
        "use_fvg": True,
        "use_swing": "auto",
        "structure": "both",
        "bias": "with_trend",
    }
    
    # 初始化回测引擎
    engine = BacktestEngine(
        initial_balance=10000.0,
        commission_rate=0.001,
        risk_per_trade=100.0,  # 每单最大亏损 100 USDT
    )
    
    # 创建策略实例
    strategy = SMCFiboFlexStrategy(
        symbol="ETHUSDT",
        timeframe="1h",
        config=strategy_config,
    )
    
    print(f"\n🎯 策略配置:")
    print(f"   预设: balanced")
    print(f"   最大亏损/单: {strategy_config['max_loss']} USDT")
    print(f"   最小盈亏比: {strategy_config['min_rr']}")
    print(f"   Fibo 水平: {strategy_config['fibo_levels']}")
    
    # 运行回测
    print(f"\n🚀 开始回测...")
    results = engine.run(candles, strategy)
    
    print(f"\n📈 回测结果:")
    print(f"   总交易次数: {results['total_trades']}")
    print(f"   盈利次数: {results['winning_trades']}")
    print(f"   亏损次数: {results['losing_trades']}")
    print(f"   胜率: {results['win_rate']:.1%}")
    print(f"   最终余额: {results['final_balance']:.2f} USDT")
    print(f"   总盈亏: {results['total_pnl']:.2f} USDT")
    print(f"   最大回撤: {results['max_drawdown']:.2f}%")
    
    if results.get("signals"):
        print(f"\n✅ 检测到 {len(results['signals'])} 个信号:")
        for i, sig in enumerate(results["signals"][:10], 1):
            print(f"   {i}. [{sig['timestamp']}] {sig['side']} @ {sig['entry_price']}")
            print(f"      SL: {sig.get('stop_loss', 'N/A')} | TP: {sig.get('take_profit', 'N/A')}")
            print(f"      置信度: {sig.get('confidence', 0)}% | 原因: {sig.get('reason', 'N/A')}")
    else:
        print(f"\n⚠️  未检测到任何信号")
        print(f"\n可能原因:")
        print(f"   1. 策略参数过于严格 (require_retest=False 已关闭)")
        print(f"   2. 最近的 ETHUSDT 行情没有明显的 SMC 结构")
        print(f"   3. bias='with_trend' 可能在震荡行情中错过反向信号")
        print(f"   4. Fibo 水平设置可能不适合当前市场")
    
    # 保存详细结果
    output_file = "/tmp/ethusdt_smc_backtest.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "candles_count": len(candles),
            "strategy_config": strategy_config,
            "results": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\n💾 详细结果已保存: {output_file}")

if __name__ == "__main__":
    run_backtest()
