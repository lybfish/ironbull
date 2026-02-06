# IronBull v0 — Implementation Status

> 本文件是唯一可信的“当前进度”来源。每做完一个模块就在这里登记。

## 已冻结基线（Frozen Baselines）
- ✅ v0 Project Directory Structure: Frozen
- ✅ v0.1 Module Contract: Frozen
- ✅ v1 Blueprint（事实层）: 冻结，仅作参考（v0 不展开）

## 已完成（Done）
### libs/core ✅
- 状态：已实现并可 import（config/logger/exceptions/utils）
- 说明：支持 default.yaml + env override；日志包含 service_name/request_id

### libs/contracts ✅
- 状态：已实现并验证通过（11 个 dataclass）
- 注意：__init__.py 未定义 __all__ 属于可选工程项，不影响 Contract

### libs/indicators ✅
- 状态：已实现并通过 import/基础计算验证
- 约束：纯计算，无 IO/网络/DB（已满足）

### services / nodes（骨架）✅
- services/signal-hub：已可跑（/health, /api/signals）
- services/risk-control：已可跑（/health, /api/risk/check）
- services/execution-dispatcher：已可跑（/health, /api/execution/submit, /api/execution/result/{task_id}）
- nodes/crypto-node：已可跑（/health, /api/node/execute）
- nodes/mt5-node：已可跑（/health, /api/node/execute）

### 最小链路 Demo ✅
- `scripts/demo_flow.sh` 本机跑通（Signal → Risk → Dispatcher → Node → Result）
- `scripts/demo_strategy_engine.sh` 本机跑通（Strategy → SignalHub → Risk → Dispatcher → Node → Result）

## 进行中（In Progress）
- （空）

## 已完成（Done）- v1 Phase 1 ✅

### libs/core/database.py ✅
- 状态：已实现（MySQL 连接池 + Session 管理）
- 功能：
  - 基于 SQLAlchemy 2.0 的数据库连接管理
  - 支持配置文件 + 环境变量
  - 连接池配置（pool_size/max_overflow/timeout/recycle）
  - get_db() 上下文管理器
- 配置：config/default.yaml 新增 db_* 配置项

### libs/facts (事实层) ✅
- 状态：已实现（4 个事实表 + Repository）
- 表结构：
  - **fact_trade**：交易记录（signal_id/task_id/account_id 索引）
  - **fact_ledger**：账本流水（手续费/盈亏等资金变动）
  - **fact_freeze**：冻结记录（保证金/风控冻结）
  - **fact_signal_event**：信号状态事件（完整链路追踪）
- Repository：FactsRepository 封装 CRUD + 链路查询
- 迁移脚本：migrations/001_facts_layer.sql

### 服务落库集成 ✅
- signal-hub：创建信号时记录 CREATED 事件
- risk-control：风控检查时记录 RISK_PASSED/RISK_REJECTED 事件
- execution-dispatcher：执行完成时记录 Trade + Ledger + EXECUTED/FAILED 事件
- 原则：落库失败不阻塞主流程（v0 兼容）

### 链路查询 API ✅
- GET /api/signals/{signal_id}/chain - 获取信号完整链路
- 返回：events + trades + ledgers

### 验证脚本 ✅
- scripts/init_facts_db.py - 初始化数据库表
- scripts/demo_facts_chain.sh - 验证完整链路

## 已完成（Done）- Phase 6 ✅

### services/backtest ✅
- 状态：已实现并可跑
- 功能：
  - BacktestEngine：回测引擎核心（历史数据回放 + 模拟交易）
  - 支持止损止盈检查
  - 计算基础指标（胜率/收益/回撤）
- 端点：
  - GET /health
  - POST /api/backtest/run（运行回测）
- 演示脚本：scripts/demo_backtest.sh, scripts/test_backtest_simple.py
- 验收：demo_backtest.sh 本机跑通
- 端口：8030
- 说明：v0 实现最小功能，支持 ma_cross 等策略

