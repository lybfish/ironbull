#!/usr/bin/env bash
# ============================================================
# IronBull 一键部署子服务器（执行节点）
# 构建 node-bundle → 同步到子机目录（无则创建）→ 重启节点
# 用法: make deploy-child [NAME=node1] [SKIP_BUILD=1]
# 需先 make deploy-child-setup 或 make node-bundle
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUNDLE_DIR="$ROOT/dist/execution-node"
CONFIG_NAME="${1:-default}"
CONFIG_FILE="$SCRIPT_DIR/.deploy.child-$CONFIG_NAME.env"
NAME="${NAME:-}"
SKIP_BUILD="${SKIP_BUILD:-}"
[[ -n "$NAME" ]] && CONFIG_NAME="$NAME" && CONFIG_FILE="$SCRIPT_DIR/.deploy.child-$CONFIG_NAME.env"

if [[ "$CONFIG_NAME" == "-h" || "$CONFIG_NAME" == "--help" ]]; then
    echo "用法: $0 [配置名]"
    echo "  make deploy-child [NAME=xxx]       构建 + 同步 + 重启"
    echo "  make deploy-child SKIP_BUILD=1      仅同步 + 重启"
    exit 0
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "未找到配置: $CONFIG_FILE"
    echo "请先执行: make deploy-child-setup 或 make deploy-child-setup NAME=$CONFIG_NAME"
    exit 1
fi

source "$CONFIG_FILE"
[[ "${CHILD_SUDO:-}" = "yes" ]] && SUDO_CMD="sudo" || SUDO_CMD=""

ssh_cmd() {
    ssh -p "${CHILD_SSH_PORT:-22}" "$CHILD_USER@$CHILD_HOST" "$@"
}

echo "=========================================="
echo "  子服务器（执行节点）部署"
echo "=========================================="
echo "  配置: $CONFIG_NAME"
echo "  子机: $CHILD_USER@$CHILD_HOST:${CHILD_SSH_PORT:-22}"
echo "  路径: $CHILD_PATH  端口: ${CHILD_UVICORN_PORT:-9101}"
echo ""

# 1. 构建（可选）
if [[ "$SKIP_BUILD" != "1" ]]; then
    echo "[1/4] 构建执行节点包..."
    (cd "$ROOT" && make node-bundle)
    echo ""
else
    echo "[1/4] 跳过构建 (SKIP_BUILD=1)"
    if [[ ! -d "$BUNDLE_DIR" ]]; then
        echo "错误: dist/execution-node/ 不存在，请先执行 make node-bundle 或去掉 SKIP_BUILD=1"
        exit 1
    fi
    echo ""
fi

# 2. 子机创建目录
echo "[2/4] 确保子机目录存在..."
if [[ -n "$SUDO_CMD" ]]; then
    ssh_cmd "$SUDO_CMD mkdir -p $CHILD_PATH && $SUDO_CMD chown \$(whoami) $CHILD_PATH"
else
    ssh_cmd "mkdir -p $CHILD_PATH"
fi
echo ""

# 3. 同步部署包
echo "[3/4] 同步 dist/execution-node/ 到子机..."
rsync -avz --delete \
    -e "ssh -p ${CHILD_SSH_PORT:-22}" \
    "$BUNDLE_DIR/" \
    "$CHILD_USER@$CHILD_HOST:$CHILD_PATH/"
echo ""

# 4. 重启节点
echo "[4/4] 重启子机执行节点..."
PORT="${CHILD_UVICORN_PORT:-9101}"
REMOTE_RESTART="
cd $CHILD_PATH
pkill -f 'uvicorn app.main:app' 2>/dev/null || true
sleep 2
nohup env PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port $PORT >> node.log 2>&1 &
sleep 1
echo 'Restart done.'
"
ssh_cmd "$REMOTE_RESTART"
echo ""

echo "=========================================="
echo "  子机部署完成"
echo "=========================================="
echo "  节点地址: http://$CHILD_HOST:$PORT"
echo "  仅重启: make deploy-child-restart NAME=$CONFIG_NAME"
echo ""
echo "  若子机首次部署，请 SSH 到子机执行一次: cd $CHILD_PATH && pip install -r requirements.txt"
echo ""
