# 子服务器（执行节点）扩展计划

**状态**：已实施（Phase 1–5 已完成）  
**最后更新**：2026-02

---

## 一、目标与约束

- **目标**：支持多台执行节点（子服务器），中心按账户将执行任务下发到对应节点，节点只执行、不碰库。
- **约束**：子服务器不连数据库；凭证由中心随请求下发，结果由节点同步 HTTP 响应返回，中心写库与结算。
- **与 old3 区别**：中心主动 HTTP POST 到节点（非 WebSocket、非节点拉任务）；节点无状态，只收请求、执行、返回，首版不做同步余额/持仓/移动止损等，可后续按同模式扩展。

---

## 二、架构与请求方向

- **请求方向**：**中心 → 节点**（中心请求节点）。中心有信号时按节点分组，对「本笔信号有账户」的节点各发 1 次 POST；节点不向中心要任务、要凭证。
- **下发范围**：只对有绑定账户的节点发请求；发请求数 = 本笔信号涉及的不同节点数（非系统节点总数）。例：100 用户绑 100 节点 → 100 次 POST，中心并行发；若再放大可加队列 + 下发 worker。
- **通信方式**：首版 **HTTP**，不改为 WebSocket/Socket；除非后续出现「节点不能收外连」或「极高频率 + 大量节点」再考虑 WS。

---

## 三、数据与配置

### 3.1 执行节点表（dim_execution_node）

- 字段建议：id, node_code, name, base_url（如 `http://192.168.1.10:9101`）, status, last_heartbeat_at, created_at。
- 心跳：节点可选定时 POST 中心 `POST /api/nodes/{node_code}/heartbeat`，中心更新 last_heartbeat_at；路由时只选 status=1 且近期有心跳的节点。
- 配置方式：优先从表读取；若无则从 config 的 execution_nodes（列表或 URL 映射）读取。

### 3.2 账户与节点归属

- **方案**：在 **fact_exchange_account** 增加可选字段 **execution_node_id**（或 node_code）。为空或 0 表示本机执行；有值则路由到对应节点。
- 管理：Merchant API 或 data-api 支持为账户指定/切换执行节点；管理后台可展示账户所属节点。

---

## 四、中心侧（signal-monitor）逻辑

1. 产生信号后，按 strategy_code 查 dim_strategy_binding + fact_exchange_account，得到 targets（含 execution_node_id、凭证等）。
2. 按 **execution_node_id** 分组：本机一拨（空或本机），其余按 node_id 分组。
3. **本机**：沿用现有逻辑，进程内为每个 target 创建 LiveTrader 执行，写 fact_order/fact_fill，触发结算。
4. **远程节点**：对每个有账户的节点，组装 1 个 POST body（信号参数 + 该节点上所有 account 的凭证），POST 到该节点 **base_url/api/execute**；收到响应后，中心根据 body 中的 results 写 fact_order、fact_fill，并触发结算（点卡、利润池、分销）。
5. **队列模式（可选）**：配置 `use_node_execution_queue=True` 时，中心将远程节点任务投递到 Redis 队列 `NODE_EXECUTE_QUEUE`，由独立 worker（`scripts/node_execute_worker.py`）消费并 POST 到节点，再在中心写库与结算；投递失败时自动回退为直接 POST。

---

## 五、子服务器侧（执行节点）能力

### 5.1 首版必须

- **POST /api/execute**（或 /api/execute-batch）  
  - 请求 body：信号参数（symbol, side, quantity, stop_loss, take_profit 等）+ 本节点需执行的 account 列表（每项含 account_id, api_key, api_secret, exchange 等凭证）。  
  - 节点：用凭证在本机 LiveTrader 调交易所下单、设止盈止损；**不写库**。  
  - 响应 body：同步返回，如 `{ "success": true, "results": [ { "account_id": 101, "success": true, "order_id": "xxx", "filled_price": 50000, "filled_quantity": 0.01 }, ... ] }`。  
- **安全**：仅内网可达；HTTPS 或内网 HTTP；不在公网暴露凭证。

### 5.2 同步余额/持仓（已实现）

- **POST /api/sync-balance**：body 带 account 列表 + 凭证；节点查交易所余额并返回；中心写 fact_account。
- **POST /api/sync-positions**：body 带 account 列表 + 凭证；节点查交易所持仓并返回；中心写 fact_position。
- 中心通过 data-api 的 **POST /api/sync/balance**、**POST /api/sync/positions** 触发；内部调用 `libs/sync_node` 向各节点请求并写库。

### 5.3 心跳（已实现）

- **自动心跳**：节点配置 `center_url`（中心 data-api 地址）和 `node_code`（与 dim_execution_node.node_code 一致）后，节点启动时自动创建后台任务，按 `heartbeat_interval`（默认 60s）定时 POST 中心 `/api/nodes/{node_code}/heartbeat`，中心更新 `last_heartbeat_at`。
- **鉴权联动**：若同时配置了 `node_auth_secret`，心跳请求也会带上 `X-Center-Token` 头。
- **可选关闭**：不配置 `center_url` 或 `node_code` 时不发心跳，行为与旧版一致。
- **健康检查**：GET /health 中展示心跳配置状态（enabled、center_url、node_code、interval）。

### 5.4 仅中心可调（鉴权）

- **目标**：保证子机接口只被中心调用，拒绝未授权请求。
- **方式**：中心与节点配置同一密钥（`node_auth_secret`）；中心请求时带 Header `X-Center-Token: <密钥>`，节点校验。
- **节点配置**（config 或环境变量）：
  - `node_auth_enabled: true` — 开启鉴权（默认 false，便于兼容旧部署）。
  - `node_auth_secret: "your-shared-secret"` — 与中心一致。
  - 可选 `node_allowed_ips: "中心IP1,中心IP2"` — IP 白名单，为空则不校验 IP。
