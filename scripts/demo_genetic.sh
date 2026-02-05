#!/bin/bash
# ==============================================================================
# 遗传算法参数优化演示
# ==============================================================================

set -e

BACKTEST_URL="http://127.0.0.1:8030"

echo "=========================================="
echo "🧬 遗传算法参数优化演示"
echo "=========================================="
echo ""

# 检查服务
echo "检查 Backtest 服务..."
HEALTH=$(curl -s "$BACKTEST_URL/health" 2>/dev/null || echo '{}')
if echo "$HEALTH" | grep -q '"status":"ok"'; then
    echo "✅ Backtest 服务正常"
else
    echo "❌ Backtest 服务未运行"
    exit 1
fi
echo ""

# ==============================================================================
echo "=========================================="
echo "1. 遗传算法优化 MA Cross 策略"
echo "=========================================="
echo ""

echo "📊 参数空间:"
echo "   fast_ma: 5-30 (整数, 步长 1)"
echo "   slow_ma: 20-100 (整数, 步长 5)"
echo "   约束: slow_ma > fast_ma"
echo ""
echo "🧬 配置:"
echo "   种群大小: 30"
echo "   迭代代数: 15"
echo "   变异率: 0.2"
echo "   优化目标: 收益 (PnL)"
echo ""

RESULT=$(curl -s -X POST "$BACKTEST_URL/api/backtest/optimize-genetic" \
    -H "Content-Type: application/json" \
    -d '{
        "strategy_code": "ma_cross",
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "limit": 300,
        "param_space": {
            "fast_ma": {"type": "int", "low": 5, "high": 30, "step": 1},
            "slow_ma": {"type": "int", "low": 20, "high": 100, "step": 5}
        },
        "config": {
            "population_size": 30,
            "generations": 15,
            "mutation_rate": 0.2,
            "early_stop": 5
        },
        "score_by": "pnl",
        "constraints": ["slow_ma > fast_ma"]
    }')

if echo "$RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); exit(0 if d.get('success') else 1)" 2>/dev/null; then
    echo "✅ 优化完成!"
    echo ""
    echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('📈 优化结果:')
print(f'   最优参数: {d[\"best_params\"]}')
print(f'   最优适应度: {d[\"best_fitness\"]:.2f}')
print(f'   迭代代数: {d[\"generations_run\"]}')
print(f'   总评估次数: {d[\"total_evaluations\"]}')
print(f'   耗时: {d[\"elapsed_seconds\"]}s')
print()
print('📊 最优回测指标:')
m = d['best_metrics']
print(f'   交易次数: {m.get(\"total_trades\", 0)}')
print(f'   胜率: {m.get(\"win_rate\", 0):.1f}%')
print(f'   总收益: \${m.get(\"total_pnl\", 0):,.2f}')
print(f'   收益率: {m.get(\"total_pnl_pct\", 0):+.1f}%')
print(f'   最大回撤: {m.get(\"max_drawdown_pct\", 0):.1f}%')
print()
print('🏆 Top 5 参数组合:')
for i, item in enumerate(d['top_10'][:5], 1):
    p = item['params']
    f = item['fitness']
    m = item.get('metrics', {})
    pnl = m.get('total_pnl', 0)
    print(f'   {i}. fast={p.get(\"fast_ma\"):2d}, slow={p.get(\"slow_ma\"):3d} -> PnL=\${pnl:,.0f}')
print()
print('📈 进化历史:')
for h in d['evolution_history'][:6]:
    print(f'   Gen {h[\"generation\"]:2d}: best={h[\"best_fitness\"]:8.2f}, avg={h[\"avg_fitness\"]:8.2f}')
if len(d['evolution_history']) > 6:
    print('   ...')
    h = d['evolution_history'][-1]
    print(f'   Gen {h[\"generation\"]:2d}: best={h[\"best_fitness\"]:8.2f}, avg={h[\"avg_fitness\"]:8.2f}')
"
else
    echo "❌ 优化失败"
    echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"
fi
echo ""

# ==============================================================================
echo "=========================================="
echo "2. 遗传算法 vs 网格搜索对比"
echo "=========================================="
echo ""

