from dataclasses import asdict
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from libs.contracts import Signal, AccountContext, Position, RiskResult
from libs.core import get_config, get_logger, setup_logging, gen_id, AppError

# v1 Facts Layer (可选，失败不阻塞主流程)
try:
    from libs.facts import FactsRepository, AuditAction, SignalStatus
    FACTS_ENABLED = True
except ImportError:
    FACTS_ENABLED = False

# v1 Risk Engine (Phase 4)
try:
    from libs.risk import (
        RiskEngine,
        RiskCheckContext,
        MaxPositionRule,
        MaxPositionValueRule,
        DailyTradeLimitRule,
        DailyLossLimitRule,
        ConsecutiveLossCooldownRule,
        TradeCooldownRule,
        SymbolWhitelistRule,
        SymbolBlacklistRule,
        MinBalanceRule,
    )
    RISK_ENGINE_ENABLED = True
except ImportError:
    RISK_ENGINE_ENABLED = False


class PositionModel(BaseModel):
    symbol: str
    side: str
    quantity: float
    entry_price: float
    unrealized_pnl: Optional[float] = None


class AccountContextModel(BaseModel):
    account_id: int
    user_id: int
    balance: float
    available: float
    frozen: float = 0.0
    positions: Optional[List[PositionModel]] = None
    max_loss_per_trade: Optional[float] = None
    max_daily_loss: Optional[float] = None
    cooldown_seconds: Optional[int] = None
    symbol_whitelist: Optional[List[str]] = None
    symbol_blacklist: Optional[List[str]] = None


class SignalModel(BaseModel):
    signal_id: str
    strategy_code: str
    symbol: str
    canonical_symbol: str
    side: str
    signal_type: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    quantity: Optional[float] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    timeframe: str = ""
    timestamp: int = 0
    status: str = "pending"


class RiskCheckRequest(BaseModel):
    signal: SignalModel
    account: AccountContextModel


class RiskCheckResponse(BaseModel):
    result: dict


config = get_config()
service_name = "risk-control"
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name=service_name,
)
logger = get_logger(service_name)

app = FastAPI(title="risk-control")

# 创建风控引擎（如果可用）
risk_engine: Optional[RiskEngine] = None
if RISK_ENGINE_ENABLED:
    risk_engine = RiskEngine(fail_fast=True)
    # 添加默认规则（可通过配置调整）
    risk_engine.add_rule(MinBalanceRule(min_balance=config.get_float("risk_min_balance", 100.0)))
    risk_engine.add_rule(MaxPositionRule(max_positions=config.get_int("risk_max_positions", 10)))
    risk_engine.add_rule(MaxPositionValueRule(max_value=config.get_float("risk_max_position_value", 50000.0)))
    risk_engine.add_rule(DailyTradeLimitRule(max_trades=config.get_int("risk_daily_trade_limit", 100)))
    risk_engine.add_rule(DailyLossLimitRule(max_loss=config.get_float("risk_daily_loss_limit", 1000.0)))
    risk_engine.add_rule(ConsecutiveLossCooldownRule(
        max_consecutive=config.get_int("risk_max_consecutive_losses", 5),
        cooldown_minutes=config.get_int("risk_loss_cooldown_minutes", 30)
    ))
    risk_engine.add_rule(TradeCooldownRule(cooldown_seconds=config.get_int("risk_trade_cooldown_seconds", 0)))
    logger.info("risk engine initialized", rules=len(risk_engine.rules))


def _error_payload(code: str, message: str, detail: Optional[dict] = None, request_id: Optional[str] = None) -> dict:
    payload = {"code": code, "message": message, "detail": detail or {}}
    if request_id:
        payload["request_id"] = request_id
    return payload


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=422,
        content=_error_payload("VALIDATION_ERROR", "Validation failed", {"errors": exc.errors()}, request_id),
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=400,
        content=_error_payload(exc.code, exc.message, exc.detail, request_id),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", None)
    detail = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload("HTTP_ERROR", "HTTP error", detail, request_id),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.error("unhandled exception", request_id=request_id, error=str(exc))
    return JSONResponse(
        status_code=500,
        content=_error_payload("INTERNAL_ERROR", "Internal error", {"error": str(exc)}, request_id),
    )


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or gen_id("req_")
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/health")
def health():
    return {"status": "ok", "service": service_name}


