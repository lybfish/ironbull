# Merchant API 接口文档

> **版本**: v2.0 &nbsp;|&nbsp; **更新日期**: 2026-02-07  
> **服务端口**: 8010  
> **Base URL**: `https://merchant.aigomsg.com`（生产） / `http://localhost:8010`（开发）

Merchant API 面向代理商/商户 B2B 场景，用于管理租户下的用户、点卡、策略与会员分销。  
共 **20 个业务接口** + 1 个健康检查。

---

## 1. 认证方式

所有接口（除 `/health`）均需在请求头中携带 **AppKey + 签名**：

| Header        | 必填 | 说明 |
|---------------|------|------|
| `X-App-Key`   | 是   | 租户 AppKey（由平台分配） |
| `X-Timestamp` | 是   | 当前时间戳（秒），用于防重放 |
| `X-Sign`      | 是   | 签名，见下方计算规则 |

**签名计算**：

```
Sign = MD5(AppKey + Timestamp + AppSecret)
```

- 字符串拼接顺序：`AppKey` + `Timestamp` + `AppSecret`（无分隔符）
- MD5 结果取**小写** hex 字符串
- 时间戳有效期为 **5 分钟**，超出返回 401

**示例**（Python）：

```python
import hashlib, time

app_key    = "your_app_key"
app_secret = "your_app_secret"
timestamp  = str(int(time.time()))
raw        = app_key + timestamp + app_secret
sign       = hashlib.md5(raw.encode()).hexdigest()

headers = {
    "X-App-Key":   app_key,
    "X-Timestamp": timestamp,
    "X-Sign":      sign,
}
```

**配额限制**：所有业务接口经过配额检查，超限返回 HTTP **429**。

---

## 2. 统一响应格式

| 字段   | 类型   | 说明 |
|--------|--------|------|
| `code` | int    | 0=成功，非 0=业务错误 |
| `msg`  | string | 提示信息 |
| `data` | any    | 业务数据，失败时为 null |

成功示例：

```json
{ "code": 0, "msg": "success", "data": { ... } }
```

失败示例：

```json
{ "code": 1, "msg": "用户不存在", "data": null }
```

**HTTP 状态码**：业务错误仍返回 200，通过 `code` 区分；认证失败返回 **401**，配额超限返回 **429**。

---

## 3. 接口列表概览

| # | 模块 | 方法 | 路径 | 说明 |
|---|------|------|------|------|
| 1 | 用户管理 | GET  | `/merchant/root-user` | 获取根用户信息 |
| 2 | 用户管理 | POST | `/merchant/user/create` | 创建用户 |
| 3 | 用户管理 | GET  | `/merchant/users` | 用户列表（分页） |
| 4 | 用户管理 | GET  | `/merchant/user/info` | 用户详情（含余额/等级/团队/账户/策略） |
| 5 | 用户管理 | POST | `/merchant/user/apikey` | 绑定 API Key |
| 6 | 用户管理 | POST | `/merchant/user/apikey/unbind` | 解绑 API Key |
| 7 | 点卡     | GET  | `/merchant/balance` | 商户点卡余额 |
| 8 | 点卡     | POST | `/merchant/user/recharge` | 给用户充值/赠送点卡 |
| 9 | 点卡     | GET  | `/merchant/point-card/logs` | 点卡流水（分页） |
| 10 | 策略   | GET  | `/merchant/strategies` | 策略列表（租户已启用） |
| 11 | 策略   | POST | `/merchant/user/strategy/open` | 为用户开启（绑定）策略 |
| 12 | 策略   | POST | `/merchant/user/strategy/update` | 修改策略参数（本金/杠杆/风险档位） |
| 13 | 策略   | POST | `/merchant/user/strategy/close` | 关闭策略 |
| 14 | 策略   | GET  | `/merchant/user/strategies` | 用户已绑定策略列表 |
| 15 | 分销   | POST | `/merchant/user/transfer-point-card` | 点卡互转 |
| 16 | 分销   | GET  | `/merchant/user/team` | 用户团队（直推） |
| 17 | 分销   | POST | `/merchant/user/set-market-node` | 设置市场节点 |
| 18 | 分销   | GET  | `/merchant/user/rewards` | 奖励流水 |
| 19 | 分销   | POST | `/merchant/user/withdraw` | 申请提现 |
| 20 | 分销   | GET  | `/merchant/user/withdrawals` | 提现记录 |
| -- | 系统   | GET  | `/health` | 健康检查（无需认证） |

---

## 4. 用户管理

### 4.1 获取根用户信息

`GET /merchant/root-user`