echo "🔲 网格搜索 (穷举)..."
GRID_START=$(python3 -c "import time; print(time.time())")
GRID_RESULT=$(curl -s -X POST "$BACKTEST_URL/api/backtest/optimize" \
    -H "Content-Type: application/json" \
    -d '{
        "strategy_code": "ma_cross",
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "limit": 300,
        "param_grid": {
            "fast_ma": [5, 10, 15, 20, 25],
            "slow_ma": [30, 40, 50, 60, 70, 80, 90, 100]
        },
        "score_by": "pnl",
        "constraints": {"slow_ma_gt_fast_ma": true}
    }')
GRID_END=$(python3 -c "import time; print(time.time())")

echo "🧬 遗传算法 (智能搜索)..."
GA_START=$(python3 -c "import time; print(time.time())")
GA_RESULT=$(curl -s -X POST "$BACKTEST_URL/api/backtest/optimize-genetic" \
    -H "Content-Type: application/json" \
    -d '{
        "strategy_code": "ma_cross",
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "limit": 300,
        "param_space": {
            "fast_ma": {"type": "int", "low": 5, "high": 25, "step": 1},
            "slow_ma": {"type": "int", "low": 30, "high": 100, "step": 1}
        },
        "config": {
            "population_size": 20,
            "generations": 10,
            "mutation_rate": 0.3
        },
        "score_by": "pnl",
        "constraints": ["slow_ma > fast_ma"]
    }')
GA_END=$(python3 -c "import time; print(time.time())")

echo ""
echo "对比结果:"
python3 << EOF
import json
import re

# 处理 JSON 中的 Infinity
def parse_json(s):
    s = re.sub(r':-?Infinity', ':null', s)
    s = re.sub(r':-?inf', ':null', s)
    return json.loads(s)

grid = parse_json('$GRID_RESULT')
ga = parse_json('$GA_RESULT')

grid_time = $GRID_END - $GRID_START
ga_time = $GA_END - $GA_START

print("┌─────────────────────┬────────────────┬────────────────┐")
print("│                     │   网格搜索     │   遗传算法     │")
print("├─────────────────────┼────────────────┼────────────────┤")

grid_combos = grid.get('total_combinations', 0)
ga_evals = ga.get('total_evaluations', 0)
print(f"│ 评估次数            │ {grid_combos:>14} │ {ga_evals:>14} │")

grid_pnl = grid.get('best_score', 0)
ga_pnl = ga.get('best_fitness', 0)
print(f"│ 最优收益            │ \${grid_pnl:>12,.0f} │ \${ga_pnl:>12,.0f} │")

grid_params = grid.get('best_params', {})
ga_params = ga.get('best_params', {})
grid_fast = grid_params.get('fast_ma', '-')
grid_slow = grid_params.get('slow_ma', '-')
ga_fast = ga_params.get('fast_ma', '-')
ga_slow = ga_params.get('slow_ma', '-')
print(f"│ 最优 fast_ma        │ {grid_fast:>14} │ {ga_fast:>14} │")
print(f"│ 最优 slow_ma        │ {grid_slow:>14} │ {ga_slow:>14} │")

grid_sec = grid.get('elapsed_seconds', grid_time)
ga_sec = ga.get('elapsed_seconds', ga_time)
print(f"│ 耗时(秒)            │ {grid_sec:>14.2f} │ {ga_sec:>14.2f} │")

print("└─────────────────────┴────────────────┴────────────────┘")
print()

# 分析
print("📊 分析:")
if ga_pnl >= grid_pnl * 0.95:
    print(f"   ✅ 遗传算法找到了相近或更好的解")
else:
    print(f"   ⚠️ 网格搜索结果更优 (遗传算法可能陷入局部最优)")

search_space = (25 - 5 + 1) * (100 - 30 + 1)  # 21 * 71 = 1491
print(f"   📌 参数空间大小: {search_space} 种组合")
print(f"   📌 网格搜索覆盖: {grid_combos} 组合 ({grid_combos/search_space*100:.1f}%)")
print(f"   📌 遗传算法探索: {ga_evals} 组合 ({ga_evals/search_space*100:.1f}%)")

if ga_evals < grid_combos:
    print(f"   🚀 遗传算法减少了 {grid_combos - ga_evals} 次评估 ({(1 - ga_evals/grid_combos)*100:.0f}% 更高效)")
EOF

echo ""
echo "=========================================="
echo "🎉 演示完成!"
echo "=========================================="
