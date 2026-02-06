# 交易所支持一览

本文说明各模块对 **Binance、OKX、Gate** 的支持情况，便于策略/信号与执行、K 线、实时价格按同一交易所贯通使用。

## 总览

| 能力           | Binance | OKX | Gate |
|----------------|--------|-----|------|
| 绑定 API（Merchant） | ✅     | ✅  | ✅   |
| 交易执行（LiveTrader） | ✅     | ✅  | ✅   |
| K 线（data-provider） | ✅     | ✅  | ✅   |
| 实时行情（REST ticker） | ✅     | ✅  | ✅   |
| 实时行情（WebSocket） | ✅     | ✅  | ✅   |

- **绑定 API**：Merchant API 支持 `binance`、`okx`、`gate`；OKX 需传 `passphrase`。
- **交易执行**：`libs.trading.LiveTrader` 通过 CCXT 支持上述三家（Gate 在 CCXT 中为 `gateio`，内部已做映射）。
- **K 线**：data-provider 的 `GET /api/candles` 支持 `exchange` 查询参数，使用 `libs.exchange` 的 Binance/OKX/Gate 客户端。
- **实时价格**：`GET /api/ticker` 与 WebSocket `/ws` 均按 `exchange`（或配置的 `default_exchange`）使用对应交易所行情。

## 使用要点

1. **统一交易所**  
   策略/信号若在 OKX 或 Gate 执行，应使用同一交易所的 K 线和实时价格（请求或配置中指定 `exchange=okx` / `exchange=gate`），避免用 Binance 行情在 OKX/Gate 下单。

2. **data-provider 默认交易所**  
   配置项 `default_exchange`（默认 `binance`）用于未传 `exchange` 时的 K 线与 ticker；WebSocket 行情流也使用该默认交易所。

3. **Gate 与 CCXT 名称**  
   对外统一使用 `gate`；内部与 CCXT 交互时使用 `gateio`（LiveTrader、TickerStream 已做映射）。

## 合约与现货区分

- **market_type**：`future`（合约）与 `spot`（现货）在 LiveTrader 中区分处理。
  - 合约：symbol 会转为 CCXT 格式 `BTC/USDT:USDT`，并参与**持仓模式**检测（见下）；止盈止损带 `reduceOnly`，Gate 带 `close=True`。
  - 现货：无 positionSide、无持仓模式，按普通买卖处理。
- execution-node 的 task 中 `market_type` 默认 `future`；若接现货账户需显式传 `market_type=spot`。
- 同步持仓、同步余额：仅合约账户使用 `fetch_positions()`；现货用 `fetch_balance()`，无持仓同步。

## 合约持仓模式（双向 / 单向，参考 old3）

- **目标**：保证下单可传 `positionSide`（LONG/SHORT），需账户为**双向持仓**；若为单向持仓则不能传 `positionSide`，否则交易所报错。
- **实现**（`libs/trading/live_trader.py`）：
  - **Binance USDT 合约**：首次合约下单前调用 `ensure_dual_position_mode()`：先 GET 当前模式，若非双向则 POST 切换为双向；若切换失败（如 -4059 有持仓无法切换）则置为单向模式，后续下单**不传** `positionSide`。
  - **OKX / Gate**：不通过 API 检测，默认按双向传 `positionSide`；若某账户在网页为单向，后续可按所方文档或报错再单独处理。
- 止盈止损、平仓：同样仅当检测为双向时才传 `positionSide`，与下单逻辑一致。

## 合约保证金模式（逐仓 → 全仓）

- **目标**：若当前为**逐仓**（isolated），尝试改为**全仓**（cross），保证下单按全仓逻辑；若已有持仓无法切换则忽略，继续下单。
- **实现**（`libs/trading/live_trader.py`）：
  - 合约下单、止盈止损前调用 `ensure_cross_margin_mode(symbol)`：每 symbol 只尝试一次，调用交易所 `set_margin_mode("cross", symbol)`（CCXT）；若返回 -4046（No need to change，已是全仓）则视为成功；若因有持仓等原因失败则仅打日志，不阻断下单。
  - Binance 按 symbol 设置；OKX/Gate 若支持 `set_margin_mode` 则同样尝试。

