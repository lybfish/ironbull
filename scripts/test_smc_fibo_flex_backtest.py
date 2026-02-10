#!/usr/bin/env python3
"""
SMC Fibo Flex 策略回测脚本（纯本地，不依赖HTTP服务）

用法:
    # 使用模拟数据快速测试
    PYTHONPATH=. python3 scripts/test_smc_fibo_flex_backtest.py

    # 使用真实K线数据文件
    PYTHONPATH=. python3 scripts/test_smc_fibo_flex_backtest.py --candles /path/to/candles.json --symbol BTCUSDT --timeframe 15m

    # 使用预设配置
    PYTHONPATH=. python3 scripts/test_smc_fibo_flex_backtest.py --preset conservative
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta
import math
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy


# ============================================================================
# 配置区域（可根据需要修改）
# ============================================================================

# 默认回测参数
DEFAULT_INITIAL_BALANCE = 10000.0
DEFAULT_COMMISSION_RATE = 0.001  # 0.1%
DEFAULT_RISK_PER_TRADE = 100.0  # 每单最大亏损（0 = 固定仓位）

# 默认策略配置（balanced 预设）
DEFAULT_STRATEGY_CONFIG = {
    "preset_profile": "balanced",
    "max_loss": 100,
    "min_rr": 1.8,
    "fibo_levels": [0.382, 0.5, 0.618, 0.705],
    "require_retest": False,  # 回测时先关闭，方便看到更多信号
    "require_htf_filter": False,  # 回测时先关闭，减少过滤
    "enable_signal_score": False,  # 回测时先关闭，减少过滤
}


# ============================================================================
# 数据生成/加载
# ============================================================================

def generate_mock_candles(count: int = 2000, base_price: float = 50000.0, seed: int = 42):
    """生成模拟K线数据（带趋势和波动，便于产生swing points）"""
    random.seed(seed)
    candles = []
    current_time = datetime.now() - timedelta(minutes=15 * count)
    
    for i in range(count):
        # 叠加趋势 + 正弦波 + 随机噪声
        trend = i * 1.5
        wave = math.sin(i / 30.0) * 400
        noise = random.uniform(-80, 80)
        
        base = base_price + trend + wave + noise
        
        open_price = base + random.uniform(-40, 40)
        close_price = base + random.uniform(-40, 40)
        high_price = max(open_price, close_price) + random.uniform(30, 150)
        low_price = min(open_price, close_price) - random.uniform(30, 150)
        
        candles.append({
            "timestamp": current_time.isoformat(),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": round(1000.0 + random.uniform(-200, 200), 2),
        })
        
        current_time += timedelta(minutes=15)
    
    return candles


def load_candles_from_file(file_path: str):
    """从JSON文件加载K线数据"""
    print(f"📂 从文件加载K线数据: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 支持两种格式：
        # 1. 直接是数组: [{"timestamp": ..., "open": ..., ...}, ...]
        # 2. 包装对象: {"candles": [...], ...}
        if isinstance(data, list):
            candles = data
        elif isinstance(data, dict) and "candles" in data:
            candles = data["candles"]
        else:
            raise ValueError("JSON格式不支持，期望数组或包含'candles'字段的对象")
        
        if not candles:
            raise ValueError("K线数据为空")
        
        # 验证必需字段并转换时间戳格式
        required_fields = ["timestamp", "open", "high", "low", "close"]
        for i, candle in enumerate(candles):
            # 验证字段
            for field in required_fields:
                if field not in candle:
                    if i < 5:  # 只对前5根报错
                        raise ValueError(f"第{i+1}根K线缺少字段: {field}")
            
            # 转换时间戳：如果是数字（Unix时间戳），转为ISO格式
            ts = candle.get("timestamp")
            if isinstance(ts, (int, float)):
                # 判断是秒还是毫秒时间戳
                if ts > 1e10:  # 毫秒时间戳
                    ts = ts / 1000
                dt = datetime.fromtimestamp(ts)
                candle["timestamp"] = dt.isoformat()
            elif isinstance(ts, str):
                # 已经是字符串格式，保持不变
                pass
            else:
                if i < 5:  # 只对前5根报错
                    raise ValueError(f"第{i+1}根K线时间戳格式不支持: {type(ts)}")
        
        print(f"✅ 加载成功: {len(candles)} 根K线")
        print(f"   时间范围: {candles[0].get('timestamp', 'N/A')} ~ {candles[-1].get('timestamp', 'N/A')}")
        print(f"   价格范围: {min(c.get('low', 0) for c in candles):.2f} ~ {max(c.get('high', 0) for c in candles):.2f}")
        
        return candles
        
    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        raise
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        raise


# ============================================================================
# 回测执行
# ============================================================================

def run_backtest(
    strategy_config: dict,
    candles: list,
    symbol: str,
    timeframe: str,
    initial_balance: float,
    commission_rate: float,
    risk_per_trade: float,
    lookback: int = 50,
):
    """运行回测"""
    print("\n" + "=" * 60)
    print("🚀 开始回测")
    print("=" * 60)
    
    # 1. 加载策略
    print(f"\n1️⃣  加载策略: smc_fibo_flex")
    try:
        strategy = get_strategy("smc_fibo_flex", strategy_config)
        print(f"✅ 策略加载成功: {strategy.name}")
        print(f"   版本: {strategy.version}")
    except Exception as e:
        print(f"❌ 策略加载失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 2. 创建回测引擎
    print(f"\n2️⃣  创建回测引擎")
    engine = BacktestEngine(
        initial_balance=initial_balance,
        commission_rate=commission_rate,
        risk_per_trade=risk_per_trade if risk_per_trade > 0 else None,
    )
    print(f"✅ 引擎创建成功")
    print(f"   初始资金: {initial_balance:,.2f} USDT")
    print(f"   手续费率: {commission_rate * 100:.3f}%")
    if risk_per_trade > 0:
        print(f"   每单风险: {risk_per_trade:,.2f} USDT (以损定仓)")
    else:
        print(f"   仓位模式: 固定仓位")
    
    # 3. 运行回测
    print(f"\n3️⃣  运行回测...")
    print(f"   标的: {symbol} {timeframe}")
    print(f"   K线数量: {len(candles)}")
    print(f"   Lookback: {lookback}")
    
    try:
        result = engine.run(
            strategy=strategy,
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            lookback=lookback,
        )
        print(f"✅ 回测完成")
        return result
    except Exception as e:
        print(f"❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# 结果展示
# ============================================================================

def print_results(result):
    """打印回测结果"""
    if not result:
        return
    
    print("\n" + "=" * 60)
    print("📊 回测结果")
    print("=" * 60)
    
    # 基本信息
    print(f"\n策略: {result.strategy_code}")
    print(f"交易对: {result.symbol}")
    print(f"周期: {result.timeframe}")
    print(f"时间范围: {result.start_time} ~ {result.end_time}")
    
    # 交易统计
    print(f"\n📈 交易统计")
    print(f"  总交易次数: {result.total_trades}")
    print(f"  盈利次数: {result.winning_trades}")
    print(f"  亏损次数: {result.losing_trades}")
    print(f"  胜率: {result.win_rate:.2f}%")
    
    if result.total_trades > 0 and hasattr(result, 'avg_holding_time') and result.avg_holding_time:
        print(f"  平均持仓时间: {result.avg_holding_time:.1f} 根K线")
    
    # 收益统计
    print(f"\n💰 收益统计")
    print(f"  初始资金: {result.initial_balance:,.2f} USDT")
    print(f"  最终资金: {result.final_balance:,.2f} USDT")
    print(f"  最高资金: {result.peak_balance:,.2f} USDT")
    print(f"  总盈亏: {result.total_pnl:,.2f} USDT")
    print(f"  总收益率: {result.total_pnl_pct:.2f}%")
    
    if result.total_trades > 0:
        print(f"  平均盈亏: {result.avg_pnl:,.2f} USDT")
        print(f"  平均盈利: {result.avg_win:,.2f} USDT")
        print(f"  平均亏损: {result.avg_loss:,.2f} USDT")
    
    # 风险统计
    print(f"\n⚠️  风险统计")
    print(f"  最大回撤: {result.max_drawdown:,.2f} USDT")
    print(f"  最大回撤率: {result.max_drawdown_pct:.2f}%")
    
    # 盈亏比
    if hasattr(result, 'avg_risk_reward_ratio') and result.avg_risk_reward_ratio:
        print(f"  平均盈亏比: {result.avg_risk_reward_ratio:.2f}")
    
    # 交易记录
    if result.trades:
        print(f"\n📝 交易记录（前10笔）")
        for i, trade in enumerate(result.trades[:10], 1):
            pnl_str = f"{trade.pnl:,.2f}" if trade.pnl is not None else "N/A"
            pnl_pct_str = f"({trade.pnl_pct:.2f}%)" if hasattr(trade, 'pnl_pct') and trade.pnl_pct else ""
            exit_price_str = f"{trade.exit_price:.2f}" if trade.exit_price else "N/A"
            
            # 处理 trade_id（可能是字符串或整数）
            trade_id_str = str(trade.trade_id)
            if len(trade_id_str) > 8:
                trade_id_str = trade_id_str[:8] + "..."
            
            print(f"  [{i}] {trade_id_str} | {trade.side} @ {trade.entry_price:.2f} "
                  f"→ {exit_price_str} | PnL: {pnl_str} {pnl_pct_str} | {trade.exit_reason}")
        
        if len(result.trades) > 10:
            print(f"  ... 还有 {len(result.trades) - 10} 笔交易")
    else:
        print(f"\n📝 无交易记录")
    
    print("\n" + "=" * 60)


# ============================================================================
# 主函数
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="SMC Fibo Flex 策略回测脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用模拟数据快速测试
  %(prog)s

  # 使用真实K线数据文件
  %(prog)s --candles /tmp/btcusdt_15m.json --symbol BTCUSDT --timeframe 15m

  # 使用预设配置
  %(prog)s --preset conservative --candles /tmp/eurusd_1h.json --symbol EURUSD --timeframe 1h
        """
    )
    
    parser.add_argument(
        "--candles",
        type=str,
        help="K线数据JSON文件路径（可选，不提供则使用模拟数据）"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="BTCUSDT",
        help="交易对符号（默认: BTCUSDT）"
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="15m",
        help="时间周期（默认: 15m）"
    )
    parser.add_argument(
        "--preset",
        type=str,
        choices=["conservative", "balanced", "aggressive", "forex_specific"],
        help="使用预设配置（会覆盖默认配置）"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="策略配置JSON文件路径（可选，会覆盖预设）"
    )
    parser.add_argument(
        "--initial-balance",
        type=float,
        default=DEFAULT_INITIAL_BALANCE,
        help=f"初始资金（默认: {DEFAULT_INITIAL_BALANCE:,.2f}）"
    )
    parser.add_argument(
        "--commission-rate",
        type=float,
        default=DEFAULT_COMMISSION_RATE,
        help=f"手续费率（默认: {DEFAULT_COMMISSION_RATE*100:.3f}%%）"
    )
    parser.add_argument(
        "--risk-per-trade",
        type=float,
        default=DEFAULT_RISK_PER_TRADE,
        help=f"每单最大亏损（默认: {DEFAULT_RISK_PER_TRADE:,.2f}，0=固定仓位）"
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=50,
        help="Lookback周期（默认: 50）"
    )
    parser.add_argument(
        "--mock-count",
        type=int,
        default=2000,
        help="模拟数据K线数量（默认: 2000，仅在未提供--candles时使用）"
    )
    
    args = parser.parse_args()
    
    # 打印标题
    print("=" * 60)
    print("SMC Fibo Flex 策略回测")
    print("=" * 60)
    
    # 1. 加载/生成K线数据
    print(f"\n📊 准备K线数据")
    if args.candles:
        try:
            candles = load_candles_from_file(args.candles)
        except Exception as e:
            print(f"❌ 加载K线数据失败: {e}")
            return 1
    else:
        print(f"📊 生成模拟K线数据（{args.mock_count}根）...")
        candles = generate_mock_candles(count=args.mock_count)
        print(f"✅ 生成完成")
    
    # 2. 加载策略配置
    print(f"\n⚙️  加载策略配置")
    strategy_config = DEFAULT_STRATEGY_CONFIG.copy()
    
    # 如果指定了预设，加载预设配置
    if args.preset:
        preset_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "libs",
            "strategies",
            "smc_fibo_flex",
            "examples",
            f"{args.preset}.json"
        )
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                preset_data = json.load(f)
                if "strategy_config" in preset_data:
                    strategy_config.update(preset_data["strategy_config"])
                if "preset_profile" in preset_data:
                    strategy_config["preset_profile"] = preset_data["preset_profile"]
            print(f"✅ 加载预设: {args.preset}")
        except Exception as e:
            print(f"⚠️  加载预设失败: {e}，使用默认配置")
    
    # 如果指定了配置文件，加载并覆盖
    if args.config:
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                custom_config = json.load(f)
                if "strategy_config" in custom_config:
                    strategy_config.update(custom_config["strategy_config"])
                else:
                    strategy_config.update(custom_config)
            print(f"✅ 加载自定义配置: {args.config}")
        except Exception as e:
            print(f"⚠️  加载自定义配置失败: {e}，使用现有配置")
    
    print(f"   配置预览: preset={strategy_config.get('preset_profile', 'N/A')}, "
          f"min_rr={strategy_config.get('min_rr', 'N/A')}, "
          f"require_retest={strategy_config.get('require_retest', 'N/A')}")
    
    # 3. 运行回测
    result = run_backtest(
        strategy_config=strategy_config,
        candles=candles,
        symbol=args.symbol,
        timeframe=args.timeframe,
        initial_balance=args.initial_balance,
        commission_rate=args.commission_rate,
        risk_per_trade=args.risk_per_trade,
        lookback=args.lookback,
    )
    
    # 4. 打印结果
    if result:
        print_results(result)
        return 0
    else:
        print("\n❌ 回测失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
