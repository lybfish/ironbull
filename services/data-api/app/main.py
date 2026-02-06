"""
Data API Service - 统一数据查询接口

为 OrderTrade、Position、Ledger、Analytics 提供 REST 查询 API。
通过 query 参数 tenant_id（必填）、account_id（可选）做租户与账户隔离。
端口：8026

接口：
- GET /api/orders       - 订单查询
- GET /api/fills        - 成交查询
- GET /api/positions    - 持仓查询
- GET /api/accounts     - 资金账户查询
- GET /api/transactions - 流水查询
- GET /api/analytics/performance - 绩效与净值曲线
- GET /api/analytics/risk       - 风险指标
- GET /api/analytics/statistics  - 交易统计
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from libs.core.database import init_database
from libs.core.logger import get_logger, setup_logging
from libs.core import get_config

from .routers import orders, positions, accounts, analytics, auth, strategies, signal_monitor, nodes, sync, tenants, admins, dashboard, users, bindings, exchange_accounts, quota

config = get_config()
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name="data-api",
)
log = get_logger("data-api")

init_database()
log.info("data-api starting")

app = FastAPI(
    title="Data API",
    description="统一数据查询：订单、成交、持仓、资金、流水、绩效与风险",
    version="1.0",
)

# CORS：从配置 cors_origins 读取，逗号分隔；未配置则仅允许本地开发端口
_cors_raw = config.get_str("cors_origins", "").strip()
if _cors_raw:
    _cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
else:
    _cors_origins = [
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
    ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(positions.router)
app.include_router(accounts.router)
app.include_router(analytics.router)
app.include_router(strategies.router)
app.include_router(signal_monitor.router)
app.include_router(nodes.router)
app.include_router(sync.router)
app.include_router(tenants.router)
app.include_router(admins.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(bindings.router)
app.include_router(exchange_accounts.router)
app.include_router(quota.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "data-api"}


if __name__ == "__main__":
    import uvicorn
    # 8026 避免与 crypto-node 常用 8025 冲突
    uvicorn.run(app, host="0.0.0.0", port=8026)
