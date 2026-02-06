#!/usr/bin/env python3
"""
打出执行节点独立部署包到 dist/execution-node/（最小依赖，不含 DB/Redis 业务代码）。
子服务器可拷贝该目录后 pip install + uvicorn 运行，或基于该目录用 PyInstaller/Nuitka 打可执行文件。

用法（在项目根目录）:
  python3 scripts/build_node_bundle.py
"""

import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist" / "execution-node"
NODE_LIBS = DIST_DIR / "libs"


def rm_if_exists(path: Path):
    if path.exists():
        shutil.rmtree(path) if path.is_dir() else path.unlink()


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def copy_tree(src: Path, dst: Path, ignore=None):
    if not src.is_dir():
        return
    shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=True)


def main():
    # 清理并创建目录
    rm_if_exists(DIST_DIR)
    ensure_dir(DIST_DIR)
    ensure_dir(NODE_LIBS)
    ensure_dir(NODE_LIBS / "core")
    ensure_dir(NODE_LIBS / "trading")
    ensure_dir(DIST_DIR / "config")

    # 1) 服务代码：services/execution-node/app -> dist/execution-node/app
    copy_tree(REPO_ROOT / "services" / "execution-node" / "app", DIST_DIR / "app")
    # 可执行文件入口（PyInstaller/Nuitka 打包时用）
    run_py = REPO_ROOT / "scripts" / "execution_node_run.py"
    if run_py.exists():
        shutil.copy2(run_py, DIST_DIR / "run.py")

    # 2) libs/core 整目录
    copy_tree(REPO_ROOT / "libs" / "core", NODE_LIBS / "core")

    # 3) libs/trading 仅 base.py, live_trader.py + 精简 __init__.py
    shutil.copy2(REPO_ROOT / "libs" / "trading" / "base.py", NODE_LIBS / "trading" / "base.py")
    shutil.copy2(REPO_ROOT / "libs" / "trading" / "live_trader.py", NODE_LIBS / "trading" / "live_trader.py")
    (NODE_LIBS / "trading" / "__init__.py").write_text(
        '"""节点用精简版：仅导出 base 与 live_trader，不拉 settlement/order_trade/position/ledger"""\n'
        "from .base import Trader, OrderResult, OrderStatus, OrderSide, OrderType, Balance\n"
        "from .live_trader import LiveTrader\n"
        "__all__ = [\"Trader\", \"OrderResult\", \"OrderStatus\", \"OrderSide\", \"OrderType\", \"Balance\", \"LiveTrader\"]\n",
        encoding="utf-8",
    )

    # 4) 节点用 config：仅 log，无 db/redis；可选中心鉴权 + 心跳
    node_yaml = """# 执行节点用配置（不连数据库、不连 Redis）
service_name: execution-node
log_level: INFO
log_structured: false

# ---- 心跳（节点 → 中心）----
# 中心 data-api 地址，如 http://192.168.1.1:8026；为空则不发心跳
# center_url: ""
# 本节点编码，需与中心 dim_execution_node.node_code 一致
# node_code: ""
# 心跳间隔（秒），默认 60
# heartbeat_interval: 60

# ---- 仅中心可调（鉴权）----
# 与中心配置相同密钥后，节点开启鉴权
# node_auth_enabled: true
# node_auth_secret: ""
# 可选 IP 白名单（逗号分隔，为空则不校验）
# node_allowed_ips: ""
"""
    (DIST_DIR / "config" / "default.yaml").write_text(node_yaml, encoding="utf-8")

    # 5) requirements.txt（节点最小依赖）
    node_req = """# 执行节点最小依赖
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
python-multipart>=0.0.6
pyyaml>=6.0
ccxt>=4.0.0
httpx>=0.24.0
"""
    (DIST_DIR / "requirements.txt").write_text(node_req, encoding="utf-8")

    # 6) README
    readme = """# 执行节点独立部署包

本目录为从 IronBull 主项目打出的**最小依赖**节点包，子服务器可独立部署，无需完整仓库与数据库/Redis。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动

在**本目录**下执行（端口与中心 dim_execution_node.base_url 一致，默认 9101）：

```bash
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 9101
```

可选环境变量：`LOG_LEVEL`（如 DEBUG）、`PORT`（若用脚本包装）。

## 说明

- 本机**不配置**数据库、Redis；节点只接收中心 POST，用请求内凭证调交易所并返回结果。
- 打可执行文件：见本目录下 BUILD_EXECUTABLE.md（或项目 docs/ops/EXECUTION_NODE_BUILD.md）。
"""
    (DIST_DIR / "README.md").write_text(readme, encoding="utf-8")

    # 7) 可执行文件构建说明（已实际验证通过）
    build_exe = """# 打可执行文件（PyInstaller）

在本目录已具备最小依赖的前提下，可打出单可执行文件，子机无需安装 Python。

## 安装 PyInstaller

```bash
pip install pyinstaller
```

## 打包

在本目录（dist/execution-node）下执行：

```bash
pyinstaller --onefile --name execution-node \\
  --paths . \\
  --add-data "config:config" \\
  --add-data "app:app" \\
  --add-data "libs:libs" \\
  --hidden-import app --hidden-import app.main \\
  --hidden-import libs.core --hidden-import libs.core.config \\
  --hidden-import libs.core.logger \\
  --hidden-import libs.trading --hidden-import libs.trading.base \\
  --hidden-import libs.trading.live_trader \\
  --hidden-import uvicorn.logging \\
  --hidden-import uvicorn.loops.auto \\
  --hidden-import uvicorn.protocols.http.auto \\
  --hidden-import uvicorn.protocols.http.h11_impl \\
  --hidden-import uvicorn.protocols.websockets.auto \\
  --hidden-import uvicorn.lifespan.on \\
  --hidden-import uvicorn.lifespan.off \\
  --hidden-import httpx --hidden-import yaml --hidden-import ccxt \\
  --collect-submodules ccxt \\
  run.py
```

输出在 `dist/` 子目录下，得到可执行文件 `execution-node`（约 47MB，Windows 下为 `.exe`）。

## 运行

```bash
./dist/execution-node
# 指定端口：PORT=9102 ./dist/execution-node
# 指定主机：HOST=0.0.0.0 PORT=9101 ./dist/execution-node
```

## 验证

```bash
curl http://127.0.0.1:9101/health
# 应返回 {"status":"ok","service":"execution-node",...}
```
"""
    (DIST_DIR / "BUILD_EXECUTABLE.md").write_text(build_exe, encoding="utf-8")

    print(f"OK: dist/execution-node/ 已生成于 {DIST_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
