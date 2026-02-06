#!/usr/bin/env bash
# ============================================================
# IronBull 生产启动脚本
# 用法：
#   1. 复制 env.production.example 为 .env.production 并填入实际值
#   2. chmod +x deploy/start.sh
#   3. ./deploy/start.sh start   — 启动所有服务
#      ./deploy/start.sh stop    — 停止所有服务
#      ./deploy/start.sh restart — 重启
#      ./deploy/start.sh status  — 查看状态
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.production"
PID_DIR="${PROJECT_ROOT}/tmp/pids"
LOG_DIR="${PROJECT_ROOT}/tmp/logs"

# 加载环境变量
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
    echo "[✓] Loaded env from $ENV_FILE"
else
    echo "[!] $ENV_FILE not found, using defaults (NOT recommended for production)"
fi

export PYTHONPATH="$PROJECT_ROOT"
mkdir -p "$PID_DIR" "$LOG_DIR"

# ---- 服务定义 ----
declare -A SERVICES=(
    [data-api]="uvicorn app.main:app --host 0.0.0.0 --port 8026 --workers 2"
    [merchant-api]="uvicorn app.main:app --host 0.0.0.0 --port 8010 --workers 2"
    [signal-monitor]="python3 -m flask run --host=0.0.0.0 --port=8020"
    [monitor-daemon]="python3 scripts/monitor_daemon.py"
)

declare -A SERVICE_DIRS=(
    [data-api]="$PROJECT_ROOT/services/data-api"
    [merchant-api]="$PROJECT_ROOT/services/merchant-api"
    [signal-monitor]="$PROJECT_ROOT/services/signal-monitor"
    [monitor-daemon]="$PROJECT_ROOT"
)

start_service() {
    local name=$1
    local cmd="${SERVICES[$name]}"
    local dir="${SERVICE_DIRS[$name]}"
    local pid_file="$PID_DIR/${name}.pid"
    local log_file="$LOG_DIR/${name}.log"

    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        echo "  [skip] $name already running (pid=$(cat "$pid_file"))"
        return
    fi

    echo "  [start] $name ..."
    cd "$dir"
    nohup $cmd >> "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"
    echo "  [ok] $name started (pid=$pid, log=$log_file)"
}

stop_service() {
    local name=$1
    local pid_file="$PID_DIR/${name}.pid"

    if [ ! -f "$pid_file" ]; then
        echo "  [skip] $name not running (no pid file)"
        return
    fi

    local pid
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
        echo "  [stop] $name (pid=$pid) ..."
        kill "$pid"
        sleep 2
        # 如果还没退出，强制杀
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        echo "  [ok] $name stopped"
    else
        echo "  [skip] $name not running (stale pid)"
    fi
    rm -f "$pid_file"
}

status_service() {
    local name=$1
    local pid_file="$PID_DIR/${name}.pid"

    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        echo "  ● $name  running  (pid=$(cat "$pid_file"))"
    else
        echo "  ○ $name  stopped"
    fi
}

case "${1:-help}" in
    start)
        echo "=== Starting IronBull services ==="
        for svc in "${!SERVICES[@]}"; do
            start_service "$svc"
        done
        echo "=== Done ==="
        ;;
    stop)
        echo "=== Stopping IronBull services ==="
        for svc in "${!SERVICES[@]}"; do
            stop_service "$svc"
        done
        echo "=== Done ==="
        ;;
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
    status)
        echo "=== IronBull service status ==="
        for svc in "${!SERVICES[@]}"; do
            status_service "$svc"
        done
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
