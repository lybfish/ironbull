# P0 证据抽取包

本文档为规划阶段产出，遵循 `docs/PLANNING_ONLY.md` 的全局约束：仅从 SQL 文件中提取证据并做字段语义注释，不涉及任何新表设计、迁移方案或代码实现。

**审计日期**：2026-02-05
**证据来源**：
- `_legacy_readonly/old1/trade_*.sql`
- `_legacy_readonly/old2/tradecore_*.sql`
- `_legacy_readonly/old3/quanttrade.sql`

---

## 一、P0 证据抽取（逐表）

---

### 1.1 old1: `trade_orders_live`

**表用途**：实盘挂单状态表

```sql
CREATE TABLE `trade_orders_live` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `source` varchar(16) NOT NULL COMMENT 'mt5/ccxt',
  `exchange_id` varchar(32) DEFAULT NULL COMMENT '交易所/平台',
  `symbol_raw` varchar(32) NOT NULL COMMENT '原始symbol',
  `symbol_norm` varchar(32) NOT NULL COMMENT '归一化symbol',
  `timeframe` varchar(16) NOT NULL COMMENT '小周期',
  `htf_timeframe` varchar(16) DEFAULT NULL COMMENT '大周期',
  `signal_ts` int(11) NOT NULL COMMENT '信号K线时间戳(UTC秒)',
  `side` varchar(8) NOT NULL COMMENT '方向（BUY/SELL）',
  `status` varchar(32) NOT NULL COMMENT '状态（等待确认/已撤单/已成交）',
  `entry_price` double DEFAULT NULL COMMENT '入场意图价',
  `stop_loss` double DEFAULT NULL COMMENT '止损',
  `take_profit` double DEFAULT NULL COMMENT '止盈',
  `cancel_reason` text COMMENT '撤单原因',
  `auto_trade` tinyint(1) NOT NULL DEFAULT '0' COMMENT '自动下单',
  `executed` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否已执行开仓',
  `executed_at` timestamp NULL DEFAULT NULL COMMENT '执行时间',
  `last_ts` int(11) DEFAULT NULL COMMENT '最后K线时间戳',
  PRIMARY KEY (`id`),
  KEY `idx_symbol` (`symbol_norm`),
  KEY `idx_status` (`status`),
  KEY `idx_signal_ts` (`signal_ts`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实盘挂单状态';
```

**字段语义要点**：

| 字段 | 语义 | 类型 | 风险标注 |
|------|------|------|----------|
| `status` | 订单状态 | varchar(32) | ⚠️ **中文字符串**（等待确认/已撤单/已成交） |
| `side` | 交易方向 | varchar(8) | BUY/SELL |
| `executed` | 是否已执行 | tinyint(1) | 布尔标识，非状态机 |

**风险点**：
- 【事实】`status` 使用中文字符串，与 old2/old3 不兼容
- 【事实】**无 `account_id` 字段**，无法支持多账户
- 【事实】**无 `filled_quantity`/`avg_price`/`fee` 字段**，无成交信息
- 【事实】**无 `order_id`/`trade_id` 字段**，无唯一订单标识

---

### 1.2 old1: `trade_positions_live`

**表用途**：实盘持仓状态表

```sql
CREATE TABLE `trade_positions_live` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `source` varchar(16) NOT NULL COMMENT 'mt5/ccxt',
  `exchange_id` varchar(32) DEFAULT NULL COMMENT '交易所/平台',
  `symbol_norm` varchar(32) NOT NULL COMMENT '归一化symbol',
  `side` varchar(8) NOT NULL COMMENT '方向（long/short）',
  `entry_price` double DEFAULT NULL COMMENT '入场价',
  `size` double DEFAULT NULL COMMENT '持仓数量',
  `signal_id` bigint(20) DEFAULT NULL COMMENT '关联信号ID',
  `signal_ts` int(11) DEFAULT NULL COMMENT '关联信号时间戳',
  `pending` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否等待成交',
  `tp_sl_set` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否已补挂TP/SL',
  `tp_sl_set_at` timestamp NULL DEFAULT NULL COMMENT 'TP/SL补挂时间',
  `last_close_ts` int(11) DEFAULT NULL COMMENT '最近平仓时间戳',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_position` (`source`,`exchange_id`,`symbol_norm`),
  KEY `idx_symbol` (`symbol_norm`),
  KEY `idx_side` (`side`),
  KEY `idx_updated` (`updated_at`)
) ENGINE=InnoDB AUTO_INCREMENT=5489 DEFAULT CHARSET=utf8mb4 COMMENT='实盘持仓状态';
```

**字段语义要点**：

| 字段 | 语义 | 类型 | 风险标注 |
|------|------|------|----------|
| `side` | 持仓方向 | varchar(8) | long/short（小写） |
| `size` | 持仓数量 | double | **无精度控制** |
| `entry_price` | 入场价 | double | **无精度控制** |

**风险点**：
- 【事实】**无 `account_id` 字段**，无法支持多账户
- 【事实】**无 `available`/`frozen`/`locked` 字段**，无冻结机制
- 【事实】**无 `unrealized_pnl`/`realized_pnl` 字段**，无盈亏记录
- 【事实】**无 `cost`/`margin` 字段**，无成本/保证金信息
- 【事实】使用 `double` 类型存储金额，精度风险

---

### 1.3 old1: `trade_klines_unified`

**表用途**：统一 K 线数据表

```sql
CREATE TABLE `trade_klines_unified` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `source` varchar(16) NOT NULL COMMENT 'mt5/ccxt',
  `exchange_id` varchar(32) DEFAULT NULL COMMENT '交易所/平台',
  `symbol_raw` varchar(32) NOT NULL COMMENT '原始symbol',
  `symbol_norm` varchar(32) NOT NULL COMMENT '归一化symbol',
  `timeframe` varchar(16) NOT NULL COMMENT '周期',
  `ts` int(11) NOT NULL COMMENT 'K线时间戳(UTC秒)',
  `open` double NOT NULL,
  `high` double NOT NULL,
  `low` double NOT NULL,
  `close` double NOT NULL,
  `volume` double NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_kline` (`source`,`exchange_id`,`symbol_norm`,`timeframe`,`ts`),
  KEY `idx_symbol` (`symbol_norm`),
  KEY `idx_ts` (`ts`)
) ENGINE=InnoDB AUTO_INCREMENT=445577 DEFAULT CHARSET=utf8mb4 COMMENT='交易对K线表';
```

