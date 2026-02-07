# Merchant API 接口文档

Merchant API 面向代理商/商户 B2B 场景，用于管理租户下的用户、点卡、策略与会员分销。  
**Base URL**：`https://merchant.aigomsg.com`（
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

**示例**（伪代码）：

```
AppKey   = "your_app_key"
Timestamp = "1738888888"
AppSecret = "your_app_secret"
raw = AppKey + Timestamp + AppSecret
X-Sign = md5(raw).toLowerCase()
```

请求时设置：

```
X-App-Key: your_app_key
X-Timestamp: 1738888888
X-Sign: <计算得到的 32 位小写 hex>
```

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

**HTTP 状态码**：业务错误仍返回 200，通过 `code` 区分；认证失败返回 401，配额超限返回 429。

---

## 3. 接口列表概览

| 模块     | 方法 | 路径 | 说明 |
|----------|------|------|------|
| 用户管理 | GET  | `/merchant/root-user` | 获取根用户信息 |
| 用户管理 | POST | `/merchant/user/create` | 创建用户 |
| 用户管理 | GET  | `/merchant/users` | 用户列表 |
| 用户管理 | GET  | `/merchant/user/info` | 用户详情 |
| 用户管理 | POST | `/merchant/user/apikey` | 绑定 API Key |
| 用户管理 | POST | `/merchant/user/apikey/unbind` | 解绑 API Key |
| 点卡     | GET  | `/merchant/balance` | 商户点卡余额 |
| 点卡     | POST | `/merchant/user/recharge` | 给用户充值/赠送点卡 |
| 点卡     | GET  | `/merchant/point-card/logs` | 点卡流水 |
| 策略     | GET  | `/merchant/strategies` | 策略列表 |
| 策略     | POST | `/merchant/user/strategy/open` | 开启策略 |
| 策略     | POST | `/merchant/user/strategy/close` | 关闭策略 |
| 策略     | GET  | `/merchant/user/strategies` | 用户已绑定策略列表 |
| 会员分销 | POST | `/merchant/user/transfer-point-card` | 点卡互转 |
| 会员分销 | GET  | `/merchant/user/team` | 用户团队（直推） |
| 会员分销 | POST | `/merchant/user/set-market-node` | 设置市场节点 |
| 会员分销 | GET  | `/merchant/user/rewards` | 奖励流水 |
| 会员分销 | POST | `/merchant/user/withdraw` | 申请提现 |
| 会员分销 | GET  | `/merchant/user/withdrawals` | 提现记录 |

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
| create_time | string | 创建时间 |

---

### 4.2 创建用户

`POST /merchant/user/create`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数        | 类型   | 必填 | 说明 |
|-------------|--------|------|------|
| email       | string | 是   | 用户邮箱 |
| password    | string | 是   | 密码 |
| invite_code | string | 否   | 邀请人邀请码；不传则挂在根用户下 |

**响应 data**：`user_id`, `email`, `invite_code`, `inviter_id`, `create_time`

**错误**：邀请码无效、邀请码不属于该商户、邮箱已存在等返回 `code: 1`。

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

**响应 data**：`{ "list": [...], "total": n, "page": p, "limit": l }`  
list 每项：`user_id`, `email`, `invite_code`, `inviter_id`, `is_root`, `point_card_self`, `point_card_gift`, `point_card_total`, `status`, `create_time`。  
**约定**：`status` 1=正常，2=禁用（与库存 0/1 映射）。

---

### 4.4 用户详情

`GET /merchant/user/info?email=xxx`

| 参数  | 类型   | 必填 | 说明 |
|-------|--------|------|------|
| email | string | 是   | 用户邮箱 |

**响应 data**：用户基本信息 + 点卡 + 等级 + 团队 + 账户（含 API 信息）+ 策略汇总，例如：

- `user_id`, `email`, `invite_code`, `inviter_invite_code`, `status`, `create_time`
- `invite_count`, `point_card_self`, `point_card_gift`, `point_card_total`
- `level`, `level_name`, `is_market_node`, `self_hold`
- `team_direct_count`, `team_total_count`, `team_performance`
- `reward_usdt`, `total_reward`, `withdrawn_reward`
- **`bound_exchanges`**：已绑定交易所列表，如 `["binance", "okx"]`
- **`accounts`**：数组，每项为绑定的交易所账户（含完整 API 秘钥，仅供商户后端安全使用，勿暴露到前端或日志）：
  - `account_id`, `exchange`, `account_type`
  - **`api_key`**：API Key 原文
  - **`api_secret`**：API Secret 原文
  - **`passphrase`**：OKX/Gate 的 API Passphrase，Binance 为 null
  - `balance`, `futures_balance`, `futures_available`, `status`
- `active_strategies`, `total_profit`, `total_trades`

**安全说明**：用户详情接口会返回该用户下所有绑定账户的 api_key、api_secret、passphrase。调用方须在服务端使用，禁止将响应暴露给前端、写入日志或传给第三方。

**约定**：`status`、`accounts[].status` 均为 1=正常，2=禁用。

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
| passphrase   | string | 否   | OKX 必填（API Passphrase）；Gate 可选；Binance 不填 |
| account_type | string | 否   | 默认 `futures` |

**响应 data**：`account_id`, `exchange`, `account_type`  
**错误**：不支持的交易所、OKX 未传 passphrase、用户不存在等。

---

### 4.6 解绑用户 API Key

`POST /merchant/user/apikey/unbind`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数       | 类型 | 必填 | 说明 |
|------------|------|------|------|
| email      | string | 是 | 用户邮箱 |
| account_id | int  | 是   | 交易所账户 ID（绑定接口返回的 account_id） |