### 工程规范 ✅
- 日志规范：所有服务/节点日志统一包含 `service_name`/`request_id`
- 错误码统一：HTTP 错误统一返回 `{code, message, detail, request_id}`

## 已完成（Done）- v1 Phase 1 ✅
### Facts Layer（MySQL）✅
- 状态：已实现并接入（Trade/Ledger/FreezeRecord/SignalEvent）
- 迁移脚本：`migrations/001_facts_layer.sql`
- 初始化脚本：`scripts/init_facts_db.py`
- 说明：execution-dispatcher 在执行完成后写入事实层

## 已完成（Done）- Phase 5 ✅

### libs/strategies ✅
- 状态：已实现 21 个策略（完整迁移 old3）
- 策略分类：
  - **基础策略(6)**：ma_cross, macd, rsi_boll, boll_squeeze, breakout, momentum
  - **趋势策略(4)**：trend_aggressive, trend_add, swing, ma_dense
  - **震荡/反转策略(3)**：reversal, scalping, arbitrage
  - **对冲策略(3)**：hedge, hedge_conservative, reversal_hedge
  - **高级策略(5)**：smc, mtf, sr_break, grid, hft
- 功能：get_strategy(code) 动态加载，list_strategies() 列出所有
- 验证：全部 21 个策略导入和分析测试通过

### services/strategy-engine ✅
- 状态：已实现并可跑
- 端点：
  - GET /health
  - GET /api/strategies（列出可用策略）
  - POST /api/analyze（带 K 线数据触发分析）
  - POST /api/run（从 data-provider 获取数据并分析）
- 演示脚本：scripts/demo_strategy_engine.sh

### services/data-provider ✅
- 状态：已实现并可跑（mock 数据）
- 端点：
  - GET /health
  - GET /api/candles?symbol=...&timeframe=...&limit=...（单周期 K 线）
  - GET /api/mtf/candles?symbol=...&timeframes=...&limit=...（多周期 K 线）
  - GET /api/macro/events?from=...&to=...&country=...&impact=...（宏观事件）
- 演示脚本：scripts/demo_data_provider.sh
- 说明：v0 使用 mock 数据，后续可替换为真实数据源

### services/follow-service ✅
- 状态：已实现并可跑（mock 跟单关系 + 广播）
- 端点：
  - GET /health
  - POST /api/relations（创建跟单关系）
  - GET /api/relations（查询跟单关系）
  - DELETE /api/relations/{relation_id}
  - POST /api/broadcast（广播信号并提交到 dispatcher）
  - GET /api/tasks/{task_id}
- 演示脚本：scripts/demo_follow_service.sh
- 说明：v0 使用内存存储，后续可替换为 DB

### libs/runner + services/strategy-runner ✅
- 状态：已实现并可跑
- 功能：
  - StrategyRunner：定时/事件驱动的策略执行器
  - StrategyTask：策略任务配置
  - HTTP API 管理策略任务
- 端点（services/strategy-runner）：
  - GET /health
  - GET /api/strategies（获取可用策略列表）
  - POST /api/tasks（创建策略任务）
  - GET /api/tasks（列出所有任务）
  - GET /api/tasks/{task_id}（获取单个任务）
  - DELETE /api/tasks/{task_id}（删除任务）
  - POST /api/tasks/{task_id}/run（手动运行一次）
  - POST /api/tasks/{task_id}/enable（启用任务）
  - POST /api/tasks/{task_id}/disable（禁用任务）
  - POST /api/runner/start（启动调度循环）
  - POST /api/runner/stop（停止调度循环）
  - GET /api/runner/stats（获取运行统计）
- 演示脚本：scripts/demo_strategy_runner.sh

## 已完成（Done）- v1 Phase 2 ✅

### 状态机与审计 ✅
- 状态：已实现
- 状态机：`libs/facts/states.py`
  - SignalStatus：信号状态流转（PENDING → EXECUTED/FAILED）
  - ExecutionStatus：执行状态流转（PENDING → FILLED/FAILED）
  - TradeStatus：交易记录状态
  - AuditAction：审计动作枚举
