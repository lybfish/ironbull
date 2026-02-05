#!/bin/bash
# ========================================
# IronBull v1 Phase 4 - 风控规则演示
# ========================================
# 演示内容：
# 1. 查看风控规则列表
# 2. 测试正常通过的风控检查
# 3. 测试余额不足被拒绝
# 4. 测试持仓数量超限被拒绝
# 5. 启用/禁用规则
# ========================================

set -e

echo "=========================================="
echo " IronBull v1 Phase 4 - 风控规则演示"
echo "=========================================="

RISK_URL="http://127.0.0.1:8020"

# 检查服务
echo ""
echo "1. 检查 risk-control 服务..."
HEALTH=$(curl -s "$RISK_URL/health" 2>/dev/null || echo '{"error": "not running"}')
echo "   响应: $HEALTH"

if echo "$HEALTH" | grep -q "error"; then
    echo "   ❌ 服务未运行！请先启动 risk-control 服务"
    exit 1
fi
echo "   ✅ 服务正常"

# 查看风控规则
echo ""
echo "2. 查看风控规则列表..."
RULES=$(curl -s "$RISK_URL/api/risk/rules")
echo "   规则列表:"
echo "$RULES" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data.get('rules', []):
    status = '✅' if r['enabled'] else '❌'
    print(f\"    {status} {r['name']} ({r['code']})\")
"

# 测试正常通过
echo ""
echo "3. 测试正常风控检查（余额充足）..."
RESULT=$(curl -s -X POST "$RISK_URL/api/risk/check" \
    -H "Content-Type: application/json" \
    -d '{
        "signal": {
            "signal_id": "sig_risk_test_001",
            "strategy_code": "ma_cross",
            "symbol": "BTC/USDT",
            "canonical_symbol": "BTCUSDT",
            "side": "buy",
            "signal_type": "entry",
            "entry_price": 50000,
            "quantity": 0.01
        },
        "account": {
            "account_id": 1001,
            "member_id": 100,
            "balance": 10000,
            "available": 8000,
            "frozen": 2000
        }
    }')

PASSED=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['passed'])")
if [ "$PASSED" = "True" ]; then
    echo "   ✅ 风控通过"
else
    REASON=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['result'].get('reject_reason', 'unknown'))")
    echo "   ❌ 风控拒绝: $REASON"
fi

# 测试余额不足
echo ""
echo "4. 测试余额不足（available < 100）..."
RESULT=$(curl -s -X POST "$RISK_URL/api/risk/check" \
    -H "Content-Type: application/json" \
    -d '{
        "signal": {
            "signal_id": "sig_risk_test_002",
            "strategy_code": "ma_cross",
            "symbol": "BTC/USDT",
            "canonical_symbol": "BTCUSDT",
            "side": "buy",
            "signal_type": "entry",
            "entry_price": 50000,
            "quantity": 0.01
        },
        "account": {
            "account_id": 1002,
            "member_id": 100,
            "balance": 100,
            "available": 50,
            "frozen": 50
        }
    }')

PASSED=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['passed'])")
if [ "$PASSED" = "False" ]; then
    REASON=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['result'].get('reject_reason', 'unknown'))")
    echo "   ✅ 正确拒绝: $REASON"
else
    echo "   ⚠️ 应该被拒绝但通过了"
fi

# 测试仓位价值超限
echo ""
echo "5. 测试仓位价值超限（quantity * price > 50000）..."
RESULT=$(curl -s -X POST "$RISK_URL/api/risk/check" \
    -H "Content-Type: application/json" \
    -d '{
        "signal": {
            "signal_id": "sig_risk_test_003",
            "strategy_code": "ma_cross",
            "symbol": "BTC/USDT",
            "canonical_symbol": "BTCUSDT",
            "side": "buy",
            "signal_type": "entry",
            "entry_price": 50000,
            "quantity": 1.5
        },
        "account": {
            "account_id": 1003,
            "member_id": 100,
            "balance": 100000,
            "available": 80000,
            "frozen": 20000
        }
    }')

PASSED=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['passed'])")
if [ "$PASSED" = "False" ]; then
    REASON=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['result'].get('reject_reason', 'unknown'))")
    echo "   ✅ 正确拒绝: $REASON"
else
    echo "   ⚠️ 应该被拒绝但通过了"
fi

# 测试禁用规则
echo ""
echo "6. 测试禁用 min_balance 规则..."
curl -s -X POST "$RISK_URL/api/risk/rules/min_balance/disable" > /dev/null

echo "   重新测试余额不足..."
RESULT=$(curl -s -X POST "$RISK_URL/api/risk/check" \
    -H "Content-Type: application/json" \
    -d '{
        "signal": {
            "signal_id": "sig_risk_test_004",
            "strategy_code": "ma_cross",
            "symbol": "BTC/USDT",
            "canonical_symbol": "BTCUSDT",
            "side": "buy",
            "signal_type": "entry",
            "entry_price": 50000,
            "quantity": 0.01
        },
        "account": {
            "account_id": 1004,
            "member_id": 100,
            "balance": 100,
            "available": 50,
            "frozen": 50
        }
    }')

PASSED=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['passed'])")
if [ "$PASSED" = "True" ]; then
    echo "   ✅ 规则禁用后通过了"
else
    echo "   ⚠️ 规则禁用后仍被拒绝"
fi

# 重新启用规则
echo ""
echo "7. 重新启用 min_balance 规则..."
curl -s -X POST "$RISK_URL/api/risk/rules/min_balance/enable" > /dev/null
echo "   ✅ 规则已启用"

echo ""
echo "=========================================="
echo " 风控规则演示完成"
echo "=========================================="
echo ""
echo "已验证的规则："
echo "  - MinBalanceRule: 最小余额检查"
echo "  - MaxPositionValueRule: 单仓最大价值"
echo "  - 规则启用/禁用"
echo ""
echo "其他可用规则（需要历史数据支持）："
echo "  - MaxPositionRule: 最大持仓数量"
echo "  - DailyTradeLimitRule: 每日交易限额"
echo "  - DailyLossLimitRule: 每日亏损限额"
echo "  - ConsecutiveLossCooldownRule: 连续亏损冷却"
echo "  - TradeCooldownRule: 交易间隔冷却"
echo "=========================================="
