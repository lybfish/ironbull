#!/bin/bash
#
# Signal Monitor Demo - 信号监控与推送演示
#
# 使用前请先配置 Telegram:
#   1. 与 @BotFather 对话创建 Bot，获取 Token
#   2. 与 Bot 对话或将 Bot 加入群组
#   3. 访问 https://api.telegram.org/bot<TOKEN>/getUpdates 获取 Chat ID
#   4. 设置环境变量:
#      export TELEGRAM_BOT_TOKEN="your_bot_token"
#      export TELEGRAM_CHAT_ID="your_chat_id"
#   或修改 config/default.yaml

set -e

BASE_URL="http://localhost:8020"
DATA_URL="http://localhost:8010"

echo "=========================================="
echo "  IronBull Signal Monitor Demo"
echo "=========================================="
echo ""

# 检查 data-provider 服务
echo "1. 检查 data-provider 服务..."
if curl -s "$DATA_URL/health" | grep -q "ok"; then
    echo "   ✅ data-provider 服务正常"
else
    echo "   ❌ data-provider 服务未启动"
    echo "   请先启动: cd services/data-provider && PYTHONPATH=../.. python3 -m flask run --port=8010"
    exit 1
fi

# 检查 signal-monitor 服务
echo ""
echo "2. 检查 signal-monitor 服务..."
if curl -s "$BASE_URL/health" | grep -q "ok"; then
    echo "   ✅ signal-monitor 服务正常"
else
    echo "   ❌ signal-monitor 服务未启动"
    echo "   请先启动: cd services/signal-monitor && PYTHONPATH=../.. python3 -m flask run --port=8020"
    exit 1
fi

# 测试 Telegram 通知
echo ""
echo "3. 测试 Telegram 通知..."
NOTIFY_RESULT=$(curl -s -X POST "$BASE_URL/api/test-notify")
if echo "$NOTIFY_RESULT" | grep -q '"success": true'; then
    echo "   ✅ Telegram 通知测试成功"
    echo "   请检查 Telegram 是否收到消息"
else
    ERROR=$(echo "$NOTIFY_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error','未知错误'))" 2>/dev/null || echo "未知错误")
    echo "   ❌ Telegram 通知失败: $ERROR"
    echo ""
    echo "   请检查配置:"
    echo "   - 环境变量 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID"
    echo "   - 或 config/default.yaml 中的 telegram_* 配置"
    echo ""
    read -p "   是否继续演示? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 立即检测信号
echo ""
echo "4. 立即检测 ETH/USDT 信号..."
SIGNAL_RESULT=$(curl -s -X POST "$BASE_URL/api/check-now" \
    -H "Content-Type: application/json" \
    -d '{
        "strategy": "market_regime",
        "symbol": "ETHUSDT",
        "timeframe": "1h",
        "config": {"atr_mult_sl": 1.5, "atr_mult_tp": 3.0},
        "notify": true
    }')

if echo "$SIGNAL_RESULT" | grep -q '"signal": {'; then
    echo "   🚨 检测到信号!"
    echo "$SIGNAL_RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
s = d.get('signal', {})
if s:
    print(f\"   方向: {s.get('side')}  价格: {s.get('entry_price'):.2f}\")
    print(f\"   止损: {s.get('stop_loss'):.2f}  止盈: {s.get('take_profit'):.2f}\")
    print(f\"   置信度: {s.get('confidence')}%\")
"
    echo "   ✅ 信号已推送到 Telegram"
else
    echo "   ℹ️  当前无交易信号"
fi

# 显示当前配置
echo ""
echo "5. 当前监控配置:"
curl -s "$BASE_URL/api/config" | python3 -c "
import sys, json
d = json.load(sys.stdin)
c = d.get('config', {})
print(f\"   检测间隔: {c.get('interval_seconds', 300)}秒\")
print(f\"   最低置信度: {c.get('min_confidence', 50)}%\")
print(f\"   冷却时间: {c.get('cooldown_minutes', 60)}分钟\")
print(f\"   策略配置:\")
for s in c.get('strategies', []):
    symbols = ', '.join(s.get('symbols', []))
    print(f\"     - {s.get('code')}: {symbols} ({s.get('timeframe')})\")
"

# 启动监控
echo ""
echo "6. 启动信号监控..."
START_RESULT=$(curl -s -X POST "$BASE_URL/api/start")
if echo "$START_RESULT" | grep -q '"success": true'; then
    echo "   ✅ 监控已启动"
else
    ERROR=$(echo "$START_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error',''))" 2>/dev/null)
    echo "   ℹ️  $ERROR"
fi

# 显示状态
echo ""
echo "7. 监控状态:"
curl -s "$BASE_URL/api/status" | python3 -c "
import sys, json
d = json.load(sys.stdin)
state = d.get('state', {})
print(f\"   运行中: {'是' if state.get('running') else '否'}\")
print(f\"   检测次数: {state.get('total_checks', 0)}\")
print(f\"   信号次数: {state.get('total_signals', 0)}\")
print(f\"   上次检测: {state.get('last_check', '无')}\")
"

echo ""
echo "=========================================="
echo "  演示完成!"
echo "=========================================="
echo ""
echo "后续操作:"
echo "  - 查看状态: curl $BASE_URL/api/status"
echo "  - 停止监控: curl -X POST $BASE_URL/api/stop"
echo "  - 修改配置: curl -X POST $BASE_URL/api/config -d '{...}'"
echo ""
echo "修改监控配置示例:"
echo "  curl -X POST $BASE_URL/api/config -H 'Content-Type: application/json' -d '{"
echo "    \"interval_seconds\": 180,"
echo "    \"strategies\": [{"
echo "      \"code\": \"market_regime\","
echo "      \"config\": {\"atr_mult_sl\": 2.0, \"atr_mult_tp\": 4.0},"
echo "      \"symbols\": [\"BTCUSDT\", \"ETHUSDT\", \"SOLUSDT\"],"
echo "      \"timeframe\": \"15m\""
echo "    }]"
echo "  }'"
echo ""
