#!/bin/bash
# ============================================================
# IronBull Strategy Runner Demo
# 演示策略定时运行功能
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服务端口
DATA_PROVIDER_PORT=8010
SIGNAL_HUB_PORT=8001
STRATEGY_RUNNER_PORT=8020

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}IronBull Strategy Runner Demo${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# 检查依赖服务
echo -e "${YELLOW}[1] 检查依赖服务...${NC}"

check_service() {
    local name=$1
    local port=$2
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $name (port $port) - running"
        return 0
    else
        echo -e "  ${RED}✗${NC} $name (port $port) - not running"
        return 1
    fi
}

MISSING_SERVICES=0

if ! check_service "data-provider" $DATA_PROVIDER_PORT; then
    MISSING_SERVICES=1
fi

if ! check_service "signal-hub" $SIGNAL_HUB_PORT; then
    MISSING_SERVICES=1
fi

if [ $MISSING_SERVICES -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}请先启动依赖服务:${NC}"
    echo "  cd $PROJECT_ROOT"
    echo "  PYTHONPATH=. python3 services/data-provider/app/main.py &"
    echo "  PYTHONPATH=. python3 services/signal-hub/app/main.py &"
    echo ""
    echo -e "${YELLOW}然后再运行此脚本。${NC}"
    exit 1
fi

echo ""

# 启动 strategy-runner（如果未运行）
echo -e "${YELLOW}[2] 检查 strategy-runner 服务...${NC}"
if ! check_service "strategy-runner" $STRATEGY_RUNNER_PORT; then
    echo -e "  ${YELLOW}→${NC} 启动 strategy-runner..."
    cd "$PROJECT_ROOT"
    PYTHONPATH=. python3 services/strategy-runner/app/main.py &
    RUNNER_PID=$!
    sleep 2
    
    if ! check_service "strategy-runner" $STRATEGY_RUNNER_PORT; then
        echo -e "  ${RED}✗${NC} 启动失败"
        exit 1
    fi
fi
echo ""

# 获取可用策略
echo -e "${YELLOW}[3] 获取可用策略列表...${NC}"
STRATEGIES=$(curl -s "http://localhost:$STRATEGY_RUNNER_PORT/api/strategies" | python3 -m json.tool 2>/dev/null || echo "{}")
echo "$STRATEGIES" | head -20
echo ""

# 创建策略任务
echo -e "${YELLOW}[4] 创建策略任务...${NC}"

# 任务 1: MA Cross 策略
echo -e "  ${BLUE}→${NC} 创建 MA Cross 任务..."
curl -s -X POST "http://localhost:$STRATEGY_RUNNER_PORT/api/tasks" \
    -H "Content-Type: application/json" \
    -d '{
        "task_id": "task_ma_cross_btc",
        "strategy_code": "ma_cross",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "interval_seconds": 30,
        "candle_limit": 100,
        "auto_submit": true
    }' | python3 -m json.tool
echo ""

# 任务 2: RSI Boll 策略
echo -e "  ${BLUE}→${NC} 创建 RSI Boll 任务..."
curl -s -X POST "http://localhost:$STRATEGY_RUNNER_PORT/api/tasks" \
    -H "Content-Type: application/json" \
    -d '{
        "task_id": "task_rsi_boll_eth",
        "strategy_code": "rsi_boll",
        "symbol": "ETHUSDT",
        "timeframe": "1h",
        "interval_seconds": 60,
        "candle_limit": 100,
        "auto_submit": true
    }' | python3 -m json.tool
echo ""

# 任务 3: MACD 策略
echo -e "  ${BLUE}→${NC} 创建 MACD 任务..."
curl -s -X POST "http://localhost:$STRATEGY_RUNNER_PORT/api/tasks" \
    -H "Content-Type: application/json" \
    -d '{
        "task_id": "task_macd_btc",
        "strategy_code": "macd",
        "symbol": "BTCUSDT",
        "timeframe": "4h",
        "interval_seconds": 120,
        "candle_limit": 100,
        "auto_submit": true
    }' | python3 -m json.tool
echo ""

# 列出所有任务
echo -e "${YELLOW}[5] 列出所有任务...${NC}"
curl -s "http://localhost:$STRATEGY_RUNNER_PORT/api/tasks" | python3 -m json.tool
echo ""

# 手动运行一次任务
echo -e "${YELLOW}[6] 手动运行任务 (task_ma_cross_btc)...${NC}"
curl -s -X POST "http://localhost:$STRATEGY_RUNNER_PORT/api/tasks/task_ma_cross_btc/run" | python3 -m json.tool
echo ""

echo -e "${YELLOW}[7] 手动运行任务 (task_rsi_boll_eth)...${NC}"
curl -s -X POST "http://localhost:$STRATEGY_RUNNER_PORT/api/tasks/task_rsi_boll_eth/run" | python3 -m json.tool
echo ""

# 启动 Runner 调度循环
echo -e "${YELLOW}[8] 启动 Runner 调度循环...${NC}"
curl -s -X POST "http://localhost:$STRATEGY_RUNNER_PORT/api/runner/start" | python3 -m json.tool
echo ""

# 等待几秒让 Runner 运行
echo -e "${YELLOW}[9] 等待 5 秒让 Runner 运行...${NC}"
sleep 5
echo ""

# 获取统计信息
echo -e "${YELLOW}[10] 获取运行统计...${NC}"
curl -s "http://localhost:$STRATEGY_RUNNER_PORT/api/runner/stats" | python3 -m json.tool
echo ""

# 停止 Runner
echo -e "${YELLOW}[11] 停止 Runner...${NC}"
curl -s -X POST "http://localhost:$STRATEGY_RUNNER_PORT/api/runner/stop" | python3 -m json.tool
echo ""

# 最终状态
echo -e "${YELLOW}[12] 最终任务状态...${NC}"
curl -s "http://localhost:$STRATEGY_RUNNER_PORT/api/tasks" | python3 -m json.tool
echo ""

echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}Demo 完成!${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "你可以继续使用以下 API:"
echo -e "  ${YELLOW}GET${NC}  http://localhost:$STRATEGY_RUNNER_PORT/api/strategies  - 获取策略列表"
echo -e "  ${YELLOW}POST${NC} http://localhost:$STRATEGY_RUNNER_PORT/api/tasks       - 创建任务"
echo -e "  ${YELLOW}GET${NC}  http://localhost:$STRATEGY_RUNNER_PORT/api/tasks       - 列出任务"
echo -e "  ${YELLOW}POST${NC} http://localhost:$STRATEGY_RUNNER_PORT/api/tasks/{id}/run - 手动运行"
echo -e "  ${YELLOW}POST${NC} http://localhost:$STRATEGY_RUNNER_PORT/api/runner/start   - 启动调度"
echo -e "  ${YELLOW}POST${NC} http://localhost:$STRATEGY_RUNNER_PORT/api/runner/stop    - 停止调度"
echo -e "  ${YELLOW}GET${NC}  http://localhost:$STRATEGY_RUNNER_PORT/api/runner/stats   - 运行统计"
