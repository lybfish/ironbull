#!/usr/bin/env bash
# ============================================================
# IronBull 生产启动脚本
# ============================================================
# 端口分配规范：
# +--------+------------------+--------------------------------+
# | 端口   | 服务              | 说明                           |
# +--------+------------------+--------------------------------+
# | 8005   | data-provider    | 交易所数据提供者                 |
# | 8010   | merchant-api     | 商家/商户管理 API               |
# | 8020   | signal-monitor   | 信号监控服务 (Flask 应用)              |
# | 8026   | data-api         | 数据 API (管理后台)             |
# | 9101   | execution-node   | 币圈执行节点                    |
# | 9102   | mt5-node         | MT5 节点 (Linux控制端)          |
# | 9103   | 预留             | mt5.aigomsg.com 反向代理用     |
# +--------+------------------+--------------------------------+
# 注意：每个服务独占一个端口，互不干扰
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

# 诊断：确认 python3 和关键模块可用
echo "[✓] Running as: $(whoami) | HOME=$HOME | python3=$(command -v python3 || echo 'NOT FOUND')"
if ! command -v python3 >/dev/null 2>&1; then
    echo "[!] python3 not found in PATH. PATH=$PATH"
    echo "    Fix: install python3, or ensure your .bash_profile adds it to PATH"
    exit 1
fi
if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo "[!] python3 found ($(command -v python3)) but 'uvicorn' module not installed"
    echo "    Fix: pip3 install uvicorn fastapi"
    exit 1
fi

# ---- 服务定义 ----
ALL_SERVICES="data-provider merchant-api signal-monitor data-api execution-node mt5-node"

get_service_cmd() {
    case "$1" in
        data-provider)    echo "python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8005 --workers 1" ;;
        merchant-api)     echo "python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --workers 2" ;;
        signal-monitor)   echo "python3 -m flask --app app.main run --host=0.0.0.0 --port=8020" ;;
        data-api)         echo "python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8026 --workers 2" ;;
        execution-node)   echo "python3 -m uvicorn app.main:app --host 0.0.0.0 --port 9101 --workers 1" ;;
        mt5-node)         echo "python3 -m uvicorn nodes.mt5-node.app.main:app --host 0.0.0.0 --port 9102 --workers 1" ;;
        *)                echo "" ;;
    esac
}

get_service_dir() {
    case "$1" in
        data-provider)    echo "$PROJECT_ROOT/services/data-provider" ;;
        merchant-api)     echo "$PROJECT_ROOT/services/merchant-api" ;;
        signal-monitor)   echo "$PROJECT_ROOT/services/signal-monitor" ;;
        data-api)         echo "$PROJECT_ROOT/services/data-api" ;;
        execution-node)   echo "$PROJECT_ROOT/services/execution-node" ;;
        mt5-node)         echo "$PROJECT_ROOT/nodes/mt5-node" ;;
        *)                echo "" ;;
    esac
}

start_service() {
    local name=$1
    local cmd
    local dir
    cmd=$(get_service_cmd "$name")
    dir=$(get_service_dir "$name")
    local pid_file="$PID_DIR/${name}.pid"
    local log_file="$LOG_DIR/${name}.log"

    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        echo "  [skip] $name already running (pid=$(cat "$pid_file"))"
        return
    fi
    rm -f "$pid_file" 2>/dev/null || true

    if [ -f "$log_file" ]; then
        local log_size
        log_size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo 0)
        if [ "$log_size" -gt 209715200 ] 2>/dev/null; then
            mv "$log_file" "${log_file}.$(date +%Y%m%d-%H%M%S).bak"
            echo "  [rotate] $name log rotated (was ${log_size} bytes)"
        fi
    fi

    echo "  [start] $name ..."
    cd "$dir"

    # 导出所有 IRONBULL_ 环境变量，确保子进程能继承
    export $(grep -E '^IRONBULL_' "$ENV_FILE" | xargs) 2>/dev/null || true

    nohup $cmd >> "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"

    sleep 2
    if kill -0 "$pid" 2>/dev/null; then
        echo "  [ok] $name started (pid=$pid, log=$log_file)"
    else
        echo "  [FAIL] $name exited immediately"
        tail -15 "$log_file" 2>/dev/null || echo "  (no log output)"
        rm -f "$pid_file"
    fi
}

stop_service() {
    local name=$1
    local pid_file="$PID_DIR/${name}.pid"

    if [ ! -f "$pid_file" ]; then
        echo "  [skip] $name not running (no pid file)"
        return
    fi

    local pid
    pid=$(cat "$pid_file" 2>/dev/null) || pid=""
    if [ -z "$pid" ]; then
        echo "  [skip] $name not running (empty pid file)"
        rm -f "$pid_file"
        return
    fi
    if kill -0 "$pid" 2>/dev/null; then
        echo "  [stop] $name (pid=$pid) ..."
        kill "$pid" 2>/dev/null || true
        sleep 2
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        echo "  [ok] $name stopped"
    else
        echo "  [skip] $name not running (stale pid $pid)"
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

# 解析：第 1 个参数为动作，第 2 个起为可选服务名；无服务名则操作全部
ACTION="${1:-help}"
shift || true
TARGET_SVC=""
if [ $# -gt 0 ]; then
    for name in "$@"; do
        if [ -n "$(get_service_cmd "$name")" ]; then
            TARGET_SVC="$TARGET_SVC $name"
        else
            echo "[!] Unknown service: $name (valid: $ALL_SERVICES)"
            exit 1
        fi
    done
    TARGET_SVC=$(echo "$TARGET_SVC" | xargs)
else
    TARGET_SVC="$ALL_SERVICES"
fi

case "$ACTION" in
    start)
        echo "=== Starting IronBull services ==="
        for svc in $TARGET_SVC; do
            start_service "$svc"
        done
        echo "=== Done ==="
        ;;
    stop)
        echo "=== Stopping IronBull services ==="
        for svc in $TARGET_SVC; do
            stop_service "$svc"
        done
        echo "=== Done ==="
        ;;
    restart)
        echo "=== Restarting IronBull services ==="
        for svc in $TARGET_SVC; do
            stop_service "$svc"
        done
        sleep 1
        for svc in $TARGET_SVC; do
            start_service "$svc"
        done
        echo "=== Done ==="
        ;;
    status)
        echo "=== IronBull service status ==="
        for svc in $TARGET_SVC; do
            status_service "$svc"
        done
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status} [service ...]"
        echo "  Services: $ALL_SERVICES"
        echo "  Example:  $0 restart"
        echo "  Example:  $0 restart data-api merchant-api"
        echo "  Note:     Run from project root; ensure tmp/pids is writable."
        exit 1
        ;;
esac
