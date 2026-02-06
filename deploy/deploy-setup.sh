#!/usr/bin/env bash
# ============================================================
# IronBull 部署配置引导（参考 old3 deploy-setup）
# 一次配置后，本地可用 make push-deploy 一键 push + 连线上拉代码并发布
# 用法: ./deploy/deploy-setup.sh [配置名]  或  make deploy-setup [NAME=prod]
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_NAME="${1:-default}"
CONFIG_FILE="$SCRIPT_DIR/.deploy.$CONFIG_NAME.env"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

if [[ "$CONFIG_NAME" == "-h" || "$CONFIG_NAME" == "--help" ]]; then
    echo "用法: $0 [配置名]"
    echo "  make deploy-setup        # 配置名 default"
    echo "  make deploy-setup NAME=prod"
    echo "生成: deploy/.deploy.<配置名>.env（勿提交 Git）"
    exit 0
fi

echo "=========================================="
echo "  IronBull 部署配置引导"
echo "=========================================="
echo ""
echo -e "配置名: ${CYAN}$CONFIG_NAME${NC} → $CONFIG_FILE"
echo ""

# 1. 检查 Git / SSH
echo -e "${YELLOW}[1/5] 检查本地环境...${NC}"
command -v git >/dev/null 2>&1 || { echo -e "${RED}✗ 未安装 git${NC}"; exit 1; }
command -v ssh >/dev/null 2>&1 || { echo -e "${RED}✗ 未安装 ssh${NC}"; exit 1; }
echo -e "${GREEN}✓ Git、SSH 已安装${NC}"
echo ""

# 2. 服务器信息
echo -e "${YELLOW}[2/5] 服务器信息${NC}"
read -p "服务器地址 (IP 或域名): " DEPLOY_HOST
read -p "SSH 端口 [22]: " DEPLOY_PORT
DEPLOY_PORT="${DEPLOY_PORT:-22}"
read -p "SSH 用户名 [root]: " DEPLOY_USER
DEPLOY_USER="${DEPLOY_USER:-root}"
read -p "项目在服务器上的路径 (如 /opt/ironbull): " DEPLOY_PATH
[[ -z "$DEPLOY_PATH" ]] && DEPLOY_PATH="/opt/ironbull"
echo ""

# 3. Git 远程与分支
echo -e "${YELLOW}[3/5] Git 配置${NC}"
read -p "远程名 [origin]: " DEPLOY_REMOTE
DEPLOY_REMOTE="${DEPLOY_REMOTE:-origin}"
CUR_BRANCH=$(cd "$ROOT" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
read -p "部署分支 [$CUR_BRANCH]: " DEPLOY_BRANCH
DEPLOY_BRANCH="${DEPLOY_BRANCH:-$CUR_BRANCH}"
echo ""

# 4. SSH 免密与 sudo
echo -e "${YELLOW}[4/5] SSH 免密登录${NC}"
if ssh -o BatchMode=yes -o ConnectTimeout=5 -p "$DEPLOY_PORT" "$DEPLOY_USER@$DEPLOY_HOST" "echo ok" 2>/dev/null; then
    echo -e "${GREEN}✓ 免密登录已可用${NC}"
else
    echo -e "${YELLOW}当前无法免密登录，需要先配置（只需输入一次服务器密码）${NC}"
    echo ""
    echo "  接下来会引导您输入该服务器的登录密码，将公钥写入服务器后即可免密。"
    read -p "是否现在配置免密登录？[Y/n]: " DO_COPY
    DO_COPY="${DO_COPY:-Y}"
    if [[ "$DO_COPY" =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${CYAN}请在弹出的提示中输入服务器 $DEPLOY_USER@$DEPLOY_HOST 的登录密码：${NC}"
        if ssh-copy-id -p "$DEPLOY_PORT" "$DEPLOY_USER@$DEPLOY_HOST"; then
            if ssh -o BatchMode=yes -o ConnectTimeout=5 -p "$DEPLOY_PORT" "$DEPLOY_USER@$DEPLOY_HOST" "echo ok" 2>/dev/null; then
                echo -e "${GREEN}✓ 免密登录已配置成功${NC}"
            else
                echo -e "${YELLOW}公钥已复制，但免密测试仍失败，请检查服务器 authorized_keys 或重试${NC}"
            fi
        else
            echo -e "${RED}配置失败，请检查密码或网络后重试。后续 make push-deploy 时可能需多次输入密码。${NC}"
        fi
    else
        echo -e "${YELLOW}已跳过。后续 make push-deploy 时需输入服务器密码。${NC}"
    fi
fi
echo ""

echo -e "${YELLOW}[5/5] 线上执行是否使用 sudo${NC}"
read -p "在服务器上执行命令时是否使用 sudo？[y/N]: " DEPLOY_SUDO_READ
DEPLOY_SUDO=""
[[ "$DEPLOY_SUDO_READ" =~ ^[Yy]$ ]] && DEPLOY_SUDO="yes"
echo ""

# 写入配置
mkdir -p "$SCRIPT_DIR"
cat > "$CONFIG_FILE" << EOF
# 部署配置 - $CONFIG_NAME
# 由 deploy-setup.sh 生成，勿提交 Git

DEPLOY_HOST=$DEPLOY_HOST
DEPLOY_PORT=$DEPLOY_PORT
DEPLOY_USER=$DEPLOY_USER
DEPLOY_PATH=$DEPLOY_PATH
DEPLOY_REMOTE=$DEPLOY_REMOTE
DEPLOY_BRANCH=$DEPLOY_BRANCH
# 线上执行时是否加 sudo（创建目录、执行 deploy.sh 等）
DEPLOY_SUDO=$DEPLOY_SUDO
EOF

echo -e "${GREEN}✓ 已写入: $CONFIG_FILE${NC}"
echo ""
echo "=========================================="
echo "  配置完成"
echo "=========================================="
echo "  服务器: $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PORT"
echo "  路径:   $DEPLOY_PATH"
echo "  分支:   $DEPLOY_BRANCH"
echo ""
echo "若线上尚未有代码，先执行（在服务器创建目录并 clone）："
if [ "$CONFIG_NAME" = "default" ]; then
    echo "  make deploy-init"
else
    echo "  make deploy-init NAME=$CONFIG_NAME"
fi
echo "然后本地一键发布（push + 线上拉代码并重启）："
if [ "$CONFIG_NAME" = "default" ]; then
    echo "  make push-deploy"
    echo "  make push-deploy BUILD=1    # 含前端构建"
    echo "  make push-deploy NO_MIGRATE=1"
else
    echo "  make push-deploy NAME=$CONFIG_NAME"
fi
echo ""