**响应 data**：

| 字段        | 类型   | 说明 |
|-------------|--------|------|
| user_id     | int    | 根用户 ID |
| email       | string | 邮箱 |
| invite_code | string | 邀请码 |
| create_time | string | 创建时间 (`YYYY-MM-DD HH:mm:ss`) |

**响应示例**：

```json
{
  "code": 0, "msg": "success",
  "data": {
    "user_id": 1,
    "email": "admin@example.com",
    "invite_code": "ABC123",
    "create_time": "2025-01-15 10:30:00"
  }
}
```

---

### 4.2 创建用户

`POST /merchant/user/create`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数        | 类型   | 必填 | 说明 |
|-------------|--------|------|------|
| email       | string | 是   | 用户邮箱 |
| password    | string | 是   | 密码 |
| invite_code | string | 否   | 邀请人邀请码；不传则挂在根用户下 |

**响应 data**：

| 字段        | 类型   | 说明 |
|-------------|--------|------|
| user_id     | int    | 新用户 ID |
| email       | string | 邮箱 |
| invite_code | string | 该用户的邀请码 |
| inviter_id  | int    | 邀请人 ID |
| create_time | string | 创建时间 |

**错误**：邀请码无效 (`code:1`)、邀请码不属于该商户、邮箱已存在等。

---

### 4.3 用户列表

`GET /merchant/users`

| 参数        | 类型   | 必填 | 说明 |
|-------------|--------|------|------|
| page        | int    | 否   | 页码，默认 1 |
| limit       | int    | 否   | 每页条数，默认 20，最大 100 |
| email       | string | 否   | 按邮箱筛选 |
| invite_code | string | 否   | 按邀请码筛选 |
| status      | int    | 否   | 1=正常，2=禁用 |

**响应 data**：

