# 小额实盘测试说明

用 **LiveTrader** 做一次小额下单 + 可选止盈止损，整体验证：交易所连接、symbol 规范、精度、双向持仓/全仓逻辑。  
默认走**测试网**（sandbox），主网需显式加 `--real` 并建议金额 5～10 USDT。

---

## 1. 前置条件

- **Python**：项目根目录可执行 `python scripts/live_small_test.py`（依赖与 data-api 等一致）。
- **配置/环境**：
  - `exchange_api_key` / `IRONBULL_EXCHANGE_API_KEY`
  - `exchange_api_secret` / `IRONBULL_EXCHANGE_API_SECRET`
  - `exchange_passphrase` / `IRONBULL_EXCHANGE_PASSPHRASE`（**OKX 必填**）
  - `exchange_name` / `IRONBULL_EXCHANGE_NAME`（binance / okx / gate，默认 binance）
  - `exchange_sandbox` / `IRONBULL_EXCHANGE_SANDBOX`（默认 true；脚本加 `--real` 时会改为主网）

---

## 2. 推荐流程

### 2.1 仅查余额和持仓（不下单）

```bash
cd /path/to/ironbull
python scripts/live_small_test.py --dry-run
```

用于确认 API 有效、交易所连接正常、当前余额与持仓；同时会打印该交易对的**未成交委托数**（含止盈止损单）。

### 2.2 仅平仓（市价平掉当前持仓）

```bash
python scripts/live_small_test.py --close
```

会查询当前持仓，对每个方向市价平仓（双向持仓会传 `position_side`，避免开反向单）。

### 2.3 撤销止盈/止损等未成交委托

```bash
python scripts/live_small_test.py --cancel-orders
```

会查询该交易对下**所有未成交委托**（含止盈、止损条件单），逐个撤单。主网使用建议加 `--real --yes`。

### 2.4 测试网小额下单（默认 5 USDT）

```bash
# 默认：测试网、BTC/USDT、5 USDT、会下止盈止损
python scripts/live_small_test.py

# 不下止盈止损
python scripts/live_small_test.py --no-sl-tp

# 指定金额与交易对
python scripts/live_small_test.py --amount 5 --symbol ETH/USDT
```

脚本会：查余额 → 取当前价 → 市价开多 → 若成交则下窄幅止盈止损（0.3%）→ 再查余额与持仓。

### 2.5 主网小额实盘（需显式确认）

```bash
# 主网 5 USDT（会提示确认）
python scripts/live_small_test.py --real --amount 5

# 主网、OKX、ETH
python scripts/live_small_test.py --real --amount 5 --exchange okx --symbol ETH/USDT
```

加 `--real` 后使用主网、关闭 sandbox；脚本会提示「按 Enter 继续」再执行。

---

## 3. 参数说明

| 参数 | 说明 | 默认 |
|------|------|------|
| `--dry-run` | 只查余额、持仓和未成交委托，不下单 | false |
| `--close` | 仅平仓：市价平掉当前持仓 | false |
| `--cancel-orders` | 撤销该交易对下所有未成交委托（含止盈止损） | false |
| `--sl-tp-only` | 仅对当前持仓挂止盈止损（需先有持仓） | false |
| `--real` | 主网实盘（关闭 sandbox） | false |
| `--amount` | 下单金额（USDT） | 5 |
| `--symbol` | 交易对 | BTC/USDT |
| `--exchange` | 交易所 binance/okx/gate | 读配置 |
| `--no-sl-tp` | 不下止盈止损单 | 会下 |

---

## 4. 验证项（脚本会打印）

- **[1] 余额**：USDT 总额、可用。
- **[2] 当前价**：用于计算下单数量。
- **[3] 订单结果**：status、filled_qty、filled_price、exchange_order_id；若有错误会打印。
- **[4] 止盈止损**：若成交且未加 `--no-sl-tp`，会下 sl/tp 并打印交易所订单号。
- **[5] 下单后余额与持仓**：再次查余额和持仓列表。

建议到交易所网页/APP 核对：订单、成交、持仓、保证金模式（全仓/逐仓）、持仓模式（双向/单向）是否符合预期。

---

## 5. 常见问题

- **未配置 API**：报错提示配置 `exchange_api_key` / `exchange_api_secret`；OKX 还需 `exchange_passphrase`。
- **测试网 vs 主网**：不加 `--real` 时用测试网；主网必须加 `--real` 并确认金额。
- **止盈止损失败**：部分交易所在有持仓时改模式会报错，脚本会打日志并继续；若需止盈止损可到交易所手动挂单。
- **金额范围**：脚本会把 `--amount` 限制在 1～100 USDT，避免误操作过大。

---

## 6. 与完整链路的关系

- 本脚本**不经过** execution-node、不写 fact_order/fact_fill 等库；仅用 **LiveTrader** 直连交易所，适合快速验证「交易所 + symbol + 精度 + 双向/全仓」逻辑。
- 完整实盘闭环（信号 → 下单 → 落库 → 分析）见 [LIVE_VERIFY.md](./LIVE_VERIFY.md)（local_monitor + verify_live_loop）。
- 若要通过 execution-node 做小额测试，可对中心发起一次 `/api/execute`，payload 中 `amount_usdt` 设为 5～10、`sandbox` 先 true 再 false，详见 execution-node 与 data-api 文档。
