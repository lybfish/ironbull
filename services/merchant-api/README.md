# Merchant API

代理商 B2B 接口：用户管理、点卡、策略、会员分销与奖励。  
认证方式：AppKey + 签名（X-App-Key, X-Timestamp, X-Sign）。

## 接口文档

完整接口说明见项目文档：  
**[docs/api/MERCHANT_API.md](../../docs/api/MERCHANT_API.md)**

包含：认证、统一响应格式、19 个接口的路径/参数/请求体/响应说明。

## 认证摘要

- Header：`X-App-Key`、`X-Timestamp`、`X-Sign`
- 签名：`Sign = MD5(AppKey + Timestamp + AppSecret)`（小写 hex）
- 时间戳有效期为 5 分钟

## 依赖

需安装 `python-multipart`（Form 表单）：已写入项目根目录 `requirements.txt`。

## 启动

```bash
cd services/merchant-api
PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

端口占用时可改用 8011。生产环境由 `deploy/start.sh` 管理。

## 健康检查

```bash
curl http://127.0.0.1:8010/health
```

返回 `{"status":"ok","service":"merchant-api"}`。
