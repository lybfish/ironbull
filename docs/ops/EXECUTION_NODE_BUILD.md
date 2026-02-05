# 执行节点独立部署与可执行文件构建

子服务器可独立部署执行节点，无需完整 IronBull 仓库。支持两种方式：**部署目录**（pip + uvicorn）与 **可执行文件**（PyInstaller）。

## 1. 打出部署包

在项目根目录执行：

```bash
python3 scripts/build_node_bundle.py
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