- 审计表：`fact_audit_log`（追踪所有状态变更）
- 迁移脚本：`migrations/002_audit_log.sql`
- 服务集成：signal-hub、risk-control、execution-dispatcher

## 已完成（Done）- v1 Phase 3 ✅

### 队列与异步 ✅
- 状态：已实现并验证
- 组件：
  - `libs/core/redis_client.py`：Redis 连接池 + 常用操作
  - `libs/queue/task_queue.py`：任务队列（支持 DLQ、重试）
  - `libs/queue/idempotency.py`：幂等性检查器
  - `libs/queue/worker.py`：消费者 Worker 基类
- API（execution-dispatcher）：
  - POST /api/execution/submit-async：异步提交任务
  - GET /api/execution/queue/stats：队列状态
  - GET /api/execution/idempotency/{signal_id}：幂等性查询
- Worker：`services/execution-dispatcher/app/worker.py`
- 配置：`config/default.yaml` 新增 redis_* 配置
- 验证脚本：`scripts/demo_async_queue.sh`
- 功能：
  - 任务入队/出队（Redis List）
  - 幂等性检查（SETNX + TTL）
  - 处理队列 + 死信队列
  - 重试机制（max_retries=3）

## 已完成（Done）- v1 Phase 4 ✅

### 风控增强 ✅
- 状态：已实现并验证
- 组件：
  - `libs/risk/engine.py`：风控规则引擎
  - `libs/risk/rules.py`：内置规则实现
- 内置规则：
  - **MinBalanceRule**：最小余额检查
  - **MaxPositionRule**：最大持仓数量
  - **MaxPositionValueRule**：单仓最大价值
  - **DailyTradeLimitRule**：每日交易限额
  - **DailyLossLimitRule**：每日亏损限额
  - **WeeklyTradeLimitRule**：每周交易限额
  - **ConsecutiveLossCooldownRule**：连续亏损冷却
  - **TradeCooldownRule**：交易间隔冷却
  - **SymbolWhitelistRule**：品种白名单
  - **SymbolBlacklistRule**：品种黑名单
- API（risk-control）：
  - GET /api/risk/rules：列出所有规则
  - GET /api/risk/stats/{account_id}：账户风控统计
  - POST /api/risk/rules/{name}/enable：启用规则
  - POST /api/risk/rules/{name}/disable：禁用规则
- 配置：`config/default.yaml` 新增 risk_* 配置项
- 验证脚本：`scripts/demo_risk_rules.sh`

## 已完成（Done）- v1 Phase 5 ✅

### 数据与回测升级 ✅
- 状态：已实现并验证
- 组件：
  - `libs/exchange/client.py`：交易所客户端基类
  - `libs/exchange/binance.py`：Binance 客户端（ccxt）
  - `libs/exchange/okx.py`：OKX 客户端（ccxt）
  - `libs/exchange/utils.py`：工具函数（symbol 标准化等）
- 支持交易所：Binance, OKX
- data-provider 新增功能：
  - 真实 K 线数据（通过 ccxt）
  - 最新行情 API
  - 数据源切换（mock/live）
- 新增 API：
  - GET /api/exchanges：列出支持的交易所
  - GET /api/ticker：获取最新行情
  - GET /api/source：获取数据源配置
- 配置：`config/default.yaml` 新增 data_source, default_exchange
- 验证脚本：`scripts/demo_live_data.sh`
- 依赖：ccxt>=4.0.0

## 已完成（Done）- v1 Phase 7 ✅

### 真实合约交易执行 ✅
- 状态：已实现并验证（Binance USDT 永续合约）
- 组件：
  - `libs/trading/live_trader.py`：真实交易执行器
    - 支持 Binance USDT 永续合约（binanceusdm）
    - 支持双向持仓模式（LONG/SHORT）
    - 市价开仓 + 自动止盈止损
  - `libs/trading/auto_trader.py`：自动交易管理器
    - 三种模式：notify_only / confirm_each / auto_execute
    - 风控限制：单笔金额/每日次数/最大持仓/最低置信度
    - 交易记录管理
  - `libs/notify/telegram.py`：Telegram 通知
    - 信号推送、交易通知、系统告警