```json
{
  "list": [
    {
      "user_id": 2,
      "email": "user@example.com",
      "invite_code": "XYZ789",
      "inviter_id": 1,
      "is_root": 0,
      "point_card_self": 100.0,
      "point_card_gift": 50.0,
      "point_card_total": 150.0,
      "status": 1,
      "create_time": "2025-02-01 12:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

**字段说明**：

| 字段             | 类型   | 说明 |
|------------------|--------|------|
| user_id          | int    | 用户 ID |
| email            | string | 邮箱 |
| invite_code      | string | 邀请码 |
| inviter_id       | int    | 邀请人 ID |
| is_root          | int    | 是否根用户 (0/1) |
| point_card_self  | float  | 自充点卡余额 |
| point_card_gift  | float  | 赠送点卡余额 |
| point_card_total | float  | 点卡总余额 |
| status           | int    | 1=正常，2=禁用 |
| create_time      | string | 创建时间 |

---

### 4.4 用户详情

`GET /merchant/user/info?email=xxx`

| 参数  | 类型   | 必填 | 说明 |
|-------|--------|------|------|
| email | string | 是   | 用户邮箱 |

**响应 data** — 一次返回用户全部信息：

```json
{
  "user_id": 2,
  "email": "user@example.com",
  "invite_code": "XYZ789",
  "inviter_invite_code": "ABC123",
  "status": 1,
  "create_time": "2025-02-01 12:00:00",
  "invite_count": 5,
  "point_card_self": 100.0,
  "point_card_gift": 50.0,
  "point_card_total": 150.0,
  "level": 2,
  "level_name": "VIP2",
  "is_market_node": 0,
  "self_hold": 500.0,
  "team_direct_count": 5,
  "team_total_count": 20,
  "team_performance": 10000.0,
  "reward_usdt": 88.5,
  "total_reward": 200.0,
  "withdrawn_reward": 111.5,
  "bound_exchanges": ["binance", "okx"],
  "accounts": [
    {
      "account_id": 10,
      "exchange": "binance",
      "account_type": "futures",
      "api_key": "your_api_key",
      "api_secret": "your_api_secret",
      "passphrase": null,
      "balance": 1000.0,
      "futures_balance": 1000.0,
      "futures_available": 800.0,
      "status": 1
    }
  ],
  "active_strategies": 2,
  "total_profit": 500.0,
  "total_trades": 35
}
```

**字段说明**：

| 字段                | 类型      | 说明 |
|---------------------|-----------|------|
| user_id             | int       | 用户 ID |
| email               | string    | 邮箱 |
| invite_code         | string    | 邀请码 |
| inviter_invite_code | string    | 邀请人的邀请码 |
| status              | int       | 1=正常，2=禁用 |
| create_time         | string    | 创建时间 |
| invite_count        | int       | 直推人数 |
| point_card_self     | float     | 自充点卡余额 |
| point_card_gift     | float     | 赠送点卡余额 |
| point_card_total    | float     | 点卡总余额 |
| level               | int       | 会员等级 |
| level_name          | string    | 等级名称 |
| is_market_node      | int       | 是否市场节点 (0/1) |
| self_hold           | float     | 自持金额 |
| team_direct_count   | int       | 直推人数 |
| team_total_count    | int       | 团队总人数（含多层） |
| team_performance    | float     | 团队业绩 |
| reward_usdt         | float     | 可用奖励余额 (USDT) |
| total_reward        | float     | 累计奖励 |
| withdrawn_reward    | float     | 已提现奖励 |
| bound_exchanges     | string[]  | 已绑定交易所列表 |
| accounts            | object[]  | 绑定的交易所账户（见下表） |
| active_strategies   | int       | 活跃策略数 |
| total_profit        | float     | 总盈利 |
| total_trades        | int       | 总交易笔数 |

**accounts[] 字段**：

| 字段              | 类型   | 说明 |
|-------------------|--------|------|
| account_id        | int    | 交易所账户 ID |
| exchange          | string | 交易所名称 |
| account_type      | string | 账户类型 (futures/spot) |
| api_key           | string | API Key 原文 |
| api_secret        | string | API Secret 原文 |
| passphrase        | string | OKX/Gate 的 Passphrase，Binance 为 null |
| balance           | float  | 余额 |
| futures_balance   | float  | 合约余额 |
| futures_available | float  | 合约可用余额 |
| status            | int    | 1=正常，2=禁用 |

> **⚠ 安全说明**：用户详情会返回 `api_key`、`api_secret`、`passphrase`。调用方须在服务端使用，**禁止**将响应暴露给前端、写入日志或传给第三方。

---

### 4.5 绑定用户 API Key

`POST /merchant/user/apikey`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数         | 类型   | 必填 | 说明 |
|--------------|--------|------|------|
| email        | string | 是   | 用户邮箱 |
| exchange     | string | 是   | 交易所：`binance` / `okx` / `gate` |
| api_key      | string | 是   | API Key |
| api_secret   | string | 是   | API Secret |
| passphrase   | string | 条件 | OKX **必填**（API Passphrase）；Gate 可选；Binance 不填 |
| account_type | string | 否   | 默认 `futures` |

**响应 data**：

| 字段         | 类型   | 说明 |
|--------------|--------|------|
| account_id   | int    | 创建/更新的账户 ID |
| exchange     | string | 交易所名称 |
| account_type | string | 账户类型 |

**错误**：不支持的交易所、OKX 未传 passphrase、用户不存在等。

---

### 4.6 解绑用户 API Key

`POST /merchant/user/apikey/unbind`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数       | 类型   | 必填 | 说明 |
|------------|--------|------|------|
| email      | string | 是   | 用户邮箱 |
| account_id | int    | 是   | 交易所账户 ID（绑定接口返回的 account_id） |

**响应 data**：成功时为 `null`，`msg` 为「解绑成功」。

---

## 5. 点卡

### 5.1 商户点卡余额

`GET /merchant/balance`

**响应 data**：商户维度的点卡余额信息。

---

### 5.2 给用户充值/赠送点卡

`POST /merchant/user/recharge`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数   | 类型   | 必填 | 说明 |
|--------|--------|------|------|
| email  | string | 是   | 用户邮箱 |
| amount | float  | 是   | 金额 |
| type   | int    | 否   | 1=充值(self)，2=赠送(gift)，默认 2 |

**响应**：`msg` 为「分发成功」，data 含变动后余额等信息。

---

### 5.3 点卡流水

`GET /merchant/point-card/logs`

| 参数        | 类型   | 必填 | 说明 |
|-------------|--------|------|------|
| page        | int    | 否   | 默认 1 |
| limit       | int    | 否   | 默认 20 |
| change_type | int    | 否   | 变动类型筛选 |
| email       | string | 否   | 传则查该用户的点卡流水；不传则查商户代理商流水 |
| start_time  | string | 否   | 开始时间 |
| end_time    | string | 否   | 结束时间 |

**响应 data**：

```json
{
  "list": [
    {
      "id": 1,
      "change_type": 2,
      "change_type_name": "赠送",
      "source_type": 2,
      "amount": 100.0,
      "before_self": 0.0,
      "after_self": 0.0,
      "before_gift": 0.0,
      "after_gift": 100.0,
      "member_id": 2,
      "to_type": 2,
      "remark": "代理商赠送",
      "create_time": 1738888888,
      "create_time_str": "2025-02-07 10:30:00"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

**change_type 含义**：

| 场景 | change_type | 说明 |
|------|------------|------|
| 商户流水（不传 email） | 1=后台充值，2=后台赠送，3=分发给用户 |  |
| 用户流水（传 email）   | 1=充值，2=赠送，3=转出，4=转入，5=盈利扣费 |  |

备注含义详见 [LEDGER_REMARKS.md](./LEDGER_REMARKS.md)。

---

## 6. 策略

### 6.1 策略列表

`GET /merchant/strategies`

返回当前租户下**已启用**的策略实例列表。每个策略包含完整的仓位配置参数。

**响应 data**（数组）：

| 字段             | 类型   | 说明 |
|------------------|--------|------|
| id               | int    | 策略 ID（等同 strategy_id） |
| strategy_id      | int    | 策略 ID |
| name             | string | 展示名称（租户实例覆盖优先） |
| description      | string | 策略描述 |
| symbol           | string | 交易对 (如 BTC/USDT) |
| timeframe        | string | K线周期 (如 1h) |
| min_capital      | float  | 最低资金要求 (USDT) |
| capital          | float  | 默认本金 (USDT) |
| leverage         | int    | 默认杠杆倍数 |
| risk_mode        | int    | 风险档位：1=稳健(1%) 2=均衡(1.5%) 3=激进(2%) |
| risk_mode_label  | string | 风险档位中文：稳健 / 均衡 / 激进 |
| amount_usdt      | float  | 计算后的下单金额 (USDT)，= capital × risk_pct × leverage |
| status           | int    | 状态 1=启用 |

**响应示例**：

```json
{
  "code": 0, "msg": "success",
  "data": [
    {
      "id": 1,
      "strategy_id": 1,
      "name": "趋势动量(稳健) 3.0",
      "description": "趋势动量 3.0 是一套基于人工智能行情识别的稳健型趋势跟随交易系统...",
      "symbol": "BTC/USDT",
      "timeframe": "1h",
      "min_capital": 200.0,
      "capital": 1000.0,
      "leverage": 20,
      "risk_mode": 1,
      "risk_mode_label": "稳健",
      "amount_usdt": 200.0,
      "status": 1
    },
    {
      "id": 2,
      "strategy_id": 2,
      "name": "趋势动量(均衡) 3.0",
      "description": "趋势动量 3.0 均衡版...",
      "symbol": "BTC/USDT",
      "timeframe": "1h",
      "min_capital": 200.0,
      "capital": 1000.0,
      "leverage": 20,
      "risk_mode": 2,
      "risk_mode_label": "均衡",
      "amount_usdt": 300.0,
      "status": 1
    },
    {
      "id": 3,
      "strategy_id": 3,
      "name": "趋势动量(激进) 3.0",
      "description": "趋势动量 3.0 激进版...",
      "symbol": "BTC/USDT",
      "timeframe": "1h",
      "min_capital": 200.0,
      "capital": 1000.0,
      "leverage": 20,
      "risk_mode": 3,
      "risk_mode_label": "激进",
      "amount_usdt": 400.0,
      "status": 1
    }
  ]
}
```

> **下单金额计算公式**：`amount_usdt = capital × risk_pct × leverage`  
> 其中 `risk_pct` 由 `risk_mode` 决定：1=1%，2=1.5%，3=2%。

---

### 6.2 开启（绑定）策略

`POST /merchant/user/strategy/open`  
**Content-Type**: `application/x-www-form-urlencoded`

为用户开启策略绑定，绑定后系统会按策略信号自动为该用户下单交易。

**请求参数**：

| 参数           | 类型   | 必填 | 默认值 | 说明 |
|----------------|--------|------|--------|------|
| email          | string | 是   | -      | 用户邮箱 |
| strategy_id    | int    | 是   | -      | 策略 ID（来自 `GET /merchant/strategies` 返回的 `id`） |
| account_id     | int    | 是   | -      | 交易所账户 ID（来自用户详情 `accounts[].account_id`） |
| mode           | int    | 否   | 2      | 执行模式：1=单次模式（仅执行一次），2=循环模式（每次信号都执行） |
| capital        | float  | 否   | 0      | 本金/最大仓位 (USDT)。如 1000 表示以 1000U 本金参与 |
| leverage       | int    | 否   | 20     | 杠杆倍数。可选值：5, 10, 20, 50, 75, 100 |
| risk_mode      | int    | 否   | 1      | 风险档位：**1**=稳健(1%) **2**=均衡(1.5%) **3**=激进(2%) |
| min_point_card | float  | 否   | 1.0    | 开通所需最低点卡余额 |

**仓位参数说明**：

用户的实际下单金额由 `capital`、`leverage`、`risk_mode` 三者计算而得：

```
下单金额 = capital × risk_pct × leverage
```

| risk_mode | 档位名称 | risk_pct | 示例（capital=1000, leverage=20） |
|-----------|---------|----------|-----------------------------------|
| 1         | 稳健    | 1%       | 1000 × 1% × 20 = **200 USDT**    |
| 2         | 均衡    | 1.5%     | 1000 × 1.5% × 20 = **300 USDT**  |
| 3         | 激进    | 2%       | 1000 × 2% × 20 = **400 USDT**    |

- 若不传 `capital`（默认0），系统会使用策略的默认仓位参数
- 若传了 `capital > 0`，则使用用户自定义的仓位参数
- 同一个策略可以绑定到用户的不同交易所账户（account_id 不同）

**响应 data**：

| 字段            | 类型   | 说明 |
|-----------------|--------|------|
| binding_id      | int    | 绑定记录 ID |
| strategy_id     | int    | 策略 ID |
| account_id      | int    | 交易所账户 ID |
| mode            | int    | 执行模式（1=单次，2=循环） |
| capital         | float  | 本金 (USDT) |
| leverage        | int    | 杠杆倍数 |
| risk_mode       | int    | 风险档位 |
| risk_mode_label | string | 风险档位名称（稳健/均衡/激进） |
| amount_usdt     | float  | 计算后的下单金额 (USDT) |

**响应示例**：

```json
{
  "code": 0,
  "msg": "开启成功",
  "data": {
    "binding_id": 15,
    "strategy_id": 1,
    "account_id": 10,
    "mode": 2,
    "capital": 1000.0,
    "leverage": 20,
    "risk_mode": 1,
    "risk_mode_label": "稳健",
    "amount_usdt": 200.0
  }
}
```

**完整调用示例**（Python）：

```python
import requests

resp = requests.post(
    "https://merchant.aigomsg.com/merchant/user/strategy/open",
    headers=headers,  # 认证头
    data={
        "email": "user@example.com",
        "strategy_id": 1,          # 趋势动量(稳健) 3.0
        "account_id": 10,          # Binance 合约账户
        "mode": 2,                 # 循环模式
        "capital": 1000,           # 本金 1000 USDT
        "leverage": 20,            # 20 倍杠杆
        "risk_mode": 1,            # 稳健(1%)
    }
)
print(resp.json())
# → {"code": 0, "msg": "开启成功", "data": {"binding_id": 15, "capital": 1000.0, "leverage": 20, "risk_mode": 1, "risk_mode_label": "稳健", "amount_usdt": 200.0, ...}}
```

**错误**：

| 错误信息 | 原因 |
|---------|------|
| 该策略未对本租户开放或已下架 | strategy_id 不在本租户的策略实例中 |
| 用户不存在 | email 不属于本租户 |
| 点卡不足 | 用户点卡余额 < min_point_card |
| 交易所账户不存在 | account_id 无效 |
| 已绑定该策略 | 同一 strategy_id + account_id 已存在绑定 |

---

### 6.3 修改策略参数

`POST /merchant/user/strategy/update`  
**Content-Type**: `application/x-www-form-urlencoded`

修改已绑定策略的仓位参数（本金/杠杆/风险档位），**不影响策略运行状态**。  
只需传需要修改的字段，未传的保持不变。

**请求参数**：

| 参数        | 类型   | 必填 | 说明 |
|-------------|--------|------|------|
| email       | string | 是   | 用户邮箱 |
| strategy_id | int    | 是   | 策略 ID |
| account_id  | int    | 是   | 交易所账户 ID |
| capital     | float  | 否   | 新的本金 (USDT)，不传则不修改 |
| leverage    | int    | 否   | 新的杠杆倍数，不传则不修改 |
| risk_mode   | int    | 否   | 新的风险档位（1/2/3），不传则不修改 |

**响应 data**：

| 字段            | 类型   | 说明 |
|-----------------|--------|------|
| binding_id      | int    | 绑定记录 ID |
| capital         | float  | 修改后的本金 (USDT) |
| leverage        | int    | 修改后的杠杆倍数 |
| risk_mode       | int    | 修改后的风险档位 |
| risk_mode_label | string | 风险档位名称（稳健/均衡/激进） |
| amount_usdt     | float  | 重新计算的下单金额 (USDT) |

**响应示例**：

```json
{
  "code": 0,
  "msg": "修改成功",
  "data": {
    "binding_id": 15,
    "capital": 2000.0,
    "leverage": 20,
    "risk_mode": 2,
    "risk_mode_label": "均衡",
    "amount_usdt": 600.0
  }
}
```

**完整调用示例**（Python）：

```python
# 示例1: 只修改本金
resp = requests.post(
    "https://merchant.aigomsg.com/merchant/user/strategy/update",
    headers=headers,
    data={
        "email": "user@example.com",
        "strategy_id": 1,
        "account_id": 10,
        "capital": 2000,           # 本金从 1000 改为 2000
    }
)
# → amount_usdt: 2000 × 1% × 20 = 400 USDT

# 示例2: 同时修改杠杆和风险档位
resp = requests.post(
    "https://merchant.aigomsg.com/merchant/user/strategy/update",
    headers=headers,
    data={
        "email": "user@example.com",
        "strategy_id": 1,
        "account_id": 10,
        "leverage": 50,            # 杠杆改为 50x
        "risk_mode": 3,            # 风险档位改为激进(2%)
    }
)
# → amount_usdt: 2000 × 2% × 50 = 2000 USDT
```

**错误**：

| 错误信息 | 原因 |
|---------|------|
| 用户不存在 | email 不属于本租户 |
| 绑定不存在 | strategy_id + account_id 未找到绑定记录 |

---

### 6.4 关闭策略

`POST /merchant/user/strategy/close`  
**Content-Type**: `application/x-www-form-urlencoded`

关闭用户的策略绑定，关闭后系统不再为该用户执行该策略的交易信号。

| 参数        | 类型   | 必填 | 说明 |
|-------------|--------|------|------|
| email       | string | 是   | 用户邮箱 |
| strategy_id | int    | 是   | 策略 ID |
| account_id  | int    | 是   | 交易所账户 ID |

**响应 data**：成功时为 `null`，`msg` 为「关闭成功」。

**完整调用示例**（Python）：

```python
resp = requests.post(
    "https://merchant.aigomsg.com/merchant/user/strategy/close",
    headers=headers,
    data={
        "email": "user@example.com",
        "strategy_id": 1,
        "account_id": 10,
    }
)
# → {"code": 0, "msg": "关闭成功", "data": null}
```

---

### 6.5 用户已绑定策略列表

`GET /merchant/user/strategies?email=xxx`

查询用户当前所有策略绑定记录，包含仓位参数和盈亏统计。

| 参数  | 类型   | 必填 | 说明 |
|-------|--------|------|------|
| email | string | 是   | 用户邮箱 |

**响应 data**（数组）：

| 字段            | 类型   | 说明 |
|-----------------|--------|------|
| strategy_id     | int    | 策略 ID |
| strategy_name   | string | 策略展示名称 |
| symbol          | string | 交易对 |
| account_id      | int    | 交易所账户 ID |
| status          | int    | 绑定状态：1=运行中，0=已停止 |
| mode            | int    | 执行模式：1=单次，2=循环 |
| capital         | float  | 本金 (USDT) |
| leverage        | int    | 杠杆倍数 |
| risk_mode       | int    | 风险档位 (1/2/3) |
| risk_mode_label | string | 风险档位名称（稳健/均衡/激进） |
| amount_usdt     | float  | 下单金额 (USDT) |
| total_profit    | float  | 累计盈亏 (USDT) |
| total_trades    | int    | 累计交易笔数 |
| create_time     | string | 绑定时间 |

**响应示例**：

```json
{
  "code": 0, "msg": "success",
  "data": [
    {
      "strategy_id": 1,
      "strategy_name": "趋势动量(稳健) 3.0",
      "symbol": "BTC/USDT",
      "account_id": 10,
      "status": 1,
      "mode": 2,
      "capital": 1000.0,
      "leverage": 20,
      "risk_mode": 1,
      "risk_mode_label": "稳健",
      "amount_usdt": 200.0,
      "total_profit": 88.50,
      "total_trades": 12,
      "create_time": "2026-02-07 21:49:10"
    }
  ]
}
```

---

## 7. 会员分销与奖励

### 7.1 点卡互转

`POST /merchant/user/transfer-point-card`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数       | 类型   | 必填 | 说明 |
|------------|--------|------|------|
| from_email | string | 是   | 转出方邮箱 |
| to_email   | string | 是   | 转入方邮箱 |
| amount     | float  | 是   | 金额 |
| type       | int    | 否   | 1=自充互转(self→self)，2=赠送互转(gift→gift)，默认 1 |

**约束**：仅支持同一邀请链路内互转，不能给自己转。

**响应 data**：

| 字段            | 类型   | 说明 |
|-----------------|--------|------|
| from_email      | string | 转出方邮箱 |
| to_email        | string | 转入方邮箱 |
| type            | int    | 互转类型 |
| type_name       | string | 类型名称 |
| amount          | float  | 金额 |
| from_self_after | float  | 转出方自充余额（转后） |
| from_gift_after | float  | 转出方赠送余额（转后） |
| to_self_after   | float  | 转入方自充余额（转后） |
| to_gift_after   | float  | 转入方赠送余额（转后） |

---

### 7.2 用户团队（直推）

`GET /merchant/user/team?email=xxx`

| 参数  | 类型   | 必填 | 说明 |
|-------|--------|------|------|
| email | string | 是   | 用户邮箱 |
| page  | int    | 否   | 默认 1 |
| limit | int    | 否   | 默认 20 |

**响应 data**：

```json
{
  "list": [
    {
      "user_id": 3,
      "email": "member@example.com",
      "level": 1,
      "level_name": "VIP1",
      "is_market_node": 0,
      "team_performance": 5000.0,
      "sub_count": 3,
      "create_time": "2025-03-01 09:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20,
  "team_stats": {
    "direct_count": 1,
    "total_count": 10,
    "total_performance": 50000.0
  }
}
```

**list[] 字段**：

| 字段             | 类型   | 说明 |
|------------------|--------|------|
| user_id          | int    | 用户 ID |
| email            | string | 邮箱 |
| level            | int    | 会员等级 |
| level_name       | string | 等级名称 |
| is_market_node   | int    | 是否市场节点 |
| team_performance | float  | 团队业绩 |
| sub_count        | int    | 下级人数 |
| create_time      | string | 创建时间 |

**team_stats 字段**：

| 字段              | 类型  | 说明 |
|-------------------|-------|------|
| direct_count      | int   | 直推人数 |
| total_count       | int   | 团队总人数 |
| total_performance | float | 团队总业绩 |

---

### 7.3 设置市场节点

`POST /merchant/user/set-market-node`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数    | 类型   | 必填 | 说明 |
|---------|--------|------|------|
| email   | string | 是   | 用户邮箱 |
| is_node | int    | 是   | 1=设为市场节点，0=取消 |

**响应 data**：成功时为 `null`，`msg` 为「已设置为市场节点」或「已取消市场节点资格」。

---

### 7.4 奖励流水

`GET /merchant/user/rewards?email=xxx`

| 参数        | 类型   | 必填 | 说明 |
|-------------|--------|------|------|
| email       | string | 是   | 用户邮箱 |
| page        | int    | 否   | 默认 1 |
| limit       | int    | 否   | 默认 20 |
| reward_type | string | 否   | 按奖励类型筛选：`direct` / `level_diff` / `peer` |

**响应 data**：

```json
{
  "list": [
    {
      "id": 1,
      "reward_type": "direct",
      "reward_type_name": "直推奖",
      "amount": 10.0,
      "source_user_id": 3,
      "source_email": "member@example.com",
      "rate": 0.1,
      "settle_batch": "20250207",
      "remark": "直推奖励",
      "create_time": "2025-02-07 10:30:00"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

**list[] 字段**：

| 字段            | 类型   | 说明 |
|-----------------|--------|------|
| id              | int    | 记录 ID |
| reward_type     | string | 奖励类型：direct / level_diff / peer |
| reward_type_name| string | 中文名称：直推奖 / 级差奖 / 平级奖 |
| amount          | float  | 奖励金额 (USDT) |
| source_user_id  | int    | 来源用户 ID |
| source_email    | string | 来源用户邮箱 |
| rate            | float  | 奖励比例 |
| settle_batch    | string | 结算批次 |
| remark          | string | 备注 |
| create_time     | string | 创建时间 |

---

### 7.5 申请提现

`POST /merchant/user/withdraw`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数           | 类型   | 必填 | 说明 |
|----------------|--------|------|------|
| email          | string | 是   | 用户邮箱 |
| amount         | float  | 是   | 提现金额 |
| wallet_address | string | 是   | 收款钱包地址 |
| wallet_network | string | 否   | 链类型，默认 TRC20 |
| remark         | string | 否   | 备注 |

**响应 data**：

| 字段          | 类型   | 说明 |
|---------------|--------|------|
| withdrawal_id | int    | 提现记录 ID |
| amount        | float  | 提现金额 |
| fee           | float  | 手续费 |
| actual_amount | float  | 实际到账金额 |
| status        | int    | 状态码 |
| status_name   | string | 状态名称 |
| create_time   | string | 创建时间 |

**提现状态**：

| status | 名称   |
|--------|--------|
| 0      | 待审核 |
| 1      | 已通过 |
| 2      | 已拒绝 |
| 3      | 已完成 |

---

### 7.6 提现记录

`GET /merchant/user/withdrawals?email=xxx`

| 参数   | 类型   | 必填 | 说明 |
|--------|--------|------|------|
| email  | string | 是   | 用户邮箱 |
| page   | int    | 否   | 默认 1 |
| limit  | int    | 否   | 默认 20 |
| status | int    | 否   | 按状态筛选 (0/1/2/3) |

**响应 data**：

```json
{
  "list": [
    {
      "id": 1,
      "amount": 100.0,
      "fee": 1.0,
      "actual_amount": 99.0,
      "wallet_address": "Txxxxxxxxxx",
      "wallet_network": "TRC20",
      "status": 0,
      "status_name": "待审核",
      "tx_hash": "",
      "audit_time": "",
      "complete_time": "",
      "create_time": "2025-02-07 10:30:00"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

**list[] 字段**：

| 字段           | 类型   | 说明 |
|----------------|--------|------|
| id             | int    | 记录 ID |
| amount         | float  | 提现金额 |
| fee            | float  | 手续费 |
| actual_amount  | float  | 实际到账金额 |
| wallet_address | string | 钱包地址 |
| wallet_network | string | 链类型 |
| status         | int    | 状态码 |
| status_name    | string | 状态名称 |
| tx_hash        | string | 链上交易哈希（已完成时） |
| audit_time     | string | 审核时间 |
| complete_time  | string | 完成时间 |
| create_time    | string | 创建时间 |

---

## 8. 健康检查

`GET /health`  
无需认证。

**响应**：

```json
{ "status": "ok", "service": "merchant-api" }
```

---

## 9. 附录

### 9.1 错误处理

| HTTP 状态码 | 含义 |
|-------------|------|
| 200         | 成功或业务错误（通过 `code` 区分） |
| 401         | 认证失败（AppKey 无效/签名错误/时间戳过期） |
| 429         | 配额超限 |

### 9.2 仓位参数说明

系统采用 **本金 × 风险比例 × 杠杆** 的统一仓位模型：

| 参数      | 说明 | 取值范围 |
|-----------|------|---------|
| capital   | 本金/最大仓位 (USDT) | 建议 ≥ min_capital |
| leverage  | 杠杆倍数 | 5 / 10 / 20 / 50 / 75 / 100 |
| risk_mode | 风险档位 | 1=稳健(1%) / 2=均衡(1.5%) / 3=激进(2%) |

**计算公式**：

```
保证金  = capital × risk_pct
下单金额 = capital × risk_pct × leverage
```

**示例**：

| 本金 (capital) | 杠杆 (leverage) | 风险档位 (risk_mode) | 保证金 | 下单金额 (amount_usdt) |
|:-:|:-:|:-:|:-:|:-:|
| 1000 | 20 | 1 (稳健 1%) | 10 | 200 |
| 1000 | 20 | 2 (均衡 1.5%) | 15 | 300 |
| 1000 | 20 | 3 (激进 2%) | 20 | 400 |
| 2000 | 50 | 1 (稳健 1%) | 20 | 1000 |
| 5000 | 10 | 3 (激进 2%) | 100 | 1000 |

### 9.3 参考文档

- **点卡/流水备注**：详见 [LEDGER_REMARKS.md](./LEDGER_REMARKS.md)
- **API Key 绑定说明**：详见 [MERCHANT_BIND_API.md](./MERCHANT_BIND_API.md)

### 9.4 状态码约定

- **用户状态**（`users[].status`、`accounts[].status`）：1=正常，2=禁用
- **提现状态**：0=待审核，1=已通过，2=已拒绝，3=已完成
- **策略状态**：1=启用
- **绑定状态**：1=运行中，0=已停止

### 9.5 典型业务流程

```
1. 创建用户      POST /merchant/user/create
2. 充值点卡      POST /merchant/user/recharge
3. 绑定 API Key  POST /merchant/user/apikey
4. 查看策略列表   GET  /merchant/strategies
5. 开启策略      POST /merchant/user/strategy/open   (含 capital/leverage/risk_mode)
6. 查看绑定      GET  /merchant/user/strategies
7. 修改参数      POST /merchant/user/strategy/update  (可单独改 capital/leverage/risk_mode)
8. 关闭策略      POST /merchant/user/strategy/close
```