**响应 data**：成功时为 `null`，`msg` 为「解绑成功」。

---

## 5. 点卡

### 5.1 商户点卡余额

`GET /merchant/balance`

**响应 data**：商户维度的点卡余额结构（具体字段以实际返回为准，如自充/赠送余额等）。

---

### 5.2 给用户充值/赠送点卡

`POST /merchant/user/recharge`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数   | 类型  | 必填 | 说明 |
|--------|-------|------|------|
| email  | string | 是 | 用户邮箱 |
| amount | float | 是   | 金额 |
| type   | int   | 否   | 1=充值(self)，2=赠送(gift)，默认 2 |

**响应 data**：分发结果（如变动后余额等），`msg` 为「分发成功」。

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

**响应 data**：`{ "list": [...], "total": n, "page": p, "limit": l }`  
list 每项：`id`, `change_type`, `change_type_name`, `source_type`, `amount`, `before_self`, `after_self`, `before_gift`, `after_gift`, `member_id`, `to_type`, `remark`, `create_time`, `create_time_str`。  
备注含义见 [LEDGER_REMARKS.md](./LEDGER_REMARKS.md)。

---

## 6. 策略

### 6.1 策略列表

`GET /merchant/strategies`

返回当前租户下**已启用**的策略实例列表。

**响应 data**：数组，每项 `id`, `strategy_id`, `name`, `description`, `symbol`, `timeframe`, `min_capital`, `status`。展示名、杠杆、金额等以租户策略实例为准。

---

### 6.2 开启策略

`POST /merchant/user/strategy/open`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数           | 类型  | 必填 | 说明 |
|----------------|-------|------|------|
| email          | string | 是 | 用户邮箱 |
| strategy_id    | int   | 是   | 策略 ID（来自策略列表） |
| account_id     | int   | 是   | 交易所账户 ID（用户详情中 accounts[].account_id） |
| mode           | int   | 否   | 默认 2 |
| min_point_card | float | 否   | 开通所需最小点卡余额，默认 1.0 |

**响应 data**：`binding_id`, `strategy_id`, `account_id`, `mode`  
**错误**：策略未开放、用户不存在、点卡不足、账户不存在等。

---

### 6.3 关闭策略

`POST /merchant/user/strategy/close`  
**Content-Type**: `application/x-www-form-urlencoded`

| 参数        | 类型   | 必填 | 说明 |
|-------------|--------|------|------|
| email       | string | 是   | 用户邮箱 |
| strategy_id | int    | 是   | 策略 ID |
| account_id  | int    | 是   | 交易所账户 ID |

**响应 data**：成功时为 `null`。

---

### 6.4 用户已绑定策略列表

`GET /merchant/user/strategies?email=xxx`

| 参数  | 类型   | 必填 | 说明 |
|-------|--------|------|------|
| email | string | 是   | 用户邮箱 |

**响应 data**：数组，每项包含策略信息及绑定状态、收益等（以实际返回为准）。

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
**响应 data**：`from_email`, `to_email`, `type`, `type_name`, `amount`, `from_self_after`, `from_gift_after`, `to_self_after`, `to_gift_after`。

---

### 7.2 用户团队（直推）

`GET /merchant/user/team?email=xxx`

| 参数  | 类型   | 必填 | 说明 |
|-------|--------|------|------|
| email | string | 是   | 用户邮箱 |
| page  | int    | 否   | 默认 1 |
| limit | int    | 否   | 默认 20 |

**响应 data**：`list`（直推成员列表，含 user_id, email, level, level_name, is_market_node, team_performance, sub_count, create_time）、`total`, `page`, `limit`、`team_stats`（direct_count, total_count, total_performance）。

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
| reward_type | string | 否   | 直推/级差/平级等筛选 |

**响应 data**：`{ "list": [...], "total": n, "page": p, "limit": l }`  
list 每项：`id`, `reward_type`, `reward_type_name`, `amount`, `source_user_id`, `source_email`, `rate`, `settle_batch`, `remark`, `create_time`。  
备注含义见 [LEDGER_REMARKS.md](./LEDGER_REMARKS.md)。

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

**响应 data**：`withdrawal_id`, `amount`, `fee`, `actual_amount`, `status`, `status_name`, `create_time`。  
**状态**：0=待审核，1=已通过，2=已拒绝，3=已完成。

---

### 7.6 提现记录

`GET /merchant/user/withdrawals?email=xxx`

| 参数   | 类型   | 必填 | 说明 |
|--------|--------|------|------|
| email  | string | 是   | 用户邮箱 |
| page   | int    | 否   | 默认 1 |
| limit  | int    | 否   | 默认 20 |
| status | int    | 否   | 按状态筛选 |

**响应 data**：`{ "list": [...], "total": n, "page": p, "limit": l }`  
list 每项：`id`, `amount`, `fee`, `actual_amount`, `wallet_address`, `wallet_network`, `status`, `status_name`, `tx_hash`, `audit_time`, `complete_time`, `create_time`。

---

## 8. 健康检查

`GET /health`  
无需认证。

**响应**：`{ "status": "ok", "service": "merchant-api" }`

---

## 9. 附录

- **配额**：若启用配额，超限返回 HTTP 429，需联系平台调整或等待重置。
- **点卡/流水备注**：详见 [LEDGER_REMARKS.md](./LEDGER_REMARKS.md)。
- **API Key 绑定说明**：详见 [MERCHANT_BIND_API.md](./MERCHANT_BIND_API.md)（若存在）。
