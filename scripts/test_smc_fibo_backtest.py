#!/usr/bin/env python3
"""
SMC 斐波那契策略回测脚本

测试新实现的3个功能：
1. 斐波那契 Fallback 机制
2. 增强止损止盈配置
3. Pin Bar 比例调整

用法:
    PYTHONPATH=. python3 scripts/test_smc_fibo_backtest.py
"""

import sys
import os
import json
import requests
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 配置
BACKTEST_URL = "http://127.0.0.1:8030"
DATA_PROVIDER_URL = "http://127.0.0.1:8005"  # 注意：data-provider 在 8005 端口

# 测试配置
SYMBOL = "ETHUSDT"
TIMEFRAME = "1h"
LIMIT = 1000  # 获取1000根K线
INITIAL_BALANCE = 10000.0
COMMISSION_RATE = 0.0004  # 0.04% (Binance费率)
RISK_PER_TRADE = 100.0   # 每单最大亏损100 USDT（以损定仓）

# SMC 斐波那契策略配置
STRATEGY_CONFIG = {
    # 资金管理
    "max_loss": 100,              # 每单最大亏损
    "min_rr": 2.0,                # 最小盈亏比
    
    # 斐波那契参数
    "fibo_levels": [0.382, 0.5, 0.618],
    "fibo_tolerance": 0.005,
    "fibo_fallback": True,        # ✅ 启用斐波那契 Fallback
    
    # SMC 参数
    "lookback": 50,
    "swing_left": 5,
    "swing_right": 3,
    "ob_min_body_ratio": 0.5,
    
    # 止损止盈配置
    "sl_buffer_pct": 0.002,
    "stop_source": "auto",        # ✅ auto/ob/swing
    "tp_mode": "fibo",            # ✅ fibo/swing/rr
    
    # 多时间框架
    "htf_multiplier": 4,
    "htf_ema_fast": 20,
    "htf_ema_slow": 50,
    "require_htf_filter": True,
    
    # 回踩确认
    "require_retest": True,
    "retest_bars": 20,
    "pinbar_ratio": 2.0,          # ✅ 已调整为2.0（与old1一致）
    "allow_engulf": True,
    "retest_ignore_stop_touch": False,
}


def check_services():
    """检查服务是否运行"""
    print("🔍 检查服务状态...")
    
    try:
        resp = requests.get(f"{BACKTEST_URL}/health", timeout=5)
        if resp.status_code == 200:
            print("✅ Backtest Service: 运行中")
        else:
            print("❌ Backtest Service: 未运行")
            return False
    except Exception as e:
        print(f"❌ Backtest Service: 连接失败 - {e}")
        return False
    
    try:
        resp = requests.get(f"{DATA_PROVIDER_URL}/health", timeout=5)
        if resp.status_code == 200:
            print("✅ Data Provider: 运行中")
        else:
            print("❌ Data Provider: 未运行")
            return False
    except Exception as e:
        print(f"❌ Data Provider: 连接失败 - {e}")
        return False
    
    return True


