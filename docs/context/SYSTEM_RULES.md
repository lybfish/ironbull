# IronBull v0 — System Rules (Frozen)

## 0. 目标（v0）
- 先跑起来：K线 → Strategy → Signal → RiskControl → ExecutionDispatcher → Node → OrderResult
- 不自锁：模块独立、可替换、可扩展
- v1 再做：事实层/Trade/Ledger/冻结链路/全面审计

## 1. 冻结项（禁止修改）
### 1.1 目录结构冻结（v0）
- 顶层目录：services/ nodes/ libs/ config/ scripts/ docs/ docker/
- 服务边界不合并、不混放
- shared libs 只放纯公共能力（contracts/core/indicators/strategies）

### 1.2 Contract 冻结（v0.1）
- 禁止修改：libs/contracts 中 **字段名、字段类型、字段语义、可选性**
- 允许新增：仅 v1 扩展（新增 dataclass 或新增字段必须走 v1 版本）
- 允许修复：拼写错误/导入错误/循环依赖等“工程性问题”，但不得改变字段语义

### 1.3 模块边界冻结（v0）
- Strategy：只产出 StrategyOutput / Signal，不下单、不做风控、不查余额
- SignalHub：只做标准化/状态/广播，不做风控、不做下单
- RiskControl：只做过滤、止损止盈、仓位，不做下单
- Dispatcher：只做路由/队列/节点管理，不做策略/风控
- ExecutionNode：只做下单执行与回传结果，不做策略/风控/持仓管理

## 2. 允许项（实施阶段可做）
- 允许输出：模块骨架、服务入口、API routes、最小可运行 demo、启动脚本
- 允许实现：healthcheck、日志、配置加载、错误码规范（不影响 Contract）
- 允许替换：内部实现方式（HTTP/队列），但接口输入输出保持 Contract v0.1

## 3. 代码风格与工程约束
### 3.1 语言与依赖
- v0 推荐 Python（FastAPI/Flask 任一，先跑通即可）
- indicators 必须纯计算：无 IO、无网络、无 DB
- core 工具库：日志/配置/时间/重试/异常

### 3.2 配置与密钥
- 所有密钥只允许来自：环境变量或 config 文件（不硬编码）
- Node 端可支持：节点本地保存凭证（或 dispatcher 下发临时凭证），v0 不做强加密实现细节

### 3.3 可运行性
- 每个 service/node 必须可独立启动（最少 health endpoint）
- 最小链路必须可在本机用 mock 跑通

## 4. 交付与验收（v0）
- 每完成一个模块：必须给出
  - 启动方式（命令）
  - healthcheck 结果
  - 1 个最小 demo（输入→输出）
- 不追求全功能，但必须“跑得起来 + 可扩展”

## 5. 禁止的常见返工来源（强约束）
- 禁止“顺便重构目录/命名/Contract”
- 禁止跨层访问：Strategy 直接调用 Node、RiskControl 直接下单等
- 禁止把业务状态塞进 indicators 或 contracts
