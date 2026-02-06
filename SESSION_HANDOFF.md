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

## 关键文件索引

- **节点鉴权**：services/execution-node/app/main.py、signal-monitor、libs/sync_node、node_execute_worker
- **节点心跳**：services/execution-node/app/main.py（lifespan + _heartbeat_loop）
- **管理后台鉴权**：libs/admin/、libs/core/auth/jwt.py、services/data-api/app/（deps.py + routers/auth.py）
- **管理后台页面**：services/admin-web/src/（views/ 17 个页面，api/index.js，router/index.js，components/Layout.vue）
- **监控告警**：libs/monitor/（health_checker + node_checker + db_checker + alerter）、scripts/monitor_daemon.py、services/data-api/app/routers/monitor.py
- **财务流水**：libs/pointcard/（models + service）、libs/reward/（models + service + withdrawal_service + repository）
- **提现管理**：libs/reward/withdrawal_service.py、services/data-api/app/routers/withdrawals.py、admin-web/views/Withdrawals.vue
- **Merchant API**：services/merchant-api/app/routers/（user/reward/pointcard/strategy）— 19 个接口
- **迁移脚本**：migrations/（001–012），最新 012_rename_member_id_to_user_id.sql

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

### 财务流水补全 + 提现完整流程（已完成）
- **后台充值补流水**：`data-api/routers/tenants.py` recharge 接口在更新余额时同步写入 `fact_point_card_log`
- **新增 fact_reward_log 表**：记录所有 `reward_usdt` 变动（奖励发放 reward_in / 提现冻结 withdraw_freeze / 拒绝退回 withdraw_reject_return），含 before/after 余额快照
  - `libs/reward/models.py` 新增 `RewardLog` 模型
  - `libs/reward/service.py` 直推/级差/平级奖发放时写流水
  - `libs/reward/withdrawal_service.py` 提现申请/拒绝时写流水
  - 迁移 SQL：`migrations/011_reward_log.sql`
- **提现完整生命周期**：
  - `WithdrawalService` 新增 `approve()`（0→1 审核通过）、`reject()`（0→2 拒绝+退回余额+写流水）、`complete()`（1→3 打款完成+累加 withdrawn_reward）
  - `data-api/routers/withdrawals.py`：GET 列表 + POST 通过/拒绝/完成
  - `admin-web/views/Withdrawals.vue`：提现管理页面（状态筛选、通过确认、拒绝弹窗、完成弹窗填 TxHash）
- **测试**：`test_recharge_log.py`（2例）+ `test_withdrawal.py`（8例），全量 44 测试通过

### Merchant API 全量对齐文档 v1.3.1（已完成）
- 对照 `_legacy_readonly/old3/quanttrade/docs/merchant-api.md` v1.3.1，分三轮完成全部对齐：
- **第一轮（6 处差异）**：
  1. `POST /merchant/user/create`：`inviter_id`(int) → `invite_code`(string)
  2. `GET /merchant/user/info`：补全 11 个字段（level/team/reward 等）
  3. `POST /merchant/user/transfer-point-card`：`from_user_id`/`to_user_id` → `from_email`/`to_email`
  4. `GET /merchant/user/rewards`：`source_email` 批量查询填充
  5. `GET /merchant/strategies`：补 `status` 字段
  6. 删除 3 个冗余接口，22 → 19 个
- **第二轮（member_id 统一 + 字段修正）**：
  7. 全项目 `member_id` → `user_id`（模型/仓库/合约/服务/脚本），迁移 `012_rename_member_id_to_user_id.sql`
  8. `GET /user/team` 列表移除 `self_hold`，`team_stats` 改用 `total_performance`
  9. `GET /point-card/logs` 分发记录用 `CHANGE_DISTRIBUTE=3` + `related_user_id`