**字段语义要点**：

| 字段 | 语义 | 类型 | 备注 |
|------|------|------|------|
| `ts` | 时间戳 | int(11) | UTC 秒（事实确认） |
| `symbol_norm` | 归一化 symbol | varchar(32) | 格式如 `BTC/USDT:USDT`（CCXT 格式） |
| `symbol_raw` | 原始 symbol | varchar(32) | 格式如 `BTCUSDT` |

**风险点**：
- 【事实】时间戳为 **UTC 秒**（从注释和数据确认）
- 【事实】symbol 格式为 **CCXT 格式**（含 `:USDT` 后缀）
- 【推断】与 old2/old3 的 symbol 格式不兼容

---

### 1.4 old2: `think_trade_orders`

**表用途**：订单表

```sql
CREATE TABLE `think_trade_orders` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `order_id` varchar(128) NOT NULL COMMENT '外部订单ID',
  `signal_id` int(10) unsigned DEFAULT NULL COMMENT '关联信号',
  `platform_type` varchar(16) DEFAULT NULL COMMENT '平台类型:mt5/ccxt',
  `broker` varchar(32) DEFAULT NULL COMMENT 'MT5服务商:xm/ttp/exness',
  `exchange_id` varchar(32) DEFAULT NULL COMMENT 'CCXT交易所:binance/okx/bybit',
  `account_id` int(10) unsigned DEFAULT NULL COMMENT '关联账户ID',
  `symbol` varchar(32) NOT NULL,
  `side` varchar(8) NOT NULL COMMENT 'BUY/SELL',
  `type` varchar(16) NOT NULL COMMENT 'market/limit/stop',
  `price` decimal(20,8) DEFAULT NULL,
  `volume` decimal(20,8) NOT NULL,
  `filled` decimal(20,8) DEFAULT '0.00000000' COMMENT '已成交量',
  `status` varchar(32) NOT NULL COMMENT 'pending/filled/cancelled/failed',
  `avg_price` decimal(20,8) DEFAULT NULL COMMENT '成交均价',
  `fee` decimal(20,8) DEFAULT NULL COMMENT '手续费',
  `create_time` int(11) NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int(11) NOT NULL DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_order` (`order_id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_status` (`status`),
  KEY `idx_account_id` (`account_id`),
  -- ... 其他索引省略
) ENGINE=InnoDB AUTO_INCREMENT=211 DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**字段语义要点**：

| 字段 | 语义 | 类型 | 风险标注 |
|------|------|------|----------|
| `status` | 订单状态 | varchar(32) | ⚠️ **英文字符串**（pending/filled/cancelled/failed） |
| `side` | 交易方向 | varchar(8) | BUY/SELL（大写） |
| `filled` | 已成交量 | decimal(20,8) | 有成交信息 |
| `avg_price` | 成交均价 | decimal(20,8) | 有成交信息 |
| `fee` | 手续费 | decimal(20,8) | 有费用字段 |

**风险点**：
- 【事实】`status` 为英文字符串，**无"部分成交"状态**（只有 pending/filled/cancelled/failed）
- 【事实】有 `account_id`，支持多账户
- 【事实】**无独立 `trade_id`/`fill_id`**，成交信息内嵌在订单中
- 【事实】从样例数据看，部分订单 `account_id` 为 NULL

---

### 1.5 old2: `think_trade_positions`

**表用途**：持仓表

