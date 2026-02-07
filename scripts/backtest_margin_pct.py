#!/usr/bin/env python3
"""
逐仓保证金百分比策略回测

模型参数:
- 最大持仓: 1000 USDT
- 保证金: 1000 × 1% = 10 USDT
- 杠杆: 20X
- 仓位名义价值: 10 × 20 = 200 USDT
- 止盈: 保证金的 45% = 4.5 USDT (价格波动 2.25%)
- 止损: 保证金的 70% = 7.0 USDT (价格波动 3.50%)
- 投入本金: 2000 USDT
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import ccxt
from services.backtest.app.backtest_engine import BacktestEngine
from libs.strategies import get_strategy


def fetch_candles(symbol="ETH/USDT", timeframe="1h", limit=1000):
    """从 Binance 获取真实 K 线数据"""
    print(f"从 Binance 获取 {symbol} {timeframe} K线数据 (最多 {limit} 根)...")
    exchange = ccxt.binance({"enableRateLimit": True})
    
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    
    candles = []
    for row in ohlcv:
        candles.append({
            "timestamp": datetime.fromtimestamp(row[0] / 1000).isoformat(),
            "open": row[1],
            "high": row[2],
            "low": row[3],
            "close": row[4],
            "volume": row[5],
        })
    
    return candles


def run_backtest(candles, symbol, timeframe, config_label, strategy_config, engine_kwargs):
    """运行单次回测并返回结果"""
    strategy = get_strategy("market_regime", strategy_config)
    engine = BacktestEngine(**engine_kwargs)
    
    result = engine.run(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        candles=candles,
        lookback=100,  # market_regime 需要至少 60 根
    )
    
    return result


def print_result(label, result):
    """格式化输出回测结果"""
    print(f"\n{'=' * 70}")
    print(f"  {label}")
    print(f"{'=' * 70}")
    print(f"  交易对: {result.symbol}  |  周期: {result.timeframe}")
    print(f"  时间: {result.start_time.strftime('%Y-%m-%d %H:%M')} ~ {result.end_time.strftime('%Y-%m-%d %H:%M')}")
    print()
    
    print(f"  📊 交易统计")
    print(f"     总交易: {result.total_trades} 笔")
    print(f"     盈利: {result.winning_trades} 笔  |  亏损: {result.losing_trades} 笔")
    print(f"     胜率: {result.win_rate:.1f}%")
    print(f"     多头: {result.long_trades} 笔 (PnL {result.long_pnl:.2f})")
    print(f"     空头: {result.short_trades} 笔 (PnL {result.short_pnl:.2f})")
    print()
    
    print(f"  💰 收益统计")
    print(f"     总盈亏: {result.total_pnl:+.2f} USDT ({result.total_pnl_pct:+.2f}%)")
    print(f"     平均每笔: {result.avg_pnl:+.2f} USDT")
    print(f"     平均盈利: {result.avg_win:+.2f} USDT")
    print(f"     平均亏损: {result.avg_loss:+.2f} USDT")
    print()
    
    print(f"  📈 风险指标")
    print(f"     盈亏比: {result.risk_reward_ratio:.2f}")
    print(f"     盈利因子: {result.profit_factor:.2f}")
    print(f"     期望值: {result.expectancy:+.2f} USDT/笔")
    print(f"     最大回撤: {result.max_drawdown:.2f} USDT ({result.max_drawdown_pct:.2f}%)")
    print()
    
    print(f"  💼 账户")
    print(f"     初始资金: {result.initial_balance:.0f} USDT")
    print(f"     最终资金: {result.final_balance:.2f} USDT")
    print(f"     最高资金: {result.peak_balance:.2f} USDT")
    
    # 显示前10笔交易
    if result.trades:
        print(f"\n  📝 交易记录 (前10笔 / 共{len(result.trades)}笔)")
        print(f"     {'#':>3}  {'方向':>4}  {'入场价':>10}  {'出场价':>10}  {'PnL':>10}  {'原因':>12}")
        print(f"     {'---':>3}  {'----':>4}  {'--------':>10}  {'--------':>10}  {'--------':>10}  {'----------':>12}")
        for t in result.trades[:10]:
            side_str = "多" if t.side == "BUY" else "空"
            pnl_str = f"{t.pnl:+.2f}" if t.pnl else "N/A"
            exit_str = f"{t.exit_price:.2f}" if t.exit_price else "N/A"
            print(f"     {t.trade_id:>3}  {side_str:>4}  {t.entry_price:>10.2f}  {exit_str:>10}  {pnl_str:>10}  {t.exit_reason or 'N/A':>12}")
        if len(result.trades) > 10:
            print(f"     ... 还有 {len(result.trades) - 10} 笔")
    
    # 止盈/止损统计
    if result.trades:
        tp_count = sum(1 for t in result.trades if t.exit_reason == "TAKE_PROFIT")
        sl_count = sum(1 for t in result.trades if t.exit_reason == "STOP_LOSS")
        sig_count = sum(1 for t in result.trades if t.exit_reason == "SIGNAL")
        end_count = sum(1 for t in result.trades if t.exit_reason == "END")
        print(f"\n  🎯 出场原因分布")
        print(f"     止盈: {tp_count} 笔  |  止损: {sl_count} 笔  |  信号平仓: {sig_count} 笔  |  到期: {end_count} 笔")


def main():
    # =============================================
    # 参数设定
    # =============================================
    SYMBOL = "ETH/USDT"
    TIMEFRAME = "1h"
    CANDLE_LIMIT = 1000      # 约 41 天的 1h 数据
    
    MAX_POSITION = 1000      # 最大持仓 1000 USDT
    RISK_PCT = 0.01          # 1% 保证金比例
    LEVERAGE = 20             # 20X 杠杆
    TP_PCT = 0.45             # 保证金的 45% 止盈
    SL_PCT = 0.70             # 保证金的 70% 止损
    
    MARGIN = MAX_POSITION * RISK_PCT        # = 10 USDT
    POSITION_VALUE = MARGIN * LEVERAGE      # = 200 USDT
    INITIAL_BALANCE = 2000                  # 投入本金
    
    print("=" * 70)
    print("  逐仓保证金百分比策略回测")
    print("=" * 70)
    print()
    print(f"  模型参数:")
    print(f"    最大持仓: {MAX_POSITION} USDT")
    print(f"    保证金: {MAX_POSITION} × {RISK_PCT:.0%} = {MARGIN} USDT")
    print(f"    杠杆: {LEVERAGE}X")
    print(f"    仓位名义: {MARGIN} × {LEVERAGE} = {POSITION_VALUE} USDT")
    print(f"    止盈: 保证金 × {TP_PCT:.0%} = {MARGIN * TP_PCT:.1f} USDT (价格波动 {TP_PCT/LEVERAGE:.2%})")
    print(f"    止损: 保证金 × {SL_PCT:.0%} = {MARGIN * SL_PCT:.1f} USDT (价格波动 {SL_PCT/LEVERAGE:.2%})")
    print(f"    风险回报比: {MARGIN * TP_PCT:.1f} : {MARGIN * SL_PCT:.1f} = 1 : {SL_PCT/TP_PCT:.2f}")
    print(f"    盈亏平衡胜率: {SL_PCT/(TP_PCT+SL_PCT):.1%}")
    print(f"    投入本金: {INITIAL_BALANCE} USDT")
    print()
    
    # 获取数据
    candles = fetch_candles(SYMBOL, TIMEFRAME, CANDLE_LIMIT)
    print(f"  获取到 {len(candles)} 根 K 线")
    print(f"  时间: {candles[0]['timestamp']} ~ {candles[-1]['timestamp']}")
    print(f"  价格: {candles[0]['close']:.2f} ~ {candles[-1]['close']:.2f}")
    
    # =============================================
    # 回测 1: 新模型（逐仓保证金百分比）
    # =============================================
    result_new = run_backtest(
        candles=candles,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        config_label="逐仓保证金百分比",
        strategy_config={
            "sl_tp_mode": "margin_pct",
            "leverage": LEVERAGE,
            "tp_pct": TP_PCT,
            "sl_pct": SL_PCT,
            "max_position": MAX_POSITION,
            "risk_pct": RISK_PCT,
        },
        engine_kwargs={
            "initial_balance": INITIAL_BALANCE,
            "commission_rate": 0.0005,  # 0.05% taker 手续费
            "amount_usdt": POSITION_VALUE,
            "leverage": LEVERAGE,
            "margin_mode": "isolated",
        },
    )
    print_result(f"方案 A: 逐仓保证金百分比 (TP {TP_PCT:.0%} / SL {SL_PCT:.0%})", result_new)
    
    # =============================================
    # 回测 2: 原模型（ATR 倍数）作为对比
    # =============================================
    result_old = run_backtest(
        candles=candles,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        config_label="ATR 倍数 (原)",
        strategy_config={
            "sl_tp_mode": "atr",
            "atr_mult_sl": 1.2,
            "atr_mult_tp": 4.5,
        },
        engine_kwargs={
            "initial_balance": INITIAL_BALANCE,
            "commission_rate": 0.0005,
            "amount_usdt": POSITION_VALUE,
            "leverage": LEVERAGE,
            "margin_mode": "isolated",
        },
    )
    print_result("方案 B: ATR 倍数 (SL 1.2x / TP 4.5x) - 对比", result_old)
    
    # =============================================
    # 回测 3: 调整参数 — 更保守的 TP
    # =============================================
    result_c = run_backtest(
        candles=candles,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        config_label="保守方案",
        strategy_config={
            "sl_tp_mode": "margin_pct",
            "leverage": LEVERAGE,
            "tp_pct": 0.30,    # 30% 止盈（更容易达到）
            "sl_pct": 0.50,    # 50% 止损（更窄）
            "max_position": MAX_POSITION,
            "risk_pct": RISK_PCT,
        },
        engine_kwargs={
            "initial_balance": INITIAL_BALANCE,
            "commission_rate": 0.0005,
            "amount_usdt": POSITION_VALUE,
            "leverage": LEVERAGE,
            "margin_mode": "isolated",
        },
    )
    print_result("方案 C: 保守参数 (TP 30% / SL 50%)", result_c)
    
    # =============================================
    # 对比总结
    # =============================================
    print(f"\n{'=' * 70}")
    print(f"  📊 三方案对比总结")
    print(f"{'=' * 70}")
    print(f"  {'':>20}  {'方案A':>12}  {'方案B(ATR)':>12}  {'方案C(保守)':>12}")
    print(f"  {'TP/SL模式':>20}  {'45%/70%':>12}  {'ATR 1.2/4.5':>12}  {'30%/50%':>12}")
    print(f"  {'总交易':>20}  {result_new.total_trades:>12}  {result_old.total_trades:>12}  {result_c.total_trades:>12}")
    print(f"  {'胜率':>20}  {result_new.win_rate:>11.1f}%  {result_old.win_rate:>11.1f}%  {result_c.win_rate:>11.1f}%")
    print(f"  {'总盈亏':>20}  {result_new.total_pnl:>+11.2f}  {result_old.total_pnl:>+11.2f}  {result_c.total_pnl:>+11.2f}")
    print(f"  {'收益率':>20}  {result_new.total_pnl_pct:>+11.2f}%  {result_old.total_pnl_pct:>+11.2f}%  {result_c.total_pnl_pct:>+11.2f}%")
    print(f"  {'盈亏比':>20}  {result_new.risk_reward_ratio:>12.2f}  {result_old.risk_reward_ratio:>12.2f}  {result_c.risk_reward_ratio:>12.2f}")
    print(f"  {'盈利因子':>20}  {result_new.profit_factor:>12.2f}  {result_old.profit_factor:>12.2f}  {result_c.profit_factor:>12.2f}")
    print(f"  {'期望值/笔':>20}  {result_new.expectancy:>+11.2f}  {result_old.expectancy:>+11.2f}  {result_c.expectancy:>+11.2f}")
    print(f"  {'最大回撤':>20}  {result_new.max_drawdown:>11.2f}  {result_old.max_drawdown:>11.2f}  {result_c.max_drawdown:>11.2f}")
    print(f"  {'最大回撤率':>20}  {result_new.max_drawdown_pct:>11.2f}%  {result_old.max_drawdown_pct:>11.2f}%  {result_c.max_drawdown_pct:>11.2f}%")
    print(f"  {'最终资金':>20}  {result_new.final_balance:>11.2f}  {result_old.final_balance:>11.2f}  {result_c.final_balance:>11.2f}")
    print()


if __name__ == "__main__":
    main()
