# Merchant API

代理商 B2B 接口，与 old3 merchant-api 文档兼容。

## 认证

- Header: `X-App-Key`, `X-Timestamp`, `X-Sign`
- Sign = `md5(AppKey + Timestamp + AppSecret)`，5 分钟有效

## 数据库

执行迁移（在项目根目录）：

```bash
mysql -u root -p ironbull < migrations/007_platform_layer.sql
```

## 依赖

需安装 `python-multipart`（Form 表单）：`pip install python-multipart`（已写入项目 requirements.txt）

## 启动

```bash
cd services/merchant-api
PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

若 8010 被占用可改用 8011。

## 接口

- 用户管理: GET/POST /merchant/root-user, /merchant/user/create, /merchant/users, /merchant/user/info, /merchant/user/apikey, /merchant/user/apikey/unbind
- 点卡: GET /merchant/balance, POST /merchant/user/recharge, GET /merchant/user/balance, GET /merchant/point-card/logs
- 策略: GET /merchant/strategies, POST /merchant/user/strategy/open, POST /merchant/user/strategy/close, GET /merchant/user/strategies
- 会员分销: POST /merchant/user/transfer-point-card, GET /merchant/user/level, GET /merchant/user/team, POST /merchant/user/set-market-node, GET /merchant/user/rewards, GET /merchant/user/reward-balance, POST /merchant/user/withdraw, GET /merchant/user/withdrawals