def _ensure_numbers(signal: Signal) -> Signal:
    if not signal.quantity or signal.quantity <= 0:
        signal.quantity = 0.01
    if signal.stop_loss is None:
        if signal.entry_price:
            if signal.side.upper() == "SELL":
                signal.stop_loss = signal.entry_price * 1.02
            else:
                signal.stop_loss = signal.entry_price * 0.98
        else:
            signal.stop_loss = 0.0
    if signal.take_profit is None:
        if signal.entry_price:
            if signal.side.upper() == "SELL":
                signal.take_profit = signal.entry_price * 0.98
            else:
                signal.take_profit = signal.entry_price * 1.02
        else:
            signal.take_profit = 0.0
    return signal


def _get_account_stats(account_id: int) -> Dict[str, Any]:
    """
    获取账户统计数据（用于风控规则检查）
    
    从 Facts 层查询历史数据
    """
    stats = {
        "daily_trade_count": 0,
        "weekly_trade_count": 0,
        "daily_loss": 0.0,
        "consecutive_losses": 0,
        "last_trade_time": None,
    }
    
    if not FACTS_ENABLED:
        return stats
    
    try:
        repo = FactsRepository()
        
        # 今日交易数
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        stats["daily_trade_count"] = repo.count_trades_since(account_id, today_start)
        
        # 本周交易数
        week_start = today_start - timedelta(days=today_start.weekday())
        stats["weekly_trade_count"] = repo.count_trades_since(account_id, week_start)
        
        # 今日亏损
        stats["daily_loss"] = repo.sum_losses_since(account_id, today_start)
        
        # 连续亏损次数
        stats["consecutive_losses"] = repo.count_consecutive_losses(account_id)
        
        # 最后交易时间
        stats["last_trade_time"] = repo.get_last_trade_time(account_id)
        
    except Exception as e:
        logger.warning("failed to get account stats", error=str(e))
    
    return stats


