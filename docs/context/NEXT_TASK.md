# IronBull v0 — Next Task Plan

## ✅ 最近完成

### 管理后台增强（2026-02）
- ✅ **策略管理页**：策略目录表、按租户策略绑定列表（用户/点卡/状态/盈亏），点卡为 0 提示不执行
- ✅ **信号监控页**：data-api 代理 GET /api/signal-monitor/status，展示运行状态、检测次数、最近信号
- ✅ **data-api**：GET /api/strategies、GET /api/strategy-bindings、GET /api/signal-monitor/status

### 点卡与分销闭环（2026-02）
- ✅ **开策略校验点卡**：`MemberService.open_strategy` 支持 `min_point_card`，不足则拒绝开通；Merchant API 默认至少 1 点卡
- ✅ **盈利扣费后自动分销**：`PointCardService.deduct_for_profit` 写利润池后立即调用 `RewardService.distribute_for_pool`，直推/级差/平级自动结算

### 实盘验证（2026-02）
- ✅ **scripts/verify_live_loop.py**：轮询数据库数据量与最新记录，报告分析指标是否可计算
- ✅ **docs/ops/LIVE_VERIFY.md**：实盘验证说明（配置前提、local_monitor / verify_live_loop 运行指南、验证项清单）

### Data API - 统一查询接口（2026-02）
- ✅ **services/data-api**（FastAPI，8026）：/api/orders、/api/fills、/api/positions、/api/accounts、/api/transactions、/api/analytics/performance、/api/analytics/risk、/api/analytics/statistics；query 参数 tenant_id 必填、account_id 可选

### Phase 10+ - 信号与策略绑定多账户执行（2026-02）
- ✅ **libs/member**：`ExecutionTarget` + `MemberService.get_execution_targets_by_strategy_code(strategy_code)`，按策略返回绑定账户及执行所需凭证
- ✅ **signal-monitor**：按策略分发（`dispatch_by_strategy` / `strategy_dispatch_amount`），有信号时查 binding → 每账户创建 LiveTrader+TradeSettlementService 执行；无绑定时回退单账户 AutoTrader

### Phase 10 - 多租户与 Merchant API（2026-02-06）
- ✅ **平台层表**：dim_tenant, dim_user, fact_exchange_account, dim_strategy, dim_strategy_binding, fact_point_card_log, fact_profit_pool, fact_user_reward, fact_user_withdrawal, dim_level_config, fact_api_log
- ✅ **Merchant API**：22 个接口（用户/点卡/策略/奖励），AppKey+Sign 认证，端口 8010/8011
- ✅ **结算触发点卡**：`TradeSettlementService.settle_fill` 在 realized_pnl > 0 时自动调用点卡扣费 30%（需 account_id 对应 fact_exchange_account.id）

### Phase 9 - Analytics 分析模块（2026-02-06）
- ✅ **Analytics 模块**：绩效分析与风险指标
  - fact_performance_snapshot / fact_trade_statistics / fact_risk_metrics 表
  - 绩效指标：收益率、净值、累计收益
  - 风险指标：夏普比率、索提诺比率、最大回撤、VaR/CVaR
  - 交易统计：胜率、盈亏比、获利因子、连胜/连亏
  - 净值曲线生成
- ✅ **signal-monitor / local_monitor 集成**
  - 真实交易数据自动持久化
  - `--no-persist` 参数支持

### Phase 8 - SaaS 核心模块重建（2026-02-05）
- ✅ **OrderTrade 模块**：订单/成交事实记录
- ✅ **Position 模块**：持仓管理
- ✅ **Ledger 模块**：资金/账务管理
- ✅ **TradeSettlementService**：交易结算服务
- ✅ **LiveTrader 集成**：支持 settlement_service

### Phase 7 - 真实合约交易（2026-02-05）
- ✅ Binance USDT 永续合约交易
- ✅ 双向持仓模式支持（LONG/SHORT）
- ✅ 自动止盈止损订单
- ✅ Telegram 通知集成
- ✅ signal-monitor 服务 + 本地监控脚本

---

