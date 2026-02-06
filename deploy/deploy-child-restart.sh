#!/usr/bin/env bash
# ============================================================
# 仅重启子服务器上的执行节点（不构建、不同步）
# 用法: make deploy-child-restart [NAME=node1]
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_NAME="${1:-default}"
CONFIG_FILE="$SCRIPT_DIR/.deploy.child-$CONFIG_NAME.env"
NAME="${NAME:-}"
[[ -n "$NAME" ]] && CONFIG_NAME="$NAME" && CONFIG_FILE="$SCRIPT_DIR/.deploy.child-$CONFIG_NAME.env"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "未找到配置: $CONFIG_FILE"
    echo "请先执行: make deploy-child-setup 或 make deploy-child-setup NAME=$CONFIG_NAME"
    exit 1
fi

source "$CONFIG_FILE"
PORT="${CHILD_UVICORN_PORT:-9101}"

ssh -p "${CHILD_SSH_PORT:-22}" "$CHILD_USER@$CHILD_HOST" "
cd $CHILD_PATH
pkill -f 'uvicorn app.main:app' 2>/dev/null || true
sleep 2
nohup env PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port $PORT >> node.log 2>&1 &
sleep 1
echo 'Restart done.'
"
echo "子机节点已重启: http://$CHILD_HOST:$PORT"
