#!/bin/bash
#
# 参数优化演示脚本
# 自动寻找 ma_cross 策略的最优参数
#

set -e

BACKTEST_URL="http://127.0.0.1:8030"

echo "=============================================="
echo "参数优化 Demo"
echo "=============================================="
echo ""

# 检查服务
echo "检查 backtest 服务..."
curl -s "$BACKTEST_URL/health" > /dev/null || { echo "❌ Backtest 服务未运行"; exit 1; }
echo "✅ 服务正常"
echo ""

# 1. MA Cross 策略优化
echo "=============================================="
echo "1. 优化 MA Cross 策略参数"
echo "=============================================="
echo ""
echo "参数网格:"
echo "  fast_ma: [5, 10, 15, 20, 25]"
echo "  slow_ma: [20, 30, 40, 50, 60]"
echo "  约束: slow_ma > fast_ma"
echo ""
echo "优化目标: 最大收益 (pnl)"
echo ""

RESULT=$(curl -s -X POST "$BACKTEST_URL/api/backtest/optimize" \
    -H "Content-Type: application/json" \
    -d '{
        "strategy_code": "ma_cross",
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "limit": 300,
        "param_grid": {
            "fast_ma": [5, 10, 15, 20, 25],
            "slow_ma": [20, 30, 40, 50, 60]
        },
        "score_by": "pnl",
        "constraints": {
            "slow_ma_gt_fast_ma": true
        }
    }')

echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)

if data.get('success'):
    print('✅ 优化完成!')
    print()
    print(f'总组合数: {data[\"total_combinations\"]}')
    print(f'耗时: {data[\"elapsed_seconds\"]}秒')
    print()
    print('📊 最优参数:')
    for k, v in data['best_params'].items():
        print(f'    {k}: {v}')
    print()
    print(f'最优得分: {data[\"best_score\"]:.2f}')
    print()
    
    br = data.get('best_result', {})
    print('最优结果:')
    print(f'    收益: \${br.get(\"total_pnl\", 0):.2f} ({br.get(\"total_pnl_pct\", 0):.2f}%)')
    print(f'    胜率: {br.get(\"win_rate\", 0):.1f}%')
    print(f'    交易: {br.get(\"total_trades\", 0)}次')
    print(f'    回撤: {br.get(\"max_drawdown_pct\", 0):.1f}%')
    print()
    
    print('🏆 Top 5 参数组合:')
    print('-' * 60)
    for i, item in enumerate(data.get('top_10', [])[:5], 1):
        p = item['params']
        print(f'{i}. fast={p.get(\"fast_ma\"):2d} slow={p.get(\"slow_ma\"):2d} | 收益: {item[\"total_pnl\"]:8.2f} 胜率: {item[\"win_rate\"]:5.1f}%')
else:
    print('❌ 优化失败')
    print(data)
"
echo ""

# 2. 优化 MACD 策略
echo "=============================================="
echo "2. 优化 MACD 策略参数"
echo "=============================================="
echo ""
echo "参数网格:"
echo "  macd_fast: [8, 12, 16]"
echo "  macd_slow: [20, 26, 32]"
echo "  macd_signal: [7, 9, 11]"
echo ""

RESULT2=$(curl -s -X POST "$BACKTEST_URL/api/backtest/optimize" \
    -H "Content-Type: application/json" \
    -d '{
        "strategy_code": "macd",
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "limit": 300,
        "param_grid": {
            "macd_fast": [8, 12, 16],
            "macd_slow": [20, 26, 32],
            "macd_signal": [7, 9, 11]
        },
        "score_by": "sharpe"
    }')

echo "$RESULT2" | python3 -c "
import sys, json
data = json.load(sys.stdin)

if data.get('success'):
    print('✅ 优化完成!')
    print()
    print(f'总组合数: {data[\"total_combinations\"]}')
    print()
    print('📊 最优参数:')
    for k, v in data['best_params'].items():
        print(f'    {k}: {v}')
    print()
    
    br = data.get('best_result', {})
    print(f'收益: \${br.get(\"total_pnl\", 0):.2f} | 胜率: {br.get(\"win_rate\", 0):.1f}% | 回撤: {br.get(\"max_drawdown_pct\", 0):.1f}%')
else:
    print('❌ 优化失败:', data.get('message', 'unknown'))
"
echo ""

# 3. 对比默认参数 vs 优化参数
echo "=============================================="
echo "3. 对比：默认参数 vs 优化参数"
echo "=============================================="
echo ""

# 提取最优参数
BEST_FAST=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('best_params', {}).get('fast_ma', 10))")
BEST_SLOW=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('best_params', {}).get('slow_ma', 30))")

echo "默认参数: fast_ma=10, slow_ma=30"
echo "优化参数: fast_ma=$BEST_FAST, slow_ma=$BEST_SLOW"
echo ""

# 默认参数回测
DEFAULT_RESULT=$(curl -s -X POST "$BACKTEST_URL/api/backtest/run-live" \
    -H "Content-Type: application/json" \
    -d '{
        "strategy_code": "ma_cross",
        "strategy_config": {"fast_ma": 10, "slow_ma": 30},
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "limit": 300
    }')

# 优化参数回测
OPTIMIZED_RESULT=$(curl -s -X POST "$BACKTEST_URL/api/backtest/run-live" \
    -H "Content-Type: application/json" \
    -d "{
        \"strategy_code\": \"ma_cross\",
        \"strategy_config\": {\"fast_ma\": $BEST_FAST, \"slow_ma\": $BEST_SLOW},
        \"symbol\": \"BTC/USDT\",
        \"timeframe\": \"1h\",
        \"limit\": 300
    }")

echo "对比结果:"
echo "-" * 50
printf "%-15s %12s %12s\n" "指标" "默认参数" "优化参数"
echo "-" * 50

DEFAULT_PNL=$(echo "$DEFAULT_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('total_pnl', 0))")
OPTIMIZED_PNL=$(echo "$OPTIMIZED_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('total_pnl', 0))")

DEFAULT_WIN=$(echo "$DEFAULT_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('win_rate', 0))")
OPTIMIZED_WIN=$(echo "$OPTIMIZED_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('win_rate', 0))")

DEFAULT_DD=$(echo "$DEFAULT_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('max_drawdown_pct', 0))")
OPTIMIZED_DD=$(echo "$OPTIMIZED_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('max_drawdown_pct', 0))")

printf "%-15s %12.2f %12.2f\n" "收益($)" "$DEFAULT_PNL" "$OPTIMIZED_PNL"
printf "%-15s %11.1f%% %11.1f%%\n" "胜率" "$DEFAULT_WIN" "$OPTIMIZED_WIN"
printf "%-15s %11.1f%% %11.1f%%\n" "最大回撤" "$DEFAULT_DD" "$OPTIMIZED_DD"

echo ""
echo "=============================================="
echo "Demo 完成"
echo "=============================================="
