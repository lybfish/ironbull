# Merchant API 接口文档

> **版本**: v1.1 &nbsp;|&nbsp; **更新日期**: 2026-02-07  
> **服务端口**: 8010  
> **Base URL**: `https://merchant.aigomsg.com`（生产） / `http://localhost:8010`（开发）

Merchant API 面向代理商/商户 B2B 场景，用于管理租户下的用户、点卡、策略与会员分销。  
共 **19 个业务接口** + 1 个健康检查。

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
| 11 | 策略   | POST | `/merchant/user/strategy/open` | 为用户开启策略 |
| 12 | 策略   | POST | `/merchant/user/strategy/close` | 关闭策略 |
| 13 | 策略   | GET  | `/merchant/user/strategies` | 用户已绑定策略列表 |
| 14 | 分销   | POST | `/merchant/user/transfer-point-card` | 点卡互转 |
| 15 | 分销   | GET  | `/merchant/user/team` | 用户团队（直推） |
| 16 | 分销   | POST | `/merchant/user/set-market-node` | 设置市场节点 |
| 17 | 分销   | GET  | `/merchant/user/rewards` | 奖励流水 |
| 18 | 分销   | POST | `/merchant/user/withdraw` | 申请提现 |
| 19 | 分销   | GET  | `/merchant/user/withdrawals` | 提现记录 |
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

返回当前租户下**已启用**的策略实例列表。

**响应 data**（数组）：

| 字段        | 类型   | 说明 |
|-------------|--------|------|
| id          | int    | 策略 ID（等同 strategy_id） |
| strategy_id | int    | 策略 ID |
| name        | string | 展示名称（租户实例覆盖优先） |
| description | string | 策略描述 |
| symbol      | string | 交易对 (如 BTC/USDT) |
| timeframe   | string | 周期 |
| min_capital | float  | 最低资金要求 |
| status      | int    | 状态 |

**响应示例**：

```json
{
  "code": 0, "msg": "success",
  "data": [
    {
      "id": 1,
      "strategy_id": 1,
      "name": "BTC 趋势策略",
      "description": "基于均线突破的BTC合约策略",
      "symbol": "BTC/USDT",
      "timeframe": "4h",
      "min_capital": 200.0,
      "status": 1
    }
  ]
}
```

---

### 6.2 开启策略

`POST /merchant/user/strategy/open`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数           | 类型   | 必填 | 说明 |
|----------------|--------|------|------|
| email          | string | 是   | 用户邮箱 |
| strategy_id    | int    | 是   | 策略 ID（来自策略列表） |
| account_id     | int    | 是   | 交易所账户 ID（用户详情中 accounts[].account_id） |
| mode           | int    | 否   | 执行模式：1=**单次模式**（仅执行一次，触发后不再跟单），2=**循环模式**（每次信号都执行），默认 2 |
| min_point_card | float  | 否   | 开通所需最小点卡余额，默认 1.0 |

**响应 data**：

| 字段        | 类型 | 说明 |
|-------------|------|------|
| binding_id  | int  | 绑定记录 ID |
| strategy_id | int  | 策略 ID |
| account_id  | int  | 账户 ID |
| mode        | int  | 执行模式（1=单次，2=循环） |

**错误**：策略未对本租户开放或已下架、用户不存在、点卡不足、账户不存在等。

---

### 6.3 关闭策略

`POST /merchant/user/strategy/close`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数        | 类型   | 必填 | 说明 |
|-------------|--------|------|------|
| email       | string | 是   | 用户邮箱 |
| strategy_id | int    | 是   | 策略 ID |
| account_id  | int    | 是   | 交易所账户 ID |

**响应 data**：成功时为 `null`，`msg` 为「关闭成功」。

---

### 6.4 用户已绑定策略列表

`GET /merchant/user/strategies?email=xxx`

| 参数  | 类型   | 必填 | 说明 |
|-------|--------|------|------|
| email | string | 是   | 用户邮箱 |

**响应 data**：数组，每项包含策略信息及绑定状态、收益等。

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

### 9.2 参考文档

- **点卡/流水备注**：详见 [LEDGER_REMARKS.md](./LEDGER_REMARKS.md)
- **API Key 绑定说明**：详见 [MERCHANT_BIND_API.md](./MERCHANT_BIND_API.md)（若存在）

### 9.3 状态码约定

- **用户状态**（`users[].status`、`accounts[].status`）：1=正常，2=禁用
- **提现状态**：0=待审核，1=已通过，2=已拒绝，3=已完成
- **策略状态**：1=启用
