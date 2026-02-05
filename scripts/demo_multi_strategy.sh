#!/bin/bash
#
# 多策略对比回测演示脚本
# 对比 ma_cross / macd / rsi / rsi_boll / boll_squeeze 策略
#

set -e

BACKTEST_URL="http://127.0.0.1:8030"

echo "=============================================="
echo "多策略对比回测 Demo"
echo "=============================================="
echo ""

# 检查服务
echo "检查 backtest 服务..."
curl -s "$BACKTEST_URL/health" > /dev/null || { echo "❌ Backtest 服务未运行"; exit 1; }
echo "✅ 服务正常"
echo ""

# 定义策略
STRATEGIES=(
    "ma_cross|MA交叉|{\"fast_ma\": 10, \"slow_ma\": 30}"
    "macd|MACD|{\"macd_fast\": 12, \"macd_slow\": 26, \"macd_signal\": 9}"
    "rsi|RSI|{\"rsi_period\": 14, \"rsi_overbought\": 70, \"rsi_oversold\": 30}"
    "rsi_boll|RSI布林带|{\"rsi_period\": 14, \"boll_period\": 20}"
    "boll_squeeze|布林压缩|{\"squeeze_threshold\": 3.0, \"boll_period\": 20}"
)

# 测试参数
SYMBOL="BTC/USDT"
TIMEFRAME="1h"
LIMIT=300

echo "回测参数:"
echo "  交易对:   $SYMBOL"
echo "  时间周期: $TIMEFRAME"
echo "  K线数量:  $LIMIT"
echo ""

echo "=============================================="
echo "开始回测各策略..."
echo "=============================================="
echo ""

# 存储结果
RESULTS=""

for strategy_info in "${STRATEGIES[@]}"; do
    IFS='|' read -r code name config <<< "$strategy_info"
    
    echo ">>> 回测: $name ($code)"
    
    RESULT=$(curl -s -X POST "$BACKTEST_URL/api/backtest/run-live" \
        -H "Content-Type: application/json" \
        -d "{
            \"strategy_code\": \"$code\",
            \"strategy_config\": $config,
            \"symbol\": \"$SYMBOL\",
            \"timeframe\": \"$TIMEFRAME\",
            \"limit\": $LIMIT,
            \"initial_balance\": 10000
        }" 2>/dev/null)
    
    SUCCESS=$(echo "$RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('success', False))" 2>/dev/null || echo "False")
    
    if [ "$SUCCESS" = "True" ]; then
        # 提取结果
        LINE=$(echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
r = data['result']
trades = r['total_trades']
win_rate = r['win_rate']
pnl = r['total_pnl']
pnl_pct = r['total_pnl_pct']
dd = r['max_drawdown_pct']
print(f'{trades}|{win_rate:.1f}|{pnl:.2f}|{pnl_pct:.2f}|{dd:.1f}')
")
        
        IFS='|' read -r trades win_rate pnl pnl_pct dd <<< "$LINE"
        
        # 格式化输出
        printf "    交易: %3s次  胜率: %5s%%  收益: %10s (%6s%%)  回撤: %5s%%\n" "$trades" "$win_rate" "$pnl" "$pnl_pct" "$dd"
        
        # 存储用于排名
        RESULTS="$RESULTS$code|$name|$trades|$win_rate|$pnl|$pnl_pct|$dd\n"
    else
        echo "    ❌ 回测失败"
        ERROR=$(echo "$RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('detail', d.get('message', 'unknown')))" 2>/dev/null || echo "unknown")
        echo "    错误: $ERROR"
    fi
    
    echo ""
done

echo "=============================================="
echo "策略排名（按收益）"
echo "=============================================="
echo ""

printf "%-15s %-12s %6s %8s %12s %8s %8s\n" "策略" "名称" "交易" "胜率" "收益" "收益率" "回撤"
echo "------------------------------------------------------------------------------"

echo -e "$RESULTS" | sort -t'|' -k5 -rn | while IFS='|' read -r code name trades win_rate pnl pnl_pct dd; do
    [ -z "$code" ] && continue
    printf "%-15s %-12s %6s %7s%% %12s %7s%% %7s%%\n" "$code" "$name" "$trades" "$win_rate" "$pnl" "$pnl_pct" "$dd"
done

echo ""
echo "=============================================="
echo "Demo 完成"
echo "=============================================="
