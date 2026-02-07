"""
Signal Monitor Service - 信号监控与推送服务

功能：
1. 定时运行策略，检测交易信号
2. 有信号时推送到 Telegram
3. 支持多策略、多交易对监控
4. 支持交易数据持久化（OrderTrade → Position → Ledger）

端点：
- GET /health - 健康检查
- GET /api/status - 监控状态
- POST /api/start - 启动监控
- POST /api/stop - 停止监控
- POST /api/config - 更新配置
- POST /api/test-notify - 测试通知

使用方式：
  cd services/signal-monitor
  PYTHONPATH=../.. python3 -m flask run --host=0.0.0.0 --port=8020
"""

import sys
import os
import time
import threading
import httpx
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from flask import Flask, request, jsonify
from libs.core import get_config, get_logger, setup_logging, gen_id
from libs.core.database import get_session
from libs.strategies import get_strategy, list_strategies
from libs.notify import TelegramNotifier
from libs.trading import (
    AutoTrader,
    TradeMode,
    RiskLimits,
    TradeSettlementService,
    LiveTrader,
    OrderSide,
    OrderType,
    OrderStatus,
)
from libs.member import MemberService, ExecutionTarget
from libs.execution_node import ExecutionNodeRepository
from libs.execution_node.apply_results import apply_remote_results as apply_remote_results_to_db
from libs.queue import get_node_execute_queue, TaskMessage
import asyncio
from dataclasses import asdict

# Flask App
app = Flask(__name__)

# 配置
config = get_config()
DATA_PROVIDER_URL = config.get_str("data_provider_url", "http://127.0.0.1:8010")
HTTP_TIMEOUT = config.get_float("http_timeout", 30.0)

# 日志
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name="signal-monitor",
)
log = get_logger("signal-monitor")

# 通知器
notifier = TelegramNotifier()

# 监控状态
monitor_state = {
    "running": False,
    "last_check": None,
    "last_signal": None,
    "total_signals": 0,
    "total_checks": 0,
    "errors": 0,
}

# 全局监控参数（仅保留与策略无关的配置）
MONITOR_INTERVAL = config.get_int("monitor_interval_seconds", 300)
NOTIFY_ON_SIGNAL = config.get_bool("notify_on_signal", True)

# 向后兼容：当数据库中没有 status=1 的策略时，使用此 fallback（仅用于冷启动）
_FALLBACK_STRATEGY = {
    "code": config.get_str("default_strategy_code", "market_regime"),
    "config": {
        "atr_mult_sl": config.get_float("default_atr_mult_sl", 1.5),
        "atr_mult_tp": config.get_float("default_atr_mult_tp", 3.0),
    },
    "symbols": config.get_list("monitor_symbols", ["BTCUSDT", "ETHUSDT"]),
    "timeframe": config.get_str("monitor_timeframe", "1h"),
    "min_confidence": config.get_int("min_confidence", 50),
    "cooldown_minutes": config.get_int("signal_cooldown_minutes", 60),
}

# 信号冷却记录（内存缓存 + 数据库持久化双重保障）
signal_cooldown: Dict[str, datetime] = {}

# 监控线程
monitor_thread: Optional[threading.Thread] = None
stop_event = threading.Event()


def _load_cooldowns_from_db():
    """启动时从数据库恢复冷却状态（防止重启丢失）"""
    try:
        from libs.core.database import get_session
        from sqlalchemy import text
        session = get_session()
        rows = session.execute(text(
            "SELECT strategy_code, symbol, cooldown_until FROM dim_signal_cooldown "
            "WHERE cooldown_until > NOW()"
        )).fetchall()
        for row in rows:
            key = f"{row[0]}:{row[1]}"
            signal_cooldown[key] = row[2]
            log.debug("恢复冷却", key=key, until=str(row[2]))
        session.close()
        log.info("冷却记录已恢复", count=len(rows))
    except Exception as e:
        log.warning("恢复冷却记录失败（表可能不存在）", error=str(e))


