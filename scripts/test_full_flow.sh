#!/usr/bin/env bash
# ============================================================
# IronBull 全流程集成测试
#
# 用法：
#   bash scripts/test_full_flow.sh              # 全部 Layer
#   bash scripts/test_full_flow.sh --layer 1    # 仅 Layer 1
#   bash scripts/test_full_flow.sh --layer 2    # 仅 Layer 2
#   bash scripts/test_full_flow.sh --layer 3    # 仅 Layer 3
#   bash scripts/test_full_flow.sh --layer 5    # 仅 Layer 5 (dry-run)
# ============================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

# 加载 .env.local（若存在）
if [ -f "$ROOT/.env.local" ]; then
    set -a
    source "$ROOT/.env.local"
    set +a
fi

# DB 密码（Docker MySQL 默认）
export IRONBULL_DB_PASSWORD="${IRONBULL_DB_PASSWORD:-root123456}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
BOLD='\033[1m'

PASS=0
FAIL=0
SKIP=0

pass() { ((PASS++)); echo -e "  ${GREEN}✓${NC} $1"; }
fail() { ((FAIL++)); echo -e "  ${RED}✗${NC} $1"; }
skip() { ((SKIP++)); echo -e "  ${YELLOW}⊘${NC} $1 (skipped)"; }
header() { echo -e "\n${BOLD}══════ $1 ══════${NC}"; }

# 解析参数
LAYER="${2:-all}"
if [[ "${1:-}" == "--layer" ]]; then
    LAYER="$2"
fi

check_health() {
    local name="$1" url="$2"
    if curl -sf --max-time 3 "$url" > /dev/null 2>&1; then
        pass "$name health OK ($url)"
        return 0
    else
        fail "$name health FAIL ($url)"
        return 1
    fi
}

# ============================================================
# Layer 1: 模型/导入/数据库验证 (pytest)
# ============================================================
run_layer1() {
    header "Layer 1: 模型/导入/数据库验证"

    if python3 -m pytest tests/test_integration.py -v --tb=short \
        -k "TestLayer1" --no-header -q 2>&1; then
        pass "Layer 1 pytest 全部通过"
    else
        fail "Layer 1 pytest 有失败项（见上方输出）"
    fi
}

# ============================================================
# Layer 2: 服务健康检查
# ============================================================
run_layer2() {
    header "Layer 2: 服务健康检查"

    check_health "data-api"       "http://127.0.0.1:8026/health"
    check_health "merchant-api"   "http://127.0.0.1:8010/health"
    check_health "signal-monitor" "http://127.0.0.1:8020/health"
    check_health "data-provider"  "http://127.0.0.1:8005/health"
    check_health "execution-node" "http://127.0.0.1:9101/health"
}

# ============================================================
# Layer 3: API 端点测试 (pytest, 需服务运行)
# ============================================================
run_layer3() {
    header "Layer 3: API 端点测试"

    # 先检查 data-api 是否可用
    if ! curl -sf --max-time 3 "http://127.0.0.1:8026/health" > /dev/null 2>&1; then
        skip "Layer 3: data-api 未运行，跳过 API 测试"
        return
    fi

    if python3 -m pytest tests/test_integration.py -v --tb=short \
        -k "TestLayer3" --no-header -q 2>&1; then
        pass "Layer 3 API 测试全部通过"
    else
        fail "Layer 3 API 测试有失败项（见上方输出）"
    fi
}

# ============================================================
# Layer 4: 信号分发流程验证
# ============================================================
run_layer4() {
    header "Layer 4: 信号分发流程验证"

    # 检查 signal-monitor
    if ! curl -sf --max-time 3 "http://127.0.0.1:8020/health" > /dev/null 2>&1; then
        skip "Layer 4: signal-monitor 未运行"
        return
    fi

    # 测试 /api/status（验证 monitor_config 已清除）
    STATUS=$(curl -sf --max-time 5 "http://127.0.0.1:8020/api/status" 2>&1)
    if echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'config' in d" 2>/dev/null; then
        pass "signal-monitor /api/status 正常"
    else
        fail "signal-monitor /api/status 异常: $STATUS"
    fi

    # 测试 /api/config（验证策略从 DB 加载）
    CONFIG=$(curl -sf --max-time 5 "http://127.0.0.1:8020/api/config" 2>&1)
    if echo "$CONFIG" | python3 -c "
import sys, json
d = json.load(sys.stdin)
strats = d.get('config', {}).get('strategies', [])
assert len(strats) >= 1, 'no strategies loaded'
print(f'  loaded {len(strats)} strategies from DB')
" 2>&1; then
        pass "signal-monitor 从数据库加载策略成功"
    else
        fail "signal-monitor 策略加载异常: $CONFIG"
    fi

    # 测试 /api/check-now（需要 data-provider）
    if curl -sf --max-time 3 "http://127.0.0.1:8005/health" > /dev/null 2>&1; then
        CHECK=$(curl -sf --max-time 15 -X POST \
            -H "Content-Type: application/json" \
            -d '{"symbol":"BTCUSDT","strategy":"market_regime","notify":false}' \
            "http://127.0.0.1:8020/api/check-now" 2>&1)
        if echo "$CHECK" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('success') is True" 2>/dev/null; then
            pass "signal-monitor /api/check-now 正常"
        else
            fail "signal-monitor /api/check-now 异常: $CHECK"
        fi
    else
        skip "Layer 4: data-provider 未运行，跳过 check-now"
    fi
}

# ============================================================
# Layer 5: 实盘交易 dry-run
# ============================================================
run_layer5() {
    header "Layer 5: 实盘交易 dry-run"

    # 确保有 exchange 配置
    if ! python3 -c "
from libs.core import get_config
c = get_config()
key = c.get_str('exchange_api_key')
assert key, 'no api key'
" 2>/dev/null; then
        skip "Layer 5: 未配置交易所 API key"
        return
    fi

    # 读取当前配置的交易所
    EXCHANGE=$(python3 -c "
from libs.core import get_config
c = get_config()
print(c.get_str('exchange_name', 'binance'))
" 2>/dev/null || echo "unknown")

    echo -e "  当前交易所: ${BOLD}$EXCHANGE${NC}"

    # dry-run: 仅查余额和持仓
    if python3 scripts/live_small_test.py --real --yes --dry-run --exchange "$EXCHANGE" 2>&1; then
        pass "$EXCHANGE dry-run 通过（余额/持仓查询正常）"
    else
        fail "$EXCHANGE dry-run 失败"
    fi
}

# ============================================================
# 汇总
# ============================================================
summary() {
    header "测试汇总"
    echo -e "  ${GREEN}通过: $PASS${NC}  ${RED}失败: $FAIL${NC}  ${YELLOW}跳过: $SKIP${NC}"
    if [ "$FAIL" -gt 0 ]; then
        echo -e "\n  ${RED}有 $FAIL 项测试失败！${NC}"
        exit 1
    else
        echo -e "\n  ${GREEN}全部测试通过！${NC}"
    fi
}

# ============================================================
# 执行
# ============================================================
echo -e "${BOLD}IronBull 全流程集成测试${NC}"
echo "工作目录: $ROOT"

case "$LAYER" in
    1) run_layer1 ;;
    2) run_layer2 ;;
    3) run_layer3 ;;
    4) run_layer4 ;;
    5) run_layer5 ;;
    all)
        run_layer1
        run_layer2
        run_layer3
        run_layer4
        run_layer5
        ;;
    *)
        echo "用法: $0 [--layer 1|2|3|4|5|all]"
        exit 1
        ;;
esac

summary