```sql
CREATE TABLE `think_trade_positions` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `create_time` int(11) NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int(11) NOT NULL DEFAULT '0' COMMENT '更新时间',
  `position_id` varchar(128) DEFAULT NULL COMMENT '外部持仓ID',
  `platform_type` varchar(16) DEFAULT NULL COMMENT '平台类型:mt5/ccxt',
  `broker` varchar(32) DEFAULT NULL COMMENT 'MT5服务商:xm/ttp/exness',
  `exchange_id` varchar(32) DEFAULT NULL COMMENT 'CCXT交易所:binance/okx/bybit',
  `account_id` int(10) unsigned DEFAULT NULL COMMENT '关联账户ID',
  `symbol` varchar(32) NOT NULL,
  `side` varchar(8) NOT NULL COMMENT 'BUY/SELL',
  `volume` decimal(20,8) NOT NULL,
  `entry_price` decimal(20,8) NOT NULL,
  `sl` decimal(20,8) DEFAULT NULL,
  `tp` decimal(20,8) DEFAULT NULL,
  `unrealized_pnl` decimal(20,8) DEFAULT '0.00000000' COMMENT '未实现盈亏',
  `status` varchar(16) DEFAULT 'open' COMMENT 'open/closed',
  `opened_at` int(10) unsigned DEFAULT '0',
  `closed_at` int(10) unsigned DEFAULT NULL,
  `mark` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_symbol` (`symbol`),
  KEY `idx_status` (`status`),
  KEY `idx_account_id` (`account_id`),
  -- ... 其他索引省略
) ENGINE=InnoDB AUTO_INCREMENT=53 DEFAULT CHARSET=utf8mb4 COMMENT='持仓表';
```

**字段语义要点**：

| 字段 | 语义 | 类型 | 风险标注 |
|------|------|------|----------|
| `side` | 持仓方向 | varchar(8) | BUY/SELL（非 LONG/SHORT） |
| `volume` | 持仓数量 | decimal(20,8) | - |
| `unrealized_pnl` | 未实现盈亏 | decimal(20,8) | 有浮动盈亏 |
| `status` | 持仓状态 | varchar(16) | open/closed |

**风险点**：
- 【事实】**无 `available`/`frozen` 字段**，无冻结机制
- 【事实】**无 `realized_pnl` 字段**，无已实现盈亏
- 【事实】**无 `cost`/`margin` 字段**，无成本/保证金
- 【事实】`side` 使用 BUY/SELL，非 LONG/SHORT

---

### 1.6 old2: `think_trade_accounts`

**表用途**：交易账户表（含资金信息）

```sql
CREATE TABLE `think_trade_accounts` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `account_name` varchar(100) NOT NULL COMMENT '账户名称',
  `platform` varchar(32) NOT NULL COMMENT '平台类型:mt5/ccxt_okx/ccxt_binance',
  `platform_type` varchar(16) DEFAULT NULL COMMENT '平台类型:mt5/ccxt',
  `broker` varchar(32) DEFAULT NULL COMMENT 'MT5服务商:xm/ttp/exness',
  `exchange_id` varchar(32) DEFAULT NULL COMMENT 'CCXT交易所:binance/okx/bybit',
  `login` varchar(64) DEFAULT NULL COMMENT '登录账号',
  `password` varchar(255) DEFAULT NULL COMMENT '密码(加密)',
  `server` varchar(100) DEFAULT NULL COMMENT '服务器',
  `api_config` text COMMENT 'API配置JSON',
  -- ... API 相关字段省略 ...
  `balance` decimal(15,2) DEFAULT '0.00' COMMENT '余额',
  `equity` decimal(15,2) DEFAULT '0.00' COMMENT '净值',
  `margin` decimal(15,2) DEFAULT '0.00' COMMENT '已用保证金',
  `free_margin` decimal(15,2) DEFAULT '0.00' COMMENT '可用保证金',
  `margin_level` decimal(10,2) DEFAULT '0.00' COMMENT '保证金水平(%)',
  `profit` decimal(15,2) DEFAULT '0.00' COMMENT '浮动盈亏',
  `is_default` tinyint(1) DEFAULT '0' COMMENT '是否默认账户',
  `status` tinyint(1) DEFAULT '1' COMMENT '状态:1启用0禁用',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `last_sync_time` bigint(20) DEFAULT NULL COMMENT '最后同步时间',
  `create_time` bigint(20) DEFAULT NULL COMMENT '创建时间',
  `update_time` bigint(20) DEFAULT NULL COMMENT '更新时间',
  `mark` tinyint(1) DEFAULT '1' COMMENT '有效标识',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_login` (`platform`,`login`),
  -- ... 索引省略
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COMMENT='交易账户表';
```

**字段语义要点**：

| 字段 | 语义 | 类型 | 备注 |
|------|------|------|------|
| `balance` | 余额 | decimal(15,2) | 账户总余额 |
| `equity` | 净值 | decimal(15,2) | 账户净值 |
| `margin` | 已用保证金 | decimal(15,2) | - |
| `free_margin` | 可用保证金 | decimal(15,2) | - |
| `profit` | 浮动盈亏 | decimal(15,2) | - |

**风险点**：
- 【事实】资金字段**混在账户表中**，非独立 Ledger 表
- 【事实】**无 `frozen` 字段**（只有 margin/free_margin）
- 【事实】**无资金流水表**，余额变动不可追溯
- 【事实】精度为 `decimal(15,2)`，仅 2 位小数

---

### 1.7 old2: `think_trade_klines`

**表用途**：K 线数据表