def fetch_candles(symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
    """从 data-provider 获取 K 线"""
    try:
        url = f"{DATA_PROVIDER_URL}/api/candles"
        params = {"symbol": symbol, "timeframe": timeframe, "limit": limit, "source": "live"}
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json().get("candles", [])
    except Exception as e:
        log.error(f"获取K线失败 {symbol}: {e}")
        return []


def check_signal(strategy_code: str, strategy_config: Dict, 
                 symbol: str, timeframe: str) -> Optional[Dict]:
    """检测单个策略信号"""
    try:
        # 获取 K 线
        candles = fetch_candles(symbol, timeframe)
        if len(candles) < 100:
            log.warning(f"K线数据不足: {symbol} {len(candles)}")
            return None
        
        # 运行策略
        strategy = get_strategy(strategy_code, strategy_config)
        signal = strategy.analyze(
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
        )
        
        if signal:
            return {
                "symbol": signal.symbol,
                "signal_type": signal.signal_type,   # OPEN / CLOSE / HEDGE 等
                "side": signal.side,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "confidence": signal.confidence,
                "reason": signal.reason,
                "indicators": signal.indicators or {},
                "strategy": strategy_code,
                "timeframe": timeframe,
                "timestamp": datetime.now().isoformat(),
            }
        return None
        
    except Exception as e:
        log.error(f"策略分析失败 {strategy_code}/{symbol}: {e}")
        return None


def _timeframe_to_minutes(tf: str) -> int:
    """将时间周期转换为分钟数，用于计算冷却时间"""
    units = {"m": 1, "h": 60, "d": 1440, "w": 10080}
    try:
        num = int(tf[:-1])
        unit = tf[-1].lower()
        return num * units.get(unit, 60)
    except Exception:
        return 60


def is_in_cooldown(symbol: str, strategy: str, cooldown_minutes: int = 60) -> bool:
    """检查是否在冷却期（cooldown_minutes 来自策略配置）"""
    key = f"{strategy}:{symbol}"
    if key not in signal_cooldown:
        return False

    cooldown_until = signal_cooldown[key]
    # 支持两种格式：datetime 表示冷却到期时间（新），或 datetime 表示设定时间（旧）
    now = datetime.now()
    if cooldown_until > now:
        # 新格式：cooldown_until 是到期时间
        return True
    # 兼容旧格式：cooldown_until 是设定时间
    elapsed = (now - cooldown_until).total_seconds() / 60
    return elapsed < cooldown_minutes


def set_cooldown(symbol: str, strategy: str, timeframe: str = "1h"):
    """
    设置冷却 — 冷却时间 = max(策略配置的 cooldown, 当前 K 线剩余时间 × 2)
    这样确保同一根 K 线内不会重复开仓（即使止损后），至少等下一根 K 线。
    """
    key = f"{strategy}:{symbol}"
    tf_minutes = _timeframe_to_minutes(timeframe)
    # 计算当前周期剩余时间：至少等到当前 K 线结束 + 半个周期（避免边界重入）
    now = datetime.now()
    minutes_into_period = (now.hour * 60 + now.minute) % tf_minutes
    remaining = tf_minutes - minutes_into_period + (tf_minutes // 2)
    cooldown_until = now + timedelta(minutes=max(remaining, tf_minutes))
    signal_cooldown[key] = cooldown_until
    log.info("设置冷却", key=key, until=cooldown_until.isoformat(), remaining_min=remaining)
    # 持久化到数据库（防止重启丢失）
    try:
        from libs.core.database import get_session
        from sqlalchemy import text
        db = get_session()
        db.execute(text(
            "INSERT INTO dim_signal_cooldown (strategy_code, symbol, cooldown_until, created_at) "
            "VALUES (:code, :sym, :until, NOW()) "
            "ON DUPLICATE KEY UPDATE cooldown_until = :until"
        ), {"code": strategy, "sym": symbol, "until": cooldown_until})
        db.commit()
        db.close()
    except Exception as e:
        log.warning("冷却持久化失败", error=str(e))


def _split_hedge_signal(signal: Dict) -> List[Dict]:
    """
    将 HEDGE 信号拆分为两个独立的单向信号（BUY + SELL），
    从 indicators 中读取各自的止损止盈。
    返回: [long_signal, short_signal]
    """
    indicators = signal.get("indicators") or {}
    base = {k: v for k, v in signal.items() if k not in ("side", "stop_loss", "take_profit", "signal_type")}

    long_signal = {
        **base,
        "signal_type": "OPEN",
        "side": "BUY",
        "stop_loss": indicators.get("long_stop_loss", signal.get("stop_loss")),
        "take_profit": indicators.get("long_take_profit", signal.get("take_profit")),
    }
    short_signal = {
        **base,
        "signal_type": "OPEN",
        "side": "SELL",
        "stop_loss": indicators.get("short_stop_loss", signal.get("stop_loss")),
        "take_profit": indicators.get("short_take_profit", signal.get("take_profit")),
    }
    return [long_signal, short_signal]


def _load_strategies_from_db():
    """
    从 dim_strategy 加载 status=1 的策略列表，返回统一格式的 dict list。
    若数据库不可用或无数据，回退到全局配置中的 fallback 策略。
    """
    session = None
    try:
        session = get_session()
        from libs.member.repository import MemberRepository
        repo = MemberRepository(session)
        rows = repo.list_strategies(status=1)
        if rows:
            result = []
            for s in rows:
                result.append({
                    "code": s.code,
                    "config": s.get_config(),
                    "symbols": s.get_symbols(),
                    "timeframe": s.timeframe or "1h",
                    "min_confidence": int(s.min_confidence or 50),
                    "cooldown_minutes": int(s.cooldown_minutes or 60),
                    "exchange": s.exchange or None,
                    "market_type": s.market_type or "future",
                    "amount_usdt": float(s.amount_usdt or 0),
                    "leverage": int(s.leverage or 0),
                })
            log.info("从数据库加载策略", count=len(result))
            return result
    except Exception as e:
        log.warning("从数据库加载策略失败, 使用 fallback", error=str(e))
    finally:
        if session:
            try:
                session.close()
            except Exception:
                pass

    # fallback：使用全局配置
    return [_FALLBACK_STRATEGY]


def _quick_sync_positions():
    """快速同步持仓（在信号检测前执行，确保数据库持仓状态是最新的）"""
    try:
        from libs.sync_node.service import sync_positions_from_nodes
        session = get_session()
        try:
            sync_positions_from_nodes(session)
            session.commit()
        except Exception as e:
            session.rollback()
            log.warning("信号前快速同步持仓失败", error=str(e))
        finally:
            session.close()
    except Exception as e:
        log.warning("快速同步 session 失败", error=str(e))


def monitor_loop():
    """监控主循环 - 每轮从数据库加载最新策略配置"""
    global monitor_state

    log.info("信号监控启动")

    # 启动时从 DB 恢复冷却记录（防止重启丢失）
    _load_cooldowns_from_db()

    while not stop_event.is_set():
        try:
            monitor_state["last_check"] = datetime.now().isoformat()
            monitor_state["total_checks"] += 1

            # ── 关键：信号检测前先同步持仓，确保 DB 是最新状态 ──
            _quick_sync_positions()

            # 每轮动态加载策略（支持运行时增删改策略，无需重启）
            strategies = _load_strategies_from_db()

            for strat_cfg in strategies:
                code = strat_cfg.get("code")
                cfg = strat_cfg.get("config", {})
                symbols = strat_cfg.get("symbols", [])
                timeframe = strat_cfg.get("timeframe", "1h")
                min_conf = strat_cfg.get("min_confidence", 50)
                cooldown = strat_cfg.get("cooldown_minutes", 60)

                for symbol in symbols:
                    # 检查冷却（使用策略级别的冷却时间）
                    if is_in_cooldown(symbol, code, cooldown):
                        log.debug(f"冷却中跳过: {code}/{symbol}")
                        continue

                    # 检测信号
                    signal = check_signal(code, cfg, symbol, timeframe)

                    if signal:
                        confidence = signal.get("confidence", 0)

                        if confidence >= min_conf:
                            # ── HEDGE 信号拆分为 BUY + SELL 两单 ──
                            sig_type = (signal.get("signal_type") or "OPEN").upper()
                            if sig_type == "HEDGE":
                                signals_to_exec = _split_hedge_signal(signal)
                                log.info(
                                    f"检测到对冲信号: {symbol} @ {signal['entry_price']}，拆分为 BUY+SELL 两单"
                                )
                            else:
                                signals_to_exec = [signal]
                                log.info(f"检测到信号: {signal['side']} {symbol} @ {signal['entry_price']}")

                            for sig in signals_to_exec:
                                # 将策略层参数注入信号（amount_usdt、leverage），供执行层使用
                                if strat_cfg.get("amount_usdt"):
                                    sig["amount_usdt"] = strat_cfg["amount_usdt"]
                                if strat_cfg.get("leverage"):
                                    sig["leverage"] = strat_cfg["leverage"]

                                monitor_state["last_signal"] = sig
                                monitor_state["total_signals"] += 1

                                # 按策略多账户分发（若启用）
                                if DISPATCH_BY_STRATEGY and sig.get("strategy"):
                                    try:
                                        dispatch_result = execute_signal_by_strategy(sig)
                                        log.info(
                                            f"strategy dispatch [{sig.get('side')}]",
                                            targets=dispatch_result.get("targets", 0),
                                            success_count=dispatch_result.get("success_count", 0),
                                        )
                                    except Exception as e:
                                        log.error(f"strategy dispatch error [{sig.get('side')}]", error=str(e))

                                # 推送通知
                                if NOTIFY_ON_SIGNAL:
                                    result = notifier.send_signal(sig)
                                    if result.success:
                                        log.info(f"信号已推送: {sig.get('side')} {symbol}")
                                    else:
                                        log.error(f"推送失败: {result.error}")

                            # 冷却：无论单信号还是对冲，一轮只设一次冷却
                            # 传入 timeframe 确保冷却至少覆盖当前 K 线周期
                            set_cooldown(symbol, code, timeframe)
                        else:
                            log.debug(f"信号置信度不足: {confidence} < {min_conf}")

        except Exception as e:
            log.error(f"监控循环异常: {e}")
            monitor_state["errors"] += 1

        # 等待下次检测
        stop_event.wait(MONITOR_INTERVAL)

    log.info("信号监控已停止")


# ========== API Routes ==========

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "signal-monitor"})


