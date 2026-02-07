"""
风控配置管理 API（管理端配置存储与违规查询）

GET  /api/risk/rules      -> 获取当前风控规则列表及参数
PUT  /api/risk/rules      -> 更新风控规则配置
GET  /api/risk/violations  -> 风控违规历史记录
POST /api/risk/test        -> 测试风控规则（模拟检查）

注意：规则存 Redis（ironbull:risk:config），供本 API 与 evui 风控管理页使用。
执行链路（signal-monitor / risk-control 服务）目前未读取该配置，仍使用 config 或代码内默认规则。
若需「后台改规则即生效」，需在 risk-control 或 signal-monitor 中改为从 Redis/本 API 拉取规则再构建引擎。
"""

from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta

from libs.facts.models import AuditLog

from ..deps import get_db, get_current_admin

router = APIRouter(prefix="/api/risk", tags=["risk"])

# 风控规则配置存储（内存 + 支持持久化到 Redis）
# 格式：{rule_name: {enabled, params...}}
_DEFAULT_RISK_CONFIG = {
    "min_balance": {"enabled": True, "min_balance": 100.0, "description": "最小余额限制", "severity": "critical"},
    "max_position": {"enabled": True, "max_positions": 10, "description": "最大持仓数量", "severity": "error"},
    "max_position_value": {"enabled": False, "max_value": 10000.0, "description": "单仓最大价值", "severity": "error"},
    "daily_trade_limit": {"enabled": True, "max_trades": 100, "description": "日交易次数上限", "severity": "warning"},
    "weekly_trade_limit": {"enabled": False, "max_trades": 500, "description": "周交易次数上限", "severity": "warning"},
    "daily_loss_limit": {"enabled": True, "max_loss": 1000.0, "description": "日亏损上限(USDT)", "severity": "critical"},
    "consecutive_loss_cooldown": {"enabled": True, "max_consecutive": 5, "cooldown_minutes": 30, "description": "连续亏损冷却", "severity": "warning"},
    "trade_cooldown": {"enabled": False, "cooldown_seconds": 60, "description": "交易间隔冷却(秒)", "severity": "warning"},
    "symbol_whitelist": {"enabled": False, "symbols": [], "description": "交易品种白名单", "severity": "error"},
    "symbol_blacklist": {"enabled": False, "symbols": [], "description": "交易品种黑名单", "severity": "error"},
}


def _get_risk_config() -> dict:
    """获取风控配置（优先从 Redis，fallback 内存默认）"""
    try:
        from libs.core.redis_client import get_json
        cached = get_json("ironbull:risk:config")
        if cached and isinstance(cached, dict):
            # 合并新增的默认规则
            merged = dict(_DEFAULT_RISK_CONFIG)
            merged.update(cached)
            return merged
    except Exception:
        pass
    return dict(_DEFAULT_RISK_CONFIG)


def _save_risk_config(config: dict):
    """保存风控配置到 Redis（永不过期，使用 SET 而非 SETEX）"""
    try:
        import json
        from libs.core.redis_client import get_redis
        raw = json.dumps(config, ensure_ascii=False)
        get_redis().set("ironbull:risk:config", raw)
    except Exception:
        pass


@router.get("/rules")
def get_risk_rules(
    _admin: Dict[str, Any] = Depends(get_current_admin),
):
    """获取当前风控规则列表"""
    config = _get_risk_config()
    rules = []
    for name, cfg in config.items():
        rules.append({
            "name": name,
            "enabled": cfg.get("enabled", False),
            "description": cfg.get("description", ""),
            "severity": cfg.get("severity", "warning"),
            "params": {k: v for k, v in cfg.items() if k not in ("enabled", "description", "severity")},
        })
    return {"success": True, "data": rules}


class RuleUpdateBody(BaseModel):
    rules: Dict[str, Dict[str, Any]]


@router.put("/rules")
def update_risk_rules(
    body: RuleUpdateBody,
    _admin: Dict[str, Any] = Depends(get_current_admin),
):
    """更新风控规则配置"""
    config = _get_risk_config()

    for rule_name, updates in body.rules.items():
        if rule_name not in config:
            continue
        for key, value in updates.items():
            config[rule_name][key] = value

    _save_risk_config(config)
    return {"success": True, "message": "风控规则已更新", "data": config}


@router.get("/violations")
def list_violations(
    days: int = Query(7, ge=1, le=30),
    _admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """风控违规历史（从审计日志中提取 RISK_ 相关记录）"""
    start = datetime.now() - timedelta(days=days)
    date_list = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]

    # 从审计日志中查找风控相关的记录
    violations = (
        db.query(AuditLog)
        .filter(
            AuditLog.created_at >= start,
            AuditLog.error_code.like("RISK_%"),
        )
        .order_by(AuditLog.id.desc())
        .limit(200)
        .all()
    )

    # 按规则分组统计
    rule_stats = (
        db.query(AuditLog.error_code, func.count(AuditLog.id))
        .filter(AuditLog.created_at >= start, AuditLog.error_code.like("RISK_%"))
        .group_by(AuditLog.error_code)
        .all()
    )

    # 每日违规趋势
    daily_rows = (
        db.query(cast(AuditLog.created_at, Date).label("d"), func.count(AuditLog.id))
        .filter(AuditLog.created_at >= start, AuditLog.error_code.like("RISK_%"))
        .group_by("d")
        .all()
    )
    daily_map = {str(r[0]): r[1] for r in daily_rows}

    return {
        "success": True,
        "data": {
            "total": len(violations),
            "by_rule": [{"rule": r[0], "count": r[1]} for r in rule_stats],
            "daily": {
                "dates": date_list,
                "counts": [daily_map.get(d, 0) for d in date_list],
            },
            "recent": [
                {
                    "id": v.id,
                    "error_code": v.error_code,
                    "error_message": v.error_message,
                    "action": v.action,
                    "account_id": v.account_id,
                    "detail": v.detail,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                }
                for v in violations[:50]
            ],
        },
    }