- **中心配置**：`node_auth_secret: "your-shared-secret"`（与节点一致）；未配或为空则不带头，节点未开启鉴权时行为不变。
- **实现**：execution-node 对 `/api/execute`、`/api/sync-balance`、`/api/sync-positions` 做依赖校验；中心侧 signal-monitor、sync_node、node_execute_worker 在 POST 时带上 `X-Center-Token`。

---

## 六、分阶段实施

| 阶段 | 内容 | 状态 | 产出/实现位置 |
|------|------|------|----------------|
| **Phase 1** | 节点表 + 心跳 API（中心提供）+ 从配置/表读节点列表 | ✅ 已完成 | dim_execution_node、data-api POST /api/nodes/{node_code}/heartbeat、GET /api/nodes |
| **Phase 2** | fact_exchange_account.execution_node_id；signal-monitor 按 node 分流，远程 POST 到节点，中心写库与结算 | ✅ 已完成 | signal-monitor 按 execution_node_id 分组，远程 POST；libs/execution_node/apply_results.py |
| **Phase 3** | 子服务器 **POST /api/execute**，接收任务+凭证，LiveTrader 执行，同步返回 results | ✅ 已完成 | services/execution-node/app/main.py |
| **Phase 4** | 同步余额/持仓：节点 /api/sync-balance、/api/sync-positions；中心调用并写库 | ✅ 已完成 | execution-node 上述端点；libs/sync_node；data-api POST /api/sync/balance、/api/sync/positions |
| **Phase 5** | 中心投递队列，下发 worker 消费并 POST 到节点 | ✅ 已完成 | NODE_EXECUTE_QUEUE、use_node_execution_queue 配置、scripts/node_execute_worker.py |

---

## 七、推荐方案小结

- **账户→节点**：fact_exchange_account.execution_node_id。
- **凭证**：中心随 POST body 下发（子服务器不碰库）。
- **结果**：节点同步 HTTP 响应返回，中心写库并做结算。
- **通信**：HTTP，中心请求节点；首版不改为 WebSocket。
- **并发**：中心对多节点并行 POST；单请求可带多 account（batch）；再大用队列+worker。
- **实施顺序**：先 Phase 1 + Phase 2 + Phase 3，再按需 Phase 4/5。

---

## 八、配置与运行

### 8.1 配置项（中心 / signal-monitor）

- **use_node_execution_queue**（默认 false）：为 true 时，远程节点任务投递到 Redis 队列 `node-execute`，由 node_execute_worker 消费并 POST 到节点；为 false 时 signal-monitor 直接 POST 到各节点。
- 其他：dim_execution_node 表或配置中的 execution_nodes、心跳超时阈值（如 120s）等按需配置。

### 8.2 队列 Worker

- **脚本**：`scripts/node_execute_worker.py`
- **用法**（项目根目录）：
  ```bash
  PYTHONPATH=. python3 scripts/node_execute_worker.py
  ```
- **环境变量**：`NODE_EXECUTE_POLL_TIMEOUT`（默认 30，秒）控制队列阻塞轮询超时。
- **依赖**：Redis 可用（与 libs/queue 一致）；消费后向节点 POST /api/execute，再调用 `libs/execution_node.apply_results.apply_remote_results` 在中心写库并结算。

### 8.3 文档引用

- [NEXT_TASK.md](NEXT_TASK.md) 中「选项 5：子服务器/执行节点扩展」指向本文档。

---

## 九、子服务器部署：独立部署包或可执行文件

子服务器**只跑「执行」**：接收中心 POST，用凭证调交易所，返回结果；**不连数据库、不连 Redis**。推荐使用**独立部署包**或**可执行文件**，无需整库拷贝。

### 9.1 打出独立部署包（推荐）

在项目根目录执行：

```bash
python3 scripts/build_node_bundle.py
```

会在 `dist/execution-node/` 下生成**最小依赖**节点包（仅 libs/core、libs/trading 的 base+live_trader，无 order_trade/position/ledger）。将该目录拷贝到子服务器即可。

- **子服务器上**：进入 `dist/execution-node/`，`pip install -r requirements.txt`，然后：
  ```bash
  PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 9101
  ```
- 包内含 `README.md`、`config/default.yaml`（仅 log，无 db/redis）、`BUILD_EXECUTABLE.md`（打可执行文件说明）。

### 9.2 打可执行文件（可选）

子服务器若希望**不安装 Python**，可基于 `dist/execution-node/` 用 PyInstaller 打出单可执行文件。进入 `dist/execution-node/` 后按包内 `BUILD_EXECUTABLE.md` 操作（入口为 `run.py`）。打完后子机只需运行该可执行文件（及可选 config）。

### 9.3 端口与网络

- **端口**：与中心 `dim_execution_node.base_url` 一致（如 `http://子服务器IP:9101`）。
- **网络**：中心需能访问子机对应端口；建议仅内网。
- **配置**：节点包内 `config/default.yaml` 仅含 log 等；**不必配置** `db_*`、`redis_*`。

### 9.4 小结

| 位置         | 部署物                     | 运行方式              |
|--------------|----------------------------|------------------------|
| **中心服务器** | 完整项目                    | signal-monitor、data-api、node_execute_worker（可选）、MySQL、Redis 等 |
| **子服务器**   | `dist/execution-node/` 或据此打出的可执行文件 | **仅** execution-node（uvicorn 或单可执行文件），不部署整库、不跑 DB/Redis |