@app.route("/api/status", methods=["GET"])
def get_status():
    """获取监控状态"""
    strategies = _load_strategies_from_db()
    # 构建冷却状态列表
    now = datetime.now()
    cooldowns = []
    for key, until in signal_cooldown.items():
        if until > now:
            parts = key.split(":", 1)
            cooldowns.append({
                "strategy": parts[0] if len(parts) > 0 else key,
                "symbol": parts[1] if len(parts) > 1 else "",
                "cooldown_until": until.isoformat(),
                "remaining_minutes": round((until - now).total_seconds() / 60, 1),
            })
    return jsonify({
        "success": True,
        "state": monitor_state,
        "config": {
            "interval_seconds": MONITOR_INTERVAL,
            "sync_interval_seconds": SYNC_INTERVAL,
            "strategies_count": len(strategies),
            "notify_enabled": NOTIFY_ON_SIGNAL,
            "dispatch_by_strategy": DISPATCH_BY_STRATEGY,
            "strategy_dispatch_amount": STRATEGY_DISPATCH_AMOUNT,
        },
        "cooldowns": cooldowns,
    })


@app.route("/api/config", methods=["GET"])
def get_config_api():
    """获取完整配置（策略配置现在从数据库读取）"""
    strategies = _load_strategies_from_db()
    return jsonify({
        "success": True,
        "config": {
            "interval_seconds": MONITOR_INTERVAL,
            "sync_interval_seconds": SYNC_INTERVAL,
            "notify_on_signal": NOTIFY_ON_SIGNAL,
            "dispatch_by_strategy": DISPATCH_BY_STRATEGY,
            "strategy_dispatch_amount": STRATEGY_DISPATCH_AMOUNT,
            "strategies": strategies,
        },
    })


@app.route("/api/config", methods=["POST"])
def update_config():
    """
    更新配置 — 策略级参数请直接修改 dim_strategy 表（monitor_loop 每轮自动加载）。
    此端点仅支持修改全局运行参数。
    """
    global MONITOR_INTERVAL, NOTIFY_ON_SIGNAL, SYNC_INTERVAL

    data = request.get_json() or {}

    if "interval_seconds" in data:
        MONITOR_INTERVAL = int(data["interval_seconds"])
    if "sync_interval_seconds" in data:
        SYNC_INTERVAL = int(data["sync_interval_seconds"])
    if "notify_on_signal" in data:
        NOTIFY_ON_SIGNAL = bool(data["notify_on_signal"])
    # 策略级参数（min_confidence / cooldown_minutes / symbols 等）已下沉到 dim_strategy 表，
    # 直接修改数据库即可，monitor_loop 每轮自动加载最新配置。
    log.info("全局监控配置已更新", interval=MONITOR_INTERVAL, sync_interval=SYNC_INTERVAL, notify=NOTIFY_ON_SIGNAL)

    return jsonify({
        "success": True,
        "config": {
            "interval_seconds": MONITOR_INTERVAL,
            "sync_interval_seconds": SYNC_INTERVAL,
            "notify_on_signal": NOTIFY_ON_SIGNAL,
            "note": "策略级参数请直接修改 dim_strategy 表",
        },
    })


@app.route("/api/start", methods=["POST"])
def start_monitor():
    """启动监控"""
    global monitor_thread, monitor_state
    
    if monitor_state["running"]:
        return jsonify({"success": False, "error": "监控已在运行中"})
    
    stop_event.clear()
    monitor_state["running"] = True
    
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    
    log.info("监控已启动")
    
    strategies = _load_strategies_from_db()
    return jsonify({
        "success": True,
        "message": "监控已启动",
        "config": {
            "interval_seconds": MONITOR_INTERVAL,
            "strategies_count": len(strategies),
        },
    })


