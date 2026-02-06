# 会话交接

新开聊天时：**@SESSION_HANDOFF.md** 然后说「按这个继续」即可接上进度。

---

## 1. 项目整体

- **IronBull**：量化/交易 SaaS。链路：策略 → 信号 → 执行（本机或子节点）→ 订单/成交/持仓/账本 → 点卡扣费与分销 → 分析。多租户、Merchant API、管理后台(evui)、data-api 查询。
- **中心 vs 子机**：中心有 DB/Redis，跑 signal-monitor、data-api、node_execute_worker 等；子机只跑 execution-node，**不连库**，中心 HTTP POST 下发任务与凭证，节点同步返回 results，中心写库与结算。详见 `docs/context/PLAN_EXECUTION_NODES.md`。

---

## 2. 约束与原则

- **不能动的**（见 `docs/context/SYSTEM_RULES.md`）：目录结构（services/nodes/libs/config/scripts/docs）；libs/contracts 字段与语义；模块边界（Strategy 只产信号、Node 只执行）；禁止跨层调用。
- **关键文档**：`PLAN_EXECUTION_NODES.md`（执行节点）、`NEXT_TASK.md`（待办）、`IMPLEMENTATION_STATUS.md`（进度）、`SYSTEM_RULES.md`（冻结项）。
- **改动原则**：动接口先对 Contract/文档；动执行节点先看 PLAN_EXECUTION_NODES；不把业务状态塞进 indicators/contracts；密钥只走配置/环境变量。

---

## 3. 最近完成（摘要）

### 执行节点与部署
- Phase 1–5：dim_execution_node、心跳/节点列表 API、execution-node（POST /api/execute、sync-balance、sync-positions）；signal-monitor 按 execution_node_id 分流；node_execute_worker 消费队列并 POST 到节点。子机独立部署：`scripts/build_node_bundle.py` → `dist/execution-node/`；PyInstaller 打包见 `dist/execution-node/BUILD_EXECUTABLE.md`。
- 中心-节点联调：心跳、鉴权、同步余额/持仓全链路已验证；配置见 `config/default.yaml`（node_auth_secret）与 execution-node 环境变量。

### 管理后台与 data-api
- 独立管理员体系：dim_admin、JWT（admin_id + username），平台超管按 tenant_id 切换视角。初始账号：**admin / admin123**。
- data-api：认证(auth/login、me、change-password)、Dashboard、租户/用户/管理员/策略绑定/交易所账户、提现(withdrawals)、配额(quota-plans、quota-usage)、监控(monitor/status)、审计(audit-logs)。**点卡流水与奖励**：GET /api/pointcard-logs、GET /api/rewards 在 `main.py` 中显式注册，避免 404。
- 管理后台前端(evui)：Vue + Element，端口 5174；Dashboard、订单/成交/持仓/资金/流水、绩效/策略/信号、租户/用户/策略绑定/交易所账户/管理员、提现、配额、点卡流水、奖励记录、系统监控等。

### 财务与 Merchant API
- 后台充值写 fact_point_card_log；fact_reward_log（RewardLog）记录奖励/提现流水；提现完整流程：approve/reject/complete，data-api + evui 提现管理页。
- Merchant API 与文档 v1.3.1 对齐：19 个接口，member_id→user_id（返回层点卡流水保留 member_id 映射），入参 email 化、点卡转账分类型、status 对外 1/2 映射等。

### 奖励分配系统（全溯源重构）
- **RewardService 预算制重写**（`libs/reward/service.py`）：网体 20% 是硬预算上限，分配优先级：直推 > 级差 > 平级，预算用完即停，**不超发**。
- **全溯源**：所有资金去向均写入 `fact_user_reward` + `fact_reward_log`，每分钱可查。reward_type 区分：`tech_team`（10%技术）、`direct`/`direct_undist`（直推）、`level_diff`（级差）、`peer`/`peer_undist`（平级）、`network_undist`（网体剩余）、`platform_retain`（70%平台留存）。
- **租户隔离**：未分配资金归**对应租户的根账户**（`dim_user.is_root=1`），非全局统一账户。
- **租户累计字段**：`dim_tenant` 增加 `tech_reward_total`（累计技术分配）、`undist_reward_total`（累计网体未分配），每次分配自动更新。
- **ProfitPool 追踪字段**：`fact_profit_pool` 增加 7 个字段（tech_amount / network_amount / platform_amount / direct_distributed / diff_distributed / peer_distributed / network_undistributed）。
- **迁移**：`migrations/016_profit_pool_distribution_tracking.sql`、`migrations/017_tenant_reward_tracking.sql`。

