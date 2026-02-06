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
from datetime import datetime
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

# 监控配置
monitor_config = {
    "interval_seconds": 300,  # 检测间隔（默认5分钟）
    "strategies": [
        {
            "code": "market_regime",
            "config": {"atr_mult_sl": 1.5, "atr_mult_tp": 3.0},
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframe": "1h",
        }
    ],
    "min_confidence": 50,     # 最低置信度
    "notify_on_signal": True, # 有信号时通知
    "cooldown_minutes": 60,   # 同一交易对冷却时间（避免重复通知）
}

# 信号冷却记录
signal_cooldown: Dict[str, datetime] = {}

# 监控线程
monitor_thread: Optional[threading.Thread] = None
stop_event = threading.Event()


def fetch_candles(symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
    """从 data-provider 获取 K 线"""
    try:
        url = f"{DATA_PROVIDER_URL}/api/candles"
        params = {"symbol": symbol, "timeframe": timeframe, "limit": limit, "source": "live"}
        with httpx.Client(timeout=30.0) as client:
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


def is_in_cooldown(symbol: str, strategy: str) -> bool:
    """检查是否在冷却期"""
    key = f"{strategy}:{symbol}"
    if key not in signal_cooldown:
        return False
    
    cooldown_minutes = monitor_config.get("cooldown_minutes", 60)
    elapsed = (datetime.now() - signal_cooldown[key]).total_seconds() / 60
    return elapsed < cooldown_minutes


def set_cooldown(symbol: str, strategy: str):
    """设置冷却"""
    key = f"{strategy}:{symbol}"
    signal_cooldown[key] = datetime.now()


def monitor_loop():
    """监控主循环"""
    global monitor_state
    
    log.info("信号监控启动")
    
    while not stop_event.is_set():
        try:
            monitor_state["last_check"] = datetime.now().isoformat()
            monitor_state["total_checks"] += 1
            
            # 遍历所有策略配置
            for strat_cfg in monitor_config.get("strategies", []):
                code = strat_cfg.get("code")
                cfg = strat_cfg.get("config", {})
                symbols = strat_cfg.get("symbols", [])
                timeframe = strat_cfg.get("timeframe", "1h")
                
                for symbol in symbols:
                    # 检查冷却
                    if is_in_cooldown(symbol, code):
                        log.debug(f"冷却中跳过: {code}/{symbol}")
                        continue
                    
                    # 检测信号
                    signal = check_signal(code, cfg, symbol, timeframe)
                    
                    if signal:
                        confidence = signal.get("confidence", 0)
                        min_conf = monitor_config.get("min_confidence", 50)
                        
                        if confidence >= min_conf:
                            log.info(f"检测到信号: {signal['side']} {symbol} @ {signal['entry_price']}")
                            
                            monitor_state["last_signal"] = signal
                            monitor_state["total_signals"] += 1
                            
                            # 按策略多账户分发（若启用）
                            if DISPATCH_BY_STRATEGY and signal.get("strategy"):
                                try:
                                    dispatch_result = execute_signal_by_strategy(signal)
                                    log.info(
                                        "strategy dispatch: targets=%s success_count=%s",
                                        dispatch_result.get("targets", 0),
                                        dispatch_result.get("success_count", 0),
                                    )
                                except Exception as e:
                                    log.error("strategy dispatch error: %s", e)
                            
                            # 推送通知
                            if monitor_config.get("notify_on_signal", True):
                                result = notifier.send_signal(signal)
                                if result.success:
                                    log.info(f"信号已推送: {symbol}")
                                    set_cooldown(symbol, code)
                                else:
                                    log.error(f"推送失败: {result.error}")
                        else:
                            log.debug(f"信号置信度不足: {confidence} < {min_conf}")
            
        except Exception as e:
            log.error(f"监控循环异常: {e}")
            monitor_state["errors"] += 1
        
        # 等待下次检测
        interval = monitor_config.get("interval_seconds", 300)
        stop_event.wait(interval)
    
    log.info("信号监控已停止")


# ========== API Routes ==========

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "signal-monitor"})


@app.route("/api/status", methods=["GET"])
def get_status():
    """获取监控状态"""
    return jsonify({
        "success": True,
        "state": monitor_state,
        "config": {
            "interval_seconds": monitor_config.get("interval_seconds"),
            "strategies_count": len(monitor_config.get("strategies", [])),
            "min_confidence": monitor_config.get("min_confidence"),
            "notify_enabled": monitor_config.get("notify_on_signal"),
            "dispatch_by_strategy": DISPATCH_BY_STRATEGY,
            "strategy_dispatch_amount": STRATEGY_DISPATCH_AMOUNT,
        },
    })


@app.route("/api/config", methods=["GET"])
def get_config_api():
    """获取完整配置"""
    return jsonify({
        "success": True,
        "config": monitor_config,
    })