@app.route("/api/stop", methods=["POST"])
def stop_monitor():
    """停止监控"""
    global monitor_state
    
    if not monitor_state["running"]:
        return jsonify({"success": False, "error": "监控未运行"})
    
    stop_event.set()
    monitor_state["running"] = False
    
    log.info("监控已停止")
    
    return jsonify({
        "success": True,
        "message": "监控已停止",
    })


@app.route("/api/test-notify", methods=["POST"])
def test_notify():
    """测试通知"""
    result = notifier.test_connection()
    return jsonify({
        "success": result.success,
        "message_id": result.message_id,
        "error": result.error,
    })


@app.route("/api/check-now", methods=["POST"])
def check_now():
    """立即检测一次"""
    data = request.get_json() or {}
    strategy_code = data.get("strategy", _FALLBACK_STRATEGY["code"])
    symbol = data.get("symbol")
    if not symbol:
        return jsonify({"success": False, "error": "symbol is required"}), 400
    timeframe = data.get("timeframe", _FALLBACK_STRATEGY.get("timeframe", "1h"))

    # 优先从数据库读取策略参数
    default_cfg = _FALLBACK_STRATEGY.get("config", {})
    session = None
    try:
        session = get_session()
        from libs.member.repository import MemberRepository
        repo = MemberRepository(session)
        strat = repo.get_strategy_by_code(strategy_code)
        if strat:
            default_cfg = strat.get_config()
            timeframe = data.get("timeframe") or strat.timeframe or timeframe
    except Exception as e:
        log.debug("load strategy config from db failed, using fallback", error=str(e))
    finally:
        if session:
            try:
                session.close()
            except Exception:
                pass
    strategy_config = data.get("config", default_cfg)
    
    signal = check_signal(strategy_code, strategy_config, symbol, timeframe)
    
    if signal:
        # 推送通知
        if data.get("notify", True):
            notifier.send_signal(signal)
        
        return jsonify({
            "success": True,
            "signal": signal,
        })
    else:
        return jsonify({
            "success": True,
            "signal": None,
            "message": "无交易信号",
        })


@app.route("/api/strategies", methods=["GET"])
def get_strategies():
    """获取可用策略列表（优先从数据库读取，回退到内置策略）"""
    session = None
    try:
        session = get_session()
        from libs.member.repository import MemberRepository
        repo = MemberRepository(session)
        rows = repo.list_strategies(status=1)
        if rows:
            return jsonify({
                "success": True,
                "strategies": [
                    {
                        "code": s.code,
                        "name": s.name,
                        "symbols": s.get_symbols(),
                        "timeframe": s.timeframe,
                        "exchange": s.exchange,
                        "market_type": s.market_type,
                        "amount_usdt": float(s.amount_usdt or 0),
                        "leverage": int(s.leverage or 0),
                        "min_confidence": int(s.min_confidence or 50),
                    }
                    for s in rows
                ],
            })
    except Exception as e:
        log.warning("load strategies from db failed", error=str(e))
    finally:
        if session:
            try:
                session.close()
            except Exception:
                pass

    # 回退到内置策略注册表
    strategies = list_strategies()
    return jsonify({
        "success": True,
        "strategies": [{"code": s["code"], "name": s["name"]} for s in strategies],
    })


# ========== 自动交易 API ==========

# 按策略多账户分发：为 True 时，有 strategy_code 的信号将查 dim_strategy_binding 并对每个绑定账户执行
DISPATCH_BY_STRATEGY = config.get_bool("dispatch_by_strategy", False)
# 按策略分发时，每账户下单金额（USDT）
STRATEGY_DISPATCH_AMOUNT = config.get_float("strategy_dispatch_amount", 100.0)
# 为 True 时，远程节点任务投递到 NODE_EXECUTE_QUEUE，由 worker 消费并 POST 到节点；否则直接 POST
USE_NODE_EXECUTION_QUEUE = config.get_bool("use_node_execution_queue", False)

# 自动交易器（全局单例）
auto_trader: Optional[AutoTrader] = None
# 数据库 session（用于交易持久化）
_db_session = None
# 结算服务
_settlement_service: Optional[TradeSettlementService] = None


async def _execute_signal_for_target(
    session,
    target: ExecutionTarget,
    signal: Dict[str, Any],
    amount_usdt: float,
    sandbox: bool,
) -> Dict[str, Any]:
    """
    对单个绑定账户执行信号：创建带 settlement 的 LiveTrader，下单并可选设置止盈止损。
    仅服务端使用，勿暴露 target 中的凭证。
    """
    symbol = signal.get("symbol", "")
    side_str = signal.get("side", "BUY")
    entry_price = float(signal.get("entry_price") or 0)
    stop_loss = float(signal.get("stop_loss") or 0)
    take_profit = float(signal.get("take_profit") or 0)
    leverage = int(signal.get("leverage") or 0)  # 杠杆倍数（策略配置，随信号传入）
    if not symbol or not entry_price:
        return {"account_id": target.account_id, "success": False, "error": "missing symbol or entry_price"}
    if amount_usdt <= 0:
        return {"account_id": target.account_id, "success": False, "error": "amount_usdt <= 0"}
    order_side = OrderSide.BUY if side_str.upper() == "BUY" else OrderSide.SELL
    settlement_svc = TradeSettlementService(
        session=session,
        tenant_id=target.tenant_id,
        account_id=target.account_id,
        currency="USDT",
    )
    trader = LiveTrader(
        exchange=target.exchange,
        api_key=target.api_key,
        api_secret=target.api_secret,
        passphrase=target.passphrase,
        sandbox=sandbox,
        market_type=target.market_type,
        settlement_service=settlement_svc,
        tenant_id=target.tenant_id,
        account_id=target.account_id,
    )
    try:
        # 传 amount_usdt 让 LiveTrader 内部统一换算数量（自动处理 contractSize、最小限制等）
        order_result = await trader.create_order(
            symbol=symbol,
            side=order_side,
            order_type=OrderType.MARKET,
            amount_usdt=amount_usdt,
            price=entry_price,
            leverage=leverage or None,
            signal_id=signal.get("signal_id"),
        )
        ok = order_result.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)
        filled_qty = order_result.filled_quantity or 0
        filled_price = order_result.filled_price or entry_price
        sl_tp_ok = False
        if ok and (stop_loss or take_profit) and filled_qty > 0:
            try:
                await trader.set_sl_tp(
                    symbol=symbol,
                    side=order_side,
                    quantity=filled_qty,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )
                sl_tp_ok = True
            except Exception as e:
                log.warning("set_sl_tp failed", account_id=target.account_id, error=str(e))
        await trader.close()
        return {
            "account_id": target.account_id,
            "user_id": target.user_id,
            "success": ok,
            "order_id": getattr(order_result, "order_id", None),
            "filled_quantity": filled_qty,
            "filled_price": filled_price,
            "sl_tp_set": sl_tp_ok,
        }
    except Exception as e:
        try:
            await trader.close()
        except Exception:
            pass
        log.error("execute_signal_for_target failed", account_id=target.account_id, error=str(e))
        return {"account_id": target.account_id, "user_id": target.user_id, "success": False, "error": str(e)}