- 功能：
  - ✅ 市价开仓（MARKET）
  - ✅ 自动止损单（STOP_MARKET）
  - ✅ 自动止盈单（TAKE_PROFIT_MARKET）
  - ✅ 持仓查询
  - ✅ 订单查询
- 配置：`config/default.yaml` 新增：
  - exchange_api_key / exchange_api_secret
  - exchange_market_type: future
  - auto_trade_* 系列配置
- 验证：真实 Binance 合约交易测试通过

### services/signal-monitor ✅
- 状态：已实现并可跑
- 功能：
  - 信号监控服务（HTTP API）
  - Telegram 通知集成
  - 自动交易执行
- 端点：
  - GET /health
  - GET /api/status（监控状态）
  - POST /api/trading/enable（启用交易）
  - POST /api/trading/disable（禁用交易）
  - POST /api/trading/mode（切换模式）
  - POST /api/trading/execute（执行交易）
  - GET /api/trading/positions（当前持仓）
  - GET /api/trading/history（交易历史）
- 端口：8026

### 本地监控脚本 ✅
- 脚本：`scripts/local_monitor.py`
- 功能：
  - 定期运行策略检测信号
  - 自动执行交易（带止盈止损）
  - 监控持仓盈亏
  - 发送 Telegram 通知
- 用法：
  ```bash
  # 仅通知模式
  python3 scripts/local_monitor.py
  
  # 自动交易模式
  python3 scripts/local_monitor.py -m auto -i 60
  ```
- 参数：
  - `-s`：监控的交易对
  - `-t`：K线周期
  - `-m`：模式（notify/confirm/auto）
  - `-i`：检查间隔（秒）

### 策略置信度优化 ✅
- `libs/strategies/market_regime.py`：使用多因子加权评分
- `libs/strategies/smc_fibo.py`：综合多维度计算置信度

## 已完成（Done）- v1 Phase 8 ✅

### SaaS 核心模块重建 ✅
- 状态：已实现并验证（按 SaaS Blueprint 重建高风险模块）
- 遵循不变量：
  - 成交 ≤ 订单
  - 可用 + 冻结 = 总持仓/总余额
  - 变动有来源（append-only 流水）
  - 租户隔离

### libs/order_trade（订单/成交模块）✅
- 表结构：
  - **fact_order**：订单表（生命周期管理）
  - **fact_fill**：成交表（append-only）
- 组件：
  - `models.py`：Order/Fill 数据模型
  - `states.py`：OrderStatus 状态机 + FillValidation
  - `contracts.py`：DTOs（CreateOrderDTO/RecordFillDTO 等）
  - `exceptions.py`：异常定义
  - `repository.py`：数据访问层
  - `service.py`：OrderTradeService 业务逻辑
- 迁移脚本：`migrations/003_order_trade.sql`

### libs/position（持仓模块）✅
- 表结构：
  - **fact_position**：持仓状态表
  - **fact_position_change**：持仓变动历史（append-only）
- 组件：
  - `models.py`：Position/PositionChange 数据模型
  - `states.py`：PositionSide/ChangeType + 校验规则
  - `contracts.py`：DTOs（PositionDTO/UpdatePositionDTO 等）
  - `exceptions.py`：异常定义
  - `repository.py`：数据访问层
  - `service.py`：PositionService 业务逻辑
- 功能：
  - ✅ 成交驱动持仓更新（开仓/加仓/减仓/平仓）
  - ✅ 冻结/解冻机制
  - ✅ 加权平均成本计算
  - ✅ 已实现盈亏计算
  - ✅ 完整变动审计追踪
- 迁移脚本：`migrations/004_position.sql`

### libs/ledger（资金/账务模块）✅
- 表结构：
  - **fact_account**：资金账户表
  - **fact_transaction**：交易流水表（append-only）
  - **fact_equity_snapshot**：权益快照表
