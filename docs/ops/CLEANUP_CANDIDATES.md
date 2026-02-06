# 可清理项清单

以下为建议可清理或整理的内容，按「安全 / 体积 / 冗余」分类。执行前请确认无再引用需求。

---

## 一、安全相关（建议优先）

### 1. `config/default.yaml` 中的敏感默认值

当前文件中存在**类生产敏感信息**，建议改为占位符，生产一律用环境变量覆盖：

| 配置项 | 当前 | 建议 |
|--------|------|------|
| `telegram_bot_token` | 实际 token | 改为空或占位 `"<TELEGRAM_BOT_TOKEN>"` |
| `telegram_chat_id` | 实际 chat_id | 改为空或占位 |
| `exchange_api_key` / `exchange_api_secret` | 实际密钥 | 改为空或占位 |
| `node_auth_secret` | `test-secret-2026` | 改为占位，并在部署文档中强调用 env |

**操作**：在 `config/default.yaml` 中把上述值改成占位符或空字符串，并在注释中写「生产请用 IRONBULL_* 环境变量」。若这些值曾泄露，建议在交易所/Telegram 侧轮换密钥。

---

## 二、体积 / 归档（按需）

### 2. `_legacy_readonly/` 目录（old1 / old2 / old3）

- **用途**：仅作参考（如 merchant-api 对齐、策略迁移、cursor_.md 中的事实对照）。
- **体积**：约 2400+ 文件，占用较多磁盘与仓库体积。
- **建议**：
  - 若仍需要对照 old3 文档（如 `merchant-api.md`）：可把 **old3/quanttrade/docs** 单独复制到 `docs/reference/` 或外部文档站，再删除整个 `_legacy_readonly`。
  - 若已不再需要任何旧系统参考：可将 `_legacy_readonly` 打成压缩包归档到别处，再从仓库中删除该目录。
- **注意**：删除前确认无代码或脚本直接引用其路径（当前仅文档引用）。

### 3. `cursor_.md`（根目录）

- **内容**：导出的长对话记录（约 8000+ 行），多为历史规划与讨论。
- **建议**：若不需要在仓库中保留对话历史，可删除；若需保留，可移到 `docs/archive/` 或移出 Git 仓库。

---

## 三、文档冗余（可选整理）

### 4. 任务/规划类文档

| 文件 | 说明 | 建议 |
|------|------|------|
| `docs/context/NEXT_TASK_V1.md` | 早期「Facts Layer First」计划 | 若 v1 已落地，可合并要点到 `IMPLEMENTATION_STATUS.md` 后删除或移至 `docs/archive/` |
| `docs/PLANNING_ONLY.md` | 仅规划不写代码的元规则 | 若已不再用此约束，可删除或归档 |
| `SESSION_HANDOFF.md`（根目录） | 会话交接与已完成事项 | 若已同步到 `IMPLEMENTATION_STATUS.md`，可删除或改为「仅保留最近一份」 |

### 5. 文档内链接

- 清理或归档上述文件后，检查 `docs/context/IMPLEMENTATION_STATUS.md`、`SESSION_HANDOFF.md`、`cursor_.md` 中对已删除/移动文件的引用并更新或删除。

---

## 四、脚本（确认后再删）

以下脚本**未在文档中被引用**，若确认本机/团队不再使用，可考虑删除以减噪：

| 脚本 | 说明 |
|------|------|
| `scripts/demo_genetic.sh` | 遗传算法相关 demo |
| `scripts/demo_multi_strategy.sh` | 多策略 demo |
| `scripts/demo_optimizer.sh` | 优化器 demo |
| `scripts/demo_signal_notify.sh` | 信号通知 demo |
| `scripts/demo_trading.sh` | 交易 demo |
| `scripts/demo_websocket.py` | WebSocket demo |
| `scripts/demo_data_cache.sh` | 数据缓存 demo |
| `scripts/demo_live_backtest.sh` | 实盘回测 demo |

**保留的 demo 脚本**（被 STARTUP.md / IMPLEMENTATION_STATUS.md / BACKTEST_GUIDE 引用）：  
`demo_flow.sh`、`demo_strategy_engine.sh`、`demo_data_provider.sh`、`demo_follow_service.sh`、`demo_strategy_runner.sh`、`demo_backtest.sh`、`demo_facts_chain.sh`、`demo_async_queue.sh`、`demo_risk_rules.sh`、`demo_live_data.sh`。

`seed_dim_strategy.sql` 未在代码或文档中引用，若为一次性种子数据且已执行过，可归档或删除。

---

## 五、建议执行顺序

1. **先做**：处理 `config/default.yaml` 敏感默认值（占位符 + 注释）。
2. **按需**：归档或删除 `_legacy_readonly`、`cursor_.md`（需先确认不再需要参考）。
3. **可选**：合并/归档 NEXT_TASK_V1、PLANNING_ONLY、SESSION_HANDOFF，并更新文档链接。
4. **确认后**：删除未引用脚本与 `seed_dim_strategy.sql`。

如需我按某一类直接改仓库（例如只做 default.yaml 占位符），可说明要执行哪几项。