### 租户根账户自动创建
- **创建租户自动建根账户**（`services/data-api/app/routers/tenants.py`）：POST /api/tenants 创建租户时自动生成 `is_root=1` 的用户并关联 `root_user_id`。
- **Pydantic v2 兼容**：status 字段支持 `"active"` / `1` 两种格式（`@field_validator(mode="before")`）。
- **前端修复**：`evui/src/views/tenant/index.vue` 的 `status: 'active'` 改为 `status: 1`。

### 前端租户奖励展示
- **后端** `_tenant_dict` 新增返回 `tech_reward_total`、`undist_reward_total` 字段。
- **前端** 租户主表格新增「技术累计」「未分配累计」两列；租户详情弹窗新增「奖励分配」区块（技术团队累计 10%、网体未分配累计、根账户累计收入）。

### 后台全面优化
- **响应格式统一**：所有 API 返回 `{"success": true, "data": ..., "total": ...}`，quota/nodes/monitor 等原 `{"code":0}` 格式已全部替换。
- **错误处理**：orders/positions/accounts/analytics/sync 全部加 try/except + logging，不再裸抛 500。
- **分页 total 修复**：positions/accounts/transactions 用 `count()` 返回真实总数，不再用 `len(当页数据)`。
- **sync 鉴权**：POST /api/sync/balance 和 /positions 加 `get_current_admin` 依赖，未登录返回 401。
- **密码 bcrypt 升级**：`libs/admin/service.py` + `admins.py` + `tenants.py` 全部用 bcrypt；**兼容旧 MD5**，管理员登录时自动升级为 bcrypt（无需手动迁移）。
- **分页参数统一**：audit_logs 的 `size` 改为 `page_size`，全部接口一致。
- **公共日期解析**：新建 `services/data-api/app/utils.py`（`parse_datetime` + `parse_date`），orders/accounts/analytics 统一引用，消除重复代码。
- **清理模板残留**：删除 25 个未使用的 vue 文件（system/user、role、menu、operlog、loginlog、data/、member/、message/、user/），减少包体积。

### 配额、监控、性能
- 配额：dim_quota_plan、fact_api_usage、QuotaService；merchant-api check_quota；data-api quota-plans、assign-plan、quota-usage。
- 监控：libs/monitor（health_checker、node_checker、db_checker、alerter）、monitor_daemon.py、GET /api/monitor/status、evui 监控页；deploy/start.sh 含 monitor-daemon。
- 性能：Dashboard 缓存 60s；订单/成交分页 total 与 count 一致；migrations/013 订单/成交列表索引。

### 实盘与交易所
- 小额实盘：scripts/live_small_test.py（--dry-run/--close/--cancel-orders/--sl-tp-only）；live_trader（Gate/OKX/Binance）；Gate 统一账户、仓位级止盈止损；OKX 仓位级 SL/TP；文档 docs/ops/LIVE_SMALL_TEST.md。

### 生产与启动
- JWT 生产必须配置 IRONBULL_JWT_SECRET；CORS 从配置读取；deploy/start.sh（.env.production）、deploy/env.production.example。**注意**：start.sh 中 `declare -A` 的 key 若含连字符需加引号（如 `["data-api"]`），否则 set -u 下会报 unbound variable。

### 策略与租户策略实例
- **设计**：`dim_strategy` 为主策略表（平台级）；`dim_tenant_strategy` 为租户策略实例表，决定「该租户下对用户展示哪些策略」及杠杆、单笔金额、最低资金、展示名/描述等覆盖；用户/商户看到的策略列表仅来自租户实例（join 主策略）；实例可「一键从主策略复制参数」。
- **迁移**：`migrations/014_strategy_show_to_user.sql`（dim_strategy 增加 show_to_user、user_display_name、user_description）；`migrations/015_tenant_strategy_instance.sql`（新建 dim_tenant_strategy）。执行脚本：`PYTHONPATH=. python3 scripts/run_migrations_014_015.py`（使用项目 config 连库，幂等）。
- **data-api**：租户策略实例 CRUD：GET/POST /api/tenants/{id}/tenant-strategies，PUT/DELETE /api/tenants/{id}/tenant-strategies/{instance_id}，POST .../copy-from-master。**路由**：tenant_strategies 必须在 tenants 之前注册，否则 GET /api/tenants/2/tenant-strategies 会 404。Pydantic v2：更新策略/租户实例使用 `model_dump(exclude_unset=True)`；withdrawals 审核/拒绝使用 `admin["admin_id"]`（勿用 `admin["id"]`）。
- **Merchant API**：GET /merchant/strategies 按当前租户查 dim_tenant_strategy(status=1) 并 join 主策略；POST /merchant/user/strategy/open 开通前校验该租户存在对应策略实例且 status=1；GET /merchant/user/strategies 展示名优先用租户实例 display_name。
- **信号与执行**：按租户解析 amount_usdt/leverage（signal-monitor `_resolve_amount_leverage_for_tenant`）；`get_execution_targets_by_strategy_code` 仅返回「该租户策略实例存在且 status=1」的 target；execution-node TaskItem 支持 `leverage`；node_execute_worker 转发时带上每 task 的 amount_usdt/leverage。
- **evui**：运营管理 → 租户策略（/operation/tenant-strategies）；选租户后列表/新增/编辑/删除/一键复制主策略；新增实例时勾选「一键复制」会拉取主策略详情并预填表单（展示名、描述、杠杆、单笔金额、最低资金），样式为复选框 + 单独一行灰色说明。

