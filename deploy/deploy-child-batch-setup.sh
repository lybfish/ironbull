#!/usr/bin/env bash
# ============================================================
# IronBull 子服务器批量部署配置引导（多台 Linux 子机，同一路径/用户/端口）
# 用法: make deploy-child-batch-setup
# 生成: deploy/.deploy.child-batch.env
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="$SCRIPT_DIR/.deploy.child-batch.env"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "用法: $0"
    echo "  make deploy-child-batch-setup"
    echo "生成: deploy/.deploy.child-batch.env（多台子机，同一部署路径与端口）"
    exit 0
fi

echo "=========================================="
echo "  子服务器批量部署配置引导（Linux）"
echo "=========================================="
echo ""
echo "  多台子机将使用相同的：部署路径、SSH 用户、uvicorn 端口。"
echo ""

echo -e "${YELLOW}[1/5] 检查本地环境...${NC}"
command -v ssh >/dev/null 2>&1 || { echo -e "${RED}✗ 未安装 ssh${NC}"; exit 1; }
command -v rsync >/dev/null 2>&1 || { echo -e "${RED}✗ 未安装 rsync${NC}"; exit 1; }
echo -e "${GREEN}✓ ssh、rsync 已安装${NC}"
echo ""

echo -e "${YELLOW}[2/5] 子机地址列表（多台 Linux）${NC}"
echo "  请输入多台子服务器地址，用空格或逗号分隔，例如："
echo "    192.168.1.10 192.168.1.11 192.168.1.12"
echo "    或 node1.example.com,node2.example.com,node3.example.com"
read -p "子机地址: " CHILD_HOSTS_RAW
# 统一为空格分隔
CHILD_HOSTS=$(echo "$CHILD_HOSTS_RAW" | tr ',' '\n' | tr -s ' \n' ' ' | xargs)
if [[ -z "$CHILD_HOSTS" ]]; then
    echo -e "${RED}未输入任何地址${NC}"
    exit 1
fi
echo "  已记录 $(echo $CHILD_HOSTS | wc -w) 台子机"
echo ""

echo -e "${YELLOW}[3/5] 共用参数（所有子机相同）${NC}"
read -p "SSH 端口 [22]: " CHILD_SSH_PORT
CHILD_SSH_PORT="${CHILD_SSH_PORT:-22}"
read -p "SSH 用户名 [root]: " CHILD_USER
CHILD_USER="${CHILD_USER:-root}"
read -p "部署路径（不存在将自动创建）[ /opt/execution-node ]: " CHILD_PATH
CHILD_PATH="${CHILD_PATH:-/opt/execution-node}"
read -p "节点 uvicorn 端口 [9101]: " CHILD_UVICORN_PORT
CHILD_UVICORN_PORT="${CHILD_UVICORN_PORT:-9101}"
echo ""

echo -e "${YELLOW}[4/5] SSH 免密登录（对第一台子机检测，建议每台都配置）${NC}"
FIRST_HOST=$(echo $CHILD_HOSTS | awk '{print $1}')
if ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new -p "$CHILD_SSH_PORT" "$CHILD_USER@$FIRST_HOST" "echo ok" 2>/dev/null; then
    echo -e "${GREEN}✓ 第一台 $FIRST_HOST 免密已可用${NC}"
else
    echo -e "${YELLOW}第一台 $FIRST_HOST 无法免密登录${NC}"
    read -p "是否为所有子机配置免密？将依次提示输入各台密码 [Y/n]: " DO_COPY
    DO_COPY="${DO_COPY:-Y}"
    if [[ "$DO_COPY" =~ ^[Yy]$ ]]; then
        for h in $CHILD_HOSTS; do
            echo ""
            echo -e "${CYAN}>>> 子机 $h，请输入该机登录密码：${NC}"
            ssh-copy-id -p "$CHILD_SSH_PORT" -o StrictHostKeyChecking=accept-new "$CHILD_USER@$h" || true
        done
        echo -e "${GREEN}已尝试为所有子机配置公钥${NC}"
    fi
fi
echo ""

echo -e "${YELLOW}[5/5] 子机上执行是否使用 sudo${NC}"
read -p "创建目录/重启进程时是否使用 sudo？[y/N]: " CHILD_SUDO_READ
CHILD_SUDO=""
[[ "$CHILD_SUDO_READ" =~ ^[Yy]$ ]] && CHILD_SUDO="yes"
echo ""

mkdir -p "$SCRIPT_DIR"
# 将空格分隔的 host 列表写成一行，便于 source 后循环
cat > "$CONFIG_FILE" << EOF
# 子服务器批量部署配置（Linux）
# 由 deploy-child-batch-setup.sh 生成，勿提交 Git

CHILD_HOSTS="$CHILD_HOSTS"
CHILD_SSH_PORT=$CHILD_SSH_PORT
CHILD_USER=$CHILD_USER
CHILD_PATH=$CHILD_PATH
CHILD_UVICORN_PORT=$CHILD_UVICORN_PORT
CHILD_SUDO=$CHILD_SUDO
EOF

echo -e "${GREEN}✓ 已写入: $CONFIG_FILE${NC}"
echo ""
echo "=========================================="
echo "  配置完成"
echo "=========================================="
echo "  子机数量: $(echo $CHILD_HOSTS | wc -w)"
echo "  路径: $CHILD_PATH  端口: $CHILD_UVICORN_PORT"
echo ""
echo "批量部署（构建一次 → 同步到所有子机 → 逐台重启）："
echo "  make deploy-child-batch"
echo "仅同步并重启（不重新 build）："
echo "  make deploy-child-batch SKIP_BUILD=1"
echo "仅批量重启所有子机节点："
echo "  make deploy-child-batch-restart"
echo ""