def _resolve_amount_leverage_for_tenant(repo, strategy, tenant_id: int):
    """
    按租户解析下单金额与杠杆：优先用 dim_tenant_strategy 实例覆盖，无则用主策略。
    返回 (amount_usdt, leverage)。
    """
    if not strategy:
        return STRATEGY_DISPATCH_AMOUNT, 0
    base_amount = float(strategy.amount_usdt or 0) if strategy else 0
    base_leverage = int(strategy.leverage or 0) if strategy else 0
    ts = repo.get_tenant_strategy(tenant_id, strategy.id)
    if ts:
        amount = float(ts.amount_usdt) if ts.amount_usdt is not None else base_amount
        leverage = int(ts.leverage) if ts.leverage is not None else base_leverage
    else:
        amount = base_amount
        leverage = base_leverage
    amount = amount if amount > 0 else STRATEGY_DISPATCH_AMOUNT
    return amount, leverage


def execute_signal_by_strategy(signal: Dict[str, Any]) -> Dict[str, Any]:
    """
    按策略分发：根据 signal["strategy"] 查 dim_strategy_binding，对每个绑定账户执行。
    金额和杠杆按租户解析：优先 dim_tenant_strategy 实例，无则用主策略 dim_strategy。
    本机账户：进程内 LiveTrader；远程节点账户：POST 到节点，再根据响应在中心写库与结算。
    """
    strategy_code = (signal or {}).get("strategy") or (signal or {}).get("strategy_code")
    if not strategy_code:
        return {"success": False, "action": "no_strategy", "message": "signal 缺少 strategy/strategy_code"}
    session = get_session()
    try:
        member_svc = MemberService(session)
        targets = member_svc.get_execution_targets_by_strategy_code(strategy_code)
        if not targets:
            return {
                "success": True,
                "action": "no_bindings",
                "targets": 0,
                "message": "该策略暂无绑定账户，将走单账户逻辑（若已配置）",
            }

        from libs.member.repository import MemberRepository
        repo = MemberRepository(session)
        strategy = repo.get_strategy_by_code(strategy_code)
        # 主策略默认值仅用于 signal 兜底（无租户实例时）
        strategy_amount = float(strategy.amount_usdt or 0) if strategy else 0
        strategy_leverage = int(strategy.leverage or 0) if strategy else 0
        if strategy_amount > 0:
            signal.setdefault("amount_usdt", strategy_amount)
        if strategy_leverage > 0:
            signal.setdefault("leverage", strategy_leverage)

        sandbox = config.get_bool("exchange_sandbox", True)
        results = []

        # ── 持仓去重：检查每个账户是否已有同向持仓，有则跳过 ──
        from libs.position.repository import PositionRepository
        from libs.exchange.utils import normalize_symbol
        pos_repo = PositionRepository(session)
        raw_symbol = (signal or {}).get("symbol", "")
        # 规范化 symbol → BTC/USDT 格式（数据库中可能存 BTCUSDT 或 BTC/USDT）
        canonical_symbol = normalize_symbol(raw_symbol, "binance")
        # 同步写入信号，保证后续存库也用规范格式
        signal["symbol"] = canonical_symbol
        symbol = canonical_symbol
        side_str = (signal or {}).get("side", "BUY").upper()
        # 合约：BUY→LONG, SELL→SHORT
        position_side = "LONG" if side_str == "BUY" else "SHORT"

        def _has_open_position(target) -> bool:
            """检查目标账户是否已有同 symbol+同向 的 OPEN 持仓（兼容两种 symbol 格式）"""
            try:
                # 同时检查规范格式（BTC/USDT）和无斜杠格式（BTCUSDT）
                variants = set([symbol, symbol.replace("/", "")])
                for s in variants:
                    pos = pos_repo.get_by_key(
                        tenant_id=target.tenant_id,
                        account_id=target.account_id,
                        symbol=s,
                        exchange=target.exchange or "binance",
                        position_side=position_side,
                    )
                    if pos and pos.quantity and float(pos.quantity) > 0:
                        return True
            except Exception:
                pass
            return False

        # 按 execution_node_id 分组：None/0=本机，其余=远程节点
        by_node = defaultdict(list)
        for t in targets:
            nid = (t.execution_node_id or 0) or 0
            by_node[nid].append(t)

        def _is_single_mode_exhausted(target) -> bool:
            """单次模式检查：mode=1 且已有历史成交记录（曾执行过），则不再执行"""
            if target.mode != 1:
                return False  # 循环模式，不限制
            try:
                from libs.order_trade.models import Order
                has_order = session.query(Order.id).filter(
                    Order.account_id == target.account_id,
                    Order.symbol.in_([symbol, symbol.replace("/", "")]),
                    Order.status.in_(["FILLED", "PARTIALLY_FILLED"]),
                ).first()
                return has_order is not None
            except Exception:
                return False

        local_targets = by_node.get(0, [])
        for target in local_targets:
            # 单次模式检查
            if _is_single_mode_exhausted(target):
                log.info("单次模式已执行过，跳过",
                         account_id=target.account_id, symbol=symbol, mode=target.mode)
                results.append({
                    "account_id": target.account_id,
                    "user_id": target.user_id,
                    "success": False,
                    "error": f"单次模式已执行过 {symbol}，跳过",
                    "skipped": True,
                })
                continue
            # 持仓去重检查
            if _has_open_position(target):
                log.info(
                    "跳过已有持仓账户",
                    account_id=target.account_id,
                    symbol=symbol,
                    position_side=position_side,
                )
                results.append({
                    "account_id": target.account_id,
                    "user_id": target.user_id,
                    "success": False,
                    "error": f"已有 {symbol} {position_side} 持仓，跳过",
                    "skipped": True,
                })
                continue
            amount, leverage = _resolve_amount_leverage_for_tenant(repo, strategy, target.tenant_id)
            target_amount = round(amount * (target.ratio / 100), 2) if target.ratio and target.ratio != 100 else amount
            signal_for_target = dict(signal)
            if leverage > 0:
                signal_for_target["leverage"] = leverage
            r = run_async(
                _execute_signal_for_target(session, target, signal_for_target, target_amount, sandbox)
            )
            results.append(r)

        node_repo = ExecutionNodeRepository(session)
        for node_id, remote_targets in by_node.items():
            if node_id == 0 or not remote_targets:
                continue
            node = node_repo.get_by_id(node_id)
            if not node or node.status != 1:
                for t in remote_targets:
                    results.append({"account_id": t.account_id, "user_id": t.user_id, "success": False, "error": "节点不可用"})
                continue
            base_url = (node.base_url or "").rstrip("/")
            if not base_url:
                for t in remote_targets:
                    results.append({"account_id": t.account_id, "user_id": t.user_id, "success": False, "error": "节点 base_url 为空"})
                continue
            # 每个 target 按租户解析 amount/leverage，再按 ratio 缩放金额；跳过已有持仓的账户
            task_list = []
            for t in remote_targets:
                if _is_single_mode_exhausted(t):
                    log.info("单次模式已执行过(远程)", account_id=t.account_id, symbol=symbol, mode=t.mode)
                    results.append({
                        "account_id": t.account_id, "user_id": t.user_id,
                        "success": False, "error": f"单次模式已执行过 {symbol}，跳过", "skipped": True,
                    })
                    continue
                if _has_open_position(t):
                    log.info("跳过已有持仓账户(远程)", account_id=t.account_id, symbol=symbol, position_side=position_side)
                    results.append({
                        "account_id": t.account_id, "user_id": t.user_id,
                        "success": False, "error": f"已有 {symbol} {position_side} 持仓，跳过", "skipped": True,
                    })
                    continue
                amount, leverage = _resolve_amount_leverage_for_tenant(repo, strategy, t.tenant_id)
                task_amount = round(amount * (t.ratio / 100), 2) if t.ratio and t.ratio != 100 else amount
                task_list.append({
                    "account_id": t.account_id,
                    "tenant_id": t.tenant_id,
                    "user_id": t.user_id,
                    "exchange": t.exchange,
                    "api_key": t.api_key,
                    "api_secret": t.api_secret,
                    "passphrase": t.passphrase,
                    "market_type": t.market_type,
                    "amount_usdt": task_amount,
                    "leverage": leverage if leverage > 0 else None,
                    "binding_id": t.binding_id,
                    "strategy_code": t.strategy_code,
                    "ratio": t.ratio,
                })
            payload = {
                "signal": signal,
                "amount_usdt": float(strategy.amount_usdt or 0) if strategy else STRATEGY_DISPATCH_AMOUNT,
                "sandbox": sandbox,
                "tasks": task_list,
            }
            if USE_NODE_EXECUTION_QUEUE:
                try:
                    queue = get_node_execute_queue()
                    task_id = gen_id("TASK")
                    message = TaskMessage(
                        task_id=task_id,
                        task_type="node_execute",
                        payload={
                            "node_id": node_id,
                            "base_url": base_url,
                            "signal": signal,
                            "amount_usdt": payload.get("amount_usdt"),
                            "sandbox": sandbox,
                            "tasks": task_list,
                        },
                        signal_id=signal.get("signal_id"),
                    )
                    queue.push(message)
                    for t in remote_targets:
                        results.append({"account_id": t.account_id, "user_id": t.user_id, "queued": True, "node_id": node_id})
                    continue
                except Exception as eq:
                    log.warning("node execute queue push failed, fallback to direct POST", node_id=node_id, error=str(eq))
            try:
                node_headers = {}
                secret = config.get_str("node_auth_secret", "").strip()
                if secret:
                    node_headers["X-Center-Token"] = secret
                with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                    resp = client.post(f"{base_url}/api/execute", json=payload, headers=node_headers or None)
                    resp.raise_for_status()
                    data = resp.json()
            except Exception as e:
                log.warning("remote node POST failed", node_id=node_id, error=str(e))
                for t in remote_targets:
                    results.append({"account_id": t.account_id, "user_id": t.user_id, "success": False, "error": str(e)})
                continue
            response_results = data.get("results") or []
            targets_by_account = {t.account_id: t for t in remote_targets}
            applied = apply_remote_results_to_db(session, signal, targets_by_account, response_results)
            results.extend(applied)

        session.commit()
        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": True,
            "action": "dispatched",
            "targets": len(targets),
            "success_count": success_count,
            "results": results,
        }
    except Exception as e:
        session.rollback()
        log.error("execute_signal_by_strategy error", error=str(e))
        return {"success": False, "action": "error", "message": str(e)}
    finally:
        session.close()


