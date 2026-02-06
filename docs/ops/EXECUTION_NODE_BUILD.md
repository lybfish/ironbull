# 执行节点独立部署与可执行文件构建

子服务器可独立部署执行节点，无需完整 IronBull 仓库。支持两种方式：**部署目录**（pip + uvicorn）与 **可执行文件**（PyInstaller）。

## 1. 打出部署包

在项目根目录执行：

```bash
make node-bundle
# 或: python3 scripts/build_node_bundle.py
```

生成 `dist/execution-node/`，内含：

- `app/` — 节点服务
- `libs/` — 仅 core + trading（base、live_trader），无 DB/结算相关代码
- `config/default.yaml` — 节点用配置（仅 log，无 db/redis）
- `requirements.txt` — 节点最小依赖
- `README.md`、`BUILD_EXECUTABLE.md`、`run.py`（可执行文件入口）

## 2. 子服务器用部署目录运行

将 `dist/execution-node/` 拷贝到子服务器后：

```bash
cd dist/execution-node
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 9101
```

端口需与中心 `dim_execution_node.base_url` 一致。

## 3. 打可执行文件（PyInstaller）

在已生成 `dist/execution-node/` 的前提下，进入该目录：

```bash
cd dist/execution-node
pip install pyinstaller
pyinstaller --onefile --name execution-node \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols --hidden-import uvicorn.protocols.http --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.lifespan --hidden-import uvicorn.lifespan.on \
  run.py
```

输出在上级 `dist/` 下得到 `execution-node`（或 Windows 下 `execution-node.exe`）。子机可直接运行：

```bash
./execution-node
# 或 PORT=9102 ./execution-node
```

若打包后运行报缺模块，可酌情增加 `--hidden-import`。更完整说明见部署包内 `BUILD_EXECUTABLE.md`。

## 4. 一键部署到子服务器（推荐）

在**中心/本机**配置一次子机信息后，可一键完成：构建 → 同步到子机目录（无则创建）→ 重启节点。

**首次配置子机（交互，含 SSH 免密引导）：**

```bash
make deploy-child-setup
# 或多台子机: make deploy-child-setup NAME=node1
```

按提示输入：子机地址、SSH 端口、用户名、**部署路径**（如 `/opt/execution-node`，不存在会自动创建）、节点 uvicorn 端口（默认 9101）、是否 sudo、并可按引导配置免密登录。

**一键部署（构建 + 同步 + 重启）：**

```bash
make deploy-child
# 或: make deploy-child NAME=node1
```

**仅更新并重启（不重新 build）：**

```bash
make deploy-child SKIP_BUILD=1
```

**仅重启子机上的节点（不构建、不同步）：**

```bash
make deploy-child-restart
# 或: make deploy-child-restart NAME=node1
```

子机首次部署后，需在子机上执行一次依赖安装：`cd <部署路径> && pip install -r requirements.txt`，之后即可通过上述命令更新与重启。

## 5. 批量部署多台子服务器（Linux）

多台 Linux 子机使用**相同**的部署路径、SSH 用户、uvicorn 端口时，可一次配置、批量部署。

**首次配置（多台子机地址 + 免密）：**

```bash
make deploy-child-batch-setup
```

按提示输入：**多台子机地址**（空格或逗号分隔，如 `192.168.1.10 192.168.1.11 192.168.1.12`）、SSH 端口、用户名、部署路径、uvicorn 端口、是否 sudo。会依次引导为每台子机配置 SSH 免密（输入各台密码一次）。配置写入 `deploy/.deploy.child-batch.env`。

**批量部署（构建一次 → 同步到所有子机 → 逐台重启）：**

```bash
make deploy-child-batch
```

**仅同步并逐台重启（不重新 build）：**

```bash
make deploy-child-batch SKIP_BUILD=1
```

**仅批量重启所有子机上的节点：**

```bash
make deploy-child-batch-restart
```

每台子机首次部署后，需 SSH 到该机执行一次：`cd <部署路径> && pip install -r requirements.txt`。
