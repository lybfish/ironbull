#!/usr/bin/env bash
# ============================================================
# IronBull 线上首次初始化：在服务器上创建目录并 clone 仓库（参考 old3）
# 用法: make deploy-init [NAME=prod]
# 需先执行 make deploy-setup 生成配置
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_NAME="${1:-default}"
CONFIG_FILE="$SCRIPT_DIR/.deploy.$CONFIG_NAME.env"
NAME="${NAME:-}"
[[ -n "$NAME" ]] && CONFIG_NAME="$NAME" && CONFIG_FILE="$SCRIPT_DIR/.deploy.$CONFIG_NAME.env"

if [[ "$CONFIG_NAME" == "-h" || "$CONFIG_NAME" == "--help" ]]; then
    echo "用法: $0 [配置名]"
    echo "  make deploy-init        # 使用 default 配置"
    echo "  make deploy-init NAME=prod"
    exit 0
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "未找到配置: $CONFIG_FILE"
    echo "请先执行: make deploy-setup 或 make deploy-setup NAME=$CONFIG_NAME"
    exit 1
fi

source "$CONFIG_FILE"
# 线上是否用 sudo（未配置则不用）
[[ "${DEPLOY_SUDO:-}" = "yes" ]] && SUDO_CMD="sudo" || SUDO_CMD=""
REPO_URL="$(cd "$ROOT" && git remote get-url "$DEPLOY_REMOTE" 2>/dev/null)" || REPO_URL=""
if [[ -z "$REPO_URL" ]]; then
    echo "无法获取仓库地址，请检查 git remote: $DEPLOY_REMOTE"
    exit 1
fi

DRY_RUN="${DRY_RUN:-}"
ssh_cmd() {
    if [[ "$DRY_RUN" = "1" ]]; then
        echo "[dry-run] ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST $*"
    else
        ssh -p "$DEPLOY_PORT" "$DEPLOY_USER@$DEPLOY_HOST" "$@"
    fi
}

echo "=========================================="
echo "  IronBull 线上首次初始化"
echo "=========================================="
echo "  服务器: $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PORT"
echo "  路径:   $DEPLOY_PATH"
echo "  分支:   $DEPLOY_BRANCH"
echo "  仓库:   $REPO_URL"
[[ "$DRY_RUN" = "1" ]] && echo "  (dry-run 模式)"
echo ""

# 检查是否已有仓库
HAS_REPO=$(ssh_cmd "test -d $DEPLOY_PATH/.git 2>/dev/null && echo yes || echo no" 2>/dev/null || echo "no")
if [[ "$HAS_REPO" = "yes" ]]; then
    echo "线上已有仓库 ($DEPLOY_PATH/.git)，无需初始化。"
    echo "直接使用 make push-deploy 即可。"
    exit 0
fi

echo "正在创建目录并克隆仓库..."
# 创建目录并 clone；若配置了 DEPLOY_SUDO=yes，则用 sudo 创建目录并 chown 给当前用户
if [[ -n "$SUDO_CMD" ]]; then
    REMOTE_SCRIPT="
set -e
if [ -d $DEPLOY_PATH/.git ]; then echo 'Already initialized.'; exit 0; fi
$SUDO_CMD mkdir -p $DEPLOY_PATH && $SUDO_CMD chown \$(whoami) $DEPLOY_PATH
cd $DEPLOY_PATH
if [ -n \"\$(ls -A 2>/dev/null)\" ] && [ ! -d .git ]; then
    echo '目录已存在且非空，请清空或换一个路径后再执行 deploy-init'; exit 1
fi
if [ ! -d .git ]; then
    git clone $REPO_URL . && (git checkout $DEPLOY_BRANCH 2>/dev/null || true)
fi
chmod +x deploy/deploy.sh deploy/start.sh deploy/deploy-setup.sh deploy/push-and-deploy.sh deploy/deploy-init.sh 2>/dev/null || true
echo 'Init done.'
"
else
    REMOTE_SCRIPT="
set -e
if [ -d $DEPLOY_PATH/.git ]; then echo 'Already initialized.'; exit 0; fi
mkdir -p $DEPLOY_PATH
cd $DEPLOY_PATH
if [ -n \"\$(ls -A 2>/dev/null)\" ] && [ ! -d .git ]; then
    echo '目录已存在且非空，请清空或换一个路径后再执行 deploy-init'; exit 1
fi
if [ ! -d .git ]; then
    git clone $REPO_URL . && (git checkout $DEPLOY_BRANCH 2>/dev/null || true)
fi
chmod +x deploy/deploy.sh deploy/start.sh deploy/deploy-setup.sh deploy/push-and-deploy.sh deploy/deploy-init.sh 2>/dev/null || true
echo 'Init done.'
"
fi
ssh_cmd "$REMOTE_SCRIPT"

echo ""
echo "=========================================="
echo "  初始化完成"
echo "=========================================="
echo "  请确保服务器上已配置 deploy/.env.production（可从 deploy/env.production.example 复制并填写）"
echo "  之后在本地执行: make push-deploy"
echo ""
