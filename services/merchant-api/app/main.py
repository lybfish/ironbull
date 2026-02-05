"""
Merchant API Service - 代理商 B2B 接口

认证：AppKey + Sign（X-App-Key, X-Timestamp, X-Sign）
端口：8010

22 个接口：用户管理(6)、点卡(4)、策略(4)、会员分销(8)
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from libs.core.database import init_database
from libs.core.logger import get_logger, setup_logging
from libs.core import get_config

from .routers import user, pointcard, strategy, reward

config = get_config()
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name="merchant-api",
)
log = get_logger("merchant-api")

init_database()
log.info("merchant-api starting")

app = FastAPI(
    title="Merchant API",
    description="代理商 B2B 接口，AppKey+Sign 认证",
    version="1.0",
)

app.include_router(user.router)
app.include_router(pointcard.router)
app.include_router(strategy.router)
app.include_router(reward.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "merchant-api"}


@app.exception_handler(401)
def auth_exception_handler(request, exc):
    return JSONResponse(
        status_code=401,
        content={"code": 401, "msg": str(exc.detail) if hasattr(exc, "detail") else "认证失败", "data": None},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
