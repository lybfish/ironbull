#!/usr/bin/env bash
# ============================================================
# IronBull 本地一键发布：push 后 SSH 到线上拉代码并执行 deploy（参考 old3 deploy.sh）
# 用法：
#   make push-deploy              # 一键：有未提交则自动 add+commit，再 push → 线上 pull + 迁移 + 重启
#   make push-deploy MSG="fix: xxx"  # 指定提交说明（默认 "deploy"）
#   make push-deploy BUILD=1      # 含线上构建 admin-web
#   make push-deploy MIGRATE=1      # 线上执行迁移（默认不跑）
#   make push-deploy DRY_RUN=1
# 首次使用请先: make deploy-setup
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_NAME="${1:-default}"
CONFIG_FILE="$SCRIPT_DIR/.deploy.$CONFIG_NAME.env"

# 从 Make 传入
BUILD="${BUILD:-}"
DRY_RUN="${DRY_RUN:-}"
NAME="${NAME:-}"
MSG="${MSG:-deploy}"   # 自动提交时的 commit message
MIGRATE="${MIGRATE:-}" # 传 MIGRATE=1 时线上才执行迁移

# 若通过 make push-deploy NAME=prod 调用，CONFIG_NAME 可能是 default，用 NAME
[[ -n "$NAME" ]] && CONFIG_NAME="$NAME" && CONFIG_FILE="$SCRIPT_DIR/.deploy.$CONFIG_NAME.env"

if [[ "$CONFIG_NAME" == "-h" || "$CONFIG_NAME" == "--help" ]]; then
    echo "用法: $0 [配置名]"
    echo "  make push-deploy [NAME=xxx] [NO_MIGRATE=1] [BUILD=1] [DRY_RUN=1]"
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

# 远程执行参数（默认不跑迁移；需要时用 make push-deploy MIGRATE=1）
REMOTE_ARGS="--no-migrate"
[[ "$MIGRATE" = "1" ]]    && REMOTE_ARGS=""
[[ "$BUILD" = "1" ]]      && REMOTE_ARGS="$REMOTE_ARGS --build"
[[ "$DRY_RUN" = "1" ]]    && REMOTE_ARGS="$REMOTE_ARGS --dry-run"

run() {
    if [[ "$DRY_RUN" = "1" ]]; then
        echo "[dry-run] $*"
    else
        "$@"
    fi
}

ssh_cmd() {
    if [[ "$DRY_RUN" = "1" ]]; then
        echo "[dry-run] ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST $*"
    else
        ssh -p "$DEPLOY_PORT" "$DEPLOY_USER@$DEPLOY_HOST" "$@"
    fi
}

echo "=========================================="
echo "  IronBull 本地 → 线上发布"
echo "=========================================="
echo "  配置: $CONFIG_NAME"
echo "  服务器: $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PORT"
echo "  路径: $DEPLOY_PATH"
echo "  分支: $DEPLOY_BRANCH"
[[ "$DRY_RUN" = "1" ]] && echo "  (dry-run 模式)"
echo ""

cd "$ROOT"

# 0. 若有未提交修改：自动 add + commit，再继续 push 与发布（一键完成）
if [[ -n "$(git status --porcelain)" ]]; then
    echo "[0/4] 存在未提交修改，自动 add + commit..."
    run git add -A
    run git commit -m "${MSG}" || true
    echo ""
fi

# 1. 确保分支并 push
echo "[1/4] 推送代码..."
CUR="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CUR" != "$DEPLOY_BRANCH" ]]; then
    echo "当前分支 $CUR，部署分支 $DEPLOY_BRANCH，正在切换..."
    run git checkout "$DEPLOY_BRANCH" 2>/dev/null || true
fi
run git fetch "$DEPLOY_REMOTE" --prune 2>/dev/null || true
REMOTE_REF="$DEPLOY_REMOTE/$DEPLOY_BRANCH"
if git rev-parse --verify "$REMOTE_REF" >/dev/null 2>&1; then
    REMOTE_COMMIT="$(git rev-parse "$REMOTE_REF")"
    LOCAL_COMMIT="$(git rev-parse HEAD)"
    if git merge-base --is-ancestor "$REMOTE_COMMIT" HEAD 2>/dev/null; then
        run git push "$DEPLOY_REMOTE" "$DEPLOY_BRANCH" || exit 1
        echo "已推送 $DEPLOY_BRANCH"
    elif [[ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]]; then
        echo "本地与远程一致，无需推送"
    else
        echo "本地落后于远程，请先 pull 再执行 push-deploy"
        exit 1
    fi
else
    run git push -u "$DEPLOY_REMOTE" "$DEPLOY_BRANCH" || run git push "$DEPLOY_REMOTE" "$DEPLOY_BRANCH" || exit 1
    echo "已推送 $DEPLOY_BRANCH"
fi
# 2. 若线上尚无仓库，先执行首次初始化（创建目录并 clone）
echo "[2/4] 检查线上是否已拉取代码..."
HAS_REPO=""
if [[ "$DRY_RUN" = "1" ]]; then
    HAS_REPO="no"
else
    HAS_REPO=$(ssh -p "$DEPLOY_PORT" "$DEPLOY_USER@$DEPLOY_HOST" "test -d $DEPLOY_PATH/.git 2>/dev/null && echo yes || echo no" 2>/dev/null || echo "no")
fi
if [[ "$HAS_REPO" != "yes" ]]; then
    echo "线上尚未初始化（无 $DEPLOY_PATH 或未 clone），正在执行首次初始化..."
    "$SCRIPT_DIR/deploy-init.sh" "$CONFIG_NAME" || exit 1
    echo ""
fi

# 3. SSH 到服务器执行 deploy（sudo 时用绝对路径，避免子进程 cwd 不同导致找不到脚本）
echo "[3/4] 连接服务器并拉代码、发布..."
DEPLOY_SCRIPT="$DEPLOY_PATH/deploy/deploy.sh"
if [[ -n "$SUDO_CMD" ]]; then
    REMOTE_RUN="cd $DEPLOY_PATH && $SUDO_CMD bash $DEPLOY_SCRIPT $REMOTE_ARGS"
else
    REMOTE_RUN="cd $DEPLOY_PATH && bash $DEPLOY_SCRIPT $REMOTE_ARGS"
fi
ssh_cmd "$REMOTE_RUN"
echo ""

echo "[4/4] 完成"
echo "=========================================="
echo "  发布流程已执行完毕"
echo "=========================================="
