# 会话交接（新聊天时 @ 本文件再说「按这个继续」）

## 项目整体（后续改动能不跑偏）

- **项目**：IronBull — 量化/交易 SaaS。链路：策略 → 信号 → 执行（本机或子节点）→ 订单/成交/持仓/账本 → 点卡扣费与分销 → 分析。多租户、Merchant API、管理后台、data-api 查询。
- **中心 vs 子机**：中心有 DB/Redis，跑 signal-monitor、data-api、node_execute_worker 等；子机只跑 execution-node，**不连库**，中心 HTTP POST 下发任务与凭证，节点同步返回 results，中心写库与结算。详见 `docs/context/PLAN_EXECUTION_NODES.md`。
- **不能动的（见 docs/context/SYSTEM_RULES.md）**：目录结构（services/nodes/libs/config/scripts/docs）；libs/contracts 字段与语义；模块边界（Strategy 只产信号、Node 只执行不回写策略/风控）；禁止跨层调用（如 Strategy 直调 Node）。
- **关键文档**：`PLAN_EXECUTION_NODES.md`（执行节点）、`NEXT_TASK.md`（待办）、`IMPLEMENTATION_STATUS.md`（进度）、`SYSTEM_RULES.md`（冻结项与约束）。
- **后续改动的原则**：动接口先对 Contract/文档；动执行节点先看 PLAN_EXECUTION_NODES；不把业务状态塞进 indicators/contracts；密钥只走配置/环境变量。

---

## 最近做完的

- **执行节点扩展（Phase 1–5）**：dim_execution_node、心跳/节点列表 API、execution-node 服务（POST /api/execute、/api/sync-balance、/api/sync-positions）；signal-monitor 按 execution_node_id 分流，远程 POST 或投递 NODE_EXECUTE_QUEUE；node_execute_worker 消费队列并 POST 到节点；libs/sync_node、data-api 同步余额/持仓。
- **子机独立部署（方案 B）**：execution-node 改为从 live_trader/base 直引；`scripts/build_node_bundle.py` 打出 `dist/execution-node/`（最小依赖）；可执行文件说明见 `dist/execution-node/BUILD_EXECUTABLE.md`、`docs/ops/EXECUTION_NODE_BUILD.md`；PLAN_EXECUTION_NODES.md 第九节已改为「独立部署包或可执行文件」。
- **仅中心可调鉴权**：节点配置 `node_auth_enabled`、`node_auth_secret`（可选 `node_allowed_ips`），校验请求头 `X-Center-Token`；中心 signal-monitor、sync_node、node_execute_worker 在 POST 节点时带该头。详见 PLAN_EXECUTION_NODES.md 5.4 节。
- **子机自动心跳**：execution-node 配置 `center_url`（中心 data-api 地址）+ `node_code` 后，启动时自动定时 POST 中心 `/api/nodes/{node_code}/heartbeat`；支持 `heartbeat_interval`（默认 60s）；同时支持 `node_auth_secret` 鉴权头；GET /health 展示心跳状态。详见 PLAN_EXECUTION_NODES.md 5.3 节。

## 当前代码状态

- 鉴权已接在：services/execution-node/app/main.py（verify_center_token）、signal-monitor、libs/sync_node/service.py、scripts/node_execute_worker.py。
- 心跳已接在：services/execution-node/app/main.py（lifespan + _heartbeat_loop）。
- 未配置 `node_auth_secret` 时行为与之前一致（兼容）；未配置 `center_url` 或 `node_code` 时不发心跳（兼容）。

## 下次可以做的

- 在子机用 `dist/execution-node/` 实际打可执行文件（PyInstaller）并跑通。
- 配置中心与节点的 `node_auth_secret` + `center_url` + `node_code` 做联调验证。
- 其他业务或 NEXT_TASK.md 中的待办。

---
*新开聊天时：@SESSION_HANDOFF.md 然后说「按这个继续」即可接上进度。*
