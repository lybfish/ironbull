#!/usr/bin/env bash
# ============================================================
# IronBull 子服务器（执行节点）部署配置引导
# 配置后可用 make deploy-child 一键：构建 → 同步到子机 → 重启节点
# 用法: ./deploy/deploy-child-setup.sh [配置名]  或  make deploy-child-setup [NAME=node1]
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_NAME="${1:-default}"
CONFIG_FILE="$SCRIPT_DIR/.deploy.child-$CONFIG_NAME.env"
NAME="${NAME:-}"
[[ -n "$NAME" ]] && CONFIG_NAME="$NAME" && CONFIG_FILE="$SCRIPT_DIR/.deploy.child-$CONFIG_NAME.env"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

if [[ "$CONFIG_NAME" == "-h" || "$CONFIG_NAME" == "--help" ]]; then
    echo "用法: $0 [配置名]"
    echo "  make deploy-child-setup       # 配置名 default"
    echo "  make deploy-child-setup NAME=node1"
    echo "生成: deploy/.deploy.child-<配置名>.env（勿提交 Git）"
    exit 0
fi

echo "=========================================="
echo "  子服务器（执行节点）部署配置引导"
echo "=========================================="
echo ""
echo -e "配置名: ${CYAN}$CONFIG_NAME${NC} → $CONFIG_FILE"
echo ""

echo -e "${YELLOW}[1/4] 检查本地环境...${NC}"
command -v ssh >/dev/null 2>&1 || { echo -e "${RED}✗ 未安装 ssh${NC}"; exit 1; }
command -v rsync >/dev/null 2>&1 || { echo -e "${RED}✗ 未安装 rsync（同步部署包需要）${NC}"; exit 1; }
echo -e "${GREEN}✓ ssh、rsync 已安装${NC}"
echo ""

echo -e "${YELLOW}[2/4] 子服务器信息${NC}"
read -p "子服务器地址 (IP 或域名): " CHILD_HOST
read -p "SSH 端口 [22]: " CHILD_SSH_PORT
CHILD_SSH_PORT="${CHILD_SSH_PORT:-22}"
read -p "SSH 用户名 [root]: " CHILD_USER
CHILD_USER="${CHILD_USER:-root}"
read -p "部署路径（执行节点目录，不存在将自动创建）[ /opt/execution-node ]: " CHILD_PATH
CHILD_PATH="${CHILD_PATH:-/opt/execution-node}"
read -p "节点 uvicorn 端口 [9101]: " CHILD_UVICORN_PORT
CHILD_UVICORN_PORT="${CHILD_UVICORN_PORT:-9101}"
echo ""

echo -e "${YELLOW}[3/4] SSH 免密登录${NC}"
if ssh -o BatchMode=yes -o ConnectTimeout=5 -p "$CHILD_SSH_PORT" "$CHILD_USER@$CHILD_HOST" "echo ok" 2>/dev/null; then
    echo -e "${GREEN}✓ 免密登录已可用${NC}"
else
    echo -e "${YELLOW}当前无法免密登录，需要先配置（只需输入一次服务器密码）${NC}"
    echo ""
    echo "  接下来会引导您输入该子服务器的登录密码，将公钥写入后即可免密。"
    read -p "是否现在配置免密登录？[Y/n]: " DO_COPY
    DO_COPY="${DO_COPY:-Y}"
    if [[ "$DO_COPY" =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${CYAN}请在提示中输入服务器 $CHILD_USER@$CHILD_HOST 的登录密码：${NC}"
        if ssh-copy-id -p "$CHILD_SSH_PORT" "$CHILD_USER@$CHILD_HOST"; then
            if ssh -o BatchMode=yes -o ConnectTimeout=5 -p "$CHILD_SSH_PORT" "$CHILD_USER@$CHILD_HOST" "echo ok" 2>/dev/null; then
                echo -e "${GREEN}✓ 免密登录已配置成功${NC}"
            else
                echo -e "${YELLOW}公钥已复制，但免密测试仍失败，请检查服务器 authorized_keys 或重试${NC}"
            fi
        else
            echo -e "${RED}配置失败，请检查密码或网络后重试。${NC}"
        fi
    else
        echo -e "${YELLOW}已跳过。后续部署时需输入密码。${NC}"
    fi
fi
echo ""

echo -e "${YELLOW}[4/4] 子机上执行是否使用 sudo${NC}"
read -p "在子服务器上创建目录/重启进程时是否使用 sudo？[y/N]: " CHILD_SUDO_READ
CHILD_SUDO=""
[[ "$CHILD_SUDO_READ" =~ ^[Yy]$ ]] && CHILD_SUDO="yes"
echo ""

mkdir -p "$SCRIPT_DIR"
cat > "$CONFIG_FILE" << EOF
# 子服务器（执行节点）部署配置 - $CONFIG_NAME
# 由 deploy-child-setup.sh 生成，勿提交 Git

CHILD_HOST=$CHILD_HOST
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
echo "  子机: $CHILD_USER@$CHILD_HOST:$CHILD_SSH_PORT"
echo "  路径: $CHILD_PATH  端口: $CHILD_UVICORN_PORT"
echo ""
echo "一键部署（构建 + 同步 + 重启）："
if [ "$CONFIG_NAME" = "default" ]; then
    echo "  make deploy-child"
    echo "仅同步并重启（不重新 build）："
    echo "  make deploy-child SKIP_BUILD=1"
    echo "仅重启子机节点："
    echo "  make deploy-child-restart"
else
    echo "  make deploy-child NAME=$CONFIG_NAME"
    echo "  make deploy-child NAME=$CONFIG_NAME SKIP_BUILD=1"
    echo "  make deploy-child-restart NAME=$CONFIG_NAME"
fi
echo ""
