# IronBull v1 — Next Task Plan (Facts Layer First)

> 目标：先把事实层（Trade/Ledger/FreezeRecord）落地到 MySQL，再做队列异步。
> 不改 v0 contract，不重构目录结构。

## Phase 1（必须）— 事实层基础（MySQL）
### 任务清单
1. 数据库连接与配置
   - 确定 MySQL 连接方式（环境变量 / config）
   - 新增最小 DB 连接模块（不影响现有模块）

2. 事实层数据模型（v1）
   - 表结构：Trade / Ledger / FreezeRecord
   - 必须包含索引：signal_id / task_id / account_id

3. 执行结果落库
   - execution-dispatcher 在完成执行后写入 Trade + Ledger
   - 失败/错误也要落库（error_code / error_message）

4. 信号链路状态落库（最小）
   - signal-hub / risk-control 记录状态变更（pending/passed/rejected/executed）

### 验收
- 一次 demo 产生完整事实链路记录
- 可通过 signal_id 查询：Signal → Risk → Execution → Trade/Ledger

---

## Phase 2（必须）— 状态机与审计
### 任务清单
- 统一状态机（Signal/Execution）
- 增加审计记录表（request_id/signal_id/task_id 对齐）
- 对失败/重试记录原因

### 验收
- 任一 signal_id 有完整状态流转记录
- 失败可追踪原因

---

## Phase 3（可选）— 队列与异步
### 任务清单
- Dispatcher → Node 改为队列
- Signal → Risk → Execution 支持异步
- 幂等与重试

### 验收
- 幂等性验证通过
- 高并发无重复下单

---

## Phase 4（可选）— 风控增强
### 任务清单
- 仓位/限额/冷却策略
- 风控原因码落库

---

## Phase 5（可选）— 数据与回测升级
### 任务清单
- data-provider 接真实数据
- backtest 使用真实历史数据

