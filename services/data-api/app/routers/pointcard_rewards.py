"""
点卡流水与奖励记录 — 独立路由优先挂载，避免与其它 prefix=/api 冲突导致 404。
GET /api/pointcard-logs
GET /api/rewards
"""
from fastapi import APIRouter

from .user_manage import list_pointcard_logs, list_rewards

router = APIRouter(prefix="/api", tags=["user-manage"])
router.add_api_route("/pointcard-logs", list_pointcard_logs, methods=["GET"])
router.add_api_route("/rewards", list_rewards, methods=["GET"])