## 🎯 SaaS 蓝图进度

### 模块层（Modules）- 100% ✅
```
┌─────────────────────────────────────────────────────────────────┐
│ 能力域       │ 状态  │ 实现位置                                 │
├─────────────────────────────────────────────────────────────────┤
│ 1. Strategy  │  ✅   │ libs/strategies (21个策略)              │
│ 2. MarketData│  ✅   │ libs/exchange, data-provider            │
│ 3. Signal    │  ✅   │ 策略产出信号                             │
│ 4. Backtest  │  ✅   │ services/backtest                       │
│ 5. Execution │  ✅   │ libs/trading/live_trader                │
│ 6. OrderTrade│  ✅   │ libs/order_trade                        │
│ 7. Position  │  ✅   │ libs/position                           │
│ 8. Ledger    │  ✅   │ libs/ledger                             │
│ 9. Analytics │  ✅   │ libs/analytics                          │
└─────────────────────────────────────────────────────────────────┘
```

### 平台层（Platform）- 部分完成
```
┌─────────────────────────────────────────────────────────────────┐
│ 能力           │ 状态  │ 说明                                   │
├─────────────────────────────────────────────────────────────────┤
│ 租户管理        │  ✅   │ dim_tenant, TenantService              │
│ 用户管理        │  ✅   │ dim_user, MemberService, 邀请链路      │
│ 认证鉴权        │  ✅   │ Merchant API AppKey+Sign               │
│ 点卡/奖励       │  ✅   │ 点卡扣费、利润池、分销自动结算、开策略校验点卡 │
│ 角色权限        │  ❌   │ 无 Role/Permission                     │
│ 配额计费        │  ❌   │ 未实现                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 下一步建议

### 选项 1：REST API 接口（推荐优先级：⭐⭐⭐⭐⭐）✅ 已完成
**目标**：为所有模块创建统一的查询 API

**实现**：`services/data-api`（FastAPI，端口 8026）
- [x] GET /api/orders - 订单查询
- [x] GET /api/fills - 成交查询
- [x] GET /api/positions - 持仓查询
- [x] GET /api/accounts - 资金账户查询
- [x] GET /api/transactions - 流水查询
- [x] GET /api/analytics/performance - 绩效与净值曲线
- [x] GET /api/analytics/risk - 风险指标
- [x] GET /api/analytics/statistics - 交易统计

**产出**：统一查询能力，通过 query 参数 tenant_id（必填）、account_id（可选）做隔离。

---

### 选项 2：多租户与身份（推荐优先级：⭐⭐⭐⭐）✅ 部分完成
**目标**：平台层建设与管理后台鉴权

**已实现**：
- [x] Tenant / User 表（dim_tenant, dim_user）已有
- [x] 管理后台登录：POST /api/auth/login（tenant_id + email + password）→ JWT
- [x] data-api 鉴权：请求头 `Authorization: Bearer <token>` 时从 JWT 取 tenant_id，无 token 时需 query 传 tenant_id
- [x] admin-web 登录页、token 存储、请求头携带、退出与路由守卫

**可选后续**：JWT 刷新、角色/权限中间件、生产环境配置 jwt_secret

---

### 选项 3：前端管理界面（推荐优先级：⭐⭐⭐）✅ 已完成
**目标**：Web 界面管理和监控

**实现**：`services/admin-web`（Vue 3 + Vite + Element Plus，端口 5174）
- [x] Dashboard（概览：订单/成交/持仓数、绩效摘要）
- [x] 订单 / 成交 / 持仓 / 资金账户 / 流水 列表页
- [x] 绩效分析（绩效汇总、净值曲线 ECharts、风险指标）
- [x] 策略管理页面（策略目录 + 按租户绑定列表、点卡展示）
- [x] 信号监控页面（signal-monitor 状态代理、运行状态/最近信号）

**产出**：对接 data-api，支持切换租户/账户，`npm run dev` 启动。

---

### 选项 4：实盘验证（推荐优先级：⭐⭐⭐⭐⭐）✅ 已完成
**目标**：小资金实盘测试，验证完整闭环

**说明**：见 `docs/ops/LIVE_VERIFY.md`；脚本 `scripts/verify_live_loop.py` 可轮询检查数据与指标可算性。

**启动命令**：
```bash
cd /Users/pro/Documents/www/server/nginx/html/ironbull
python3 scripts/local_monitor.py -m auto -i 60
# 另终端运行：python3 scripts/verify_live_loop.py
```

**验证项**：
- [x] 订单数据正确写入 fact_order
- [x] 成交数据正确写入 fact_fill
- [x] 持仓实时更新 fact_position
- [x] 资金正确结算 fact_account
- [x] 分析指标可计算（由 verify_live_loop 检查）

---

### 选项 5：子服务器/执行节点扩展 ✅ 已完成（Phase 1–5）
**目标**：支持多台执行节点，中心按账户将任务下发到对应节点；节点只执行、不碰库。

**已实现**（详见 [docs/context/PLAN_EXECUTION_NODES.md](context/PLAN_EXECUTION_NODES.md)）：
- Phase 1：节点表 dim_execution_node、心跳 API、GET /api/nodes
- Phase 2：fact_exchange_account.execution_node_id，signal-monitor 按节点分流并 POST 到节点，中心写库与结算
- Phase 3：services/execution-node 提供 POST /api/execute，收任务+凭证，同步返回 results
- Phase 4：节点 POST /api/sync-balance、/api/sync-positions；中心 libs/sync_node + data-api POST /api/sync/balance、/api/sync/positions
- Phase 5：use_node_execution_queue 配置；NODE_EXECUTE_QUEUE；scripts/node_execute_worker.py 消费队列并 POST 到节点、写库结算  

---

## 🎯 推荐路径

### 路径 A：API + 前端（推荐）
```
1. REST API 接口 - 数据查询能力
   ↓