- **第三轮（v1.3.0 + v1.3.1 对齐）**：
  10. **12 个接口入参 `user_id` 统一改为 `email`**（user/info、apikey、unbind、recharge、logs、strategy open/close/strategies、team、set-market-node、rewards、withdraw、withdrawals）
  11. **点卡转账改为类型分开**：新增 `type` 参数（1=自充互转 self→self，2=赠送互转 gift→gift），返回 `type`/`type_name`/`from_self_after`/`from_gift_after`/`to_self_after`/`to_gift_after`
  12. 点卡流水响应字段 `user_id` → `member_id`（仅返回层映射，内部统一 `user_id`）
- 19 个接口请求参数和返回字段全部与文档 v1.3.1 一致

### 监控告警系统（已完成）
- **libs/monitor/ 模块**（4 个组件）：
  - `health_checker.py`：并发 HTTP GET 各服务 `/health`，返回 status/latency/error
  - `node_checker.py`：查 `dim_execution_node` 心跳超时检测（默认 180s）
  - `db_checker.py`：MySQL `SELECT 1` + Redis `ping` 连通性检测
  - `alerter.py`：告警管理器 — 集成 Telegram 通知、同一告警去重（cooldown）、恢复通知
- **scripts/monitor_daemon.py**：巡检守护脚本，定时循环（默认 60s）执行三项检查，状态变更触发 Telegram 告警。支持 `--interval` / `--services` 参数，SIGINT/SIGTERM 优雅退出
- **data-api GET /api/monitor/status**：实时返回所有服务 + 节点 + DB/Redis 状态（需 admin JWT）
- **admin-web 系统监控页面**（Monitor.vue）：系统状态卡片、服务健康列表（绿/红灯）、节点在线状态表、DB/Redis 详情面板、30 秒自动刷新
- **config/default.yaml**：新增 `monitor_enabled`、`monitor_interval`、`monitor_services`、`monitor_node_timeout`、`monitor_alert_cooldown` 配置项
- **deploy/start.sh**：新增 `monitor-daemon` 服务（start/stop/restart/status）
- **测试**：22 个用例（HealthChecker 5 + NodeChecker 4 + DbChecker 4 + Alerter 9），全部通过

## 当前代码状态

- **admin-web 前端**：共 17 页（新增系统监控页）
- **Merchant API**：19 个接口，与文档 v1.3.1 完全对齐（全部 email 化、转账分类型）
- **财务闭环**：所有余额变动（点卡、奖励）均有流水记录；提现有完整审核流程
- **监控告警**：轻量级巡检守护 + Telegram 告警 + 管理后台监控面板
- **命名统一**：全项目 `member_id` → `user_id`，仅 point-card/logs 返回层映射为 `member_id`
- **测试**：69 个用例全部通过（原 47 + 监控模块 22）

### 性能与稳定性优化（已完成）
- **Dashboard 缓存**：`GET /api/dashboard/summary` 使用 Redis 缓存 60s（key: `ironbull:cache:dashboard:summary`），Redis 不可用时自动回退到直查 DB；响应增加 `cached: true/false`
- **订单/成交分页 total**：`count_orders` / `count_fills` 与 `list_orders` / `list_fills` 使用相同过滤条件；`list_orders` / `list_fills` 返回 `(list, total)`；`GET /api/orders`、`GET /api/fills` 的 `total` 为符合条件的总条数（不再为当前页条数）
- **索引迁移**：`migrations/013_perf_order_fill_list_indexes.sql` 新增 `idx_order_tenant_account_time`、`idx_fill_tenant_account_time`，优化按租户+账户+时间排序的列表查询

## 下次可以做的

- **平台层 100% + 模块层 100%**：核心功能全部完成
- 可选方向：
  - admin-web 构建验证（`npm run build`）
  - UI 优化 / 更多策略 / 多语言
  - 监控告警增强（更多服务端点、历史告警日志、邮件通道）
  - 文档持续同步

---
*新开聊天时：@SESSION_HANDOFF.md 然后说「按这个继续」即可接上进度。*
