#!/usr/bin/env bash
# Follow Service Demo
set -euo pipefail

FOLLOW_SERVICE_URL=${FOLLOW_SERVICE_URL:-http://127.0.0.1:8006}
DISPATCHER_URL=${DISPATCHER_URL:-http://127.0.0.1:8003}

echo "============================================================"
echo "IronBull Follow Service Demo"
echo "============================================================"

echo ""
echo "[1] Health Check"
curl -s "$FOLLOW_SERVICE_URL/health" | python3 -m json.tool

echo ""
echo "[2] 创建跟单关系 (Leader=1, Follower=100)"
relation_resp=$(curl -s -X POST "$FOLLOW_SERVICE_URL/api/relations" \
  -H 'Content-Type: application/json' \
  -d '{
    "leader_id": 1,
    "follower_id": 100,
    "follower_account_id": 1001,
    "follow_mode": "ratio",
    "follow_value": 0.5,
    "platform": "crypto",
    "exchange": "binance"
  }')
echo "$relation_resp" | python3 -m json.tool

echo ""
echo "[3] 创建另一个跟单关系 (Leader=1, Follower=101)"
curl -s -X POST "$FOLLOW_SERVICE_URL/api/relations" \
  -H 'Content-Type: application/json' \
  -d '{
    "leader_id": 1,
    "follower_id": 101,
    "follower_account_id": 1002,
    "follow_mode": "fixed_quantity",
    "follow_value": 0.02,
    "platform": "crypto",
    "exchange": "okx"
  }' | python3 -m json.tool

echo ""
echo "[4] 列出 Leader=1 的所有跟单关系"
curl -s "$FOLLOW_SERVICE_URL/api/relations?leader_id=1" | python3 -m json.tool

echo ""
echo "[5] 广播信号给所有 Follower"
broadcast_resp=$(curl -s -X POST "$FOLLOW_SERVICE_URL/api/broadcast" \
  -H 'Content-Type: application/json' \
  -d '{
    "leader_id": 1,
    "signal": {
      "signal_id": "sig_demo_001",
      "strategy_code": "ma_cross",
      "symbol": "BTCUSDT",
      "canonical_symbol": "BTC/USDT",
      "side": "BUY",
      "signal_type": "OPEN",
      "entry_price": 42000,
      "stop_loss": 41000,
      "take_profit": 44000,
      "quantity": 0.1,
      "confidence": 80,
      "reason": "demo signal",
      "timeframe": "15m",
      "timestamp": 1700000000,
      "status": "pending"
    }
  }')
echo "$broadcast_resp" | python3 -m json.tool

tasks_created=$(echo "$broadcast_resp" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['tasks_created'])")

echo ""
echo "============================================================"
if [ "$tasks_created" -gt 0 ]; then
    echo "✅ Demo 完成！跟单任务已创建: $tasks_created"
else
    echo "⚠️ 未创建跟单任务（可能 dispatcher 未运行）"
fi
echo "============================================================"
