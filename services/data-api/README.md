# Data API

统一数据查询 REST 接口，为前端与运营提供订单、成交、持仓、资金、流水、绩效与风险查询。

## 启动

```bash
cd services/data-api
PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8026
# 或直接运行（默认 8026）
PYTHONPATH=../.. python3 app/main.py
```

## 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/orders | 订单列表（tenant_id 必填，支持 account_id/symbol/status/时间等） |
| GET | /api/fills | 成交列表（tenant_id 必填，支持 order_id/symbol/时间等） |
| GET | /api/positions | 持仓列表（tenant_id 必填，支持 account_id/symbol/has_position 等） |
| GET | /api/accounts | 资金账户列表（Ledger 层，tenant_id 必填） |
| GET | /api/transactions | 账务流水列表（tenant_id 必填，支持类型、时间范围） |
| GET | /api/analytics/performance | 绩效汇总与净值曲线（tenant_id、account_id 必填） |
| GET | /api/analytics/risk | 最新风险指标（tenant_id、account_id 必填） |
| GET | /api/analytics/statistics | 交易统计列表（tenant_id、account_id 必填） |

## 鉴权

- **登录**：POST /api/auth/login，body 传 `tenant_id`、`email`、`password`，返回 `token`。管理后台用该 token 请求其他接口。
- **请求**：带 `Authorization: Bearer <token>` 时，租户从 JWT 解析，无需再传 query `tenant_id`；未带 token 时需在 query 传 `tenant_id`（兼容 curl 等）。
- **配置**：可选环境变量或 config `jwt_secret`（生产务必设置），否则使用开发默认密钥。

## 示例

```bash
# 订单列表
curl "http://127.0.0.1:8026/api/orders?tenant_id=1&account_id=1&limit=20"

# 绩效与净值曲线
curl "http://127.0.0.1:8026/api/analytics/performance?tenant_id=1&account_id=1&start_date=2025-01-01&end_date=2025-02-01"
```