2. 前端管理界面 - 可视化展示
   ↓
3. 多租户与身份 - 平台层
```

### 路径 B：平台层优先
```
1. 多租户与身份 - 基础架构
   ↓
2. REST API 接口 - 带权限控制
   ↓
3. 前端管理界面
```

---

## 💡 建议

基于当前进度，推荐**路径 A（API + 前端）**：

1. **模块层 100% 完成**：9 大能力域全部实现
2. **数据已持久化**：交易数据可入库
3. **缺少查询能力**：目前只能直接查数据库
4. **缺少可视化**：没有前端界面

---

## 📝 注意事项

### ✅ 已解决的技术债
- ~~OrderTrade/Position/Ledger 需要重建~~ → 已完成！
- ~~v0 没有持久化~~ → 已有完整事实表
- ~~signal-monitor 未集成新模块~~ → 已集成！
- ~~Analytics 模块缺失~~ → 已实现！

### 当前技术债
- v0 使用内存存储（signal-hub/follow-service）
- v0 没有认证（所有 API 开放）
- 缺少 REST API 查询接口
- 没有前端界面

---

## 🎓 当前架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              应用层 (Apps)                                   │
│   signal-monitor │ local_monitor │ (前端待建)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                              模块层 (Modules) ✅                             │
│ ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────────┐│
│ │Strategy │MarketDat│ Signal  │Backtest │Execution│OrderTrd │  Position   ││
│ │   ✅    │   ✅    │   ✅    │   ✅    │   ✅    │   ✅    │     ✅      ││
│ └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────────┘│
│ ┌─────────┬─────────┬─────────────────────────────────────────────────────┐│
│ │ Ledger  │Analytics│                  Settlement                         ││
│ │   ✅    │   ✅    │                     ✅                              ││
│ └─────────┴─────────┴─────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│                              平台层 (Platform) ❌                            │
│   Tenant │ User │ Role │ Permission │ Auth │ Audit │ Quota                 │
│    ❌    │  ❌  │  ❌  │     ❌     │  ❌  │  ⚠️   │  ❌                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

**请告知您希望优先推进哪个方向。**

---

**最后更新**: 2026-02-06  
**当前版本**: v0 (Phase 9 - Analytics 分析模块)
