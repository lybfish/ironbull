#!/usr/bin/env bash
# ============================================================
# IronBull 生产启动脚本
# 用法：
#   1. 复制 env.production.example 为 .env.production 并填入实际值
#   2. chmod +x deploy/start.sh
#   3. 所有服务：
#      ./deploy/start.sh start   — 启动全部
#      ./deploy/start.sh stop    — 停止全部
#      ./deploy/start.sh restart — 重启全部
#      ./deploy/start.sh status  — 查看状态
#   4. 指定服务（可选，第二个参数起为服务名）：
#      ./deploy/start.sh start data-api merchant-api
#      ./deploy/start.sh stop signal-monitor
#      ./deploy/start.sh restart data-api
# 服务名：data-api | merchant-api | signal-monitor | monitor-daemon
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
# 确保 pid 目录可写，否则 start/restart 会失败
if ! [ -w "$PID_DIR" ]; then
    echo "[!] Cannot write to $PID_DIR (permission denied). Fix: chown -R \$(whoami) $PROJECT_ROOT/tmp"
    exit 1
fi

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

# ---- 服务定义（case 实现，兼容 Bash 3.x / macOS） ----
ALL_SERVICES="data-provider data-api merchant-api signal-monitor monitor-daemon execution-node"

get_service_cmd() {
    case "$1" in
        data-provider)  echo "python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8005 --workers 1" ;;
        data-api)       echo "python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8026 --workers 2" ;;
        merchant-api)   echo "python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --workers 2" ;;
        signal-monitor) echo "python3 -m flask --app app.main run --host=0.0.0.0 --port=8020" ;;
        monitor-daemon)   echo "python3 scripts/monitor_daemon.py" ;;
        execution-node)   echo "python3 -m uvicorn app.main:app --host 0.0.0.0 --port 9101 --workers 1" ;;
        *)                echo "" ;;
    esac
}

get_service_dir() {
    case "$1" in
        data-provider)  echo "$PROJECT_ROOT/services/data-provider" ;;
        data-api)       echo "$PROJECT_ROOT/services/data-api" ;;
        merchant-api)   echo "$PROJECT_ROOT/services/merchant-api" ;;
        signal-monitor) echo "$PROJECT_ROOT/services/signal-monitor" ;;
        monitor-daemon)   echo "$PROJECT_ROOT" ;;
        execution-node)   echo "$PROJECT_ROOT/services/execution-node" ;;
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
    # 进程已死或 pid 文件陈旧：删除以便本用户能写入新 pid（避免 root 部署留下的 pid 文件导致权限错误）
    rm -f "$pid_file" 2>/dev/null || true

    # 日志文件过大时自动轮转（>200MB）
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
    nohup $cmd >> "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"

    # 等待 2 秒后验证进程是否真的存活（捕获秒退情况）
    sleep 2
    if kill -0 "$pid" 2>/dev/null; then
        echo "  [ok] $name started (pid=$pid, log=$log_file)"
    else
        echo "  [FAIL] $name exited immediately (pid=$pid was not alive after 2s)"
        echo "  --- last 15 lines of $log_file ---"
        tail -15 "$log_file" 2>/dev/null || echo "  (no log output)"
        echo "  ---"
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
