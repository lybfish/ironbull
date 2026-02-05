#!/usr/bin/env bash
# ============================================================
# IronBull v1 Facts Layer Demo
# 验证完整信号链路：Signal → Risk → Execution → Trade/Ledger
# ============================================================

set -euo pipefail

SIGNAL_HUB_URL=${SIGNAL_HUB_URL:-http://127.0.0.1:8001}
RISK_CONTROL_URL=${RISK_CONTROL_URL:-http://127.0.0.1:8002}
EXEC_DISPATCHER_URL=${EXEC_DISPATCHER_URL:-http://127.0.0.1:8003}

echo "============================================================"
echo "IronBull v1 Facts Layer Demo"
echo "============================================================"

# 1. 创建信号
echo ""
echo "1️⃣  创建信号 (signal-hub)..."
signal_resp=$(curl -s -X POST "$SIGNAL_HUB_URL/api/signals" \
  -H 'Content-Type: application/json' \
  -d '{
    "strategy_code": "demo_macross",
    "timeframe": "15m",
    "strategy_output": {
      "symbol": "BTCUSDT",
      "signal_type": "OPEN",
      "side": "BUY",
      "entry_price": 40000.0,
      "stop_loss": 39000.0,
      "take_profit": 42000.0,
      "confidence": 80,
      "reason": "v1 facts demo"
    }
  }')

signal_id=$(echo "$signal_resp" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['signal']['signal_id'])")
echo "  ✅ Signal created: $signal_id"
echo "$signal_resp" | python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2))'

# 2. 风控检查
echo ""
echo "2️⃣  风控检查 (risk-control)..."
risk_resp=$(curl -s -X POST "$RISK_CONTROL_URL/api/risk/check" \
  -H 'Content-Type: application/json' \
  -d "{
    \"signal\": {
      \"signal_id\": \"$signal_id\",
      \"strategy_code\": \"demo_macross\",
      \"symbol\": \"BTCUSDT\",
      \"canonical_symbol\": \"BTC/USDT\",
      \"side\": \"BUY\",
      \"signal_type\": \"OPEN\",
      \"entry_price\": 40000.0,
      \"stop_loss\": 39000.0,
      \"take_profit\": 42000.0,
      \"confidence\": 80.0,
      \"reason\": \"v1 facts demo\",
      \"timeframe\": \"15m\",
      \"timestamp\": $(date +%s),
      \"status\": \"pending\"
    },
    \"account\": {
      \"account_id\": 1001,
      \"member_id\": 100,
      \"balance\": 10000.0,
      \"available\": 9500.0,
      \"frozen\": 500.0
    }
  }")

passed=$(echo "$risk_resp" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['result']['passed'])")
echo "  ✅ Risk check: $passed"

# 3. 提交执行
echo ""
echo "3️⃣  提交执行 (execution-dispatcher)..."
exec_resp=$(curl -s -X POST "$EXEC_DISPATCHER_URL/api/execution/submit" \
  -H 'Content-Type: application/json' \
  -d "{
    \"signal_id\": \"$signal_id\",
    \"account_id\": 1001,
    \"member_id\": 100,
    \"platform\": \"crypto\",
    \"exchange\": \"binance\",
    \"symbol\": \"BTCUSDT\",
    \"side\": \"BUY\",
    \"order_type\": \"MARKET\",
    \"quantity\": 0.01,
    \"price\": 40000.0,
    \"stop_loss\": 39000.0,
    \"take_profit\": 42000.0
  }")

task_id=$(echo "$exec_resp" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['task_id'])")
echo "  ✅ Execution submitted: $task_id"

# 4. 获取执行结果
echo ""
echo "4️⃣  获取执行结果..."
result_resp=$(curl -s "$EXEC_DISPATCHER_URL/api/execution/result/$task_id")
echo "$result_resp" | python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2))'

# 5. 查询信号链路
echo ""
echo "5️⃣  查询信号完整链路 (signal_id: $signal_id)..."
chain_resp=$(curl -s "$SIGNAL_HUB_URL/api/signals/$signal_id/chain" 2>/dev/null || echo '{"error": "Facts layer not enabled or DB not connected"}')
echo "$chain_resp" | python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2))'

echo ""
echo "============================================================"
echo "✅ Demo 完成"
echo ""
echo "Signal ID: $signal_id"
echo "Task ID:   $task_id"
echo ""
echo "链路查询 API:"
echo "  GET $SIGNAL_HUB_URL/api/signals/$signal_id/chain"
echo "============================================================"