- 组件：
  - `models.py`：Account/Transaction/EquitySnapshot 数据模型
  - `states.py`：TransactionType/AccountStatus + 校验规则
  - `contracts.py`：DTOs（AccountDTO/TradeSettlementDTO 等）
  - `exceptions.py`：异常定义
  - `repository.py`：数据访问层
  - `service.py`：LedgerService 业务逻辑
- 功能：
  - ✅ 入金/出金管理
  - ✅ 交易结算（买入扣款/卖出入账/手续费）
  - ✅ 冻结/解冻机制
  - ✅ 权益快照（净值、收益率）
  - ✅ 完整流水审计追踪
- 迁移脚本：`migrations/005_ledger.sql`

### libs/trading/settlement.py（交易结算服务）✅
- 组件：TradeSettlementService
- 功能：
  - ✅ 协调 OrderTrade → Position → Ledger 三模块
  - ✅ 成交驱动的完整交易闭环
  - ✅ 幂等性保证（通过 fill_id 去重）
  - ✅ 原子性事务（同一 session）

### LiveTrader 集成 ✅
- 状态：已集成 TradeSettlementService
- 功能：
  - ✅ 支持 settlement_service 参数（完整交易闭环）
  - ✅ 向后兼容 order_trade_service（旧版）
  - ✅ 成交后自动更新持仓和资金

### signal-monitor / local_monitor 集成 ✅
- 状态：已集成 TradeSettlementService
- 功能：
  - ✅ 真实交易数据自动持久化到数据库
  - ✅ `--no-persist` 参数支持（可选关闭持久化）
  - ✅ 订单/成交/持仓/资金完整记录

## 已完成（Done）- v1 Phase 9 ✅

### libs/analytics（分析模块）✅
- 状态：已实现并验证
- 表结构：
  - **fact_performance_snapshot**：绩效快照（每日净值、收益率）
  - **fact_trade_statistics**：交易统计（胜率、盈亏比）
  - **fact_risk_metrics**：风险指标（夏普、回撤、VaR）
- 组件：
  - `models.py`：PerformanceSnapshot/TradeStatistics/RiskMetrics 数据模型
  - `states.py`：PeriodType 枚举 + MetricCalculator 计算器
  - `contracts.py`：DTOs（PerformanceSnapshotDTO/RiskMetricsDTO 等）
  - `exceptions.py`：异常定义
  - `repository.py`：数据访问层
  - `service.py`：AnalyticsService 业务逻辑
- 功能：
  - ✅ 绩效快照（每日净值、收益率、累计收益）
  - ✅ 风险指标计算：
    - 夏普比率 (Sharpe Ratio)
    - 索提诺比率 (Sortino Ratio)
    - 卡玛比率 (Calmar Ratio)
    - 最大回撤 (Max Drawdown)
    - VaR / CVaR
    - 年化收益率 / 年化波动率
  - ✅ 交易统计：
    - 胜率 / 盈亏比 / 获利因子
    - 最大连胜 / 最大连亏
    - 平均盈亏 / 最大单笔盈亏
  - ✅ 净值曲线生成
  - ✅ 绩效汇总
- 迁移脚本：`migrations/006_analytics.sql`

### SaaS 蓝图 9 大能力域 ✅
- **模块层完成度: 100% (9/9)**
  1. Strategy ✅ - libs/strategies
  2. MarketData ✅ - libs/exchange, data-provider
  3. Signal ✅ - 策略产出信号
  4. Backtest ✅ - services/backtest
  5. Execution ✅ - libs/trading/live_trader
  6. OrderTrade ✅ - libs/order_trade
  7. Position ✅ - libs/position
  8. Ledger ✅ - libs/ledger
  9. Analytics ✅ - libs/analytics

## 已完成（Done）- 执行节点扩展（Phase 1–5）✅

### 目标与约束
- 支持多台执行节点（子服务器）；中心按账户将执行任务下发到对应节点；节点只执行、不连库；凭证随请求下发，结果由中心写库与结算。

