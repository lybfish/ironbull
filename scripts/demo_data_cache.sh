#!/bin/bash
#
# v1 Phase 5: 数据缓存演示脚本
# 验证 Redis 缓存层对 K 线数据的缓存效果
#

set -e

DATA_PROVIDER_URL="http://127.0.0.1:8010"
SYMBOL="BTC/USDT"
TIMEFRAME="15m"

echo "=============================================="
echo "v1 Phase 5: 数据缓存层 Demo"
echo "=============================================="
echo ""

# Step 1: 检查服务健康
echo "Step 1: 检查 data-provider 服务"
echo "----------------------------------------------"
HEALTH=$(curl -s "$DATA_PROVIDER_URL/health")
echo "健康检查响应: $HEALTH"

CACHE_ENABLED=$(echo "$HEALTH" | python3 -c "import sys, json; print(json.load(sys.stdin).get('cache_enabled', False))")
echo ""
echo "缓存状态: $CACHE_ENABLED"
echo ""

if [ "$CACHE_ENABLED" != "True" ]; then
    echo "⚠️  缓存未启用，请检查 Redis 连接"
    echo "继续测试 mock 数据..."
fi
echo ""

# Step 2: 清除缓存（如果存在）
echo "Step 2: 清除现有缓存"
echo "----------------------------------------------"
curl -s -X DELETE "$DATA_PROVIDER_URL/api/cache?symbol=$SYMBOL&timeframe=$TIMEFRAME" | python3 -m json.tool
echo ""

# Step 3: 首次获取数据（缓存未命中）
echo "Step 3: 首次获取 Live K 线数据（缓存未命中）"
echo "----------------------------------------------"
echo "请求: GET /api/candles?symbol=$SYMBOL&timeframe=$TIMEFRAME&limit=50&source=live"

START_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")
curl -s "$DATA_PROVIDER_URL/api/candles?symbol=$SYMBOL&timeframe=$TIMEFRAME&limit=50&source=live" > /tmp/candles_first.json
END_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")

FIRST_TIME=$((END_TIME - START_TIME))
FIRST_COUNT=$(python3 -c "import json; data=json.load(open('/tmp/candles_first.json')); print(len(data.get('candles', [])))")

echo "首次请求耗时: ${FIRST_TIME}ms"
echo "返回 K 线数量: $FIRST_COUNT"
echo ""

# Step 4: 检查缓存状态
echo "Step 4: 检查缓存状态"
echo "----------------------------------------------"
curl -s "$DATA_PROVIDER_URL/api/cache/stats?symbol=$SYMBOL&timeframe=$TIMEFRAME" | python3 -m json.tool
echo ""

# Step 5: 第二次获取数据（期望缓存命中）
echo "Step 5: 第二次获取 K 线数据（期望缓存命中）"
echo "----------------------------------------------"
echo "请求: GET /api/candles?symbol=$SYMBOL&timeframe=$TIMEFRAME&limit=50&source=live"

START_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")
curl -s "$DATA_PROVIDER_URL/api/candles?symbol=$SYMBOL&timeframe=$TIMEFRAME&limit=50&source=live" > /tmp/candles_second.json
END_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")

SECOND_TIME=$((END_TIME - START_TIME))
SECOND_COUNT=$(python3 -c "import json; data=json.load(open('/tmp/candles_second.json')); print(len(data.get('candles', [])))")

echo "第二次请求耗时: ${SECOND_TIME}ms"
echo "返回 K 线数量: $SECOND_COUNT"
echo ""

# Step 6: 跳过缓存请求
echo "Step 6: 使用 no_cache=true 跳过缓存"
echo "----------------------------------------------"
echo "请求: GET /api/candles?symbol=$SYMBOL&timeframe=$TIMEFRAME&limit=50&source=live&no_cache=true"

START_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")
curl -s "$DATA_PROVIDER_URL/api/candles?symbol=$SYMBOL&timeframe=$TIMEFRAME&limit=50&source=live&no_cache=true" > /tmp/candles_nocache.json
END_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")

NO_CACHE_TIME=$((END_TIME - START_TIME))
echo "跳过缓存请求耗时: ${NO_CACHE_TIME}ms"
echo ""

# Step 7: 测试不同时间周期
echo "Step 7: 测试不同时间周期缓存 TTL"
echo "----------------------------------------------"
for tf in "1m" "5m" "15m" "1h" "4h" "1d"; do
    curl -s "$DATA_PROVIDER_URL/api/candles?symbol=$SYMBOL&timeframe=$tf&limit=10&source=live" > /dev/null
    STATS=$(curl -s "$DATA_PROVIDER_URL/api/cache/stats?symbol=$SYMBOL&timeframe=$tf")
    TTL=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('ttl', 'N/A'))")
    COUNT=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))")
    echo "$tf: count=$COUNT, ttl=${TTL}s"
done
echo ""

# Step 8: 数据源配置
echo "Step 8: 查看数据源配置"
echo "----------------------------------------------"
curl -s "$DATA_PROVIDER_URL/api/source" | python3 -m json.tool
echo ""

# 总结
echo "=============================================="
echo "测试总结"
echo "=============================================="
echo ""
echo "首次请求（缓存未命中）: ${FIRST_TIME}ms"
echo "第二次请求（缓存命中）: ${SECOND_TIME}ms"
echo "跳过缓存请求:          ${NO_CACHE_TIME}ms"
echo ""

if [ "$CACHE_ENABLED" = "True" ]; then
    if [ $SECOND_TIME -lt $FIRST_TIME ]; then
        SPEEDUP=$(python3 -c "print(f'{$FIRST_TIME / max($SECOND_TIME, 1):.1f}x')")
        echo "✅ 缓存效果明显，加速约 $SPEEDUP"
    else
        echo "⚠️  缓存加速不明显（可能网络延迟波动）"
    fi
else
    echo "⚠️  缓存未启用，请检查 Redis"
fi

echo ""
echo "=============================================="
echo "Demo 完成"
echo "=============================================="