def get_settlement_service() -> Optional[TradeSettlementService]:
    """获取或创建结算服务"""
    global _db_session, _settlement_service
    
    # 检查是否启用交易持久化
    if not config.get_bool("trade_persistence_enabled", True):
        return None
    
    if _settlement_service is None:
        try:
            # 创建数据库 session
            _db_session = get_session()
            
            # 从配置读取租户和账户信息
            tenant_id = config.get_int("tenant_id", 1)
            account_id = config.get_int("account_id", 1)
            currency = config.get_str("account_currency", "USDT")
            
            _settlement_service = TradeSettlementService(
                session=_db_session,
                tenant_id=tenant_id,
                account_id=account_id,
                currency=currency,
            )
            
            log.info(
                "settlement service initialized",
                tenant_id=tenant_id,
                account_id=account_id,
                currency=currency,
            )
        except Exception as e:
            log.error(f"failed to create settlement service: {e}")
            return None
    
    return _settlement_service


def get_auto_trader() -> Optional[AutoTrader]:
    """获取或创建自动交易器"""
    global auto_trader
    
    if auto_trader is None:
        # 从配置读取
        api_key = config.get_str("exchange_api_key", "")
        api_secret = config.get_str("exchange_api_secret", "")
        
        if not api_key or not api_secret:
            return None
        
        mode_str = config.get_str("auto_trade_mode", "notify_only")
        mode_map = {
            "notify_only": TradeMode.NOTIFY_ONLY,
            "confirm_each": TradeMode.CONFIRM_EACH,
            "auto_execute": TradeMode.AUTO_EXECUTE,
        }
        
        risk_limits = RiskLimits(
            max_trade_amount=config.get_float("auto_trade_max_amount", 100.0),
            max_daily_trades=config.get_int("auto_trade_max_daily", 10),
            max_open_positions=config.get_int("auto_trade_max_positions", 3),
            min_confidence=config.get_int("auto_trade_min_confidence", 70),
        )
        
        # 获取结算服务（可选，用于交易持久化）
        settlement_service = get_settlement_service()
        
        auto_trader = AutoTrader(
            exchange=config.get_str("exchange_name", "binance"),
            api_key=api_key,
            api_secret=api_secret,
            passphrase=config.get_str("exchange_passphrase", ""),
            sandbox=config.get_bool("exchange_sandbox", True),
            market_type=config.get_str("exchange_market_type", "future"),
            mode=mode_map.get(mode_str, TradeMode.NOTIFY_ONLY),
            risk_limits=risk_limits,
            # 传入结算服务实现交易持久化
            settlement_service=settlement_service,
        )
        
        if config.get_bool("auto_trade_enabled", False):
            auto_trader.enable()
    
    return auto_trader


