#!/usr/bin/env bash
# Data Provider Demo
set -euo pipefail

DATA_PROVIDER_URL=${DATA_PROVIDER_URL:-http://127.0.0.1:8010}
STRATEGY_ENGINE_URL=${STRATEGY_ENGINE_URL:-http://127.0.0.1:8000}

echo "============================================================"
echo "IronBull Data Provider Demo"
echo "============================================================"

echo ""
echo "[1] Health Check"
curl -s "$DATA_PROVIDER_URL/health" | python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2))'

echo ""
echo "[2] 获取单时间周期 K 线 (BTCUSDT 15m)"
curl -s "$DATA_PROVIDER_URL/api/candles?symbol=BTCUSDT&timeframe=15m&limit=5" | python3 -c "import json,sys; data=json.loads(sys.stdin.read()); print(f\"symbol: {data['symbol']}, timeframe: {data['timeframe']}, count: {len(data['candles'])}\"); [print(f\"  {c['timestamp']} | O:{c['open']:.2f} H:{c['high']:.2f} L:{c['low']:.2f} C:{c['close']:.2f}\") for c in data['candles'][-3:]]"

echo ""
echo "[3] 获取多时间周期 K 线 (ETHUSDT 15m,1h,4h)"
curl -s "$DATA_PROVIDER_URL/api/mtf/candles?symbol=ETHUSDT&timeframes=15m,1h,4h&limit=3" | python3 -c "import json,sys; data=json.loads(sys.stdin.read()); print(f\"symbol: {data['symbol']}\"); [print(f\"  {tf}: {len(candles)} candles\") for tf, candles in data['timeframes'].items()]"

echo ""
echo "[4] 获取宏观事件"
curl -s "$DATA_PROVIDER_URL/api/macro/events?impact=high" | python3 -c "import json,sys; data=json.loads(sys.stdin.read()); print(f\"events: {len(data['events'])}\"); [print(f\"  {e['country']} | {e['title']} | {e['impact']}\") for e in data['events'][:5]]"

echo ""
echo "[5] Strategy Engine: 从 Data Provider 获取数据并运行策略"
run_resp=$(curl -s -X POST "$STRATEGY_ENGINE_URL/api/run" \
  -H 'Content-Type: application/json' \
  -d '{
    "strategy_code": "ma_cross",
    "symbol": "BTCUSDT",
    "timeframe": "15m",
    "limit": 100,
    "auto_submit": false
  }')

python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2, ensure_ascii=False))' <<<"$run_resp"

has_signal=$(python3 -c "import json; print(json.loads('''$run_resp''').get('has_signal', False))")

echo ""
echo "============================================================"
if [ "$has_signal" == "True" ]; then
    echo "✅ 检测到信号！"
else
    echo "ℹ️  无信号（正常，mock 数据可能没有形成金叉）"
fi
echo "============================================================"