```sql
CREATE TABLE `think_trade_klines` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `symbol` varchar(32) NOT NULL COMMENT '交易对',
  `timeframe` varchar(16) NOT NULL COMMENT '周期',
  `ts` int(10) unsigned NOT NULL COMMENT '时间戳',
  `o` decimal(20,8) NOT NULL COMMENT '开盘价',
  `h` decimal(20,8) NOT NULL COMMENT '最高价',
  `l` decimal(20,8) NOT NULL COMMENT '最低价',
  `c` decimal(20,8) NOT NULL COMMENT '收盘价',
  `v` decimal(20,8) NOT NULL COMMENT '成交量',
  `source` varchar(16) DEFAULT NULL COMMENT '来源',
  `platform_type` varchar(16) DEFAULT NULL COMMENT '平台类型:mt5/ccxt',
  `exchange_id` varchar(32) DEFAULT NULL COMMENT '交易所ID：okx/binance 等',git
  `broker` varchar(32) DEFAULT NULL COMMENT '经纪商：xm/ttp 等',
  `symbol_norm` varchar(32) DEFAULT NULL COMMENT '标准交易对',
  `symbol_raw` varchar(64) DEFAULT NULL COMMENT '原始交易对',
  `create_time` int(10) unsigned DEFAULT '0' COMMENT '写入时间',
  `update_time` int(10) unsigned DEFAULT '0' COMMENT '更新时间',
  `mark` tinyint(1) DEFAULT '1' COMMENT '有效标记',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_symbol_tf_ts` (`symbol`,`timeframe`,`ts`),
  -- ... 索引省略
) ENGINE=InnoDB AUTO_INCREMENT=126716 DEFAULT CHARSET=utf8mb4 COMMENT='K线数据表';
```

**字段语义要点**：

| 字段 | 语义 | 类型 | 备注 |
|------|------|------|------|
| `ts` | 时间戳 | int(10) unsigned | 时区不明确（无注释） |
| `symbol` | 交易对 | varchar(32) | 格式如 `BTCUSDT`（无分隔符） |

**风险点**：
- 【事实】`ts` 时区**未在注释中说明**（与 old1 不同）
- 【事实】`symbol` 格式为 `BTCUSDT`，与 old1 的 `BTC/USDT:USDT` 不同

---

### 1.8 old3: `think_trade_order`

**表用途**：交易订单表

```sql
CREATE TABLE `think_trade_order` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `order_no` varchar(50) NOT NULL COMMENT '订单号',
  `exchange_order_id` varchar(100) DEFAULT '' COMMENT '交易所订单ID',
  `signal_id` int unsigned DEFAULT NULL COMMENT '交易信号ID',
  `strategy_id` int unsigned NOT NULL DEFAULT '0' COMMENT '策略ID',
  `strategy_instance_id` int unsigned DEFAULT '0' COMMENT '策略实例ID',
  `hedge_group_id` varchar(50) DEFAULT '' COMMENT '对冲组ID',
  `account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '账户ID',
  `symbol` varchar(50) NOT NULL COMMENT '交易对(如BTC/USDT)',
  `side` tinyint unsigned NOT NULL COMMENT '交易方向：1买入 2卖出',
  `position_side` varchar(10) DEFAULT '' COMMENT '持仓方向 LONG/SHORT',
  `type` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '订单类型：1市价 2限价 3止损',
  `price` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '委托价格',
  `realized_pnl` decimal(20,8) DEFAULT '0.00000000' COMMENT '实现盈亏',
  `quantity` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '委托数量',
  `filled_quantity` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '成交数量',
  `filled_amount` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '成交金额',
  `avg_price` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '成交均价',
  `fee` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '手续费',
  `stop_loss` decimal(15,8) unsigned DEFAULT '0.00000000' COMMENT '止损价',
  `take_profit` decimal(15,8) unsigned DEFAULT '0.00000000' COMMENT '止盈价',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '订单状态：1待成交 2部分成交 3已成交 4已取消 5已拒绝',
  `source` tinyint unsigned DEFAULT '1' COMMENT '来源:1手动2策略3跟单4风控',
  `platform_order_id` varchar(100) DEFAULT NULL COMMENT '平台订单ID',
  `remark` varchar(255) DEFAULT NULL COMMENT '备注',
  `close_order_id` int unsigned DEFAULT '0' COMMENT '平仓订单ID，0表示未平仓',
  `error_msg` varchar(500) DEFAULT NULL COMMENT '错误信息',
  `create_time` int unsigned NOT NULL DEFAULT '0' COMMENT '创建时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `execute_time` int unsigned DEFAULT NULL COMMENT '执行时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识(1正常 0删除)',
  `member_id` int unsigned DEFAULT NULL COMMENT '会员ID',
  `point_card_deducted` decimal(15,8) DEFAULT '0.00000000' COMMENT '已扣点卡',
  `agent_share` decimal(15,8) DEFAULT '0.00000000' COMMENT '代理商分成',
  `company_share` decimal(15,8) DEFAULT '0.00000000' COMMENT '公司分成',
  `server_id` int unsigned DEFAULT '0' COMMENT '执行服务器ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  -- ... 索引省略
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易订单表';
```

**字段语义要点**：

| 字段 | 语义 | 类型 | 风险标注 |
|------|------|------|----------|
| `status` | 订单状态 | tinyint unsigned | ⚠️ **数字枚举**（1/2/3/4/5） |
| `side` | 交易方向 | tinyint unsigned | ⚠️ **数字**（1买入/2卖出） |
| `position_side` | 持仓方向 | varchar(10) | LONG/SHORT（字符串） |
| `filled_quantity` | 成交数量 | decimal(15,8) | 有成交信息 |
| `realized_pnl` | 实现盈亏 | decimal(20,8) | 有盈亏字段 |

**风险点**：
- 【事实】`status` 为数字枚举，**有"部分成交"状态**（status=2）
- 【事实】有 `account_id` + `member_id`，支持多账户/多会员
- 【事实】**无独立 `trade_id`/`fill_id`**，成交信息内嵌
- 【事实】有 `realized_pnl` 字段，比 old2 多

---

### 1.9 old3: `think_position`

**表用途**：持仓表