### Phase 1–3 ✅
- **dim_execution_node** 表；**fact_exchange_account.execution_node_id**；data-api：POST /api/nodes/{node_code}/heartbeat、GET /api/nodes。
- **services/execution-node**：POST /api/execute，接收 signal + tasks（含凭证），LiveTrader 执行，同步返回 results；不写库。
- **signal-monitor**：按 execution_node_id 分组，本机 LiveTrader、远程 POST 到节点；中心用 `libs/execution_node/apply_results.py` 写 fact_order/fact_fill 并触发结算。

### Phase 4 ✅
- execution-node：POST /api/sync-balance、POST /api/sync-positions（查交易所并返回，不写库）。
- **libs/sync_node**：向各节点请求余额/持仓，中心写 fact_account、fact_position。
- data-api：POST /api/sync/balance、POST /api/sync/positions 触发同步。

### Phase 5 ✅
- **NODE_EXECUTE_QUEUE**（Redis）：signal-monitor 配置 **use_node_execution_queue=True** 时，将远程节点任务投递到队列；否则直接 POST。
- **scripts/node_execute_worker.py**：消费队列，向节点 POST /api/execute，收到结果后调用 apply_remote_results 在中心写库与结算；支持 ack/nack 与死信。

### 鉴权 + 心跳 ✅
- **仅中心可调鉴权**：节点 `node_auth_enabled` + `node_auth_secret`（可选 `node_allowed_ips`）；中心 signal-monitor / sync_node / node_execute_worker 在 POST 节点时带 `X-Center-Token` 头。
- **子机自动心跳**：execution-node 配置 `center_url` + `node_code` 后，启动时自动定时 POST 中心 `/api/nodes/{node_code}/heartbeat`（默认 60s）；心跳同样支持 `node_auth_secret` 鉴权头；GET /health 展示心跳状态。

详见 [docs/context/PLAN_EXECUTION_NODES.md](context/PLAN_EXECUTION_NODES.md)。

## 已完成（Done）- 管理后台独立鉴权 + 平台管理 ✅

### dim_admin 独立管理员体系 ✅
- 状态：已实现并验证
- **设计**：后台管理员独立于 dim_tenant / dim_user，平台级超管可查看所有租户数据
- 组件：
  - `libs/admin/`：Admin model + AdminService（登录验证、改密码）
  - `libs/core/auth/jwt.py`：JWT payload 含 admin_id + username
  - `migrations/009_admin.sql`：dim_admin 表 + 初始账号(admin/admin123)
- 认证流程：
  - POST /api/auth/login（username + password → JWT）
  - GET /api/auth/me（JWT → admin info）
  - POST /api/auth/change-password
  - 管理员通过 query 参数 tenant_id 切换查看不同租户

### data-api 管理接口 ✅
- **Dashboard**：GET /api/dashboard/summary（平台汇总：租户/用户/订单/节点/绑定数）
- **租户管理**：GET/POST /api/tenants、PUT /api/tenants/:id、PATCH /api/tenants/:id/toggle
- **用户管理**：GET /api/users（支持按租户筛选）
- **管理员管理**：GET/POST /api/admins、PUT /api/admins/:id、PATCH /api/admins/:id/toggle、POST /api/admins/:id/reset-password

### admin-web 管理后台 ✅
- 状态：Vue 3 + Vite + Element Plus，端口 5174
- 页面（共 16 页）：
  - 概览 Dashboard（平台汇总 + 租户绩效）
  - 订单 / 成交 / 持仓 / 资金账户 / 流水（数据查看）
  - 绩效分析 / 策略管理 / 信号监控（业务监控）
  - 租户管理（CRUD + 启用禁用 + 查看密钥 + 充值点卡）
  - 用户管理（按租户筛选）
  - 管理员管理（创建/编辑/重置密码/启用禁用）
  - 策略绑定（只读查看）
  - 交易所账户（只读查看，API Key 脱敏）
  - 套餐管理（CRUD + 启停）
  - 提现管理（列表 + 通过/拒绝/完成操作）