@app.route("/api/config", methods=["POST"])
def update_config():
    """更新配置"""
    global monitor_config
    
    data = request.get_json() or {}
    
    if "interval_seconds" in data:
        monitor_config["interval_seconds"] = int(data["interval_seconds"])
    if "strategies" in data:
        monitor_config["strategies"] = data["strategies"]
    if "min_confidence" in data:
        monitor_config["min_confidence"] = int(data["min_confidence"])
    if "notify_on_signal" in data:
        monitor_config["notify_on_signal"] = bool(data["notify_on_signal"])
    if "cooldown_minutes" in data:
        monitor_config["cooldown_minutes"] = int(data["cooldown_minutes"])
    # 按策略分发由环境/配置文件控制，不通过 API 动态改，仅展示在 status
    log.info("配置已更新")
    
    return jsonify({
        "success": True,
        "config": monitor_config,
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
    
    return jsonify({
        "success": True,
        "message": "监控已启动",
        "config": {
            "interval_seconds": monitor_config.get("interval_seconds"),
            "strategies": len(monitor_config.get("strategies", [])),
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
    strategy_code = data.get("strategy", "market_regime")
    symbol = data.get("symbol", "ETHUSDT")
    timeframe = data.get("timeframe", "1h")
    strategy_config = data.get("config", {"atr_mult_sl": 1.5, "atr_mult_tp": 3.0})
    
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
    """获取可用策略列表"""
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
    if not symbol or not entry_price:
        return {"account_id": target.account_id, "success": False, "error": "missing symbol or entry_price"}
    quantity = round(amount_usdt / entry_price, 6)
    if quantity <= 0:
        return {"account_id": target.account_id, "success": False, "error": "quantity <= 0"}
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
        order_result = await trader.create_order(
            symbol=symbol,
            side=order_side,
            order_type=OrderType.MARKET,
            quantity=quantity,
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
                log.warning("set_sl_tp failed for account %s: %s", target.account_id, e)
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
        log.error("execute_signal_for_target account_id=%s error=%s", target.account_id, e)
        return {"account_id": target.account_id, "user_id": target.user_id, "success": False, "error": str(e)}


def execute_signal_by_strategy(signal: Dict[str, Any]) -> Dict[str, Any]:
    """
    按策略分发：根据 signal["strategy"] 查 dim_strategy_binding，对每个绑定账户执行。
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
        amount = STRATEGY_DISPATCH_AMOUNT
        sandbox = config.get_bool("exchange_sandbox", True)
        results = []

        # 按 execution_node_id 分组：None/0=本机，其余=远程节点
        by_node = defaultdict(list)
        for t in targets:
            nid = (t.execution_node_id or 0) or 0
            by_node[nid].append(t)

        local_targets = by_node.get(0, [])
        for target in local_targets:
            r = run_async(
                _execute_signal_for_target(session, target, signal, amount, sandbox)
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
            payload = {
                "signal": signal,
                "amount_usdt": amount,
                "sandbox": sandbox,
                "tasks": [
                    {
                        "account_id": t.account_id,
                        "tenant_id": t.tenant_id,
                        "user_id": t.user_id,
                        "exchange": t.exchange,
                        "api_key": t.api_key,
                        "api_secret": t.api_secret,
                        "passphrase": t.passphrase,
                        "market_type": t.market_type,
                    }
                    for t in remote_targets
                ],
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
                            "amount_usdt": amount,
                            "sandbox": sandbox,
                            "tasks": [asdict(t) for t in remote_targets],
                        },
                        signal_id=signal.get("signal_id"),
                    )
                    queue.push(message)
                    for t in remote_targets:
                        results.append({"account_id": t.account_id, "user_id": t.user_id, "queued": True, "node_id": node_id})
                    continue
                except Exception as eq:
                    log.warning("node execute queue push failed node_id=%s, fallback to direct POST: %s", node_id, eq)
            try:
                node_headers = {}
                secret = config.get_str("node_auth_secret", "").strip()
                if secret:
                    node_headers["X-Center-Token"] = secret
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(f"{base_url}/api/execute", json=payload, headers=node_headers or None)
                    resp.raise_for_status()
                    data = resp.json()
            except Exception as e:
                log.warning("remote node POST node_id=%s error=%s", node_id, e)
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
        log.error("execute_signal_by_strategy error: %s", e)
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
            log.error("execute_signal_by_strategy error: %s", e)
            return jsonify({"success": False, "action": "error", "message": str(e)})
    
    # 单账户逻辑
    trader = get_auto_trader()
    if trader is None:
        return jsonify({"success": False, "error": "交易所 API 未配置"})
    
    try:
        result = run_async(trader.process_signal(signal))
    except Exception as e:
        log.error("执行交易失败: %s", e)
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8020, debug=False)
