#!/usr/bin/env bash
# ============================================================
# IronBull 线上发布脚本（在服务器上执行）
# 用法：
#   ./deploy/deploy.sh              # 拉代码 + 迁移 + 重启服务
#   ./deploy/deploy.sh --no-migrate # 只拉代码 + 重启，不跑迁移
#   ./deploy/deploy.sh --build      # 拉代码 + 迁移 + 构建 admin-web + 重启
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

echo "[1/4] 拉取代码..."
run git pull
echo ""

if [ "$DO_MIGRATE" = true ]; then
    echo "[2/4] 执行迁移 (migrate-013)..."
    run make migrate-013
    echo ""
else
    echo "[2/4] 跳过迁移 (--no-migrate)"
    echo ""
fi

if [ "$DO_BUILD" = true ]; then
    echo "[3/4] 构建 admin-web..."
    run make admin-build
    echo ""
else
    echo "[3/4] 跳过前端构建"
    echo ""
fi

echo "[4/4] 重启服务..."
run make restart
echo ""

echo "=== 发布完成 ==="
echo "建议执行: make status && make health"
