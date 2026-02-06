#!/usr/bin/env bash
# ============================================================
# 仅批量重启所有子服务器上的执行节点（不构建、不同步）
# 用法: make deploy-child-batch-restart
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/.deploy.child-batch.env"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "未找到配置: $CONFIG_FILE"
    echo "请先执行: make deploy-child-batch-setup"
    exit 1
fi

source "$CONFIG_FILE"
PORT="${CHILD_UVICORN_PORT:-9101}"

for CHILD_HOST in $CHILD_HOSTS; do
    echo ">>> 重启 $CHILD_HOST ..."
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p "${CHILD_SSH_PORT:-22}" "$CHILD_USER@$CHILD_HOST" "
cd $CHILD_PATH
pkill -f 'uvicorn app.main:app' 2>/dev/null || true
sleep 2
nohup env PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port $PORT >> node.log 2>&1 &
sleep 1
echo done
" || true
done
echo "批量重启完成。"
