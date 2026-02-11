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
import traceback
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
from libs.facts.models import SignalEvent
import asyncio
import json as _json
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
SYNC_INTERVAL = config.get_int("sync_interval_seconds", 300)  # 提前定义，供 /api/status 等使用

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
_state_lock = threading.Lock()  # 保护 monitor_state、signal_cooldown 等全局状态

# ── 策略实例缓存 (Step 1a) ──
# key = "strategy_code:symbol", value = strategy instance
# 确保策略内部状态（pending_order, post_fill_state, step_counter, cooldown）跨周期保持
_strategy_cache: Dict[str, Any] = {}
_strategy_config_hash: Dict[str, str] = {}   # 配置指纹，配置变更时重建实例

# ── 限价挂单追踪 (Step 2) ──
# 内存缓存（运行时快速查询），与 DB fact_pending_limit_order 表双写
# key = "strategy_code:symbol", value = {order_id, exchange_order_id, entry_price, side, ...}
_pending_limit_orders: Dict[str, Dict[str, Any]] = {}

# ── 待确认仓位 (Step 3) ──
# key = "strategy_code:symbol", value = {filled_at, confirm_deadline_candles, filled_price, side, ...}
_awaiting_confirmation: Dict[str, Dict[str, Any]] = {}

# 监控线程
monitor_thread: Optional[threading.Thread] = None
stop_event = threading.Event()


# ═══════════════════════════════════════════════════════════════════
# pending 限价单 DB 持久化辅助函数
# ═══════════════════════════════════════════════════════════════════

def _db_save_pending(pending_key: str, info: Dict[str, Any]):
    """将 pending 限价单写入 DB（INSERT or UPDATE）"""
    try:
        from libs.position.models import PendingLimitOrder
        session = get_session()
        target = info.get("target")
        row = session.query(PendingLimitOrder).filter(
            PendingLimitOrder.pending_key == pending_key
        ).first()
        if row:
            # 更新
            row.order_id = info.get("order_id")
            row.exchange_order_id = info.get("exchange_order_id")
            row.entry_price = info.get("entry_price", 0)
            row.stop_loss = info.get("stop_loss")
            row.take_profit = info.get("take_profit")
            row.side = info.get("side", "BUY")
            row.amount_usdt = info.get("amount_usdt")
            row.leverage = info.get("leverage")
            row.status = info.get("db_status", "PENDING")
            row.updated_at = datetime.now()
        else:
            row = PendingLimitOrder(
                pending_key=pending_key,
                order_id=info.get("order_id"),
                exchange_order_id=info.get("exchange_order_id"),
                symbol=info.get("symbol", ""),
                side=info.get("side", "BUY"),
                entry_price=info.get("entry_price", 0),
                stop_loss=info.get("stop_loss"),
                take_profit=info.get("take_profit"),
                strategy_code=info.get("strategy_code", ""),
                account_id=target.account_id if target else 0,
                tenant_id=target.tenant_id if target else 0,
                amount_usdt=info.get("amount_usdt"),
                leverage=info.get("leverage"),
                timeframe=info.get("timeframe", "15m"),
                retest_bars=info.get("retest_bars", 20),
                confirm_after_fill=info.get("confirm_after_fill", False),
                post_fill_confirm_bars=info.get("post_fill_confirm_bars", 3),
                placed_at=info.get("placed_at", datetime.now()),
                status="PENDING",
            )
            session.add(row)
        session.commit()
        session.close()
    except Exception as e:
        log.warning("DB保存pending限价单失败", key=pending_key, error=str(e))


def _db_update_pending_status(pending_key: str, status: str, **extra):
    """更新 DB 中 pending 限价单状态（FILLED/CONFIRMING/EXPIRED/CANCELLED）"""
    try:
        from libs.position.models import PendingLimitOrder
        session = get_session()
        row = session.query(PendingLimitOrder).filter(
            PendingLimitOrder.pending_key == pending_key
        ).first()
        if row:
            row.status = status
            row.closed_at = datetime.now() if status in ("FILLED", "EXPIRED", "CANCELLED") else None
            for k, v in extra.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            row.updated_at = datetime.now()
            session.commit()
        session.close()
    except Exception as e:
        log.warning("DB更新pending状态失败", key=pending_key, status=status, error=str(e))


def _db_load_pending_orders() -> Dict[str, Dict[str, Any]]:
    """启动时从 DB 加载所有 PENDING/CONFIRMING 状态的限价单"""
    result = {}
    try:
        from libs.position.models import PendingLimitOrder
        from libs.member.models import ExchangeAccount
        session = get_session()
        rows = session.query(PendingLimitOrder).filter(
            PendingLimitOrder.status.in_(["PENDING", "CONFIRMING"])
        ).all()
        if not rows:
            session.close()
            return result

        # 批量获取账户信息以重建 target
        account_ids = set(r.account_id for r in rows)
        from libs.member.service import MemberService, ExecutionTarget
        member_svc = MemberService(session)

        accounts = {}
        for aid in account_ids:
            acct = session.query(ExchangeAccount).filter(ExchangeAccount.id == aid).first()
            if acct:
                accounts[aid] = acct

        for row in rows:
            acct = accounts.get(row.account_id)
            if not acct:
                log.warning("恢复pending失败: 账户不存在", account_id=row.account_id, key=row.pending_key)
                continue

            # 重建简化的 target（只需 exchange 凭证即可）
            target = ExecutionTarget(
                tenant_id=row.tenant_id,
                account_id=row.account_id,
                user_id=acct.user_id,
                exchange=acct.exchange,
                api_key=acct.api_key,
                api_secret=acct.api_secret,
                passphrase=acct.passphrase,
                market_type=acct.account_type or "future",
                binding_id=0,
                strategy_code=row.strategy_code,
                ratio=100,
            )

            info = {
                "order_id": row.order_id,
                "exchange_order_id": row.exchange_order_id,
                "symbol": row.symbol,
                "side": row.side,
                "entry_price": float(row.entry_price) if row.entry_price else 0,
                "stop_loss": float(row.stop_loss) if row.stop_loss else 0,
                "take_profit": float(row.take_profit) if row.take_profit else 0,
                "strategy_code": row.strategy_code,
                "target": target,
                "amount_usdt": float(row.amount_usdt) if row.amount_usdt else 0,
                "leverage": row.leverage,
                "placed_at": row.placed_at or row.created_at,
                "retest_bars": row.retest_bars,
                "timeframe": row.timeframe,
                "confirm_after_fill": row.confirm_after_fill,
                "post_fill_confirm_bars": row.post_fill_confirm_bars,
            }

            if row.status == "CONFIRMING":
                # 恢复到 _awaiting_confirmation
                _awaiting_confirmation[row.pending_key] = {
                    **info,
                    "filled_at": row.filled_at or datetime.now(),
                    "filled_price": float(row.filled_price) if row.filled_price else info["entry_price"],
                    "filled_qty": float(row.filled_qty) if row.filled_qty else 0,
                    "candles_checked": row.candles_checked or 0,
                }
            else:
                result[row.pending_key] = info

        session.close()
        log.info(f"从DB恢复限价单: {len(result)} pending, {len(_awaiting_confirmation)} confirming")
    except Exception as e:
        log.error("从DB加载pending限价单失败", error=str(e))
    return result


