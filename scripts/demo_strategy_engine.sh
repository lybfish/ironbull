#!/usr/bin/env bash
# Strategy Engine Demo - 演示完整流程
# Strategy → Signal Hub → Risk → Dispatcher → Node
set -euo pipefail

STRATEGY_ENGINE_URL=${STRATEGY_ENGINE_URL:-http://127.0.0.1:8000}
SIGNAL_HUB_URL=${SIGNAL_HUB_URL:-http://127.0.0.1:8001}
RISK_CONTROL_URL=${RISK_CONTROL_URL:-http://127.0.0.1:8002}
DISPATCHER_URL=${DISPATCHER_URL:-http://127.0.0.1:8003}

echo "============================================================"
echo "IronBull Strategy Engine Demo"
echo "============================================================"

# 构造测试 K 线数据（模拟金叉）
# 前 23 根下跌，最后 2 根上涨形成金叉
candles_json='['

# Phase 1: 下跌 (23 根)
for i in $(seq 0 22); do
    price=$(echo "100 - $i * 0.15" | bc)
    candles_json+=$(cat <<EOF
{"open": $price, "high": $(echo "$price + 0.3" | bc), "low": $(echo "$price - 0.3" | bc), "close": $price, "volume": 1000, "timestamp": $((1700000000 + i * 900))}
EOF
)
    candles_json+=","
done

# Phase 2: 上涨 (2 根) - 形成金叉
candles_json+='{"open": 96.5, "high": 98, "low": 96, "close": 97.5, "volume": 2000, "timestamp": 1700020700},'
candles_json+='{"open": 97.5, "high": 100, "low": 97, "close": 99.5, "volume": 2500, "timestamp": 1700021600}'
candles_json+=']'

echo ""
echo "[1] Strategy Engine: 触发 ma_cross 策略分析"
echo "---"

analyze_payload=$(cat <<EOF
{
  "strategy_code": "ma_cross",
  "symbol": "BTCUSDT",
  "timeframe": "15m",
  "candles": $candles_json,
  "config": {"fast_ma": 5, "slow_ma": 10},
  "auto_submit": true
}
EOF
)

analyze_resp=$(curl -s -X POST "$STRATEGY_ENGINE_URL/api/analyze" \
  -H 'Content-Type: application/json' \
  -d "$analyze_payload")

python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2, ensure_ascii=False))' <<<"$analyze_resp"

has_signal=$(python3 -c "import json; print(json.loads('''$analyze_resp''').get('has_signal', False))")
submitted=$(python3 -c "import json; print(json.loads('''$analyze_resp''').get('submitted', False))")
signal_id=$(python3 -c "import json; print(json.loads('''$analyze_resp''').get('signal_id', ''))")

if [ "$has_signal" != "True" ]; then
    echo "❌ 未生成信号，demo 结束"
    exit 1
fi

echo ""
echo "✅ 信号已生成"
echo "   submitted: $submitted"
echo "   signal_id: $signal_id"

if [ "$submitted" != "True" ] || [ -z "$signal_id" ]; then
    echo "❌ 信号未提交到 signal-hub，demo 结束"
    exit 1
fi

echo ""
echo "[2] Risk Control: 风控检查"
echo "---"

# 从 signal-hub 获取完整 signal（如果需要）或直接构造
strategy_output=$(python3 -c "import json; print(json.dumps(json.loads('''$analyze_resp''')['strategy_output']))")

# 构造风控请求
risk_payload=$(python3 - <<PY
import json
output = json.loads('''$strategy_output''')
signal = {
    "signal_id": "$signal_id",
    "strategy_code": "ma_cross",
    "symbol": output["symbol"],
    "canonical_symbol": output["symbol"],
    "side": output["side"],
    "signal_type": output["signal_type"],
    "entry_price": output.get("entry_price"),
    "stop_loss": output.get("stop_loss"),
    "take_profit": output.get("take_profit"),
    "confidence": output.get("confidence"),
    "reason": output.get("reason"),
    "timeframe": "15m",
    "timestamp": 1700021600,
    "status": "pending"
}
account = {"account_id": 1, "member_id": 100, "balance": 10000, "available": 8000, "frozen": 0}
print(json.dumps({"signal": signal, "account": account}))
PY
)

risk_resp=$(curl -s -X POST "$RISK_CONTROL_URL/api/risk/check" \
  -H 'Content-Type: application/json' \
  -d "$risk_payload")

python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2, ensure_ascii=False))' <<<"$risk_resp"

passed=$(python3 -c "import json; print(json.loads('''$risk_resp''')['result']['passed'])")
if [ "$passed" != "True" ]; then
    echo "❌ 风控未通过"
    exit 1
fi
echo "✅ 风控通过"

risk_signal=$(python3 -c "import json; print(json.dumps(json.loads('''$risk_resp''')['result']['signal']))")

echo ""
echo "[3] Execution Dispatcher: 提交执行"
echo "---"

submit_payload=$(python3 - <<PY
import json
signal = json.loads('''$risk_signal''')
print(json.dumps({
  "signal_id": signal["signal_id"],
  "account_id": 1,
  "member_id": 100,
  "platform": "crypto",
  "exchange": "binance",
  "symbol": signal["symbol"],
  "side": signal["side"],
  "order_type": "MARKET",
  "quantity": signal["quantity"],
  "price": signal.get("entry_price"),
  "stop_loss": signal.get("stop_loss"),
  "take_profit": signal.get("take_profit")
}))
PY
)

submit_resp=$(curl -s -X POST "$DISPATCHER_URL/api/execution/submit" \
  -H 'Content-Type: application/json' \
  -d "$submit_payload")

python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2))' <<<"$submit_resp"

task_id=$(python3 -c "import json; print(json.loads('''$submit_resp''')['task_id'])")
echo "   task_id: $task_id"

echo ""
echo "[4] Execution Result: 获取执行结果"
echo "---"

result_resp=$(curl -s "$DISPATCHER_URL/api/execution/result/$task_id")
python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2))' <<<"$result_resp"

success=$(python3 -c "import json; print(json.loads('''$result_resp''')['result']['success'])")
order_id=$(python3 -c "import json; print(json.loads('''$result_resp''')['result'].get('exchange_order_id', ''))")

echo ""
echo "============================================================"
if [ "$success" == "True" ]; then
    echo "✅ Demo 完成！完整链路跑通"
    echo "   Signal ID: $signal_id"
    echo "   Task ID: $task_id"
    echo "   Exchange Order ID: $order_id"
else
    echo "❌ 执行失败"
fi
echo "============================================================"
