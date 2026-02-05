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
from datetime import datetime
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from flask import Flask, request, jsonify
from libs.core import get_config, get_logger, setup_logging, gen_id
from libs.core.database import get_session
from libs.strategies import get_strategy, list_strategies
from libs.notify import TelegramNotifier
from libs.trading import AutoTrader, TradeMode, RiskLimits, TradeSettlementService
import asyncio

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
    
    log.info(f"配置已更新")
    
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

# 自动交易器（全局单例）
auto_trader: Optional[AutoTrader] = None
# 数据库 session（用于交易持久化）
_db_session = None
# 结算服务
_settlement_service: Optional[TradeSettlementService] = None


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
    """手动执行交易信号"""
    trader = get_auto_trader()
    
    if trader is None:
        return jsonify({"success": False, "error": "交易所 API 未配置"})
    
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
    }
    
    # 异步执行
    try:
        result = run_async(trader.process_signal(signal))
    except Exception as e:
        log.error(f"执行交易失败: {e}")
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