def _config_fingerprint(cfg: Dict) -> str:
    """配置指纹：配置变更时重建策略实例"""
    import hashlib
    return hashlib.md5(_json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()[:12]


def _get_cached_strategy(strategy_code: str, strategy_config: Dict, symbol: str):
    """
    获取或创建策略实例（缓存版）
    - 同一 strategy_code + symbol 复用实例，保持内部状态
    - 配置变更时自动重建
    """
    cache_key = f"{strategy_code}:{symbol}"
    fp = _config_fingerprint(strategy_config)
    
    if cache_key in _strategy_cache and _strategy_config_hash.get(cache_key) == fp:
        return _strategy_cache[cache_key]
    
    # 新建或配置变更 → 创建新实例
    strategy = get_strategy(strategy_code, strategy_config)
    _strategy_cache[cache_key] = strategy
    _strategy_config_hash[cache_key] = fp
    log.info("策略实例已创建/更新", key=cache_key, fingerprint=fp)
    return strategy


def _query_open_positions(symbol: str, strategy_code: str = None) -> Optional[Dict]:
    """
    查询数据库中该 symbol 的 OPEN 持仓，返回策略可识别的 positions dict
    """
    try:
        session = get_session()
        from libs.position.repository import PositionRepository
        repo = PositionRepository(session)
        # 查询所有 OPEN 持仓
        from sqlalchemy import and_
        from libs.position.models import Position
        query = session.query(Position).filter(
            and_(
                Position.symbol == symbol,
                Position.status == "OPEN",
                Position.quantity > 0,
            )
        )
        if strategy_code:
            query = query.filter(Position.strategy_code == strategy_code)
        positions = query.all()
        session.close()
        
        if not positions:
            return None
        
        # 返回策略可识别的格式（analyze 中检查 has_position / has_long / has_short）
        pos = positions[0]
        side_upper = (pos.position_side or "").upper()
        return {
            "has_position": True,
            "has_long": side_upper == "LONG",
            "has_short": side_upper == "SHORT",
            "symbol": pos.symbol,
            "side": "BUY" if side_upper == "LONG" else "SELL",
            "entry_price": float(pos.entry_price) if pos.entry_price else float(pos.avg_cost or 0),
            "quantity": float(pos.quantity or 0),
            "stop_loss": float(pos.stop_loss) if pos.stop_loss else None,
            "take_profit": float(pos.take_profit) if pos.take_profit else None,
            "position_id": pos.position_id,
        }
    except Exception as e:
        log.debug("查询持仓失败（可能表不存在）", error=str(e))
        return None


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
        with _state_lock:
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
    """检测单个策略信号（使用缓存策略实例 + 传入持仓信息）"""
    try:
        # 获取 K 线
        candles = fetch_candles(symbol, timeframe)
        if len(candles) < 100:
            log.warning(f"K线数据不足: {symbol} {len(candles)}")
            return None
        
        # ── Step 1a: 使用缓存策略实例（保持内部状态跨周期持续）──
        strategy = _get_cached_strategy(strategy_code, strategy_config, symbol)
        
        # ── Step 1b: 查询当前持仓，传给策略（防止重复开仓）──
        positions = _query_open_positions(symbol, strategy_code)
        
        # ── Step 1c: 检查是否有 pending 限价单（防止重复挂单）──
        pending_key = f"{strategy_code}:{symbol}"
        with _state_lock:
            if pending_key in _pending_limit_orders or pending_key in _awaiting_confirmation:
                return None  # 已有挂单或等待确认中，跳过
        
        signal = strategy.analyze(
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            positions=positions,
        )
        
        if signal:
            # 把策略配置中的关键参数带到信号里，执行层据此决定市价/限价 + 确认逻辑
            indicators = signal.indicators or {}
            indicators["entry_mode"] = strategy_config.get("entry_mode", "market")
            indicators["retest_bars"] = strategy_config.get("retest_bars", 20)
            indicators["confirm_after_fill"] = strategy_config.get("confirm_after_fill", False)
            indicators["post_fill_confirm_bars"] = strategy_config.get("post_fill_confirm_bars", 3)
            
            return {
                "symbol": signal.symbol,
                "signal_type": signal.signal_type,   # OPEN / CLOSE / HEDGE 等
                "side": signal.side,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "confidence": signal.confidence,
                "reason": signal.reason,
                "indicators": indicators,
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
    now = datetime.now()
    with _state_lock:
        if key not in signal_cooldown:
            return False
        cooldown_until = signal_cooldown[key]
        # 支持两种格式：datetime 表示冷却到期时间（新），或 datetime 表示设定时间（旧）
        if cooldown_until > now:
            # 新格式：cooldown_until 是到期时间
            return True
        # 兼容旧格式：cooldown_until 是设定时间
        elapsed = (now - cooldown_until).total_seconds() / 60
        if elapsed >= cooldown_minutes:
            # 已过冷却期，清理过期条目释放内存
            del signal_cooldown[key]
            return False
        return True


def set_cooldown(symbol: str, strategy: str, timeframe: str = "1h"):
    """
    设置冷却 — 冷却时间 = max(策略配置的 cooldown, 当前 K 线剩余时间 × 2)
    ★ 先持久化到数据库，成功后再更新内存，避免 DB 失败时内存与库不一致。
    """
    key = f"{strategy}:{symbol}"
    tf_minutes = _timeframe_to_minutes(timeframe)
    now = datetime.now()
    minutes_into_period = (now.hour * 60 + now.minute) % tf_minutes
    remaining = tf_minutes - minutes_into_period + (tf_minutes // 2)
    cooldown_until = now + timedelta(minutes=max(remaining, tf_minutes))
    # 先写库
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
        log.warning("冷却持久化失败，不更新内存", error=str(e))
        return
    # 再更新内存（加锁）
    with _state_lock:
        signal_cooldown[key] = cooldown_until
    log.info("设置冷却", key=key, until=cooldown_until.isoformat(), remaining_min=remaining)


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


# ═══════════════════════════════════════════════════════════════════
# Step 2+3: 限价挂单管理 + 成交后确认过滤
# ═══════════════════════════════════════════════════════════════════

def _check_pending_limit_orders_cycle():
    """
    检查所有已挂的限价单：
      - 已成交 → 写入 SL/TP（或启动确认倒计时）
      - 超时未成交 → 撤单
    在 monitor_loop 每轮末尾调用。
    """
    if not _pending_limit_orders:
        return
    
    now = datetime.now()
    to_remove = []
    
    with _state_lock:
        items = list(_pending_limit_orders.items())
    
    for pending_key, info in items:
        try:
            # 计算超时
            tf_minutes = _timeframe_to_minutes(info.get("timeframe", "15m"))
            max_wait_minutes = tf_minutes * info.get("retest_bars", 20)
            elapsed_minutes = (now - info["placed_at"]).total_seconds() / 60
            
            target = info["target"]
            sandbox = config.get_bool("exchange_sandbox", True)
            
            # 创建 trader 查询订单状态
            trader = LiveTrader(
                exchange=target.exchange,
                api_key=target.api_key,
                api_secret=target.api_secret,
                passphrase=target.passphrase,
                sandbox=sandbox,
                market_type=target.market_type,
            )
            
            loop = asyncio.new_event_loop()
            try:
                order_result = loop.run_until_complete(
                    trader.get_order(info["exchange_order_id"], info["symbol"])
                )
                
                status = order_result.status if order_result else None
                
                if status in (OrderStatus.FILLED, OrderStatus.PARTIAL):
                    # ── 限价单已成交 ──
                    filled_price = order_result.filled_price or info["entry_price"]
                    filled_qty = order_result.filled_quantity or 0
                    
                    log.info("限价单已成交",
                             key=pending_key, price=filled_price, qty=filled_qty)
                    
                    # ── 推送通知：限价单已成交 ──
                    if NOTIFY_ON_SIGNAL:
                        side_emoji = "🟢" if info["side"].upper() == "BUY" else "🔴"
                        notifier.send(
                            title="✅ 限价单已成交",
                            content=(
                                f"{side_emoji} <b>{info['side']} {info['symbol']}</b>\n\n"
                                f"💰 成交价: <code>{filled_price:,.2f}</code>\n"
                                f"📦 数量: <code>{filled_qty}</code>\n"
                                f"🛑 止损: <code>{info['stop_loss']:,.2f}</code>\n"
                                f"🎯 止盈: <code>{info['take_profit']:,.2f}</code>\n\n"
                                f"📝 策略: {info['strategy_code']}\n"
                                f"⏰ {now.strftime('%Y-%m-%d %H:%M:%S')}"
                            ),
                        )
                    
                    if info.get("confirm_after_fill"):
                        # ── Step 3: 启动确认倒计时 ──
                        with _state_lock:
                            _awaiting_confirmation[pending_key] = {
                                "filled_at": now,
                                "filled_price": filled_price,
                                "filled_qty": filled_qty,
                                "side": info["side"],
                                "symbol": info["symbol"],
                                "stop_loss": info["stop_loss"],
                                "take_profit": info["take_profit"],
                                "strategy_code": info["strategy_code"],
                                "target": target,
                                "timeframe": info["timeframe"],
                                "post_fill_confirm_bars": info.get("post_fill_confirm_bars", 3),
                                "candles_checked": 0,
                            }
                        _db_update_pending_status(pending_key, "CONFIRMING",
                                                  filled_price=filled_price,
                                                  filled_qty=filled_qty,
                                                  filled_at=now)
                        log.info("进入确认等待", key=pending_key,
                                 confirm_bars=info.get("post_fill_confirm_bars", 3))
                    else:
                        # 无需确认 → 直接写入 SL/TP
                        session = get_session()
                        try:
                            order_side = OrderSide.BUY if info["side"].upper() == "BUY" else OrderSide.SELL
                            _write_sl_tp_to_position(
                                session, target, info["symbol"], order_side,
                                filled_price, info["stop_loss"], info["take_profit"],
                                info["strategy_code"],
                            )
                            session.commit()
                        finally:
                            session.close()
                        _db_update_pending_status(pending_key, "FILLED",
                                                  filled_price=filled_price,
                                                  filled_qty=filled_qty,
                                                  filled_at=now)
                    
                    to_remove.append(pending_key)
                
                elif elapsed_minutes >= max_wait_minutes:
                    # ── 超时未成交 → 撤单 ──
                    log.info("限价单超时撤单",
                             key=pending_key, elapsed_min=f"{elapsed_minutes:.0f}",
                             max_min=max_wait_minutes)
                    loop.run_until_complete(
                        trader.cancel_order(info["exchange_order_id"], info["symbol"])
                    )
                    
                    _db_update_pending_status(pending_key, "EXPIRED")
                    
                    # ── 推送通知：限价单超时撤单 ──
                    if NOTIFY_ON_SIGNAL:
                        notifier.send(
                            title="⏰ 限价单超时撤单",
                            content=(
                                f"{'🟢' if info['side'].upper() == 'BUY' else '🔴'} "
                                f"<b>{info['side']} {info['symbol']}</b>\n\n"
                                f"💰 挂单价: <code>{info['entry_price']:,.2f}</code>\n"
                                f"⏳ 等待: {elapsed_minutes:.0f} 分钟\n"
                                f"❌ 价格未到，已自动撤单\n\n"
                                f"📝 策略: {info['strategy_code']}\n"
                                f"⏰ {now.strftime('%Y-%m-%d %H:%M:%S')}"
                            ),
                        )
                    
                    to_remove.append(pending_key)
                
                loop.run_until_complete(trader.close())
            finally:
                loop.close()
                
        except Exception as e:
            log.error("检查限价单失败", key=pending_key, error=str(e))
    
    # 清理已处理的挂单
    if to_remove:
        with _state_lock:
            for key in to_remove:
                _pending_limit_orders.pop(key, None)


def _check_awaiting_confirmations_cycle():
    """
    检查等待确认的仓位：
      - 在 post_fill_confirm_bars 内出现确认形态 → 设置 SL/TP，保留仓位
      - 超过 confirm_bars 仍无确认 → 市价平仓
    
    确认逻辑复用策略实例的 _check_post_fill_confirmation()
    """
    if not _awaiting_confirmation:
        return
    
    now = datetime.now()
    to_remove = []
    
    with _state_lock:
        items = list(_awaiting_confirmation.items())
    
    for conf_key, info in items:
        try:
            tf_minutes = _timeframe_to_minutes(info.get("timeframe", "15m"))
            elapsed_minutes = (now - info["filled_at"]).total_seconds() / 60
            candles_elapsed = int(elapsed_minutes / tf_minutes)
            
            strategy_code = info["strategy_code"]
            symbol = info["symbol"]
            
            # 获取缓存的策略实例
            cache_key = f"{strategy_code}:{symbol}"
            strategy = _strategy_cache.get(cache_key)
            if not strategy:
                log.warning("确认检查: 策略实例不存在", key=conf_key)
                to_remove.append(conf_key)
                continue
            
            # 获取 K 线用于确认检查
            candles = fetch_candles(symbol, info.get("timeframe", "15m"))
            if not candles:
                continue
            
            # 构造当前持仓信息
            current_position = {
                "side": info["side"],
                "entry_price": info["filled_price"],
                "stop_loss": info["stop_loss"],
                "take_profit": info["take_profit"],
            }
            
            # 调用策略的确认检查方法
            confirm_result = None
            if hasattr(strategy, "_check_post_fill_confirmation"):
                confirm_result = strategy._check_post_fill_confirmation(
                    symbol, candles, current_position
                )
            
            if confirm_result and confirm_result.signal_type == "CLOSE":
                # ── 确认失败 → 市价平仓 ──
                log.info("确认失败，平仓", key=conf_key, reason="UNCONFIRMED",
                         candles_elapsed=candles_elapsed)
                _close_unconfirmed_position(info)
                _db_update_pending_status(conf_key, "CANCELLED",
                                          candles_checked=candles_elapsed)
                to_remove.append(conf_key)
            
            elif confirm_result is None and hasattr(strategy, "_post_fill_state") and not strategy._post_fill_state:
                # ── 确认成功（策略清除了 _post_fill_state）→ 设置 SL/TP ──
                log.info("确认成功，设置SL/TP", key=conf_key, candles_elapsed=candles_elapsed)
                session = get_session()
                try:
                    target = info["target"]
                    order_side = OrderSide.BUY if info["side"].upper() == "BUY" else OrderSide.SELL
                    _write_sl_tp_to_position(
                        session, target, symbol, order_side,
                        info["filled_price"], info["stop_loss"], info["take_profit"],
                        strategy_code,
                    )
                    session.commit()
                finally:
                    session.close()
                _db_update_pending_status(conf_key, "FILLED",
                                          candles_checked=candles_elapsed)
                to_remove.append(conf_key)
            
            elif candles_elapsed > info.get("post_fill_confirm_bars", 3) + 1:
                # ── 超时兜底：超过确认窗口仍未决定 → 平仓 ──
                log.info("确认超时，兜底平仓", key=conf_key, candles_elapsed=candles_elapsed)
                _close_unconfirmed_position(info)
                _db_update_pending_status(conf_key, "CANCELLED",
                                          candles_checked=candles_elapsed)
                to_remove.append(conf_key)
            
        except Exception as e:
            log.error("确认检查失败", key=conf_key, error=str(e))
    
    if to_remove:
        with _state_lock:
            for key in to_remove:
                _awaiting_confirmation.pop(key, None)


def _close_unconfirmed_position(info: Dict):
    """市价平仓：确认失败的仓位"""
    try:
        target = info["target"]
        sandbox = config.get_bool("exchange_sandbox", True)
        
        # 平仓方向与开仓方向相反
        close_side = OrderSide.SELL if info["side"].upper() == "BUY" else OrderSide.BUY
        
        trader = LiveTrader(
            exchange=target.exchange,
            api_key=target.api_key,
            api_secret=target.api_secret,
            passphrase=target.passphrase,
            sandbox=sandbox,
            market_type=target.market_type,
        )
        
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                trader.create_order(
                    symbol=info["symbol"],
                    side=close_side,
                    order_type=OrderType.MARKET,
                    quantity=info.get("filled_qty", 0),
                    trade_type="CLOSE",
                    close_reason="UNCONFIRMED",
                )
            )
            ok = result.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)
            log.info("未确认仓位已平仓" if ok else "未确认仓位平仓失败",
                     symbol=info["symbol"], side=info["side"],
                     filled_price=result.filled_price)
            loop.run_until_complete(trader.close())
        finally:
            loop.close()
    except Exception as e:
        log.error("平仓未确认仓位失败", symbol=info.get("symbol"), error=str(e))


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


def _write_signal_event(
    signal_id: str,
    event_type: str,
    status: str,
    source_service: str = "signal-monitor",
    detail: dict = None,
    account_id: int = None,
    error_message: str = None,
):
    """写入信号事件到 fact_signal_event 表（独立 session，不影响主流程）"""
    try:
        session = get_session()
        event = SignalEvent(
            signal_id=signal_id or "",
            event_type=event_type,
            status=status,
            source_service=source_service,
            account_id=account_id,
            detail=_json.dumps(detail, ensure_ascii=False, default=str) if detail else None,
            error_message=error_message,
        )
        session.add(event)
        session.commit()
        session.close()
    except Exception as e:
        log.error("write signal event failed",
                  signal_id=signal_id, event_type=event_type, status=status,
                  account_id=account_id, error_message=error_message,
                  error=str(e))
        try:
            session.rollback()
            session.close()
        except Exception:
            pass


def monitor_loop():
    """监控主循环 - 每轮从数据库加载最新策略配置"""
    global monitor_state

    log.info("信号监控启动")

    # 启动时从 DB 恢复冷却记录（防止重启丢失）
    _load_cooldowns_from_db()

    while not stop_event.is_set():
        try:
            with _state_lock:
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
                                # 确保信号有 signal_id
                                if not sig.get("signal_id"):
                                    sig["signal_id"] = gen_id("SIG")

                                # 将策略层参数注入信号（amount_usdt、leverage），供执行层使用
                                if strat_cfg.get("amount_usdt"):
                                    sig["amount_usdt"] = strat_cfg["amount_usdt"]
                                if strat_cfg.get("leverage"):
                                    sig["leverage"] = strat_cfg["leverage"]

                                with _state_lock:
                                    monitor_state["last_signal"] = sig
                                    monitor_state["total_signals"] += 1

                                # ── 写入信号事件: CREATED ──
                                _write_signal_event(
                                    signal_id=sig["signal_id"],
                                    event_type="CREATED",
                                    status="pending",
                                    detail={
                                        "strategy": code,
                                        "symbol": symbol,
                                        "side": sig.get("side"),
                                        "signal_type": sig.get("signal_type", "OPEN"),
                                        "entry_price": sig.get("entry_price"),
                                        "stop_loss": sig.get("stop_loss"),
                                        "take_profit": sig.get("take_profit"),
                                        "confidence": confidence,
                                        "timeframe": timeframe,
                                    },
                                )

                                # 按策略多账户分发（若启用）
                                if DISPATCH_BY_STRATEGY and sig.get("strategy"):
                                    try:
                                        dispatch_result = execute_signal_by_strategy(sig)
                                        log.info(
                                            f"strategy dispatch [{sig.get('side')}]",
                                            targets=dispatch_result.get("targets", 0),
                                            success_count=dispatch_result.get("success_count", 0),
                                        )
                                        # ── 写入信号事件: DISPATCHED ──
                                        _dispatch_success = dispatch_result.get("success", False)
                                        _dispatch_targets = dispatch_result.get("targets", 0)
                                        _dispatch_ok = dispatch_result.get("success_count", 0)
                                        _write_signal_event(
                                            signal_id=sig["signal_id"],
                                            event_type="DISPATCHED" if _dispatch_success else "FAILED",
                                            status="executed" if _dispatch_success else "failed",
                                            detail={
                                                "action": dispatch_result.get("action"),
                                                "targets": _dispatch_targets,
                                                "success_count": _dispatch_ok,
                                                "strategy": code,
                                                "symbol": symbol,
                                                "side": sig.get("side"),
                                            },
                                            error_message=dispatch_result.get("message") if not _dispatch_success else None,
                                        )
                                    except Exception as e:
                                        log.error(f"strategy dispatch error [{sig.get('side')}]", error=str(e), traceback=traceback.format_exc())
                                        _write_signal_event(
                                            signal_id=sig["signal_id"],
                                            event_type="FAILED",
                                            status="failed",
                                            detail={
                                                "strategy": code,
                                                "symbol": symbol,
                                                "side": sig.get("side"),
                                            },
                                            error_message=str(e),
                                        )

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
            log.error(f"监控循环异常: {e}", traceback=traceback.format_exc())
            with _state_lock:
                monitor_state["errors"] += 1

        # ── Step 2+3: 每轮检查限价挂单 + 确认过滤 ──
        try:
            _check_pending_limit_orders_cycle()
        except Exception as e:
            log.error("检查限价挂单异常", error=str(e))
        
        try:
            _check_awaiting_confirmations_cycle()
        except Exception as e:
            log.error("检查确认过滤异常", error=str(e))

        # 等待下次检测
        stop_event.wait(MONITOR_INTERVAL)

    with _state_lock:
        monitor_state["running"] = False
    log.info("信号监控已停止")


# ========== API Routes ==========

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "signal-monitor"})