```sql
CREATE TABLE `think_position` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `create_time` int unsigned DEFAULT '0' COMMENT '创建时间',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '会员ID',
  `account_id` int unsigned NOT NULL DEFAULT '0' COMMENT '账户ID',
  `leader_id` int unsigned DEFAULT '0' COMMENT '领导者ID',
  `exchange` varchar(50) NOT NULL DEFAULT '' COMMENT '交易所',
  `symbol` varchar(50) NOT NULL DEFAULT '' COMMENT '交易对',
  `side` tinyint NOT NULL DEFAULT '1' COMMENT '1=买入 2=卖出',
  `position_side` varchar(10) NOT NULL DEFAULT '' COMMENT '持仓方向:LONG/SHORT',
  `quantity` decimal(20,8) NOT NULL DEFAULT '0.00000000',
  `entry_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '入场价格',
  `current_price` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '当前价格',
  `unrealized_pnl` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '未实现盈亏',
  `realized_pnl` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '已实现盈亏',
  `leverage` int NOT NULL DEFAULT '1' COMMENT '杠杆倍数',
  `margin` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '保证金',
  `liquidation_price` decimal(20,8) DEFAULT NULL COMMENT '强平价',
  `take_profit` decimal(20,8) DEFAULT NULL,
  `stop_loss` decimal(20,8) DEFAULT NULL,
  `position_value` decimal(20,8) NOT NULL DEFAULT '0.00000000' COMMENT '持仓价值',
  `position_mode` varchar(20) NOT NULL DEFAULT 'oneway' COMMENT '持仓模式:oneway单向/hedge双向',
  `strategy_id` int unsigned DEFAULT '0' COMMENT '策略ID',
  `open_time` int unsigned NOT NULL DEFAULT '0' COMMENT '开仓时间',
  `update_time` int unsigned NOT NULL DEFAULT '0' COMMENT '更新时间',
  `close_time` int unsigned DEFAULT '0' COMMENT '平仓时间',
  `mark` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '有效标识:1有效/0无效',
  PRIMARY KEY (`id`),
  -- ... 索引省略
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓表';
```

**字段语义要点**：

| 字段 | 语义 | 类型 | 备注 |
|------|------|------|------|
| `side` | 买卖方向 | tinyint | 数字（1/2） |
| `position_side` | 持仓方向 | varchar(10) | LONG/SHORT |
| `unrealized_pnl` | 未实现盈亏 | decimal(20,8) | ✅ |
| `realized_pnl` | 已实现盈亏 | decimal(20,8) | ✅ |
| `leverage` | 杠杆倍数 | int | ✅ |
| `margin` | 保证金 | decimal(20,8) | ✅ |
| `position_mode` | 持仓模式 | varchar(20) | oneway/hedge |

**风险点**：
- 【事实】**无 `available`/`frozen` 字段**，无冻结机制
- 【事实】有 `margin` 字段，但无独立的可用/冻结区分
- 【事实】有 `position_side` 支持双向持仓

---

### 1.10 old3: `think_exchange_account`

**表用途**：交易所账户表（含资金信息）

```sql
CREATE TABLE `think_exchange_account` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `exchange` varchar(50) NOT NULL DEFAULT '' COMMENT '交易所',
  `account_type` varchar(20) NOT NULL DEFAULT 'futures' COMMENT '账户类型(spot/futures/margin)',
  `is_testnet` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否测试网',
  `api_key` varchar(255) NOT NULL COMMENT 'API密钥',
  `api_secret` varchar(255) DEFAULT NULL COMMENT 'API密钥',
  `passphrase` varchar(255) DEFAULT NULL COMMENT 'API密码短语(部分平台需要)',
  `member_id` int unsigned DEFAULT NULL COMMENT '所属会员ID',
  `server_id` int unsigned DEFAULT NULL COMMENT '分配的服务器ID',
  `balance` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '账户余额',
  `total_equity` decimal(20,8) DEFAULT NULL COMMENT '总权益',
  `available_balance` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '可用余额',
  `frozen_balance` decimal(15,8) unsigned NOT NULL DEFAULT '0.00000000' COMMENT '冻结余额',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态：1启用 2停用',
  -- ... 同步相关字段省略 ...
  `spot_balance` decimal(20,8) DEFAULT NULL COMMENT '现货USDT余额',
  `spot_available` decimal(20,8) DEFAULT NULL COMMENT '现货可用余额',
  `futures_balance` decimal(20,8) DEFAULT NULL COMMENT '合约钱包余额',
  `futures_available` decimal(20,8) DEFAULT NULL COMMENT '合约可用余额',
  `futures_unrealized` decimal(20,8) DEFAULT NULL COMMENT '合约未实现盈亏',
  `futures_margin` decimal(20,8) DEFAULT NULL COMMENT '合约保证金余额',
  PRIMARY KEY (`id`),
  -- ... 索引省略
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COMMENT='交易账户表';
```

**字段语义要点**：

| 字段 | 语义 | 类型 | 备注 |
|------|------|------|------|
| `balance` | 账户余额 | decimal(15,8) | ✅ 8 位小数 |
| `available_balance` | 可用余额 | decimal(15,8) | ✅ |
| `frozen_balance` | 冻结余额 | decimal(15,8) | ✅ **有冻结字段** |
| `total_equity` | 总权益 | decimal(20,8) | ✅ |

**风险点**：
- 【事实】**有 `frozen_balance` 字段**（与 old1/old2 不同）
- 【事实】区分了 spot/futures 余额
- 【事实】资金字段仍混在账户表中，非独立 Ledger

---

### 1.11 old3: `think_member_wallet`

**表用途**：用户钱包表（平台内部钱包，非交易所账户）

```sql
CREATE TABLE `think_member_wallet` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '用户ID',
  `balance` decimal(20,2) DEFAULT '0.00' COMMENT '可用余额',
  `frozen_balance` decimal(20,2) DEFAULT '0.00' COMMENT '冻结余额',
  `total_income` decimal(20,2) DEFAULT '0.00' COMMENT '累计收入',
  `total_withdraw` decimal(20,2) DEFAULT '0.00' COMMENT '累计提现',
  `status` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '状态:1正常 0冻结',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_member` (`member_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COMMENT='用户钱包表';