@app.post("/api/risk/check", response_model=RiskCheckResponse)
def risk_check(req: RiskCheckRequest, request: Request):
    signal = Signal(**req.signal.dict())
    account = AccountContext(
        **{**req.account.dict(), "positions": None}
    )
    if req.account.positions:
        positions = [Position(**p.dict()) for p in req.account.positions]
        account.positions = positions

    signal = _ensure_numbers(signal)
    
    # 默认通过
    passed = True
    reject_code = None
    reject_reason = None
    violations = []
    
    # 使用风控引擎检查（如果可用）
    if RISK_ENGINE_ENABLED and risk_engine:
        # 获取账户统计数据
        stats = _get_account_stats(account.account_id)
        
        # 构建检查上下文
        ctx = RiskCheckContext(
            signal=signal,
            account=account,
            daily_trade_count=stats["daily_trade_count"],
            weekly_trade_count=stats["weekly_trade_count"],
            daily_loss=stats["daily_loss"],
            consecutive_losses=stats["consecutive_losses"],
            last_trade_time=stats["last_trade_time"],
        )
        
        # 执行规则检查
        violations = risk_engine.check(ctx)
        
        if violations:
            passed = False
            first_violation = violations[0]
            reject_code = first_violation.code
            reject_reason = first_violation.message

    result = RiskResult(
        passed=passed,
        signal=signal,
        calculated_quantity=signal.quantity,
        calculated_stop_loss=signal.stop_loss,
        calculated_take_profit=signal.take_profit,
        potential_loss=None,
        risk_reward_ratio=None,
        reject_code=reject_code,
        reject_reason=reject_reason,
    )

    # v1: 记录风控检查事件 + 审计日志（失败不阻塞）
    if FACTS_ENABLED:
        import threading
        def _write_facts():
            try:
                repo = FactsRepository()
                new_status = SignalStatus.PASSED.value if result.passed else SignalStatus.REJECTED.value
                # 信号事件
                repo.create_signal_event(
                    signal_id=signal.signal_id,
                    event_type="RISK_PASSED" if result.passed else "RISK_REJECTED",
                    status=new_status,
                    source_service="risk-control",
                    account_id=account.account_id,
                    detail={
                        "calculated_quantity": result.calculated_quantity,
                        "calculated_stop_loss": result.calculated_stop_loss,
                        "calculated_take_profit": result.calculated_take_profit,
                        "reject_reason": result.reject_reason,
                        "violations": [{"code": v.code, "message": v.message} for v in violations],
                    },
                    error_code=result.reject_code if not result.passed else None,
                    error_message=result.reject_reason if not result.passed else None,
                    request_id=request.state.request_id,
                )
                # 审计日志
                repo.create_audit_log(
                    action=AuditAction.SIGNAL_RISK_PASSED.value if result.passed else AuditAction.SIGNAL_RISK_REJECTED.value,
                    source_service="risk-control",
                    signal_id=signal.signal_id,
                    account_id=account.account_id,
                    status_before=SignalStatus.PENDING.value,
                    status_after=new_status,
                    success=result.passed,
                    error_code=result.reject_code if not result.passed else None,
                    error_message=result.reject_reason if not result.passed else None,
                    detail={
                        "calculated_quantity": result.calculated_quantity,
                        "symbol": signal.symbol,
                        "violations": [{"code": v.code, "message": v.message} for v in violations],
                    },
                    request_id=request.state.request_id,
                )
            except Exception as e:
                logger.warning("facts layer write failed", error=str(e))
        threading.Thread(target=_write_facts, daemon=True).start()

    if passed:
        logger.info(
            "risk check passed",
            request_id=request.state.request_id,
            signal_id=signal.signal_id,
            account_id=account.account_id,
        )
    else:
        logger.warning(
            "risk check rejected",
            request_id=request.state.request_id,
            signal_id=signal.signal_id,
            account_id=account.account_id,
            reject_code=reject_code,
            reject_reason=reject_reason,
        )
    
    return {"result": asdict(result)}


# ========== 风控规则管理 API ==========

@app.get("/api/risk/rules")
def list_rules():
    """列出所有风控规则"""
    if not RISK_ENGINE_ENABLED or not risk_engine:
        return {"rules": [], "engine_enabled": False}
    
    return {
        "rules": risk_engine.list_rules(),
        "engine_enabled": True,
    }


@app.get("/api/risk/stats/{account_id}")
def get_account_risk_stats(account_id: int):
    """获取账户风控统计数据"""
    stats = _get_account_stats(account_id)
    
    # 转换 datetime 为字符串
    if stats.get("last_trade_time"):
        stats["last_trade_time"] = stats["last_trade_time"].isoformat()
    
    return {
        "account_id": account_id,
        "stats": stats,
    }


@app.post("/api/risk/rules/{rule_name}/enable")
def enable_rule(rule_name: str):
    """启用指定规则"""
    if not RISK_ENGINE_ENABLED or not risk_engine:
        raise HTTPException(status_code=503, detail="Risk engine not available")
    
    for rule in risk_engine.rules:
        if rule.name == rule_name:
            rule.enabled = True
            logger.info("rule enabled", rule=rule_name)
            return {"rule": rule_name, "enabled": True}
    
    raise HTTPException(status_code=404, detail=f"Rule not found: {rule_name}")


@app.post("/api/risk/rules/{rule_name}/disable")
def disable_rule(rule_name: str):
    """禁用指定规则"""
    if not RISK_ENGINE_ENABLED or not risk_engine:
        raise HTTPException(status_code=503, detail="Risk engine not available")
    
    for rule in risk_engine.rules:
        if rule.name == rule_name:
            rule.enabled = False
            logger.info("rule disabled", rule=rule_name)
            return {"rule": rule_name, "enabled": False}
    
    raise HTTPException(status_code=404, detail=f"Rule not found: {rule_name}")
