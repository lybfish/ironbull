#!/bin/bash
#
# v1 Phase 5: 真实数据回测演示脚本
# 使用 Binance 真实 K 线数据验证 ma_cross 策略
#

set -e

BACKTEST_URL="http://127.0.0.1:8030"
DATA_PROVIDER_URL="http://127.0.0.1:8010"

echo "=============================================="
echo "v1 Phase 5: 真实数据回测 Demo"
echo "=============================================="
echo ""

# Step 1: 检查服务
echo "Step 1: 检查服务健康"
echo "----------------------------------------------"

echo "Data Provider:"
curl -s "$DATA_PROVIDER_URL/health" | python3 -m json.tool || echo "❌ Data Provider 未运行"
echo ""

echo "Backtest Service:"
curl -s "$BACKTEST_URL/health" | python3 -m json.tool || echo "❌ Backtest Service 未运行"
echo ""

# Step 2: 使用真实数据回测 BTC/USDT
echo "Step 2: 使用真实 K 线数据回测 BTC/USDT (ma_cross)"
echo "----------------------------------------------"
echo "请求: POST /api/backtest/run-live"
echo ""

RESULT=$(curl -s -X POST "$BACKTEST_URL/api/backtest/run-live" \
    -H "Content-Type: application/json" \
    -d '{
        "strategy_code": "ma_cross",
        "strategy_config": {"fast_ma": 5, "slow_ma": 20},
        "symbol": "BTC/USDT",
        "timeframe": "15m",
        "limit": 500,
        "initial_balance": 10000,
        "commission_rate": 0.001
    }')

echo "$RESULT" | python3 -m json.tool
echo ""

# 提取关键指标
SUCCESS=$(echo "$RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('success', False))" 2>/dev/null || echo "False")

if [ "$SUCCESS" = "True" ]; then
    echo "----------------------------------------------"
    echo "📊 回测结果摘要"
    echo "----------------------------------------------"
    
    echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
r = data['result']
print(f\"数据源:       {data.get('data_source', 'N/A')}\")
print(f\"交易所:       {data.get('exchange', 'N/A')}\")
print(f\"K线数量:      {data.get('candles_count', 0)}\")
print(f\"策略:         {r['strategy_code']}\")
print(f\"交易对:       {r['symbol']}\")
print(f\"时间周期:     {r['timeframe']}\")
print(f\"回测区间:     {r['start_time'][:19]} ~ {r['end_time'][:19]}\")
print('')
print(f\"总交易次数:   {r['total_trades']}\")
print(f\"盈利次数:     {r['winning_trades']}\")
print(f\"亏损次数:     {r['losing_trades']}\")
print(f\"胜率:         {r['win_rate']:.2f}%\")
print('')
print(f\"初始资金:     \${r['initial_balance']:.2f}\")
print(f\"最终资金:     \${r['final_balance']:.2f}\")
print(f\"总收益:       \${r['total_pnl']:.2f} ({r['total_pnl_pct']:.2f}%)\")
print(f\"最大回撤:     \${r['max_drawdown']:.2f} ({r['max_drawdown_pct']:.2f}%)\")
"
    echo ""
fi

# Step 3: 测试 ETH/USDT
echo "Step 3: 使用真实数据回测 ETH/USDT"
echo "----------------------------------------------"

RESULT2=$(curl -s -X POST "$BACKTEST_URL/api/backtest/run-live" \
    -H "Content-Type: application/json" \
    -d '{
        "strategy_code": "ma_cross",
        "strategy_config": {"fast_ma": 10, "slow_ma": 30},
        "symbol": "ETH/USDT",
        "timeframe": "1h",
        "limit": 300,
        "initial_balance": 10000
    }')

SUCCESS2=$(echo "$RESULT2" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('success', False))" 2>/dev/null || echo "False")

if [ "$SUCCESS2" = "True" ]; then
    echo "$RESULT2" | python3 -c "
import sys, json
data = json.load(sys.stdin)
r = data['result']
print(f\"交易对:       {r['symbol']}\")
print(f\"时间周期:     {r['timeframe']}\")
print(f\"K线数量:      {data.get('candles_count', 0)}\")
print(f\"总交易次数:   {r['total_trades']}\")
print(f\"胜率:         {r['win_rate']:.2f}%\")
print(f\"总收益:       \${r['total_pnl']:.2f} ({r['total_pnl_pct']:.2f}%)\")
print(f\"最大回撤:     {r['max_drawdown_pct']:.2f}%\")
"
else
    echo "$RESULT2" | python3 -m json.tool
fi
echo ""

# Step 4: 对比不同参数
echo "Step 4: 参数对比 (不同 MA 周期)"
echo "----------------------------------------------"

for FAST in 5 10 20; do
    SLOW=$((FAST * 4))
    
    RESULT_CMP=$(curl -s -X POST "$BACKTEST_URL/api/backtest/run-live" \
        -H "Content-Type: application/json" \
        -d "{
            \"strategy_code\": \"ma_cross\",
            \"strategy_config\": {\"fast_ma\": $FAST, \"slow_ma\": $SLOW},
            \"symbol\": \"BTC/USDT\",
            \"timeframe\": \"15m\",
            \"limit\": 300
        }")
    
    SUCCESS_CMP=$(echo "$RESULT_CMP" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('success', False))" 2>/dev/null || echo "False")
    
    if [ "$SUCCESS_CMP" = "True" ]; then
        echo "$RESULT_CMP" | python3 -c "
import sys, json
data = json.load(sys.stdin)
r = data['result']
cfg = r['strategy_code']
print(f\"MA({$FAST}/{$SLOW}): trades={r['total_trades']}, win_rate={r['win_rate']:.1f}%, pnl={r['total_pnl']:.2f}, dd={r['max_drawdown_pct']:.1f}%\")
"
    else
        echo "MA($FAST/$SLOW): 失败"
    fi
done
echo ""

# 总结
echo "=============================================="
echo "Demo 完成"
echo "=============================================="
echo ""
echo "新增 API:"
echo "  POST /api/backtest/run-live - 使用真实交易所 K 线数据回测"
echo ""
echo "特点:"
echo "  - 自动从 data-provider 获取真实 K 线"
echo "  - 支持指定交易所 (binance/okx)"
echo "  - 支持 Redis 缓存加速"
echo ""
