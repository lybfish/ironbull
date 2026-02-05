#!/bin/bash

# Backtest Service Demo
# 演示回测服务的完整流程

set -e

BACKTEST_URL="http://127.0.0.1:8030"
DATA_PROVIDER_URL="http://127.0.0.1:8010"

echo "============================================================"
echo "Backtest Service Demo"
echo "============================================================"
echo ""

# 检查服务是否运行
echo "1️⃣  检查服务状态..."
echo ""

if ! curl -s -f "$BACKTEST_URL/health" > /dev/null; then
    echo "❌ Backtest Service 未运行！"
    echo "请先启动: PYTHONPATH=. python3 services/backtest/app/main.py"
    exit 1
fi
echo "✅ Backtest Service: OK"

if ! curl -s -f "$DATA_PROVIDER_URL/health" > /dev/null; then
    echo "❌ Data Provider 未运行！"
    echo "请先启动: PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8005"
    exit 1
fi
echo "✅ Data Provider: OK"
echo ""

# 获取历史数据
echo "2️⃣  获取历史数据（500根15分钟K线）..."
echo ""

CANDLES_JSON=$(curl -s "$DATA_PROVIDER_URL/api/candles?symbol=BTCUSDT&timeframe=15m&limit=500")

# 提取 candles 数组并转换格式（移除 Pydantic 格式，转为纯 dict）
CANDLES=$(echo "$CANDLES_JSON" | jq '.candles | map({
    timestamp: (.timestamp | tostring + "000" | tonumber | . / 1000 | strftime("%Y-%m-%dT%H:%M:%S")),
    open: .open,
    high: .high,
    low: .low,
    close: .close,
    volume: .volume
})')

CANDLE_COUNT=$(echo "$CANDLES" | jq 'length')
echo "✅ 获取 $CANDLE_COUNT 根K线"
echo ""

# 运行回测
echo "3️⃣  运行回测（策略: ma_cross）..."
echo ""

BACKTEST_REQUEST=$(cat <<EOF
{
    "strategy_code": "ma_cross",
    "strategy_config": {
        "fast_ma": 5,
        "slow_ma": 20
    },
    "symbol": "BTCUSDT",
    "timeframe": "15m",
    "candles": $CANDLES,
    "initial_balance": 10000.0,
    "commission_rate": 0.001,
    "lookback": 50
}
EOF
)

RESULT=$(curl -s -X POST "$BACKTEST_URL/api/backtest/run" \
    -H "Content-Type: application/json" \
    -d "$BACKTEST_REQUEST")

# 检查是否成功
SUCCESS=$(echo "$RESULT" | jq -r '.success')

if [ "$SUCCESS" != "true" ]; then
    echo "❌ 回测失败:"
    echo "$RESULT" | jq '.'
    exit 1
fi

echo "✅ 回测完成"
echo ""

# 提取并显示结果
echo "============================================================"
echo "📊 回测结果"
echo "============================================================"
echo ""

# 基础信息
STRATEGY=$(echo "$RESULT" | jq -r '.result.strategy_code')
SYMBOL=$(echo "$RESULT" | jq -r '.result.symbol')
TIMEFRAME=$(echo "$RESULT" | jq -r '.result.timeframe')
START_TIME=$(echo "$RESULT" | jq -r '.result.start_time')
END_TIME=$(echo "$RESULT" | jq -r '.result.end_time')

echo "策略: $STRATEGY"
echo "交易对: $SYMBOL"
echo "周期: $TIMEFRAME"
echo "时间范围: $START_TIME ~ $END_TIME"
echo ""

# 交易统计
TOTAL_TRADES=$(echo "$RESULT" | jq -r '.result.total_trades')
WINNING_TRADES=$(echo "$RESULT" | jq -r '.result.winning_trades')
LOSING_TRADES=$(echo "$RESULT" | jq -r '.result.losing_trades')
WIN_RATE=$(echo "$RESULT" | jq -r '.result.win_rate')

echo "📈 交易统计"
echo "  总交易次数: $TOTAL_TRADES"
echo "  盈利次数: $WINNING_TRADES"
echo "  亏损次数: $LOSING_TRADES"
echo "  胜率: $WIN_RATE%"
echo ""

# 收益统计
TOTAL_PNL=$(echo "$RESULT" | jq -r '.result.total_pnl')
TOTAL_PNL_PCT=$(echo "$RESULT" | jq -r '.result.total_pnl_pct')
AVG_PNL=$(echo "$RESULT" | jq -r '.result.avg_pnl')
AVG_WIN=$(echo "$RESULT" | jq -r '.result.avg_win')
AVG_LOSS=$(echo "$RESULT" | jq -r '.result.avg_loss')

echo "💰 收益统计"
echo "  总盈亏: $TOTAL_PNL USDT"
echo "  总收益率: $TOTAL_PNL_PCT%"
echo "  平均盈亏: $AVG_PNL USDT"
echo "  平均盈利: $AVG_WIN USDT"
echo "  平均亏损: $AVG_LOSS USDT"
echo ""

# 风险统计
MAX_DD=$(echo "$RESULT" | jq -r '.result.max_drawdown')
MAX_DD_PCT=$(echo "$RESULT" | jq -r '.result.max_drawdown_pct')

echo "⚠️  风险统计"
echo "  最大回撤: $MAX_DD USDT"
echo "  最大回撤率: $MAX_DD_PCT%"
echo ""

# 账户统计
INITIAL=$(echo "$RESULT" | jq -r '.result.initial_balance')
FINAL=$(echo "$RESULT" | jq -r '.result.final_balance')
PEAK=$(echo "$RESULT" | jq -r '.result.peak_balance')

echo "💼 账户统计"
echo "  初始资金: $INITIAL USDT"
echo "  最终资金: $FINAL USDT"
echo "  最高资金: $PEAK USDT"
echo ""

# 交易记录（显示前5笔）
echo "📝 交易记录（前5笔）"
echo "$RESULT" | jq -r '.result.trades[:5] | .[] | 
    "  [\(.trade_id)] \(.side) @ \(.entry_price) → \(.exit_price) | PnL: \(.pnl) (\(.pnl_pct)%) | \(.exit_reason)"'

REMAINING=$(($TOTAL_TRADES - 5))
if [ $REMAINING -gt 0 ]; then
    echo "  ... 还有 $REMAINING 笔交易"
fi

echo ""
echo "============================================================"
echo "✅ Demo 完成"
echo "============================================================"