@app.route("/api/trading/status", methods=["GET"])
def trading_status():
    """获取自动交易状态"""
    trader = get_auto_trader()
    
    if trader is None:
        return jsonify({
            "success": True,
            "configured": False,
            "message": "交易所 API 未配置",
        })
    
    return jsonify({
        "success": True,
        "configured": True,
        **trader.get_status(),
    })


@app.route("/api/trading/enable", methods=["POST"])
def trading_enable():
    """启用自动交易"""
    trader = get_auto_trader()
    
    if trader is None:
        return jsonify({"success": False, "error": "交易所 API 未配置"})
    
    trader.enable()
    
    return jsonify({
        "success": True,
        "message": "自动交易已启用",
        "mode": trader.mode.value,
        "sandbox": trader.sandbox,
    })


@app.route("/api/trading/disable", methods=["POST"])
def trading_disable():
    """禁用自动交易"""
    trader = get_auto_trader()
    
    if trader is None:
        return jsonify({"success": False, "error": "交易所 API 未配置"})
    
    trader.disable()
    
    return jsonify({
        "success": True,
        "message": "自动交易已禁用",
    })


@app.route("/api/trading/mode", methods=["POST"])
def trading_set_mode():
    """设置交易模式"""
    trader = get_auto_trader()
    
    if trader is None:
        return jsonify({"success": False, "error": "交易所 API 未配置"})
    
    data = request.get_json() or {}
    mode_str = data.get("mode", "notify_only")
    
    mode_map = {
        "notify_only": TradeMode.NOTIFY_ONLY,
        "confirm_each": TradeMode.CONFIRM_EACH,
        "auto_execute": TradeMode.AUTO_EXECUTE,
    }
    
    if mode_str not in mode_map:
        return jsonify({"success": False, "error": f"无效模式: {mode_str}"})
    
    trader.set_mode(mode_map[mode_str])
    
    return jsonify({
        "success": True,
        "mode": mode_str,
        "message": f"交易模式已设置为: {mode_str}",
    })