## 相关文件

- 绑定 API：`services/merchant-api/app/routers/user.py`（`ALLOWED_EXCHANGES`）
- 交易执行：`libs/trading/live_trader.py`（`SUPPORTED_EXCHANGES`、gate→gateio）
- K 线/行情客户端：`libs/exchange/client.py`、`libs/exchange/gate.py`、`binance.py`、`okx.py`
- 实时行情流：`libs/ws/ticker_stream.py`（gate→gateio）
- 数据服务：`services/data-provider/app/main.py`（`/api/candles`、`/api/ticker`、`/api/exchanges`）

## Symbol 统一（参考 old3）

- **规范形式（canonical）**：`BASE/QUOTE`，如 `BTC/USDT`，用于 DB 存储、展示、跨所一致。
- **各所格式**：Binance 现货 `BTCUSDT`，OKX `BTC-USDT`，Gate `BTC_USDT`；合约在 CCXT 中多为 `BTC/USDT:USDT`。
- **实现**：
  - `libs/exchange/utils.py`：`normalize_symbol`（入参→规范）、`to_canonical_symbol`（交易所返回→规范）、`symbol_for_ccxt_futures`（规范→CCXT 合约格式）。
  - 同步持仓：execution-node 将 `fetch_positions()` 返回的 symbol 转为规范后再回传，中心写库统一为 `BTC/USDT`。
  - 下单：LiveTrader 接收规范或交易所格式，合约时内部转为 `BTC/USDT:USDT` 再调 CCXT。

## 最小面额与精度（参考 old3）

- 各所 **最小下单量、步长、最小名义价值** 不同，由 CCXT `market` 的 `limits`/`precision` 提供。
- **实现**：LiveTrader 在下单、止盈止损前调用 `exchange.amount_to_precision(symbol, quantity)`、`exchange.price_to_precision(symbol, price)` 做精度舍入；舍入后数量为 0 会直接报错。
- 建议：若需严格校验最小名义价值（minNotional）或最小数量，可先 `load_markets()` 后读 `market['limits']['amount']['min']` / `limits['cost']['min']` 再下单（old3 中通过 `amount_to_precision` 与 `contractSize` 处理张数）。

## 止盈止损（参考 old3）

- **STOP_MARKET / TAKE_PROFIT_MARKET**：LiveTrader 已支持，并传 `reduceOnly=True`；**Gate** 平仓需额外传 `params["close"] = True`（与 old3 signal-client 一致）。
- 合约下**仅当账户为双向持仓时**传 `positionSide`（LONG/SHORT）；单向持仓时不传（与下单逻辑一致，见上节）。
- OKX 等所若使用不同条件单类型，由 CCXT 映射；若遇报错可查 CCXT 文档或按所方 API 补充 params。

## 同步金额与同步持仓

- **同步余额**：中心通过 execution-node `POST /api/sync-balance` 拉取各账户 `fetch_balance()`，写回 `fact_account`（见 `libs/ledger/service.sync_balance_from_exchange`）。
- **同步持仓**：中心通过 `POST /api/sync-positions` 拉取各账户 `fetch_positions()`，execution-node 将每条持仓的 symbol 转为规范形式后返回，中心写回 `fact_position`（见 `libs/sync_node/service.sync_positions_from_nodes`、`libs/position/service.sync_position_from_exchange`）。
- 多所并存时，按 `account_id` + `exchange` 区分，symbol 统一为规范形式便于对比与展示。

## API 示例

- 绑定 API：见 `docs/api/MERCHANT_BIND_API.md`。
- K 线：`GET /api/candles?symbol=BTC/USDT&timeframe=15m&limit=100&exchange=gate`
- 行情：`GET /api/ticker?symbol=BTC/USDT&exchange=okx`
- 支持交易所列表：`GET /api/exchanges` 返回 `exchanges: ["binance", "okx", "gate"]`。