def fetch_candles(symbol: str, timeframe: str, limit: int):
    """获取历史K线数据"""
    print(f"\n📊 获取历史数据: {symbol} {timeframe} (最近{limit}根)...")
    
    try:
        resp = requests.get(
            f"{DATA_PROVIDER_URL}/api/candles",
            params={
                "symbol": symbol,
                "timeframe": timeframe,
                "limit": limit,
                "source": "live",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        candles = data.get("candles", [])
        
        if not candles:
            raise ValueError("未获取到K线数据")
        
        # 转换时间戳格式（从毫秒转为ISO格式）
        formatted_candles = []
        for c in candles:
            ts = c.get("timestamp")
            if isinstance(ts, (int, float)):
                # 如果是毫秒时间戳，转为秒
                if ts > 1e10:
                    ts = ts / 1000
                dt = datetime.fromtimestamp(ts)
            else:
                dt = datetime.now()
            
            formatted_candles.append({
                "timestamp": dt.isoformat(),
                "open": float(c.get("open", 0)),
                "high": float(c.get("high", 0)),
                "low": float(c.get("low", 0)),
                "close": float(c.get("close", 0)),
                "volume": float(c.get("volume", 0)),
            })
        
        print(f"✅ 获取到 {len(formatted_candles)} 根K线")
        print(f"   时间范围: {formatted_candles[0]['timestamp']} ~ {formatted_candles[-1]['timestamp']}")
        
        return formatted_candles
        
    except Exception as e:
        print(f"❌ 获取K线数据失败: {e}")
        raise


def run_backtest(candles: list, strategy_config: dict):
    """运行回测"""
    print(f"\n🚀 开始回测: SMC 斐波那契策略")
    print(f"   策略配置: fibo_fallback={strategy_config.get('fibo_fallback')}, "
          f"stop_source={strategy_config.get('stop_source')}, "
          f"tp_mode={strategy_config.get('tp_mode')}, "
          f"pinbar_ratio={strategy_config.get('pinbar_ratio')}")
    
    payload = {
        "strategy_code": "smc_fibo",
        "strategy_config": strategy_config,
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "candles": candles,
        "initial_balance": INITIAL_BALANCE,
        "commission_rate": COMMISSION_RATE,
        "risk_per_trade": RISK_PER_TRADE,
        "lookback": 50,
    }
    
    try:
        resp = requests.post(
            f"{BACKTEST_URL}/api/backtest/run",
            json=payload,
            timeout=300,  # 5分钟超时
        )
        resp.raise_for_status()
        result = resp.json()
        
        if not result.get("success"):
            error = result.get("error", "未知错误")
            print(f"❌ 回测失败: {error}")
            return None
        
        return result.get("result")
        
    except Exception as e:
        print(f"❌ 回测请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                print(f"   响应内容: {e.response.text[:500]}")
        raise


def print_results(result: dict):
    """打印回测结果"""
    if not result:
        return
    
    print("\n" + "=" * 60)
    print("📈 回测结果")
    print("=" * 60)
    
    # 基本信息
    print(f"\n策略: {result.get('strategy_code', 'N/A')}")
    print(f"标的: {result.get('symbol', 'N/A')} {result.get('timeframe', 'N/A')}")
    print(f"时间范围: {result.get('start_time', 'N/A')} ~ {result.get('end_time', 'N/A')}")
    
    # 交易统计
    print(f"\n📊 交易统计:")
    print(f"  总交易次数: {result.get('total_trades', 0)}")
    print(f"  盈利交易: {result.get('winning_trades', 0)}")
    print(f"  亏损交易: {result.get('losing_trades', 0)}")
    print(f"  胜率: {result.get('win_rate', 0):.2f}%")
    
    # 收益统计
    print(f"\n💰 收益统计:")
    print(f"  初始资金: ${result.get('initial_balance', 0):,.2f}")
    print(f"  最终资金: ${result.get('final_balance', 0):,.2f}")
    print(f"  总盈亏: ${result.get('total_pnl', 0):,.2f}")
    print(f"  总收益率: {result.get('total_pnl_pct', 0):.2f}%")
    print(f"  平均每笔: ${result.get('avg_pnl', 0):,.2f}")
    print(f"  平均盈利: ${result.get('avg_win', 0):,.2f}")
    print(f"  平均亏损: ${result.get('avg_loss', 0):,.2f}")
    
    # 风险统计
    print(f"\n⚠️  风险统计:")
    print(f"  最大回撤: ${result.get('max_drawdown', 0):,.2f}")
    print(f"  最大回撤率: {result.get('max_drawdown_pct', 0):.2f}%")
    
    # 盈亏比
    avg_rr = result.get('avg_risk_reward_ratio', 0)
    if avg_rr > 0:
        print(f"  平均盈亏比: {avg_rr:.2f}")
    
    print("\n" + "=" * 60)


def main():
    """主函数"""
    print("=" * 60)
    print("SMC 斐波那契策略回测")
    print("=" * 60)
    print(f"\n测试配置:")
    print(f"  标的: {SYMBOL}")
    print(f"  周期: {TIMEFRAME}")
    print(f"  初始资金: ${INITIAL_BALANCE:,.2f}")
    print(f"  每单风险: ${RISK_PER_TRADE:,.2f} (以损定仓)")
    print(f"  手续费率: {COMMISSION_RATE*100:.3f}%")
    
    # 1. 检查服务
    if not check_services():
        print("\n❌ 服务未运行，请先启动:")
        print("   Data Provider: PYTHONPATH=. python3 -m uvicorn services.data-provider.app.main:app --host 0.0.0.0 --port 8005")
        print("   Backtest: PYTHONPATH=. python3 services/backtest/app/main.py")
        return 1
    
    # 2. 获取K线数据
    try:
        candles = fetch_candles(SYMBOL, TIMEFRAME, LIMIT)
    except Exception as e:
        print(f"\n❌ 获取数据失败: {e}")
        return 1
    
    # 3. 运行回测
    try:
        result = run_backtest(candles, STRATEGY_CONFIG)
    except Exception as e:
        print(f"\n❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 4. 打印结果
    if result:
        print_results(result)
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
