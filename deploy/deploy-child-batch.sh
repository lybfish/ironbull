#!/usr/bin/env bash
# ============================================================
# IronBull 批量部署子服务器（多台 Linux 执行节点）
# 构建一次 → 同步到所有子机（目录无则创建）→ 逐台重启
# 用法: make deploy-child-batch [SKIP_BUILD=1]
# 需先 make deploy-child-batch-setup
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUNDLE_DIR="$ROOT/dist/execution-node"
CONFIG_FILE="$SCRIPT_DIR/.deploy.child-batch.env"
SKIP_BUILD="${SKIP_BUILD:-}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "用法: $0"
    echo "  make deploy-child-batch          构建 + 同步到所有子机 + 逐台重启"
    echo "  make deploy-child-batch SKIP_BUILD=1  仅同步 + 重启"
    exit 0
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "未找到配置: $CONFIG_FILE"
    echo "请先执行: make deploy-child-batch-setup"
    exit 1
fi

source "$CONFIG_FILE"
[[ "${CHILD_SUDO:-}" = "yes" ]] && SUDO_CMD="sudo" || SUDO_CMD=""
PORT="${CHILD_UVICORN_PORT:-9101}"

ssh_cmd() {
    local host=$1
    shift
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p "${CHILD_SSH_PORT:-22}" "$CHILD_USER@$host" "$@"
}

echo "=========================================="
echo "  子服务器批量部署（Linux）"
echo "=========================================="
echo "  子机: $CHILD_HOSTS"
echo "  路径: $CHILD_PATH  端口: $PORT"
echo ""

# 1. 构建（可选）
if [[ "$SKIP_BUILD" != "1" ]]; then
    echo "[1/4] 构建执行节点包（一次）..."
    (cd "$ROOT" && make node-bundle)
    echo ""
else
    echo "[1/4] 跳过构建 (SKIP_BUILD=1)"
    if [[ ! -d "$BUNDLE_DIR" ]]; then
        echo "错误: dist/execution-node/ 不存在，请先 make node-bundle 或去掉 SKIP_BUILD=1"
        exit 1
    fi
    echo ""
fi

# 2/3/4 逐台：创建目录、同步、重启
N=0
TOTAL=$(echo $CHILD_HOSTS | wc -w)
for CHILD_HOST in $CHILD_HOSTS; do
    N=$((N + 1))
    echo "[2/4] 子机 $N/$TOTAL ($CHILD_HOST) 创建目录..."
    if [[ -n "$SUDO_CMD" ]]; then
        ssh_cmd "$CHILD_HOST" "$SUDO_CMD mkdir -p $CHILD_PATH && $SUDO_CMD chown \$(whoami) $CHILD_PATH" || true
    else
        ssh_cmd "$CHILD_HOST" "mkdir -p $CHILD_PATH" || true
    fi

    echo "[3/4] 子机 $N/$TOTAL ($CHILD_HOST) 同步..."
    rsync -avz --delete \
        -e "ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -p ${CHILD_SSH_PORT:-22}" \
        "$BUNDLE_DIR/" \
        "$CHILD_USER@$CHILD_HOST:$CHILD_PATH/" || true

    echo "[4/4] 子机 $N/$TOTAL ($CHILD_HOST) 重启节点..."
    ssh_cmd "$CHILD_HOST" "
cd $CHILD_PATH
pkill -f 'uvicorn app.main:app' 2>/dev/null || true
sleep 2
nohup env PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port $PORT >> node.log 2>&1 &
sleep 1
echo done
" || true
    echo "  --- $CHILD_HOST 完成"
    echo ""
done

echo "=========================================="
echo "  批量部署完成"
echo "=========================================="
echo "  节点列表:"
for CHILD_HOST in $CHILD_HOSTS; do
    echo "    http://$CHILD_HOST:$PORT"
done
echo ""
echo "  仅批量重启: make deploy-child-batch-restart"
echo "  若某台首次部署，请 SSH 到该机执行: cd $CHILD_PATH && pip install -r requirements.txt"
echo ""
