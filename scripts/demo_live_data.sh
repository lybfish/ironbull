#!/bin/bash
# ========================================
# IronBull v1 Phase 5 - 真实数据演示
# ========================================
# 演示内容：
# 1. 检查数据源配置
# 2. 获取 mock K 线数据
# 3. 获取真实 K 线数据（Binance）
# 4. 获取最新行情
# 5. 比较 mock 和 live 数据
# ========================================

set -e

echo "=========================================="
echo " IronBull v1 Phase 5 - 真实数据演示"
echo "=========================================="

DATA_URL="http://127.0.0.1:8010"

# 检查服务
echo ""
echo "1. 检查 data-provider 服务..."
HEALTH=$(curl -s "$DATA_URL/health" 2>/dev/null || echo '{"error": "not running"}')
echo "   响应: $HEALTH"

if echo "$HEALTH" | grep -q "error"; then
    echo "   ❌ 服务未运行！请先启动 data-provider 服务"
    exit 1
fi
echo "   ✅ 服务正常"

# 检查数据源配置
echo ""
echo "2. 检查数据源配置..."
SOURCE=$(curl -s "$DATA_URL/api/source")
echo "   配置: $SOURCE"

# 获取支持的交易所
echo ""
echo "3. 获取支持的交易所..."
EXCHANGES=$(curl -s "$DATA_URL/api/exchanges")
echo "   交易所: $EXCHANGES"

# 获取 mock 数据
echo ""
echo "4. 获取 mock K 线数据 (BTC/USDT, 15m, 5条)..."
MOCK_DATA=$(curl -s "$DATA_URL/api/candles?symbol=BTC/USDT&timeframe=15m&limit=5&source=mock")
echo "   Mock 数据:"
echo "$MOCK_DATA" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data['candles'][-3:]:
    print(f\"    {c['timestamp']}: O={c['open']:.2f} H={c['high']:.2f} L={c['low']:.2f} C={c['close']:.2f}\")
"

# 获取真实数据
echo ""
echo "5. 获取真实 K 线数据 (BTC/USDT, 15m, 5条)..."
LIVE_DATA=$(curl -s "$DATA_URL/api/candles?symbol=BTC/USDT&timeframe=15m&limit=5&source=live" 2>/dev/null)

if echo "$LIVE_DATA" | grep -q "candles"; then
    echo "   真实数据:"
    echo "$LIVE_DATA" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data['candles'][-3:]:
    print(f\"    {c['timestamp']}: O={c['open']:.2f} H={c['high']:.2f} L={c['low']:.2f} C={c['close']:.2f}\")
"
    echo "   ✅ 真实数据获取成功"
else
    echo "   ⚠️ 真实数据获取失败，响应: $LIVE_DATA"
fi

# 获取最新行情
echo ""
echo "6. 获取最新行情 (BTC/USDT)..."
TICKER=$(curl -s "$DATA_URL/api/ticker?symbol=BTC/USDT" 2>/dev/null)

if echo "$TICKER" | grep -q "last"; then
    echo "   行情数据:"
    echo "$TICKER" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"    Symbol: {data['symbol']}\")
print(f\"    Last: {data['last']:.2f}\")
print(f\"    Bid: {data['bid']:.2f}\")
print(f\"    Ask: {data['ask']:.2f}\")
print(f\"    Volume 24h: {data['volume_24h']:.2f}\")
"
    echo "   ✅ 行情获取成功"
else
    echo "   ⚠️ 行情获取失败，响应: $TICKER"
fi

# 测试其他交易对
echo ""
echo "7. 测试其他交易对 (ETH/USDT)..."
ETH_DATA=$(curl -s "$DATA_URL/api/candles?symbol=ETH/USDT&timeframe=1h&limit=3&source=live" 2>/dev/null)

if echo "$ETH_DATA" | grep -q "candles"; then
    echo "   ETH/USDT 数据:"
    echo "$ETH_DATA" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data['candles']:
    print(f\"    {c['timestamp']}: O={c['open']:.2f} H={c['high']:.2f} L={c['low']:.2f} C={c['close']:.2f}\")
"
    echo "   ✅ ETH 数据获取成功"
else
    echo "   ⚠️ ETH 数据获取失败"
fi

echo ""
echo "=========================================="
echo " 真实数据演示完成"
echo "=========================================="
echo ""
echo "已验证功能："
echo "  - Mock 数据获取: ✅"
echo "  - 真实 K 线数据 (Binance): 见上方结果"
echo "  - 最新行情: 见上方结果"
echo ""
echo "切换数据源："
echo "  - 使用 ?source=mock 获取模拟数据"
echo "  - 使用 ?source=live 获取真实数据"
echo "  - 或修改 config/default.yaml 中的 data_source"
echo "=========================================="
