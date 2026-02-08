#!/bin/bash
# 线上 Gate 价格和手续费检查脚本
# 用法: bash scripts/check_gate_online.sh [days]

set -e

DAYS=${1:-1}  # 默认检查最近1天

echo "=== 检查最近 ${DAYS} 天的 Gate 订单 ==="
echo ""

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3"
    exit 1
fi

# 切换到项目目录（如果不在项目目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 加载环境变量（如果有）
if [ -f "deploy/.env.production" ]; then
    echo "加载生产环境变量..."
    set -a
    source deploy/.env.production
    set +a
fi

# 运行检查脚本
echo "运行检查脚本..."
PYTHONPATH=. python3 scripts/check_gate_online.py --days "$DAYS"

echo ""
echo "=== 检查完成 ==="
echo ""
echo "如果需要修复价格为0的订单，运行:"
echo "  PYTHONPATH=. python3 scripts/check_gate_online.py --days $DAYS --fix-price"