```

**字段语义要点**：

| 字段 | 语义 | 类型 | 备注 |
|------|------|------|------|
| `balance` | 可用余额 | decimal(20,2) | ⚠️ 仅 2 位小数 |
| `frozen_balance` | 冻结余额 | decimal(20,2) | ✅ 有冻结字段 |
| `total_income` | 累计收入 | decimal(20,2) | 汇总字段 |
| `total_withdraw` | 累计提现 | decimal(20,2) | 汇总字段 |

**风险点**：
- 【事实】有 `frozen_balance` 字段
- 【事实】精度为 2 位小数，不适合加密货币精度

---

### 1.12 old3: `think_wallet_bill`

**表用途**：钱包账单明细表（资金流水）

```sql
CREATE TABLE `think_wallet_bill` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `bill_no` varchar(32) NOT NULL DEFAULT '' COMMENT '账单编号',
  `member_id` int unsigned NOT NULL DEFAULT '0' COMMENT '用户ID',
  `amount` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '金额',
  `balance_before` decimal(20,2) DEFAULT '0.00' COMMENT '变动前余额',
  `balance_after` decimal(20,2) DEFAULT '0.00' COMMENT '变动后余额',
  `type` varchar(20) NOT NULL DEFAULT '' COMMENT '类型: income收入 withdraw提现 transfer转账 fee手续费 refund退款',
  `source` varchar(30) DEFAULT '' COMMENT '来源: trade交易 commission分成 reward奖励 recharge充值',
  `related_id` int unsigned DEFAULT '0' COMMENT '关联ID',
  `related_type` varchar(30) DEFAULT '' COMMENT '关联类型',
  `title` varchar(100) DEFAULT '' COMMENT '标题',
  `note` varchar(500) DEFAULT '' COMMENT '备注',
  `status` tinyint DEFAULT '1' COMMENT '状态:1成功 0失败 2处理中',
  `create_time` int unsigned NOT NULL DEFAULT '0',
  `update_time` int unsigned NOT NULL DEFAULT '0',
  `mark` tinyint unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_no` (`bill_no`),
  KEY `idx_member` (`member_id`),
  KEY `idx_type` (`type`),
  KEY `idx_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账单明细表';
```

**字段语义要点**：

| 字段 | 语义 | 类型 | 备注 |
|------|------|------|------|
| `bill_no` | 账单编号 | varchar(32) | 唯一标识 |
| `amount` | 金额 | decimal(20,2) | 变动金额 |
| `balance_before` | 变动前余额 | decimal(20,2) | ✅ 有快照 |
| `balance_after` | 变动后余额 | decimal(20,2) | ✅ 有快照 |
| `type` | 类型 | varchar(20) | income/withdraw/transfer/fee/refund |
| `source` | 来源 | varchar(30) | trade/commission/reward/recharge |
| `related_id` | 关联 ID | int unsigned | 可追溯业务来源 |

**风险点**：
- 【事实】**有资金流水表**（old1/old2 均无）
- 【事实】有 `balance_before`/`balance_after`，支持对账
- 【事实】有 `related_id`/`related_type`，支持关联追溯
- 【事实】`type` 不含"成交扣款"类型（只有 income/withdraw/transfer/fee/refund）

---

### 1.13 old3: `think_klines_unified`

**表用途**：统一 K 线数据表

```sql
CREATE TABLE `think_klines_unified` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `exchange` varchar(32) NOT NULL COMMENT '交易所 binance/okx',
  `symbol` varchar(32) NOT NULL COMMENT '交易对 BTC/USDT',
  `timeframe` varchar(16) NOT NULL COMMENT '周期 1m/5m/15m/1h/4h/1d',
  `ts` int unsigned NOT NULL COMMENT 'K线时间戳(UTC秒)',
  `open` decimal(20,8) NOT NULL COMMENT '开盘价',
  `high` decimal(20,8) NOT NULL COMMENT '最高价',
  `low` decimal(20,8) NOT NULL COMMENT '最低价',
  `close` decimal(20,8) NOT NULL COMMENT '收盘价',
  `volume` decimal(30,8) NOT NULL DEFAULT '0.00000000' COMMENT '成交量',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_kline` (`exchange`,`symbol`,`timeframe`,`ts`),
  -- ... 索引省略
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='统一K线数据表';
```

**字段语义要点**：

| 字段 | 语义 | 类型 | 备注 |
|------|------|------|------|
| `ts` | 时间戳 | int unsigned | **UTC 秒**（注释确认） |
| `symbol` | 交易对 | varchar(32) | 格式如 `BTC/USDT`（含斜杠） |

