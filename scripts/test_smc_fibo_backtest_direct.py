#!/usr/bin/env python3
"""
SMC 斐波那契策略回测脚本（直接调用，不依赖HTTP服务）

测试新实现的3个功能：
1. 斐波那契 Fallback 机制
2. 增强止损止盈配置
3. Pin Bar 比例调整

用法:
    PYTHONPATH=. python3 scripts/test_smc_fibo_backtest_direct.py
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy

# 测试配置
SYMBOL = "ETH/USDT"
TIMEFRAME = "15m"  # 小周期：15分钟K线
INITIAL_BALANCE = 10000.0
COMMISSION_RATE = 0.0004  # 0.04% (Binance费率)
RISK_PER_TRADE = 100.0   # 每单最大亏损100 USDT（以损定仓）

# SMC 斐波那契策略配置（与old1保持一致）
STRATEGY_CONFIG = {
    # 资金管理
    "max_loss": 100,              # 每单最大亏损
    "min_rr": 2.0,                # 最小盈亏比
    
    # 斐波那契参数（与old1一致）
    "fibo_levels": [0.5, 0.618, 0.705],  # ✅ 与old1一致
    "fibo_tolerance": 0.005,
    "fibo_fallback": True,        # ✅ 启用斐波那契 Fallback
    
    # SMC 参数
    "lookback": 50,
    "swing_left": 5,
    "swing_right": 3,
    "ob_min_body_ratio": 0.5,
    
    # 止损止盈配置（与old1一致）
    "sl_buffer_pct": 0.05,        # ✅ 修复：5%（与old1一致）
    "stop_source": "auto",        # ✅ auto/ob/swing
    "tp_mode": "swing",           # ✅ 修复：swing（与old1一致）
    
    # 多时间框架
    "htf_multiplier": 4,
    "htf_ema_fast": 20,
    "htf_ema_slow": 50,
    "require_htf_filter": True,
    
    # 回踩确认（与old1一致）
    "require_retest": True,
    "retest_bars": 20,
    "pinbar_ratio": 1.5,          # old1: pinbarRatio = 1.5
    "allow_engulf": True,
    "retest_ignore_stop_touch": False,

    # 结构 & 偏好（与old1一致）
    "structure": "both",          # bos + choch
    "bias": "with_trend",         # 顺势
}


def fetch_candles_from_exchange(symbol: str, timeframe: str, days: int = 365):
    """从交易所获取K线数据（按天数）"""
    print(f"📊 从交易所获取K线数据: {symbol} {timeframe} (最近{days}天)...")
    
    try:
        import ccxt
        exchange = ccxt.binance({"enableRateLimit": True})
        
        # 转换symbol格式
        ccxt_symbol = symbol.replace("/", "")
        
        # 计算起始时间（一年前）
        since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        # 根据时间框架估算需要的K线数量
        timeframe_to_hours = {
            "1m": 1/60, "5m": 5/60, "15m": 15/60, "30m": 30/60,
            "1h": 1, "4h": 4, "1d": 24
        }
        hours_per_candle = timeframe_to_hours.get(timeframe, 1)
        estimated_limit = int((days * 24) / hours_per_candle) + 100  # 加100作为缓冲
        
        print(f"   估算需要约 {estimated_limit} 根K线...")
        
        # 批量获取K线（每次最多1000根）
        all_ohlcv = []
        current_since = since
        batch_size = 1000
        max_retries = 3
        
        while len(all_ohlcv) < estimated_limit:
            retry_count = 0
            success = False
            while retry_count < max_retries and not success:
                try:
                    ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe, since=current_since, limit=batch_size)
                    if not ohlcv:
                        break
                    all_ohlcv.extend(ohlcv)
                    # 更新起始时间为最后一条K线的时间+1
                    current_since = ohlcv[-1][0] + 1
                    success = True
                    # 如果返回的K线少于batch_size，说明已经获取完所有数据
                    if len(ohlcv) < batch_size:
                        break
                    # 避免无限循环
                    if len(all_ohlcv) > estimated_limit * 2:
                        break
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"   重试 {retry_count}/{max_retries}...")
                        import time
                        time.sleep(1)
                    else:
                        print(f"   警告: 获取K线失败（已重试{max_retries}次）: {e}")
                        if len(all_ohlcv) > 0:
                            print(f"   已获取 {len(all_ohlcv)} 根K线，使用已有数据")
                            break
                        else:
                            raise
            if not success:
                break
        
        ohlcv = all_ohlcv
        
        if not ohlcv:
            raise ValueError("未获取到K线数据")
        
        # 转换为标准格式（内部使用 ISO 时间）
        candles = []
        for row in ohlcv:
            dt = datetime.fromtimestamp(row[0] / 1000)
            candles.append({
                "timestamp": dt.isoformat(),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            })
        
        print(f"✅ 获取到 {len(candles)} 根K线")
        print(f"   时间范围: {candles[0]['timestamp']} ~ {candles[-1]['timestamp']}")
        print(f"   价格范围: ${min(c['low'] for c in candles):,.2f} ~ ${max(c['high'] for c in candles):,.2f}")
        
        return candles
        
    except ImportError:
        print("❌ 需要安装 ccxt: pip install ccxt")
        raise
    except Exception as e:
        print(f"❌ 获取K线数据失败: {e}")
        raise


def print_results(result):
    """打印回测结果"""
    print("\n" + "=" * 60)
    print("📈 回测结果")
    print("=" * 60)
    
    # 基本信息
    print(f"\n策略: {result.strategy_code}")
    print(f"标的: {result.symbol} {result.timeframe}")
    print(f"时间范围: {result.start_time.isoformat()} ~ {result.end_time.isoformat()}")
    
    # 交易统计
    print(f"\n📊 交易统计:")
    print(f"  总交易次数: {result.total_trades}")
    print(f"  盈利交易: {result.winning_trades}")
    print(f"  亏损交易: {result.losing_trades}")
    print(f"  胜率: {result.win_rate:.2f}%")
    
    # 收益统计
    print(f"\n💰 收益统计:")
    print(f"  初始资金: ${result.initial_balance:,.2f}")
    print(f"  最终资金: ${result.final_balance:,.2f}")
    print(f"  总盈亏: ${result.total_pnl:,.2f}")
    print(f"  总收益率: {result.total_pnl_pct:.2f}%")
    print(f"  平均每笔: ${result.avg_pnl:,.2f}")
    print(f"  平均盈利: ${result.avg_win:,.2f}")
    print(f"  平均亏损: ${result.avg_loss:,.2f}")
    
    # 风险统计
    print(f"\n⚠️  风险统计:")
    print(f"  最大回撤: ${result.max_drawdown:,.2f}")
    print(f"  最大回撤率: {result.max_drawdown_pct:.2f}%")
    
    # 盈亏比（如果存在）
    if hasattr(result, 'avg_risk_reward_ratio') and result.avg_risk_reward_ratio > 0:
        print(f"  平均盈亏比: {result.avg_risk_reward_ratio:.2f}")
    
    # 交易详情（前5笔）
    if result.trades:
        print(f"\n📋 交易详情（前5笔）:")
        for i, trade in enumerate(result.trades[:5], 1):
            print(f"  {i}. {trade.side} {trade.symbol} @ ${trade.entry_price:,.2f}")
            print(f"     入场: {trade.entry_time.isoformat()}")
            if trade.exit_time:
                print(f"     出场: {trade.exit_time.isoformat()} @ ${trade.exit_price:,.2f}")
                print(f"     盈亏: ${trade.pnl:,.2f} ({trade.pnl_pct:+.2f}%)")
                print(f"     原因: {trade.exit_reason}")
            else:
                print(f"     状态: 持仓中")
            print()
    
    print("=" * 60)


def _dump_candles_json(candles, path: str):
    """导出 candles.json（timestamp 使用秒级 int，供 compare 脚本使用）"""
    import json
    dump = []
    for c in candles:
        ts = c.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = int(datetime.fromisoformat(ts).timestamp())
            except Exception:
                ts = None
        dump.append({
            "timestamp": ts,
            "open": c.get("open"),
            "high": c.get("high"),
            "low": c.get("low"),
            "close": c.get("close"),
            "volume": c.get("volume"),
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dump, f, ensure_ascii=False)


def main():
    """主函数"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump-candles", default="", help="导出 candles.json 到指定路径")
    parser.add_argument("--days", type=int, default=365, help="拉取多少天的数据")
    args = parser.parse_args()
    print("=" * 60)
    print("SMC 斐波那契策略回测（直接调用）")
    print("=" * 60)
    print(f"\n测试配置:")
    print(f"  标的: {SYMBOL}")
    print(f"  周期: {TIMEFRAME}")
    print(f"  初始资金: ${INITIAL_BALANCE:,.2f}")
    print(f"  每单风险: ${RISK_PER_TRADE:,.2f} (以损定仓)")
    print(f"  手续费率: {COMMISSION_RATE*100:.3f}%")
    print(f"\n策略配置:")
    print(f"  ✅ 斐波那契 Fallback: {STRATEGY_CONFIG.get('fibo_fallback')}")
    print(f"  ✅ 止损来源: {STRATEGY_CONFIG.get('stop_source')}")
    print(f"  ✅ 止盈模式: {STRATEGY_CONFIG.get('tp_mode')}")
    print(f"  ✅ Pin Bar 比例: {STRATEGY_CONFIG.get('pinbar_ratio')}")
    
    # 1. 获取K线数据（默认一年）
    try:
        candles = fetch_candles_from_exchange(SYMBOL, TIMEFRAME, days=args.days)
    except Exception as e:
        print(f"\n❌ 获取数据失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    if args.dump_candles:
        _dump_candles_json(candles, args.dump_candles)
        print(f"✅ 已导出 candles.json: {args.dump_candles}")
    
    # 2. 加载策略
    try:
        print(f"\n🔧 加载策略: smc_fibo")
        strategy = get_strategy("smc_fibo", STRATEGY_CONFIG)
        print(f"✅ 策略加载成功: {strategy.name}")
    except Exception as e:
        print(f"\n❌ 策略加载失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 3. 创建回测引擎
    print(f"\n🚀 开始回测...")
    engine = BacktestEngine(
        initial_balance=INITIAL_BALANCE,
        commission_rate=COMMISSION_RATE,
        risk_per_trade=RISK_PER_TRADE,
        amount_usdt=0.0,  # 使用以损定仓模式
        min_rr=STRATEGY_CONFIG.get("min_rr", 0),
    )
    
    # 4. 运行回测
    try:
        result = engine.run(
            strategy=strategy,
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=candles,
            lookback=50,
        )
    except Exception as e:
        print(f"\n❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 5. 打印结果
    print_results(result)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