@app.route("/api/status", methods=["GET"])
def get_status():
    """获取监控状态"""
    strategies = _load_strategies_from_db()
    # 构建冷却状态列表（加锁复制后遍历）
    now = datetime.now()
    cooldowns = []
    with _state_lock:
        items = list(signal_cooldown.items())
    for key, until in items:
        if until > now:
            parts = key.split(":", 1)
            cooldowns.append({
                "strategy": parts[0] if len(parts) > 0 else key,
                "symbol": parts[1] if len(parts) > 1 else "",
                "cooldown_until": until.isoformat(),
                "remaining_minutes": round((until - now).total_seconds() / 60, 1),
            })
    # 持仓监控统计
    pm_stats = {}
    if not EXCHANGE_SL_TP:
        try:
            from libs.position.monitor import get_monitor_stats
            pm_stats = get_monitor_stats()
        except Exception:
            pass
    # 获取持仓监控扫描间隔
    pm_interval = config.get_float("position_monitor_interval", 5.0)

    # ── Step 2+3: 挂单 + 确认状态 ──
    with _state_lock:
        pending_orders = [
            {
                "key": k,
                "symbol": v["symbol"],
                "side": v["side"],
                "entry_price": v["entry_price"],
                "stop_loss": v.get("stop_loss"),
                "take_profit": v.get("take_profit"),
                "strategy_code": v.get("strategy_code", ""),
                "amount_usdt": v.get("amount_usdt"),
                "placed_at": v["placed_at"].isoformat(),
                "elapsed_min": round((now - v["placed_at"]).total_seconds() / 60, 1),
                "retest_bars": v.get("retest_bars", 20),
                "timeframe": v.get("timeframe", "15m"),
            }
            for k, v in _pending_limit_orders.items()
        ]
        awaiting = [
            {
                "key": k,
                "symbol": v["symbol"],
                "side": v["side"],
                "filled_price": v["filled_price"],
                "filled_at": v["filled_at"].isoformat(),
                "confirm_bars": v.get("post_fill_confirm_bars", 3),
            }
            for k, v in _awaiting_confirmation.items()
        ]
        cached_strategies = list(_strategy_cache.keys())
        state_snapshot = dict(monitor_state)
    
    return jsonify({
        "success": True,
        "state": state_snapshot,
        "config": {
            "interval_seconds": MONITOR_INTERVAL,
            "sync_interval_seconds": SYNC_INTERVAL,
            "strategies_count": len(strategies),
            "notify_enabled": NOTIFY_ON_SIGNAL,
            "dispatch_by_strategy": DISPATCH_BY_STRATEGY,
            "strategy_dispatch_amount": STRATEGY_DISPATCH_AMOUNT,
            "exchange_sl_tp": EXCHANGE_SL_TP,
            "position_monitor": not EXCHANGE_SL_TP,
            "position_monitor_interval": pm_interval,
        },
        "position_monitor_stats": pm_stats,
        "cooldowns": cooldowns,
        "pending_limit_orders": pending_orders,
        "awaiting_confirmation": awaiting,
        "cached_strategies": cached_strategies,
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
    
    with _state_lock:
        if monitor_state["running"]:
            return jsonify({"success": False, "error": "监控已在运行中"})
        monitor_state["running"] = True
    
    stop_event.clear()
    
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
    
    with _state_lock:
        if not monitor_state["running"]:
            return jsonify({"success": False, "error": "监控未运行"})
        monitor_state["running"] = False
    stop_event.set()
    
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


@app.route("/api/position-monitor/scan", methods=["POST"])
def trigger_pm_scan():
    """手动触发一次持仓监控扫描（检查 SL/TP）"""
    if EXCHANGE_SL_TP:
        return jsonify({"success": False, "message": "当前使用交易所SL/TP模式，自管监控未启用"})
    try:
        from libs.position.monitor import run_scan_once
        result = run_scan_once()
        return jsonify({"success": True, "data": result})
    except ImportError:
        return jsonify({"success": False, "message": "position_monitor 模块未加载"})
    except Exception as e:
        log.error("manual pm scan error", error=str(e))
        return jsonify({"success": False, "message": str(e)})


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


# ========== 限价挂单管理 API ==========

@app.route("/api/pending-orders/cancel", methods=["POST"])
def cancel_pending_order():
    """
    手动撤销限价挂单（管理后台调用）。
    请求体: {"pending_key": "strategy_code:symbol", "reason": "..."}

    流程：
    1. 从内存 _pending_limit_orders / _awaiting_confirmation 查找
    2. 在交易所撤单（如果是 PENDING 状态）
    3. 如果是 CONFIRMING 状态，市价平仓
    4. 更新内存 + DB 状态
    """
    data = request.get_json(force=True, silent=True) or {}
    pending_key = data.get("pending_key", "").strip()
    reason = data.get("reason", "手动撤单")

    if not pending_key:
        return jsonify({"success": False, "error": "pending_key 必填"}), 400

    with _state_lock:
        info = _pending_limit_orders.get(pending_key)
        awaiting_info = _awaiting_confirmation.get(pending_key)

    if not info and not awaiting_info:
        return jsonify({"success": False, "error": f"未找到挂单: {pending_key}"}), 404

    try:
        if info:
            # PENDING 状态 → 交易所撤单
            target = info.get("target")
            exchange_order_id = info.get("exchange_order_id")
            symbol = info.get("symbol", "")

            if target and exchange_order_id:
                try:
                    from libs.trading.live_trader import LiveTrader
                    sandbox = config.get_bool("exchange_sandbox", True)
                    trader = LiveTrader(
                        exchange=target.exchange,
                        api_key=target.api_key,
                        api_secret=target.api_secret,
                        passphrase=target.passphrase,
                        sandbox=sandbox,
                        market_type=target.market_type,
                    )
                    import asyncio
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(
                            trader.cancel_order(order_id=exchange_order_id, symbol=symbol)
                        )
                    finally:
                        loop.close()
                    log.info("管理员撤单成功", pending_key=pending_key, reason=reason)
                except Exception as e:
                    log.warning("交易所撤单失败(可能已不存在)", pending_key=pending_key, error=str(e))

            with _state_lock:
                _pending_limit_orders.pop(pending_key, None)

            _db_update_pending_status(pending_key, "CANCELLED")
            return jsonify({
                "success": True,
                "message": f"已撤销挂单 {pending_key}",
                "reason": reason,
            })

        elif awaiting_info:
            # CONFIRMING 状态 → 市价平仓
            try:
                _close_unconfirmed_position(awaiting_info)
                log.info("管理员撤销确认中仓位", pending_key=pending_key, reason=reason)
            except Exception as e:
                log.warning("平仓失败", pending_key=pending_key, error=str(e))

            with _state_lock:
                _awaiting_confirmation.pop(pending_key, None)

            _db_update_pending_status(pending_key, "CANCELLED")
            return jsonify({
                "success": True,
                "message": f"已撤销确认中仓位 {pending_key}，已市价平仓",
                "reason": reason,
            })

    except Exception as e:
        log.error("撤单失败", pending_key=pending_key, error=str(e))
        return jsonify({"success": False, "error": str(e)}), 500


# ========== 自动交易 API ==========

# 按策略多账户分发：为 True 时，有 strategy_code 的信号将查 dim_strategy_binding 并对每个绑定账户执行
DISPATCH_BY_STRATEGY = config.get_bool("dispatch_by_strategy", False)
# 按策略分发时，每账户下单金额（USDT）
STRATEGY_DISPATCH_AMOUNT = config.get_float("strategy_dispatch_amount", 100.0)
# 为 True 时，远程节点任务投递到 NODE_EXECUTE_QUEUE，由 worker 消费并 POST 到节点；否则直接 POST
USE_NODE_EXECUTION_QUEUE = config.get_bool("use_node_execution_queue", False)
# 不在交易所挂 SL/TP 单，一律自管：由 position_monitor 监控到价平仓（防止交易所扫损、与注释一致）
EXCHANGE_SL_TP = False

# 自动交易器（全局单例）
auto_trader: Optional[AutoTrader] = None
# 数据库 session（用于交易持久化）
_db_session = None
# 结算服务
_settlement_service: Optional[TradeSettlementService] = None


def _write_sl_tp_to_position(
    session,
    target: ExecutionTarget,
    symbol: str,
    order_side,
    filled_price: float,
    stop_loss: float,
    take_profit: float,
    strategy_code: str = "",
):
    """
    将 SL/TP + 入场价写入 fact_position 表，供 position_monitor 监控到价平仓。
    """
    from libs.position.repository import PositionRepository
    from libs.trading.base import OrderSide as _OrderSide
    pos_repo = PositionRepository(session)
    # OrderSide enum → position_side 字符串
    if isinstance(order_side, _OrderSide):
        position_side = "LONG" if order_side == _OrderSide.BUY else "SHORT"
    else:
        position_side = "LONG" if str(order_side).upper().endswith("BUY") else "SHORT"
    # 尝试多种 symbol 格式 + 多种交易所名格式查找持仓
    # exchange 可能存为 "gate"/"gateio"/"binance"/"binanceusdm"/"okx" 等
    pos = None
    exchange_raw = target.exchange or ""
    exchange_variants = {exchange_raw}
    # 添加常见别名
    ex_lower = exchange_raw.lower().strip()
    _ex_aliases = {
        "gate": {"gate", "gateio"}, "gateio": {"gate", "gateio"},
        "binance": {"binance", "binanceusdm"}, "binanceusdm": {"binance", "binanceusdm"},
    }
    exchange_variants.update(_ex_aliases.get(ex_lower, {ex_lower}))
    exchange_variants.discard("")  # 移除空字符串

    symbol_variants = [symbol, symbol.replace("/", "")]
    for s in symbol_variants:
        for ex in exchange_variants:
            pos = pos_repo.get_by_key(
                tenant_id=target.tenant_id,
                account_id=target.account_id,
                symbol=s,
                exchange=ex,
                position_side=position_side,
            )
            if pos:
                break
        if pos:
            break
    if pos:
        from decimal import Decimal
        pos.entry_price = Decimal(str(filled_price)) if filled_price else None
        pos.stop_loss = Decimal(str(stop_loss)) if stop_loss else None
        pos.take_profit = Decimal(str(take_profit)) if take_profit else None
        pos.strategy_code = strategy_code or None
        pos_repo.update(pos)
        log.info(
            "SL/TP 已写入持仓表（自管模式）",
            account_id=target.account_id,
            symbol=symbol,
            entry=filled_price,
            sl=stop_loss,
            tp=take_profit,
        )
    else:
        log.warning("未找到持仓记录，无法写入 SL/TP", account_id=target.account_id, symbol=symbol)


async def _execute_signal_for_target(
    session,
    target: ExecutionTarget,
    signal: Dict[str, Any],
    amount_usdt: float,
    sandbox: bool,
) -> Dict[str, Any]:
    """
    对单个绑定账户执行信号：创建带 settlement 的 LiveTrader，下单并可选设置止盈止损。
    
    ★ Step 2 升级：支持限价单 (entry_mode=limit)
      - 限价单：挂单到交易所，追踪到 _pending_limit_orders，由 monitor_loop 管理生命周期
      - 市价单：原有逻辑不变
    
    仅服务端使用，勿暴露 target 中的凭证。
    """
    symbol = signal.get("symbol", "")
    side_str = signal.get("side", "BUY")
    entry_price = float(signal.get("entry_price") or 0)
    stop_loss = float(signal.get("stop_loss") or 0)
    take_profit = float(signal.get("take_profit") or 0)
    leverage = int(signal.get("leverage") or 0)
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
        # 根据信号类型映射 trade_type
        sig_type = (signal.get("signal_type") or "OPEN").upper()
        trade_type = {"OPEN": "OPEN", "CLOSE": "CLOSE", "ADD": "ADD", "REDUCE": "REDUCE",
                      "HEDGE": "OPEN", "GRID": "OPEN"}.get(sig_type, "OPEN")
        close_reason = signal.get("close_reason") if trade_type == "CLOSE" else None

        # ── Step 2: 根据 entry_mode 决定市价/限价 ──
        indicators = signal.get("indicators") or {}
        entry_mode = indicators.get("entry_mode", "market")
        use_limit = (entry_mode == "limit" and trade_type == "OPEN")
        
        order_type = OrderType.LIMIT if use_limit else OrderType.MARKET

        order_result = await trader.create_order(
            symbol=symbol,
            side=order_side,
            order_type=order_type,
            amount_usdt=amount_usdt,
            price=entry_price,
            leverage=leverage or None,
            signal_id=signal.get("signal_id"),
            stop_loss=stop_loss or None if not use_limit else None,     # 限价单成交前不设SL
            take_profit=take_profit or None if not use_limit else None,  # 限价单成交前不设TP
            trade_type=trade_type,
            close_reason=close_reason,
        )
        
        if use_limit:
            # ── 限价单：不会立即成交，追踪到 _pending_limit_orders ──
            strategy_code = signal.get("strategy") or signal.get("strategy_code") or ""
            pending_key = f"{strategy_code}:{symbol}"
            exchange_order_id = getattr(order_result, "exchange_order_id", None) or getattr(order_result, "order_id", None)
            
            with _state_lock:
                _pending_limit_orders[pending_key] = {
                    "order_id": getattr(order_result, "order_id", None),
                    "exchange_order_id": exchange_order_id,
                    "symbol": symbol,
                    "side": side_str,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "strategy_code": strategy_code,
                    "target": target,
                    "amount_usdt": amount_usdt,
                    "leverage": leverage,
                    "placed_at": datetime.now(),
                    "retest_bars": int(indicators.get("retest_bars", 20)),
                    "timeframe": signal.get("timeframe", "15m"),
                    "confirm_after_fill": bool(indicators.get("confirm_after_fill", False)),
                    "post_fill_confirm_bars": int(indicators.get("post_fill_confirm_bars", 3)),
                }
            
            # ── DB 持久化 ──
            _db_save_pending(pending_key, _pending_limit_orders[pending_key])
            
            log.info("限价单已挂出",
                     strategy=strategy_code, symbol=symbol, side=side_str,
                     price=entry_price, exchange_order_id=exchange_order_id)
            
            # ── 推送通知：限价单已挂出 ──
            if NOTIFY_ON_SIGNAL:
                side_emoji = "🟢" if side_str.upper() == "BUY" else "🔴"
                tf = signal.get("timeframe", "15m")
                retest_bars = int(indicators.get("retest_bars", 20))
                timeout_min = _timeframe_to_minutes(tf) * retest_bars
                notifier.send(
                    title="📋 限价单已挂出",
                    content=(
                        f"{side_emoji} <b>{side_str} {symbol}</b>\n\n"
                        f"💰 挂单价: <code>{entry_price:,.2f}</code>\n"
                        f"🛑 止损: <code>{stop_loss:,.2f}</code>\n"
                        f"🎯 止盈: <code>{take_profit:,.2f}</code>\n"
                        f"💵 金额: <code>{amount_usdt:,.0f} USDT</code>\n\n"
                        f"⏳ 超时: {timeout_min}分钟后自动撤单\n"
                        f"📝 策略: {strategy_code}\n"
                        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    ),
                )
            
            await trader.close()
            return {
                "account_id": target.account_id,
                "user_id": target.user_id,
                "success": True,
                "order_type": "LIMIT",
                "order_id": getattr(order_result, "order_id", None),
                "exchange_order_id": exchange_order_id,
                "entry_price": entry_price,
                "status": "PENDING",
            }
        
        # ── 市价单：原有逻辑 ──
        ok = order_result.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)
        filled_qty = order_result.filled_quantity or 0
        filled_price = order_result.filled_price or entry_price

        error_msg = None
        if not ok:
            error_msg = getattr(order_result, "error_message", None) or getattr(order_result, "error_code", None)
            if error_msg:
                log.warning("order not filled", account_id=target.account_id,
                            exchange=target.exchange, status=str(order_result.status),
                            error_code=getattr(order_result, "error_code", None),
                            error_message=getattr(order_result, "error_message", None))

        # SL/TP 写入持仓表，由 position_monitor 到价平仓
        sl_tp_ok = False
        if ok and (stop_loss or take_profit) and filled_qty > 0:
            sl_tp_ok = True
        if ok and filled_qty > 0:
            try:
                strategy_code = signal.get("strategy") or signal.get("strategy_code") or ""
                _write_sl_tp_to_position(
                    session, target, symbol, order_side,
                    filled_price, stop_loss, take_profit, strategy_code,
                )
            except Exception as e:
                log.warning("write sl/tp to position failed", account_id=target.account_id, error=str(e))
        await trader.close()
        return {
            "account_id": target.account_id,
            "user_id": target.user_id,
            "success": ok,
            "order_id": getattr(order_result, "order_id", None),
            "filled_quantity": filled_qty,
            "filled_price": filled_price,
            "sl_tp_set": sl_tp_ok,
            "error": error_msg,
        }
    except Exception as e:
        try:
            await trader.close()
        except Exception:
            pass
        log.error("execute_signal_for_target failed", account_id=target.account_id, error=str(e))
        return {"account_id": target.account_id, "user_id": target.user_id, "success": False, "error": str(e)}


RISK_MODE_PCT = {1: 0.01, 2: 0.015, 3: 0.02}


def _resolve_amount_leverage_for_tenant(repo, strategy, tenant_id: int):
    """
    按租户解析下单金额与杠杆：
    优先级：dim_tenant_strategy 覆盖 > dim_strategy 默认
    如果设置了 capital + risk_mode，则自动计算 amount_usdt = capital × risk_pct × leverage。
    返回 (amount_usdt, leverage, capital, risk_pct)。
    后两个值供"以损定仓"模式使用。
    """
    if not strategy:
        return STRATEGY_DISPATCH_AMOUNT, 0, 0, 0.01

    # 主策略默认值
    base_capital = float(getattr(strategy, "capital", 0) or 0)
    base_leverage = int(strategy.leverage or 0)
    base_risk_mode = int(getattr(strategy, "risk_mode", 1) or 1)
    base_amount = float(strategy.amount_usdt or 0)

    # 租户覆盖
    ts = repo.get_tenant_strategy(tenant_id, strategy.id)
    if ts:
        capital = float(ts.capital) if getattr(ts, "capital", None) is not None else base_capital
        leverage = int(ts.leverage) if ts.leverage is not None else base_leverage
        risk_mode = int(getattr(ts, "risk_mode", None) or 0) if getattr(ts, "risk_mode", None) is not None else base_risk_mode
        amount_fallback = float(ts.amount_usdt) if ts.amount_usdt is not None else base_amount
    else:
        capital = base_capital
        leverage = base_leverage
        risk_mode = base_risk_mode
        amount_fallback = base_amount

    pct = RISK_MODE_PCT.get(risk_mode, 0.01)

    # 如果设了 capital，自动计算（固定金额模式，兜底值）
    if capital > 0 and leverage > 0:
        amount = round(capital * pct * leverage, 2)
    else:
        amount = amount_fallback

    amount = amount if amount > 0 else STRATEGY_DISPATCH_AMOUNT
    return amount, leverage, capital, pct


def _calc_risk_based_amount(
    capital: float,
    risk_pct: float,
    entry_price: float,
    stop_loss: float,
    max_amount_cap: float = 0,
) -> float:
    """
    以损定仓：根据止损距离反推下单金额。
    
    公式:
        max_loss = capital × risk_pct          （每笔最大可接受亏损）
        sl_distance = |entry - sl| / entry     （止损距离百分比）
        amount_usdt = max_loss / sl_distance   （名义下单金额）
    
    安全阀:
        1. 止损距离 < 0.1% 视为无效，按 0.1% 兜底
        2. 下单金额不超过本金的 3 倍（防止止损太窄导致仓位过大）
    
    示例（本金 1000U, risk_pct 1%）:
        止损距离 1%  → amount = 10 / 0.01 = 1000U → 亏损 10U ✓
        止损距离 2%  → amount = 10 / 0.02 = 500U  → 亏损 10U ✓
        止损距离 5%  → amount = 10 / 0.05 = 200U  → 亏损 10U ✓
    """
    if capital <= 0 or risk_pct <= 0 or entry_price <= 0 or stop_loss <= 0:
        return 0

    max_loss = capital * risk_pct
    sl_distance_pct = abs(entry_price - stop_loss) / entry_price

    # 安全阀 1: 止损距离太窄（< 0.1%），用 0.1% 兜底
    if sl_distance_pct < 0.001:
        sl_distance_pct = 0.001

    amount = max_loss / sl_distance_pct

    # 安全阀 2: 不超过本金的 3 倍
    cap = max_amount_cap if max_amount_cap > 0 else capital * 3
    amount = min(amount, cap)

    return round(amount, 2)


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

        # 按 execution_node_id 分组（所有 target 必定 node_id > 0，已在 get_execution_targets 中过滤）
        by_node = defaultdict(list)
        for t in targets:
            nid = t.execution_node_id or 0
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
            # 优先级: 用户绑定参数 > 租户配置 > 策略默认
            if target.binding_amount_usdt > 0:
                # 用户绑定了本金+杠杆+风险档位，直接用计算好的 amount_usdt
                amount = target.binding_amount_usdt
                leverage = target.binding_leverage if target.binding_leverage > 0 else 20
                b_capital = float(getattr(target, "binding_capital", 0) or 0)
                b_risk_mode = int(getattr(target, "binding_risk_mode", 1) or 1)
                b_risk_pct = RISK_MODE_PCT.get(b_risk_mode, 0.01)
            else:
                amount, leverage, b_capital, b_risk_pct = _resolve_amount_leverage_for_tenant(repo, strategy, target.tenant_id)

            # ── 以损定仓：如果策略配置了 risk_based_sizing 且信号有 SL，
            #    按「每笔固定亏损 = capital × risk_pct」反推仓位大小 ──
            strat_cfg = strategy.get_config() if strategy else {}
            if strat_cfg.get("risk_based_sizing") and b_capital > 0 and b_risk_pct > 0:
                sig_entry = float(signal.get("entry_price", 0))
                sig_sl = float(signal.get("stop_loss", 0))
                if sig_entry > 0 and sig_sl > 0:
                    risk_amount = _calc_risk_based_amount(
                        capital=b_capital,
                        risk_pct=b_risk_pct,
                        entry_price=sig_entry,
                        stop_loss=sig_sl,
                    )
                    if risk_amount > 0:
                        sl_dist = abs(sig_entry - sig_sl) / sig_entry * 100
                        max_loss = b_capital * b_risk_pct
                        log.info(
                            "以损定仓",
                            account_id=target.account_id,
                            capital=b_capital,
                            risk_pct=f"{b_risk_pct*100:.1f}%",
                            max_loss=f"{max_loss:.2f}U",
                            sl_distance=f"{sl_dist:.2f}%",
                            old_amount=amount,
                            new_amount=risk_amount,
                        )
                        amount = risk_amount

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
                # 优先级: 用户绑定参数 > 租户配置 > 策略默认
                if t.binding_amount_usdt > 0:
                    amount = t.binding_amount_usdt
                    leverage = t.binding_leverage if t.binding_leverage > 0 else 20
                    r_capital = float(getattr(t, "binding_capital", 0) or 0)
                    r_risk_mode = int(getattr(t, "binding_risk_mode", 1) or 1)
                    r_risk_pct = RISK_MODE_PCT.get(r_risk_mode, 0.01)
                else:
                    amount, leverage, r_capital, r_risk_pct = _resolve_amount_leverage_for_tenant(repo, strategy, t.tenant_id)

                # 以损定仓（远程节点）
                strat_cfg_r = strategy.get_config() if strategy else {}
                if strat_cfg_r.get("risk_based_sizing") and r_capital > 0 and r_risk_pct > 0:
                    sig_entry_r = float(signal.get("entry_price", 0))
                    sig_sl_r = float(signal.get("stop_loss", 0))
                    if sig_entry_r > 0 and sig_sl_r > 0:
                        risk_amount_r = _calc_risk_based_amount(
                            capital=r_capital, risk_pct=r_risk_pct,
                            entry_price=sig_entry_r, stop_loss=sig_sl_r,
                        )
                        if risk_amount_r > 0:
                            amount = risk_amount_r

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

        # ── 为每个账户写入 EXECUTED 信号事件 ──
        _sig_id = signal.get("signal_id", "")
        for r in results:
            if r.get("skipped"):
                continue  # 跳过的不记录
            try:
                _write_signal_event(
                    signal_id=_sig_id,
                    event_type="EXECUTED" if r.get("success") else "FAILED",
                    status="executed" if r.get("success") else "failed",
                    source_service="signal-monitor",
                    account_id=r.get("account_id"),
                    detail={
                        "strategy": signal.get("strategy"),
                        "order_id": r.get("order_id"),
                        "filled_quantity": r.get("filled_quantity"),
                        "filled_price": r.get("filled_price"),
                        "symbol": symbol,
                        "side": signal.get("side"),
                    },
                    error_message=r.get("error") if not r.get("success") else None,
                )
            except Exception:
                pass  # 不影响主流程

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
    
    # ★ 输入验证：防止非法值导致崩溃或错误交易
    side_val = str(data["side"]).upper()
    if side_val not in ("BUY", "SELL"):
        return jsonify({"success": False, "error": f"无效 side: {data['side']}，仅支持 BUY/SELL"})
    try:
        entry_price = float(data["entry_price"])
        stop_loss = float(data["stop_loss"])
        take_profit = float(data["take_profit"])
    except (ValueError, TypeError) as e:
        return jsonify({"success": False, "error": f"价格字段格式错误: {e}"})
    if entry_price <= 0:
        return jsonify({"success": False, "error": f"entry_price 必须大于 0，当前: {entry_price}"})
    if stop_loss < 0 or take_profit < 0:
        return jsonify({"success": False, "error": "stop_loss 和 take_profit 不能为负数"})

    signal = {
        "symbol": str(data["symbol"]).strip(),
        "side": side_val,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confidence": int(data.get("confidence", 80)),
        "strategy": data.get("strategy"),
        "signal_id": data.get("signal_id"),
        "leverage": int(data.get("leverage") or 0) or None,
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


async def _close_position_by_account(session, account_id: int, symbol: str, position_side: Optional[str] = None) -> Dict[str, Any]:
    """
    按账户手动平仓：用该账户的 API 平掉该账户下该标的的持仓。
    不依赖全局 auto_trader，解决「交易所 API 未配置」问题。
    """
    from libs.member.models import ExchangeAccount
    from libs.position.models import Position
    from libs.position.monitor import _fetch_prices_batch, _normalize_exchange_for_ccxt

    account = session.query(ExchangeAccount).filter(ExchangeAccount.id == account_id, ExchangeAccount.status == 1).first()
    if not account:
        return {"success": False, "error": "账户不存在或已禁用"}

    q = session.query(Position).filter(
        Position.account_id == account_id,
        Position.symbol == symbol,
        Position.status == "OPEN",
        Position.quantity > 0,
    )
    if position_side:
        q = q.filter(Position.position_side == position_side)
    positions = q.all()
    if not positions:
        return {"success": False, "error": "未找到该账户下该标的的持仓"}

    position = positions[0]
    exchange_name = account.exchange or "binance"
    sym = position.symbol
    prices = await _fetch_prices_batch({exchange_name: {sym}})
    key_orig = f"{exchange_name}:{sym}"
    key_ccxt = f"{_normalize_exchange_for_ccxt(exchange_name)}:{sym}"
    current_price = prices.get(key_orig) or prices.get(key_ccxt)
    if not current_price or current_price <= 0:
        return {"success": False, "error": "无法获取该标的当前价格"}

    settlement_svc = TradeSettlementService(
        session=session,
        tenant_id=account.tenant_id,
        account_id=account.id,
        currency="USDT",
    )
    sandbox = config.get_bool("exchange_sandbox", True)
    trader = LiveTrader(
        exchange=account.exchange,
        api_key=account.api_key,
        api_secret=account.api_secret,
        passphrase=account.passphrase or "",
        sandbox=sandbox,
        market_type=position.market_type or "future",
        settlement_service=settlement_svc,
        tenant_id=account.tenant_id,
        account_id=account.id,
    )
    try:
        side = (position.position_side or "LONG").upper()
        close_side = OrderSide.SELL if side == "LONG" else OrderSide.BUY
        amount_usdt = float(position.quantity) * current_price
        pm_signal_id = gen_id("MC")
        result = await trader.create_order(
            symbol=position.symbol,
            side=close_side,
            order_type=OrderType.MARKET,
            amount_usdt=amount_usdt,
            price=current_price,
            signal_id=pm_signal_id,
            trade_type="CLOSE",
            close_reason="MANUAL",
            position_side=side,  # 必传，否则结算无法匹配到正确的持仓行（LONG/SHORT）
        )
        ok = result.status in (OrderStatus.FILLED, OrderStatus.PARTIAL)
        if ok:
            # 只更新 close_reason，不覆盖 quantity/status（结算已将其置为 0 和 CLOSED）
            from sqlalchemy import update as sql_update
            session.execute(
                sql_update(Position)
                .where(Position.position_id == position.position_id)
                .values(close_reason="MANUAL", stop_loss=None, take_profit=None, updated_at=datetime.now())
            )
            session.flush()
            log.info("手动平仓成功", account_id=account_id, symbol=symbol, filled_qty=result.filled_quantity)
        else:
            log.warning("手动平仓未成交", account_id=account_id, symbol=symbol, status=result.status.value)
        return {
            "success": ok,
            "message": "平仓成功" if ok else (result.error_message or "平仓未成交"),
            "filled_quantity": getattr(result, "filled_quantity", 0),
            "filled_price": getattr(result, "filled_price", 0),
        }
    finally:
        try:
            await trader.close()
        except Exception:
            pass


@app.route("/api/trading/close", methods=["POST"])
def trading_close_position():
    """平仓。若请求带 account_id 则按该账户 API 平仓（多账户场景）；否则用全局 auto_trader。"""
    data = request.get_json() or {}
    symbol = data.get("symbol")
    account_id = data.get("account_id")
    position_side = data.get("position_side")

    if not symbol:
        return jsonify({"success": False, "error": "缺少 symbol"})

    # 按账户平仓：使用该账户的 API，不依赖全局配置
    if account_id is not None:
        try:
            session = get_session()
            try:
                result = run_async(_close_position_by_account(session, int(account_id), symbol.strip(), position_side))
                session.commit()
            except Exception as e:
                session.rollback()
                log.error("按账户平仓失败", account_id=account_id, symbol=symbol, error=str(e))
                result = {"success": False, "error": str(e)}
            finally:
                session.close()
            return jsonify(result)
        except Exception as e:
            log.error("按账户平仓异常", error=str(e))
            return jsonify({"success": False, "error": str(e)})

    # 兼容：无 account_id 时使用全局 auto_trader（单账户）
    trader = get_auto_trader()
    if trader is None:
        return jsonify({"success": False, "error": "交易所 API 未配置（请传 account_id 按持仓账户平仓，或在 signal-monitor 配置 exchange_api_key）"})

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


def _recover_pending_limit_orders():
    """
    程序重启后从 DB 恢复 pending 限价单到内存，继续追踪生命周期。
    
    流程：
    1. 从 fact_pending_limit_order 表读取 PENDING/CONFIRMING 状态的记录
    2. 重建 ExecutionTarget（通过 account_id 查交易所凭证）
    3. 恢复到 _pending_limit_orders / _awaiting_confirmation 内存字典
    4. 下一轮 monitor_loop 会自动检查这些挂单的交易所状态
    """
    global _pending_limit_orders, _awaiting_confirmation
    try:
        recovered = _db_load_pending_orders()
        if recovered:
            with _state_lock:
                _pending_limit_orders.update(recovered)
            log.info(f"从DB恢复 {len(recovered)} 个pending限价单")
            if NOTIFY_ON_SIGNAL:
                total = len(recovered) + len(_awaiting_confirmation)
                if total > 0:
                    notifier.send(
                        title="🔄 重启恢复",
                        content=f"程序重启，已从数据库恢复 {total} 个限价单追踪。",
                    )
        else:
            log.info("无pending限价单需要恢复")
    except Exception as e:
        log.error("恢复pending限价单失败", error=str(e))


def _auto_start_monitor():
    """
    若配置了 auto_trade_enabled=true，Flask 进程启动后自动开启监控循环，
    无需手动 POST /api/start。同时启动自动同步线程。
    """
    global monitor_thread, monitor_state
    with _state_lock:
        if monitor_state["running"]:
            return
        monitor_state["running"] = True
    auto_enabled = config.get_bool("auto_trade_enabled", False)
    if not auto_enabled:
        with _state_lock:
            monitor_state["running"] = False
        log.info("auto_trade_enabled=false，监控不自动启动（可手动 POST /api/start）")
        return
    # 恢复/清理重启前的孤立限价单
    _recover_pending_limit_orders()
    # 启动信号监控
    stop_event.clear()
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    log.info("监控已自动启动 (auto_trade_enabled=true)")
    # 启动自动同步线程
    _sync_stop_event.clear()
    sync_thread = threading.Thread(target=_sync_loop, daemon=True)
    sync_thread.start()
    # 启动持仓 SL/TP 自管监控（不在交易所挂单，自己监控到价平仓）
    if not EXCHANGE_SL_TP:
        from libs.position.monitor import start_position_monitor, set_on_sl_triggered, set_on_close_notify
        # 注册止损冷却回调：止损平仓后自动设置策略冷却
        set_on_sl_triggered(lambda symbol, strategy: set_cooldown(symbol, strategy))
        # 注册平仓通知回调：SL/TP 平仓后推送 Telegram
        def _notify_close(symbol, side, trigger_type, entry_price, exit_price, pnl, strategy_code):
            emoji = "🟢" if pnl >= 0 else "🔴"
            tp_sl = "止盈 ✅" if trigger_type == "TP" else "止损 ❌"
            pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
            notifier.send(
                title=f"{emoji} {tp_sl} | {symbol}",
                content=(
                    f"策略: {strategy_code}\n"
                    f"方向: {'做多' if side == 'LONG' else '做空'}\n"
                    f"入场: {entry_price:.4f}\n"
                    f"出场: {exit_price:.4f}\n"
                    f"盈亏: {pnl_str}"
                ),
            )
        set_on_close_notify(_notify_close)
        pm_interval = config.get_float("position_monitor_interval", 5.0)
        start_position_monitor(interval=pm_interval)
        log.info("position_monitor 已启动（自管SL/TP模式）", interval=pm_interval)


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
