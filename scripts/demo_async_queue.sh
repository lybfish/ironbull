#!/bin/bash
# ========================================
# IronBull v1 Phase 3 - 异步队列演示
# ========================================
# 演示内容：
# 1. 检查 Redis 连接
# 2. 提交异步执行任务
# 3. 验证幂等性（重复提交）
# 4. 查看队列状态
# 5. 启动 Worker 处理任务
# ========================================

set -e

echo "=========================================="
echo " IronBull v1 Phase 3 - 异步队列演示"
echo "=========================================="

# 服务地址
DISPATCHER_URL="http://127.0.0.1:8040"

# 检查服务
echo ""
echo "1. 检查 execution-dispatcher 服务..."
HEALTH=$(curl -s "$DISPATCHER_URL/health" 2>/dev/null || echo '{"error": "service not running"}')
echo "   响应: $HEALTH"

if echo "$HEALTH" | grep -q "error"; then
    echo "   ❌ 服务未运行！请先启动: uvicorn services.execution-dispatcher.app.main:app --host 0.0.0.0 --port 8040"
    exit 1
fi
echo "   ✅ 服务正常"

# 检查队列状态
echo ""
echo "2. 检查队列状态..."
QUEUE_STATS=$(curl -s "$DISPATCHER_URL/api/execution/queue/stats" 2>/dev/null || echo '{"error": "queue not available"}')
echo "   队列统计: $QUEUE_STATS"

if echo "$QUEUE_STATS" | grep -q "error"; then
    echo "   ⚠️  异步队列未启用（Redis 可能未运行）"
    echo "   请确保 Redis 正在运行: redis-server"
    exit 1
fi
echo "   ✅ 队列可用"

# 生成唯一 signal_id
SIGNAL_ID="sig_async_$(date +%s)"

# 提交异步任务
echo ""
echo "3. 提交异步执行任务..."
echo "   Signal ID: $SIGNAL_ID"

SUBMIT_RESP=$(curl -s -X POST "$DISPATCHER_URL/api/execution/submit-async" \
    -H "Content-Type: application/json" \
    -d "{
        \"signal_id\": \"$SIGNAL_ID\",
        \"account_id\": 1001,
        \"member_id\": 100,
        \"platform\": \"crypto\",
        \"exchange\": \"binance\",
        \"symbol\": \"BTC/USDT\",
        \"side\": \"buy\",
        \"order_type\": \"market\",
        \"quantity\": 0.01
    }")

echo "   响应: $SUBMIT_RESP"

# 检查是否成功入队
if echo "$SUBMIT_RESP" | grep -q '"queued":true'; then
    TASK_ID=$(echo "$SUBMIT_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])")
    echo "   ✅ 任务已入队: $TASK_ID"
else
    echo "   ❌ 入队失败"
    exit 1
fi

# 验证幂等性
echo ""
echo "4. 验证幂等性（重复提交相同 signal_id）..."

SUBMIT_RESP2=$(curl -s -X POST "$DISPATCHER_URL/api/execution/submit-async" \
    -H "Content-Type: application/json" \
    -d "{
        \"signal_id\": \"$SIGNAL_ID\",
        \"account_id\": 1001,
        \"member_id\": 100,
        \"platform\": \"crypto\",
        \"exchange\": \"binance\",
        \"symbol\": \"BTC/USDT\",
        \"side\": \"buy\",
        \"order_type\": \"market\",
        \"quantity\": 0.01
    }")

echo "   响应: $SUBMIT_RESP2"

if echo "$SUBMIT_RESP2" | grep -q '"queued":false'; then
    echo "   ✅ 幂等性检查生效 - 重复请求被拒绝"
else
    echo "   ⚠️  幂等性检查未生效"
fi

# 查看幂等性状态
echo ""
echo "5. 查看幂等性状态..."
IDEM_STATUS=$(curl -s "$DISPATCHER_URL/api/execution/idempotency/$SIGNAL_ID")
echo "   状态: $IDEM_STATUS"

# 查看队列状态
echo ""
echo "6. 查看队列状态（任务入队后）..."
QUEUE_STATS2=$(curl -s "$DISPATCHER_URL/api/execution/queue/stats")
echo "   队列统计: $QUEUE_STATS2"

# 提示启动 Worker
echo ""
echo "=========================================="
echo " 任务已入队！"
echo "=========================================="
echo ""
echo "下一步：启动 Worker 处理队列任务："
echo ""
echo "  cd $(pwd)"
echo "  python -m services.execution-dispatcher.app.worker"
echo ""
echo "或者在后台运行："
echo ""
echo "  nohup python -m services.execution-dispatcher.app.worker > /tmp/worker.log 2>&1 &"
echo ""
echo "=========================================="