**风险点**：
- 【事实】时间戳为 **UTC 秒**
- 【事实】symbol 格式为 `BTC/USDT`（与 old1 的 `BTC/USDT:USDT`、old2 的 `BTCUSDT` 均不同）

---

## 二、订单状态机证据

### 2.1 status 字段对比

| 项目 | 表名 | status 类型 | 状态值 | 来源 |
|------|------|-------------|--------|------|
| old1 | `trade_orders_live` | varchar(32) | 等待确认/已撤单/已成交 | 【事实】来自 DDL 注释 |
| old2 | `think_trade_orders` | varchar(32) | pending/filled/cancelled/failed | 【事实】来自 DDL 注释 |
| old3 | `think_trade_order` | tinyint unsigned | 1待成交/2部分成交/3已成交/4已取消/5已拒绝 | 【事实】来自 DDL 注释 |

### 2.2 状态机差异分析

| 状态 | old1 | old2 | old3 |
|------|------|------|------|
| 待处理/挂单中 | 等待确认 | pending | 1 |
| **部分成交** | **无** | **无** | **2** |
| 全部成交 | 已成交 | filled | 3 |
| 已撤单 | 已撤单 | cancelled | 4 |
| 失败/拒绝 | 无 | failed | 5 |

**关键差异**：
- 【事实】**只有 old3 有"部分成交"状态（status=2）**
- 【事实】old1/old2 无法区分"部分成交"与"全部成交"
- 【推断】old2 的部分成交可能通过 `filled < volume` 判断，但状态仍为 pending 或 filled

### 2.3 需要样例数据确认的点

| # | 待确认点 | 需要证据 |
|---|----------|----------|
| 1 | old1 status 实际取值集合 | 查询 `SELECT DISTINCT status FROM trade_orders_live` |
| 2 | old2 部分成交时 status 为何值 | 查询 `SELECT * FROM think_trade_orders WHERE filled > 0 AND filled < volume` |
| 3 | old3 status=2 与 status=3 的边界条件 | 查询 `SELECT * FROM think_trade_order WHERE status IN (2,3)` |

---

## 三、成交明细缺失的"可审计性论证"

### 3.1 trade_id / fill_id 存在性证据

| 项目 | 表名 | trade_id/fill_id 字段 | 结论 |
|------|------|----------------------|------|
| old1 | `trade_orders_live` | **无** | ❌ 无独立成交标识 |
| old1 | `trade_positions_live` | **无** | ❌ 无独立成交标识 |
| old2 | `think_trade_orders` | **无** | ❌ 无独立成交标识 |
| old2 | `think_trade_positions` | **无** | ❌ 无独立成交标识 |
| old3 | `think_trade_order` | **无** | ❌ 无独立成交标识 |
| old3 | `think_position` | **无** | ❌ 无独立成交标识 |

### 3.2 独立成交表存在性证据

```
扫描结果：
- old1: 无 trade/fill/deal 表（仅 backtest_fills 用于回测）
- old2: 无 trade/fill/deal 表
- old3: 无 trade/fill/deal 表
```

**结论**：【事实】**三系统均无独立成交表，成交信息内嵌在订单表中**

### 3.3 无法支持的审计/重放场景

由于缺少独立成交表和 trade_id/fill_id，以下场景**无法实现**：

| # | 场景 | 无法实现原因 |
|---|------|--------------|
| 1 | **一笔订单多次成交的明细追溯** | 无法知道每次成交的时间、价格、数量 |
| 2 | **成交时间序列重放** | 无法按时间顺序还原成交流 |
| 3 | **成交价格 VWAP 验证** | 无法验证 avg_price 是否等于各笔成交的加权平均 |
| 4 | **成交手续费明细审计** | 无法知道每笔成交的手续费 |
| 5 | **部分成交→全部成交的状态流转审计** | 无法追溯部分成交的中间状态 |
| 6 | **成交与持仓变动的一致性校验** | 无法逐笔验证"成交→持仓变动"链路 |
| 7 | **成交与资金变动的一致性校验** | 无法逐笔验证"成交→资金扣减"链路 |
| 8 | **做市商/交易对手方追溯** | 无成交对手方信息 |

---

## 四、冻结字段与资金流水证据

### 4.1 Position 表冻结字段证据

| 项目 | 表名 | available 字段 | frozen 字段 | locked 字段 | 结论 |
|------|------|----------------|-------------|-------------|------|
| old1 | `trade_positions_live` | **无** | **无** | **无** | ❌ 无冻结机制 |
| old2 | `think_trade_positions` | **无** | **无** | **无** | ❌ 无冻结机制 |
| old3 | `think_position` | **无** | **无** | **无** | ❌ 无冻结机制 |

**结论**：【事实】**三系统的持仓表均无冻结字段**

### 4.2 Ledger 表资金冻结证据

| 项目 | 表名 | balance 字段 | available 字段 | frozen 字段 | 结论 |
|------|------|--------------|----------------|-------------|------|
| old1 | - | **无资金表** | - | - | ❌ 无 Ledger |
| old2 | `think_trade_accounts` | ✅ balance | **无** | **无**（只有 margin） | ⚠️ 仅有保证金 |
| old3 | `think_exchange_account` | ✅ balance | ✅ available_balance | ✅ frozen_balance | ✅ 有冻结字段 |
| old3 | `think_member_wallet` | ✅ balance | - | ✅ frozen_balance | ✅ 有冻结字段 |

