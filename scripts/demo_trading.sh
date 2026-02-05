#!/bin/bash
#
# v1 Phase 6: 交易功能演示脚本
# 演示 crypto-node 的模拟交易和真实交易能力
#

set -e

CRYPTO_NODE_URL="http://127.0.0.1:8025"

echo "=============================================="
echo "v1 Phase 6: 交易功能 Demo"
echo "=============================================="
echo ""

# Step 1: 检查服务
echo "Step 1: 检查 crypto-node 服务"
echo "----------------------------------------------"
HEALTH=$(curl -s "$CRYPTO_NODE_URL/health")
echo "$HEALTH" | python3 -m json.tool
echo ""

MODE=$(echo "$HEALTH" | python3 -c "import sys, json; print(json.load(sys.stdin).get('trading_mode', 'unknown'))")
echo "当前交易模式: $MODE"
echo ""

# Step 2: 查询模拟账户余额
echo "Step 2: 查询模拟账户余额"
echo "----------------------------------------------"
curl -s "$CRYPTO_NODE_URL/api/node/paper/balance" | python3 -m json.tool
echo ""

# Step 3: 执行模拟市价买入
echo "Step 3: 执行模拟市价买入 BTC/USDT"
echo "----------------------------------------------"
echo "请求: POST /api/node/execute"
echo "参数: symbol=BTC/USDT, side=BUY, type=MARKET, quantity=0.01, price=98000"
echo ""

RESULT=$(curl -s -X POST "$CRYPTO_NODE_URL/api/node/execute" \
    -H "Content-Type: application/json" \
    -d '{
        "task_id": "demo_buy_001",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 0.01,
        "price": 98000
    }')

echo "$RESULT" | python3 -m json.tool
echo ""

# 检查结果
SUCCESS=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('success', False))" 2>/dev/null || echo "False")
if [ "$SUCCESS" = "True" ]; then
    echo "✅ 买入成功"
else
    echo "❌ 买入失败"
fi
echo ""

# Step 4: 查询更新后的余额
echo "Step 4: 查询更新后的余额"
echo "----------------------------------------------"
curl -s "$CRYPTO_NODE_URL/api/node/paper/balance" | python3 -m json.tool
echo ""

# Step 5: 执行模拟市价卖出
echo "Step 5: 执行模拟市价卖出 BTC/USDT"
echo "----------------------------------------------"
echo "参数: symbol=BTC/USDT, side=SELL, type=MARKET, quantity=0.005, price=98500"
echo ""

RESULT2=$(curl -s -X POST "$CRYPTO_NODE_URL/api/node/execute" \
    -H "Content-Type: application/json" \
    -d '{
        "task_id": "demo_sell_001",
        "symbol": "BTC/USDT",
        "side": "SELL",
        "order_type": "MARKET",
        "quantity": 0.005,
        "price": 98500
    }')

echo "$RESULT2" | python3 -m json.tool
echo ""

SUCCESS2=$(echo "$RESULT2" | python3 -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('success', False))" 2>/dev/null || echo "False")
if [ "$SUCCESS2" = "True" ]; then
    echo "✅ 卖出成功"
else
    echo "❌ 卖出失败"
fi
echo ""

# Step 6: 最终余额
echo "Step 6: 最终账户余额"
echo "----------------------------------------------"
curl -s "$CRYPTO_NODE_URL/api/node/paper/balance" | python3 -m json.tool
echo ""

# Step 7: 测试余额不足
echo "Step 7: 测试余额不足场景"
echo "----------------------------------------------"
echo "尝试买入 100 BTC（应该失败）"
echo ""

RESULT3=$(curl -s -X POST "$CRYPTO_NODE_URL/api/node/execute" \
    -H "Content-Type: application/json" \
    -d '{
        "task_id": "demo_buy_fail",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 100,
        "price": 98000
    }')

echo "$RESULT3" | python3 -m json.tool
echo ""

SUCCESS3=$(echo "$RESULT3" | python3 -c "import sys, json; print(json.load(sys.stdin).get('result', {}).get('success', False))" 2>/dev/null || echo "False")
if [ "$SUCCESS3" = "False" ]; then
    echo "✅ 正确拒绝了余额不足的订单"
else
    echo "❌ 应该拒绝但没有"
fi
echo ""

# Step 8: 重置余额
echo "Step 8: 重置模拟账户"
echo "----------------------------------------------"
curl -s -X POST "$CRYPTO_NODE_URL/api/node/paper/reset" \
    -H "Content-Type: application/json" \
    -d '{"USDT": 50000, "BTC": 1, "ETH": 10}' | python3 -m json.tool
echo ""

echo "重置后的余额:"
curl -s "$CRYPTO_NODE_URL/api/node/paper/balance" | python3 -m json.tool
echo ""

# 总结
echo "=============================================="
echo "Demo 完成"
echo "=============================================="
echo ""
echo "交易模块功能:"
echo "  - 模拟交易 (paper): 不需要 API Key，本地模拟"
echo "  - 真实交易 (live):  需要 API Key，通过 ccxt 下单"
echo ""
echo "API 端点:"
echo "  POST /api/node/execute  - 执行交易"
echo "  POST /api/node/balance  - 查询余额"
echo "  GET  /api/node/paper/balance - 查询模拟余额"
echo "  POST /api/node/paper/reset   - 重置模拟余额"
echo ""
echo "切换到真实交易:"
echo "  1. 修改 config/default.yaml: trading_mode: live"
echo "  2. 在请求中传入 api_key 和 api_secret"
echo ""