- 登录：用户名 + 密码（无需 tenant_id），JWT 存 localStorage
- 租户/账户切换：右上角下拉，query 参数传递

## 已完成（Done）- 财务流水补全 + 提现完整流程 ✅

### 后台充值补流水 ✅
- `services/data-api/app/routers/tenants.py`：recharge 接口在更新 `point_card_self` / `point_card_gift` 后同步写入 `fact_point_card_log`
- 包含完整 before/after 余额快照

### fact_reward_log 奖励余额流水表 ✅
- 记录所有 `reward_usdt` 变动：奖励发放(`reward_in`) / 提现冻结(`withdraw_freeze`) / 拒绝退回(`withdraw_reject_return`)
- 组件：
  - `libs/reward/models.py`：`RewardLog` 模型
  - `libs/reward/repository.py`：`create_reward_log` + `list_reward_logs`
  - `libs/reward/service.py`：直推/级差/平级奖发放时写流水
  - `libs/reward/withdrawal_service.py`：提现申请/拒绝时写流水
  - `migrations/011_reward_log.sql`

### 提现完整生命周期 ✅
- `WithdrawalService` 四个方法：`apply()`(创建+冻结) → `approve()`(0→1 审核通过) → `complete()`(1→3 打款完成+累加 withdrawn_reward)；`reject()`(0→2 拒绝+退回余额)
- `data-api/routers/withdrawals.py`：GET 列表 + POST 通过/拒绝/完成 四个端点
- `admin-web/views/Withdrawals.vue`：提现管理页面（状态筛选、通过确认、拒绝弹窗输入理由、完成弹窗输入 TxHash）

### 测试覆盖 ✅
- `test_recharge_log.py`（2 例）：后台充值 self/gift 均写入 fact_point_card_log
- `test_withdrawal.py`（8 例）：申请/余额不足/低于最小/通过/拒绝退回+流水/重复拒绝/完成/未审核完成
- 全量 44 测试通过

## 已完成（Done）- Merchant API 对齐文档 ✅

### 接口修正（6 处差异）✅
- 对照 `_legacy_readonly/old3/quanttrade/docs/merchant-api.md` 逐一修正：
  1. `POST /merchant/user/create`：`inviter_id`(int) → `invite_code`(string)，通过邀请码查邀请人
  2. `GET /merchant/user/info`：补全 11 个字段（`inviter_invite_code`、`level`、`level_name`、`is_market_node`、`self_hold`、`team_direct_count`、`team_total_count`、`team_performance`、`reward_usdt`、`total_reward`、`withdrawn_reward`）
  3. `POST /merchant/user/transfer-point-card`：`from_user_id`/`to_user_id` → `from_email`/`to_email`
  4. `GET /merchant/user/rewards`：`source_email` 批量查询填充实际邮箱
  5. `GET /merchant/strategies`：补 `status` 字段
  6. 删除 3 个冗余接口：`user/balance`、`user/level`、`user/reward-balance`（数据已合并到 `user/info`）
- Merchant API 总接口数：22 → 19 个

---

## 风险/技术债（Known Debts）
- MTF 策略与宏观数据：v0 可先做“接口预留 + mock 数据”，不阻塞最小链路
- queue/持久化：v0 可先用内存队列或直接同步调用，v1 再换 Redis/Kafka
- 订单/成交审计：v1 才补（Trade/Ledger/FreezeRecord）

## 当前最小链路目标（MVP）
1) strategy-engine 生成 StrategyOutput
2) signal-hub 标准化为 Signal（status=pending）
3) risk-control 返回 RiskResult(passed=true) 并补齐 quantity/stop/tp（可先写死或最简规则）
4) dispatcher 路由到 node
5) node 返回 NodeResult(success=true)
6) dispatcher 输出 ExecutionResult(success=true)

完成标准：本机一键跑 demo，日志可追踪 request_id/signal_id/task_id。