def run_async(coro):
    """安全运行异步协程"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


@app.route("/api/trading/execute", methods=["POST"])
def trading_execute():
    """手动执行交易信号。若启用按策略分发且传入 strategy，则对绑定账户执行；否则走单账户 AutoTrader。"""
    data = request.get_json() or {}
    
    # 必填字段
    required = ["symbol", "side", "entry_price", "stop_loss", "take_profit"]
    for field in required:
        if field not in data:
            return jsonify({"success": False, "error": f"缺少字段: {field}"})
    
    signal = {
        "symbol": data["symbol"],
        "side": data["side"],
        "entry_price": float(data["entry_price"]),
        "stop_loss": float(data["stop_loss"]),
        "take_profit": float(data["take_profit"]),
        "confidence": data.get("confidence", 80),
        "strategy": data.get("strategy"),
        "signal_id": data.get("signal_id"),
    }
    
    # 按策略分发：有 strategy 且配置启用时，对绑定账户执行；无绑定时回退到单账户
    if DISPATCH_BY_STRATEGY and signal.get("strategy"):
        try:
            result = execute_signal_by_strategy(signal)
            if result.get("action") == "no_bindings" and result.get("targets", 0) == 0:
                trader = get_auto_trader()
                if trader is not None:
                    result = run_async(trader.process_signal(signal))
                    return jsonify({"success": result.get("success", False), **result})
            return jsonify(result)
        except Exception as e:
            log.error("execute_signal_by_strategy error", error=str(e))
            return jsonify({"success": False, "action": "error", "message": str(e)})
    
    # 单账户逻辑
    trader = get_auto_trader()
    if trader is None:
        return jsonify({"success": False, "error": "交易所 API 未配置"})
    
    try:
        result = run_async(trader.process_signal(signal))
    except Exception as e:
        log.error("执行交易失败", error=str(e))
        result = {"success": False, "message": str(e)}
    
    return jsonify({
        "success": result.get("success", False),
        **result,
    })


@app.route("/api/trading/positions", methods=["GET"])
def trading_positions():
    """获取当前持仓"""
    trader = get_auto_trader()
    
    if trader is None:
        return jsonify({"success": False, "error": "交易所 API 未配置"})
    
    return jsonify({
        "success": True,
        "positions": [p.to_dict() for p in trader.open_positions.values()],
        "count": len(trader.open_positions),
    })


@app.route("/api/trading/close", methods=["POST"])
def trading_close_position():
    """平仓"""
    trader = get_auto_trader()
    
    if trader is None:
        return jsonify({"success": False, "error": "交易所 API 未配置"})
    
    data = request.get_json() or {}
    symbol = data.get("symbol")
    
    if not symbol:
        return jsonify({"success": False, "error": "缺少 symbol"})
    
    # 异步执行
    try:
        result = run_async(trader.close_position(symbol, "manual"))
    except Exception as e:
        log.error(f"平仓失败: {e}")
        result = {"success": False, "message": str(e)}
    
    return jsonify({
        "success": result.get("success", False),
        **result,
    })


@app.route("/api/trading/history", methods=["GET"])
def trading_history():
    """获取交易历史"""
    trader = get_auto_trader()
    
    if trader is None:
        return jsonify({"success": False, "error": "交易所 API 未配置"})
    
    limit = request.args.get("limit", 20, type=int)
    
    return jsonify({
        "success": True,
        "trades": [t.to_dict() for t in trader.trade_history[-limit:]],
        "total": len(trader.trade_history),
    })


# ========== 自动同步后台线程 ==========

SYNC_INTERVAL = config.get_int("sync_interval_seconds", 300)  # 默认 5 分钟
_sync_stop_event = threading.Event()


_MARKET_SYNC_INTERVAL = 3600  # 市场信息每小时刷新一次
_last_market_sync = 0


def _sync_loop():
    """后台定时同步：余额、持仓、成交 → 数据库；市场信息每小时刷新"""
    global _last_market_sync
    import time as _time
    from libs.sync_node.service import (
        sync_balance_from_nodes,
        sync_positions_from_nodes,
        sync_trades_from_nodes,
    )
    from libs.exchange.market_service import MarketInfoService

    def _safe_sync(name, fn, max_retries=2):
        """带死锁重试的安全同步：每次用独立 session，避免一个失败影响全部"""
        for attempt in range(max_retries + 1):
            s = get_session()
            try:
                fn(s)
                s.commit()
                return True
            except Exception as e:
                s.rollback()
                err_str = str(e)
                if "Deadlock" in err_str and attempt < max_retries:
                    log.warning(f"同步 {name} 死锁，重试 {attempt + 1}/{max_retries}")
                    _time.sleep(0.5 * (attempt + 1))
                    continue
                log.warning(f"同步 {name} 失败", error=err_str)
                return False
            finally:
                s.close()
        return False

    log.info("自动同步线程启动", interval=SYNC_INTERVAL)
    while not _sync_stop_event.is_set():
        try:
            log.debug("开始自动同步: 余额")
            _safe_sync("余额", lambda s: sync_balance_from_nodes(s))
            log.debug("开始自动同步: 持仓")
            _safe_sync("持仓", lambda s: sync_positions_from_nodes(s))
            log.debug("开始自动同步: 成交")
            _safe_sync("成交", lambda s: sync_trades_from_nodes(s))

            # 市场信息刷新（每小时）
            now = _time.time()
            if now - _last_market_sync > _MARKET_SYNC_INTERVAL:
                log.info("开始同步市场信息 (dim_market_info)")
                def _sync_markets(s):
                    svc = MarketInfoService(s)
                    for ex in ("binance", "gate", "okx"):
                        svc.sync_from_ccxt(ex, market_type="swap")
                if _safe_sync("市场信息", _sync_markets):
                    _last_market_sync = now
                    log.info("市场信息同步完成")

            log.info("自动同步完成")
        except Exception as e:
            log.warning("自动同步异常", error=str(e))
        _sync_stop_event.wait(SYNC_INTERVAL)
    log.info("自动同步线程已停止")


def _auto_start_monitor():
    """
    若配置了 auto_trade_enabled=true，Flask 进程启动后自动开启监控循环，
    无需手动 POST /api/start。同时启动自动同步线程。
    """
    global monitor_thread, monitor_state
    if monitor_state["running"]:
        return
    auto_enabled = config.get_bool("auto_trade_enabled", False)
    if not auto_enabled:
        log.info("auto_trade_enabled=false，监控不自动启动（可手动 POST /api/start）")
        return
    # 启动信号监控
    stop_event.clear()
    monitor_state["running"] = True
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    log.info("监控已自动启动 (auto_trade_enabled=true)")
    # 启动自动同步线程
    _sync_stop_event.clear()
    sync_thread = threading.Thread(target=_sync_loop, daemon=True)
    sync_thread.start()


# Flask 启动后自动启动监控（仅在非 import 场景执行一次）
_auto_start_done = False


@app.before_request
def _maybe_auto_start():
    """利用第一次 HTTP 请求触发自动启动（兼容 flask run / gunicorn / uvicorn）"""
    global _auto_start_done
    if not _auto_start_done:
        _auto_start_done = True
        _auto_start_monitor()


if __name__ == "__main__":
    _auto_start_monitor()
    app.run(host="0.0.0.0", port=8020, debug=False)
