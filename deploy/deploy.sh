#!/usr/bin/env bash
# ============================================================
# IronBull 线上发布脚本（在服务器上执行）
# 用法：
#   ./deploy/deploy.sh              # 拉代码 + (evui有变更自动build) + 重启
#   ./deploy/deploy.sh --no-migrate # 跳过迁移
#   ./deploy/deploy.sh --build      # 强制构建 evui（即使无变更）
#   ./deploy/deploy.sh --dry-run    # 仅打印将要执行的步骤
#   make deploy [NO_MIGRATE=1] [BUILD=1] [DRY_RUN=1]
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

# 参数
DO_MIGRATE=true
DO_BUILD=false
DRY_RUN=false
for arg in "$@"; do
    case "$arg" in
        --no-migrate) DO_MIGRATE=false ;;
        --build)      DO_BUILD=true ;;
        --dry-run)    DRY_RUN=true ;;
        -h|--help)
            echo "用法: $0 [--no-migrate] [--build] [--dry-run]"
            echo "  --no-migrate  不执行数据库迁移"
            echo "  --build       构建 admin-web 后再重启"
            echo "  --dry-run     只打印步骤不执行"
            echo "  make deploy   NO_MIGRATE=1  BUILD=1  DRY_RUN=1"
            exit 0
            ;;
    esac
done
# Make 传入的环境变量
[[ "${NO_MIGRATE:-}" = "1" ]] && DO_MIGRATE=false
[[ "${BUILD:-}" = "1" ]] && DO_BUILD=true
[[ "${DRY_RUN:-}" = "1" ]] && DRY_RUN=true

run() {
    if [ "$DRY_RUN" = true ]; then
        echo "[dry-run] $*"
    else
        "$@"
    fi
}

echo "=== IronBull 线上发布 ==="
if [ "$DRY_RUN" = true ]; then
    echo "(dry-run 模式，不实际执行)"
fi
echo ""

echo "[1/5] 拉取代码..."
run git pull
echo ""

if [ "$DO_MIGRATE" = true ]; then
    echo "[2/5] 执行迁移 (migrate-013 ~ migrate-016)..."
    # 若当前是 root 且项目属主非 root，以属主用户执行迁移（确保 Python 环境正确）
    MIGRATE_OWNER=""
    if command -v stat >/dev/null 2>&1; then
        MIGRATE_OWNER=$(stat -c '%U' "$ROOT" 2>/dev/null) || true
    fi
    # 加载 .env.production 以获取数据库连接等环境变量
    ENV_PROD="$SCRIPT_DIR/.env.production"
    MIGRATE_ENV=""
    if [ -f "$ENV_PROD" ]; then
        MIGRATE_ENV="set -a && source $ENV_PROD && set +a && "
    fi
    if [ "$(id -u)" = "0" ] && [ -n "$MIGRATE_OWNER" ] && [ "$MIGRATE_OWNER" != "root" ]; then
        echo "  以用户 $MIGRATE_OWNER 执行迁移（当前为 root）"
        run sudo -i -u "$MIGRATE_OWNER" bash -c "${MIGRATE_ENV}cd $ROOT && make migrate"
    else
        # 使用 login shell 确保 PATH 包含 pip 安装路径
        run bash -l -c "${MIGRATE_ENV}cd $ROOT && make migrate"
    fi
    echo ""
else
    echo "[2/5] 跳过迁移 (--no-migrate)"
    echo ""
fi

# 前端构建：通常由本地 push-and-deploy.sh 完成（检测 evui 源码变更 → build → dist 一起提交）
# 线上仅在手动 --build / BUILD=1 时才构建（应急用途）
if [ "$DO_BUILD" = true ]; then
    echo "[3/5] 构建前端 (evui)..."
    run bash -c "cd $ROOT/evui && npm run build"
    echo ""
else
    echo "[3/5] 跳过前端构建（dist 已随代码提交）"
    echo ""
fi

echo "[4/5] 重启服务..."
# 若当前是 root 且项目目录属主非 root，则以属主用户执行 restart（避免 root 下无 uvicorn 等依赖）
REPO_OWNER=""
if command -v stat >/dev/null 2>&1; then
    REPO_OWNER=$(stat -c '%U' "$ROOT" 2>/dev/null) || true
fi
START_SCRIPT="$ROOT/deploy/start.sh"
if [ ! -x "$START_SCRIPT" ]; then
    [ -f "$START_SCRIPT" ] && chmod +x "$START_SCRIPT" 2>/dev/null || true
fi
if [ "$(id -u)" = "0" ] && [ -n "$REPO_OWNER" ] && [ "$REPO_OWNER" != "root" ]; then
    [ -d "$ROOT/tmp" ] && run chown -R "$REPO_OWNER:$REPO_OWNER" "$ROOT/tmp" 2>/dev/null || true
    echo "  以用户 $REPO_OWNER 执行 restart（当前为 root，依赖在该用户下）"
    # -i 加载用户的 .bash_profile / .bashrc，确保 PATH 包含 python3 及 pip 安装的模块
    run sudo -i -u "$REPO_OWNER" bash "$START_SCRIPT" restart
else
    run bash "$START_SCRIPT" restart
fi
echo ""

echo "[5/5] 发布完成，检查服务状态..."
if [ "$(id -u)" = "0" ] && [ -n "$REPO_OWNER" ] && [ "$REPO_OWNER" != "root" ]; then
    run sudo -i -u "$REPO_OWNER" bash "$START_SCRIPT" status 2>/dev/null || true
else
    run bash "$START_SCRIPT" status 2>/dev/null || true
fi
echo "建议: make health 检查各端口"
