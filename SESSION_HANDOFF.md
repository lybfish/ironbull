# 会话交接（新聊天时 @ 本文件再说「按这个继续」）

## 项目整体（后续改动能不跑偏）

- **项目**：IronBull — 量化/交易 SaaS。链路：策略 → 信号 → 执行（本机或子节点）→ 订单/成交/持仓/账本 → 点卡扣费与分销 → 分析。多租户、Merchant API、管理后台、data-api 查询。
- **中心 vs 子机**：中心有 DB/Redis，跑 signal-monitor、data-api、node_execute_worker 等；子机只跑 execution-node，**不连库**，中心 HTTP POST 下发任务与凭证，节点同步返回 results，中心写库与结算。详见 `docs/context/PLAN_EXECUTION_NODES.md`。
- **不能动的（见 docs/context/SYSTEM_RULES.md）**：目录结构（services/nodes/libs/config/scripts/docs）；libs/contracts 字段与语义；模块边界（Strategy 只产信号、Node 只执行不回写策略/风控）；禁止跨层调用（如 Strategy 直调 Node）。
- **关键文档**：`PLAN_EXECUTION_NODES.md`（执行节点）、`NEXT_TASK.md`（待办）、`IMPLEMENTATION_STATUS.md`（进度）、`SYSTEM_RULES.md`（冻结项与约束）。
- **后续改动的原则**：动接口先对 Contract/文档；动执行节点先看 PLAN_EXECUTION_NODES；不把业务状态塞进 indicators/contracts；密钥只走配置/环境变量。

---

## 最近做完的

### 执行节点（已完成）
- **Phase 1–5**：dim_execution_node、心跳/节点列表 API、execution-node 服务（POST /api/execute、/api/sync-balance、/api/sync-positions）；signal-monitor 按 execution_node_id 分流；node_execute_worker 消费队列并 POST 到节点。
- **子机独立部署**：`scripts/build_node_bundle.py` 打出 `dist/execution-node/`（最小依赖）。
- **仅中心可调鉴权**：节点 `node_auth_enabled` + `node_auth_secret` + 可选 `node_allowed_ips`，校验 `X-Center-Token`。
- **子机自动心跳**：配置 `center_url` + `node_code` 后自动定时 POST 中心心跳。
- **PyInstaller 打包验证通过**：`run.py` 直接 import app 对象（修复 string import 问题），47MB arm64 可执行文件，health/execute/sync-balance 接口正常。打包命令见 `dist/execution-node/BUILD_EXECUTABLE.md`。

### 管理后台（已完成）
- **独立管理员体系**：`dim_admin` 表独立于 dim_tenant / dim_user；JWT payload 含 `admin_id` + `username`；平台级超管，通过 `tenant_id` query 参数切换租户视角。初始账号：**admin / admin123**。
- **data-api 管理接口**：
  - 认证：POST /api/auth/login、GET /api/auth/me、POST /api/auth/change-password
  - Dashboard：GET /api/dashboard/summary（平台汇总）
  - 租户：GET/POST /api/tenants、PUT/PATCH、POST /:id/recharge（充值点卡）
  - 用户：GET /api/users（按租户筛选）
  - 管理员：GET/POST /api/admins、PUT/PATCH、POST /:id/reset-password
  - 策略绑定：GET /api/strategy-bindings-admin
  - 交易所账户：GET /api/exchange-accounts（API Key 脱敏）
- **admin-web 前端**（Vue 3 + Vite + Element Plus，端口 5174，共 15 页）：
  - 概览 Dashboard（平台汇总 + 租户绩效）
  - 订单 / 成交 / 持仓 / 资金账户 / 流水
  - 绩效分析 / 策略管理 / 信号监控
  - 租户管理（CRUD + 充值点卡 + 查看密钥）
  - 用户管理（按租户筛选）
  - 策略绑定 / 交易所账户
  - 管理员管理（创建/编辑/重置密码/启用禁用）

## 当前代码状态

- **节点鉴权**：services/execution-node/app/main.py、signal-monitor、libs/sync_node、node_execute_worker。
- **节点心跳**：services/execution-node/app/main.py（lifespan + _heartbeat_loop）。
- **管理后台鉴权**：libs/admin/、libs/core/auth/jwt.py、services/data-api/app/（deps.py + routers/auth.py）。
- **管理后台页面**：services/admin-web/src/（views/ 15 个页面，api/index.js，router/index.js，components/Layout.vue）。
- **文档已同步**：NEXT_TASK.md 平台层标记 ✅，IMPLEMENTATION_STATUS.md 新增管理后台章节。

### 中心-节点联调（已完成）
- **全链路已验证**：
  1. 节点注册：`dim_execution_node` 注册 `node-local-01`
  2. 心跳：execution-node 启动后自动每 10s POST `/api/nodes/{node_code}/heartbeat`，中心更新 `last_heartbeat_at` ✅
  3. 鉴权：无 token → 401、错误 token → 401、正确 token → 200 ✅
  4. 同步余额：中心 POST `/api/sync/balance` → 节点 POST `/api/sync-balance` → 查交易所 → 写回 `fact_account` ✅
  5. 同步持仓：链路完整（测试 key 无持仓查询权限导致 exchange error，代码无 bug）
- **关键配置**：`config/default.yaml` 新增 `node_auth_secret`；execution-node 通过 `IRONBULL_CENTER_URL`、`IRONBULL_NODE_CODE`、`IRONBULL_NODE_AUTH_SECRET` 等环境变量配置
- **Bug 修复**：execution-node `sys.path` 从 `../..` 改为 `../../..`，不再需要额外 `PYTHONPATH`

### 生产部署准备（已完成）
- **JWT Secret**：`libs/core/auth/jwt.py` 改为生产必须配置 `IRONBULL_JWT_SECRET`，未配置+`IRONBULL_ENV=production` 直接抛异常；开发环境输出 warning
- **CORS 收窄**：data-api + merchant-api 均从 `cors_origins` 配置读取允许域名（逗号分隔），未配置时仅允许 localhost 开发端口
- **admin-web 打包**：`npm run build` → `dist/`（2.5MB），gzip 后约 400KB
- **Nginx 配置**：`deploy/nginx.conf`（admin-web 静态资源 + /api/ 反代 data-api + merchant-api 独立 server）
- **启动脚本**：`deploy/start.sh`（start/stop/restart/status），加载 `.env.production` 环境变量
- **配置模板**：`deploy/env.production.example`（JWT、DB、Redis、CORS、node_auth 等）

### 配额计费（已完成）
- **数据库**：`dim_quota_plan`（4 级套餐：免费/基础/专业/企业）、`fact_api_usage`（每日用量）、`dim_tenant.quota_plan_id`
- **libs/quota**：`QuotaService` — 套餐 CRUD、API 配额检查（日/月）、资源配额检查（用户数/策略数/账户数）、用量记录与统计
- **merchant-api**：`check_quota` 依赖注入，请求前自动检查配额+记录用量，超限返回 429
- **data-api**：`/api/quota-plans` CRUD、`/api/tenants/{id}/assign-plan`、`/api/quota-usage/{tenant_id}`
- **admin-web**：套餐管理页面（CRUD + 启停）、租户页面新增套餐列 + 分配套餐功能
- **NEXT_TASK.md** 平台层全部 ✅

## 下次可以做的

- **平台层 100% + 模块层 100%**：核心功能全部完成
- 可选方向：UI 优化 / 性能优化 / 更多策略 / 监控告警 / 多语言 等
- 其他业务或 NEXT_TASK.md 中的待办

---
*新开聊天时：@SESSION_HANDOFF.md 然后说「按这个继续」即可接上进度。*