**结论**：
- 【事实】old1 无资金表
- 【事实】old2 无冻结字段（只有 margin，含义不同）
- 【事实】old3 有 `frozen_balance` 字段

### 4.3 资金流水表证据

| 项目 | 流水表名 | balance_before | balance_after | type 枚举 | 结论 |
|------|----------|----------------|---------------|-----------|------|
| old1 | **无** | - | - | - | ❌ 无流水 |
| old2 | **无** | - | - | - | ❌ 无流水 |
| old3 | `think_wallet_bill` | ✅ | ✅ | income/withdraw/transfer/fee/refund | ✅ 有流水 |

**结论**：
- 【事实】old1/old2 **无资金流水表**
- 【事实】old3 **有资金流水表**，且有 balance_before/after 支持对账
- 【事实】old3 流水 type 不含"成交扣款"（trade 在 source 字段）

### 4.4 对 04 文档结论的更新

| 04 文档原结论 | 证据验证 | 更新后结论 |
|--------------|----------|------------|
| old1 Position 无冻结字段 | ✅ 确认 | 【事实】无 available/frozen 字段 |
| old2 Position 无冻结字段 | ✅ 确认 | 【事实】无 available/frozen 字段 |
| old3 Position 无冻结字段 | ✅ 确认 | 【事实】无 available/frozen 字段 |
| old1 无资金流水表 | ✅ 确认 | 【事实】无 Ledger 表 |
| old2 无资金流水表 | ✅ 确认 | 【事实】资金混在 accounts 表，无流水 |
| old3 有资金流水表 | ✅ 确认 | 【事实】`think_wallet_bill` 存在 |

---

## 五、证据驱动结论摘要

### 5.1 订单状态机结论

| 结论 | 类型 | 证据 |
|------|------|------|
| old1 使用中文状态 | 事实 | DDL 注释："等待确认/已撤单/已成交" |
| old2 使用英文状态 | 事实 | DDL 注释："pending/filled/cancelled/failed" |
| old3 使用数字状态 | 事实 | DDL 注释："1待成交/2部分成交/3已成交/4已取消/5已拒绝" |
| 只有 old3 有"部分成交"状态 | 事实 | old3 status=2，old1/old2 无对应状态 |
| 三系统状态机不兼容 | 事实 | 类型（varchar/tinyint）和值域均不同 |

### 5.2 成交明细结论

| 结论 | 类型 | 证据 |
|------|------|------|
| 三系统均无独立成交表 | 事实 | 全库扫描无 trade/fill/deal 表 |
| 三系统均无 trade_id/fill_id | 事实 | DDL 字段列表中无此字段 |
| 成交信息内嵌在订单表 | 事实 | filled/filled_quantity/avg_price/fee 字段在订单表中 |
| 无法追溯一笔订单多次成交 | 推断 | 因无独立成交记录，只能看到累计值 |

### 5.3 冻结机制结论

| 结论 | 类型 | 证据 |
|------|------|------|
| 三系统持仓表均无冻结字段 | 事实 | DDL 中无 available/frozen/locked 字段 |
| old1 无任何资金表 | 事实 | 全库扫描无 balance/ledger/wallet 表 |
| old2 资金混在 accounts 表，无冻结 | 事实 | `think_trade_accounts` 只有 margin 字段 |
| old3 账户表有冻结字段 | 事实 | `think_exchange_account.frozen_balance` 存在 |
| old3 钱包表有冻结字段 | 事实 | `think_member_wallet.frozen_balance` 存在 |

### 5.4 资金流水结论

| 结论 | 类型 | 证据 |
|------|------|------|
| old1 无资金流水表 | 事实 | 全库扫描无 bill/journal/flow 表 |
| old2 无资金流水表 | 事实 | 全库扫描无 bill/journal/flow 表 |
| old3 有资金流水表 | 事实 | `think_wallet_bill` 存在 |
| old3 流水有 before/after 快照 | 事实 | `balance_before`/`balance_after` 字段存在 |
| old3 流水可关联业务来源 | 事实 | `related_id`/`related_type` 字段存在 |

### 5.5 symbol 规范结论

| 项目 | symbol 格式 | 证据 |
|------|-------------|------|
| old1 | `BTC/USDT:USDT` | 样例数据确认（CCXT 合约格式） |
| old2 | `BTCUSDT` | 样例数据确认（无分隔符） |
| old3 | `BTC/USDT` | DDL 注释确认（含斜杠，无合约后缀） |

### 5.6 时间戳规范结论

| 项目 | 时区 | 精度 | 证据 |
|------|------|------|------|
| old1 | UTC | 秒 | DDL 注释："K线时间戳(UTC秒)" |
| old2 | 不明确 | 秒 | DDL 注释仅写"时间戳" |
| old3 | UTC | 秒 | DDL 注释："K线时间戳(UTC秒)" |

---

### 5.7 平台重建必要性证据总结

| 能力域 | 必须重建原因 | 证据类型 |
|--------|--------------|----------|
| **OrderTrade** | 三系统均无独立成交表，无法追溯成交明细 | 事实 |
| **Position** | 三系统持仓表均无冻结字段，无法支持"下单冻结→成交释放"机制 | 事实 |
| **Ledger** | old1/old2 无流水表；old3 流水表精度仅 2 位小数 | 事实 |
| **Execution** | 三系统订单状态机完全不兼容 | 事实 |

---

*文档归属：SaaS 量化平台 Blueprint · 05 P0 证据抽取包*
*审计日期：2026-02-05*
