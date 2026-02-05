# 实盘闭环验证指南

小资金实盘跑通「信号 → 下单 → 成交 → 持仓 → 资金 → 点卡/分析」完整链路，并核对数据落库是否正确。

---

## 1. 前置条件

- **数据库**：已执行迁移，存在 `fact_order`、`fact_fill`、`fact_position`、`fact_account` 等表。
- **配置**：与 local_monitor 一致，需在环境或配置文件中设置：
  - `exchange_api_key`、`exchange_api_secret`（交易所 API）
  - `tenant_id`、`account_id`（默认 1、1，用于结算与持久化）
  - `database_url` 或 `db_*`（MySQL 连接）
- **可选**：`exchange_sandbox=true` 时使用测试网，避免主网资金风险。

---

## 2. 启动本地监控（产生交易）

```bash
cd /path/to/ironbull

# 自动执行模式，每 60 秒检查一次信号；交易结果持久化到 DB
python3 scripts/local_monitor.py --mode auto --interval 60

# 仅通知、不执行（先看信号）
# python3 scripts/local_monitor.py --mode notify --interval 60

# 不落库（仅测策略与下单，不写 fact_*）
# python3 scripts/local_monitor.py --mode auto --interval 60 --no-persist
```

保持运行一段时间，直到至少产生 1 笔订单/成交（可先用 `notify` 或 `confirm` 观察再切 `auto`）。

---

## 3. 运行验证脚本

在**另一终端**执行（可与 local_monitor 同时跑）：

```bash
cd /path/to/ironbull
python3 scripts/verify_live_loop.py
```

指定租户/账户时：

```bash
python3 scripts/verify_live_loop.py --tenant 1 --account 1
```

脚本会输出：

- **fact_order**：订单条数、已成交数
- **fact_fill**：成交条数
- **fact_position**：持仓数（quantity>0）
- **fact_account**：账本账户数、总余额/总可用
- **分析指标可算**：是否有足够数据（至少 1 笔成交）
- 最新订单/成交/持仓样例

若无订单与成交，会提示先运行 local_monitor 并产生交易。

---

## 4. 验证项清单

| 项 | 说明 | 如何确认 |
|----|------|----------|
| 订单写入 fact_order | 下单后本地库有记录 | verify_live_loop 订单数 > 0；或 data-api GET /api/orders |
| 成交写入 fact_fill | 成交回报写入 fact_fill | 成交数 > 0；或 GET /api/fills |
| 持仓更新 fact_position | 开/平仓后持仓表更新 | 持仓数、最新持仓样例；或 GET /api/positions |
| 资金结算 fact_account | 资金变动记入账本 | 总余额/总可用；或 GET /api/accounts |
| 分析指标可计算 | 有成交后可算绩效/统计 | 脚本输出「分析指标可算: 是」；或 GET /api/analytics/performance |

---

## 5. 可选：用 data-api + admin-web 核对

1. 启动 **data-api**（端口 8026）。
2. 浏览器打开 **admin-web**，登录后查看：
   - 概览：订单/成交/持仓数量、绩效摘要
   - 订单、成交、持仓、资金账户、流水、绩效分析 各页数据是否与 verify 脚本一致。

---

## 6. 常见问题

- **无订单/成交**：检查策略是否触发信号（可先用 `notify` 看日志）、API 是否开通合约交易、`tenant_id`/`account_id` 是否与 config 一致。
- **有订单无成交**：可能是市价单未立即成交或网络延迟，稍等再跑一次验证脚本。
- **验证脚本报错**：检查数据库连接与迁移是否已执行、表名是否为 `fact_order`/`fact_fill`/`fact_position`/`fact_account`。