---

## 4. 关键文件索引

| 领域           | 位置 |
|----------------|------|
| 节点鉴权/心跳  | services/execution-node/app/main.py、libs/sync_node、node_execute_worker |
| 管理后台鉴权   | libs/admin/、libs/core/auth/jwt.py、data-api/deps.py、routers/auth.py |
| 管理后台前端   | evui/src/（views/、api/、router/） |
| 策略与租户实例 | libs/member/models.py（Strategy、TenantStrategy）、repository.py；data-api/routers/strategies.py、tenant_strategies.py；merchant-api/routers/strategy.py；evui/views/tenant/tenant-strategies.vue |
| 信号/执行按租户 | services/signal-monitor/app/main.py（_resolve_amount_leverage_for_tenant、execute_signal_by_strategy）；libs/member/service.py（get_execution_targets_by_strategy_code 校验租户实例）；execution-node TaskItem.leverage；scripts/node_execute_worker.py |
| 奖励分配（全溯源）| libs/reward/service.py（RewardService，预算制 cap）、libs/reward/models.py（ProfitPool 追踪字段）|
| 公共工具       | services/data-api/app/utils.py（parse_datetime、parse_date）|
| 点卡/奖励/提现 | libs/pointcard/、libs/reward/、data-api/routers/tenants.py、withdrawals.py、user_manage.py |
| 配额           | libs/quota/、data-api/routers/quota.py |
| 监控           | libs/monitor/、scripts/monitor_daemon.py、data-api/routers/monitor.py |
| Merchant API   | services/merchant-api/app/routers/（user、reward、pointcard、strategy） |
| 实盘/交易所    | scripts/live_small_test.py、libs/trading/live_trader.py、libs/exchange/ |
| 迁移与测试     | migrations/（014-017）；scripts/run_migrations_014_015.py、test_data_api_all.py、test_full_business.py、test_reward_distribution.py |

---

## 5. 当前状态

- **evui**：多页管理后台，订单/成交/持仓/资金/流水、绩效/策略/信号、租户/用户/提现/配额/点卡流水/奖励/监控、**租户策略**（按租户管理策略实例、一键复制主策略、新增时自动带出参数）等。租户详情新增**奖励分配区块**（技术累计、未分配累计）。已清理模板残留文件（25 个）。
- **data-api**：管理接口齐全；响应格式全部统一为 `{"success":true,"data":...}`；所有查询接口加 try/except 错误处理；分页 total 用 count() 真实计数；sync 接口加鉴权；密码用 bcrypt（兼容旧 MD5 自动升级）；公共 utils 提取日期解析。
- **Merchant API**：策略列表与开通按租户实例；用户已绑定列表展示名用租户实例。
- **执行节点**：中心-节点联调通过；按租户解析 amount/leverage；子机可独立部署与打包。
- **数据库**：需执行 014-017 后所有功能才正常。014-015 可用 `scripts/run_migrations_014_015.py`；016-017 直接用 mysql 执行 `migrations/016_*.sql` 和 `migrations/017_*.sql`。
- **奖励分配**：全溯源已完成，7 个场景 97 项校验通过（含超发 cap、租户隔离、无邀请人、自持不足等边界情况）。
- **租户**：2 个活跃租户，均有根账户。新建租户自动创建根账户。

---

## 6. 注意事项（策略/租户实例相关）

- 新环境或未跑过 014/015 时：先执行 `scripts/run_migrations_014_015.py`，否则租户策略接口可能 503 或表不存在。
- data-api 中 `tenant_strategies` 路由必须挂在 `tenants` 之前，否则 `/api/tenants/{id}/tenant-strategies` 会被 tenants 的 `/{tenant_id}` 吃掉导致 404。
- 全量接口自测：`scripts/test_data_api_all.py`（需先登录拿到 token）；说明见 `scripts/README_DATA_API_TEST.md`。

---

## 7. 后续可选

- **部署到生产**：执行迁移 016-017，补建已有租户的根账户（脚本逻辑已有，见会话记录），部署最新代码
- 构建体积优化（大 chunk 代码分割、路由懒加载）
- 监控告警增强（更多端点、历史告警、邮件/钉钉通道）
