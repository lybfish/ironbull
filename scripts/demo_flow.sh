#!/usr/bin/env bash
set -euo pipefail

SIGNAL_HUB_URL=${SIGNAL_HUB_URL:-http://127.0.0.1:8001}
RISK_CONTROL_URL=${RISK_CONTROL_URL:-http://127.0.0.1:8002}
DISPATCHER_URL=${DISPATCHER_URL:-http://127.0.0.1:8003}

account_payload='{"account_id":1,"user_id":100,"balance":10000,"available":8000,"frozen":0}'

create_signal_payload='{
  "strategy_code": "demo_macross",
  "timeframe": "15m",
  "strategy_output": {
    "symbol": "BTCUSDT",
    "signal_type": "OPEN",
    "side": "BUY",
    "entry_price": 40000,
    "stop_loss": 39000,
    "take_profit": 42000,
    "confidence": 80,
    "reason": "demo"
  }
}'

echo "[1] Create signal"
signal_resp=$(curl -s -X POST "$SIGNAL_HUB_URL/api/signals" \
  -H 'Content-Type: application/json' \
  -d "$create_signal_payload")

python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2))' <<<"$signal_resp"

signal_json=$(python3 - <<PY
import json
obj=json.loads('''$signal_resp''')
print(json.dumps(obj['signal']))
PY
)

echo "[2] Risk check"
risk_payload=$(python3 - <<PY
import json
signal=json.loads('''$signal_json''')
account=json.loads('''$account_payload''')
print(json.dumps({"signal": signal, "account": account}))
PY
)

risk_resp=$(curl -s -X POST "$RISK_CONTROL_URL/api/risk/check" \
  -H 'Content-Type: application/json' \
  -d "$risk_payload")

python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2))' <<<"$risk_resp"

risk_signal=$(python3 - <<PY
import json
obj=json.loads('''$risk_resp''')
print(json.dumps(obj['result']['signal']))
PY
)

signal_id=$(python3 - <<PY
import json
print(json.loads('''$risk_signal''')['signal_id'])
PY
)

quantity=$(python3 - <<PY
import json
print(json.loads('''$risk_signal''')['quantity'])
PY
)

stop_loss=$(python3 - <<PY
import json
print(json.loads('''$risk_signal''')['stop_loss'])
PY
)

take_profit=$(python3 - <<PY
import json
print(json.loads('''$risk_signal''')['take_profit'])
PY
)

submit_payload=$(python3 - <<PY
import json
signal=json.loads('''$risk_signal''')
print(json.dumps({
  "signal_id": signal["signal_id"],
  "account_id": 1,
  "user_id": 100,
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

echo "[3] Submit execution"
submit_resp=$(curl -s -X POST "$DISPATCHER_URL/api/execution/submit" \
  -H 'Content-Type: application/json' \
  -d "$submit_payload")

python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2))' <<<"$submit_resp"

task_id=$(python3 - <<PY
import json
obj=json.loads('''$submit_resp''')
print(obj['task_id'])
PY
)

echo "[4] Get execution result"
result_resp=$(curl -s "$DISPATCHER_URL/api/execution/result/$task_id")

python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2))' <<<"$result_resp"
