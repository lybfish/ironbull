"""
Auto Trader - 自动交易执行器

根据策略信号自动执行交易
支持 TradeSettlementService 集成，实现完整交易闭环：
  OrderTrade → Position → Ledger

安全机制：
1. 需要手动启用自动交易
2. 单笔最大金额限制
3. 每日最大交易次数限制
4. 最大持仓数量限制
5. 支持"仅通知"模式
"""

import asyncio
from datetime import datetime, date
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

from libs.core import get_config, get_logger, gen_id
from libs.notify import TelegramNotifier
from .live_trader import LiveTrader
from .base import OrderSide, OrderType, OrderStatus

# 延迟导入避免循环依赖
if TYPE_CHECKING:
    from libs.order_trade import OrderTradeService
    from libs.trading.settlement import TradeSettlementService

logger = get_logger("auto-trader")
_config = get_config()


class TradeMode(Enum):
    """交易模式"""
    NOTIFY_ONLY = "notify_only"     # 仅通知，不执行
    CONFIRM_EACH = "confirm_each"    # 每笔确认
    AUTO_EXECUTE = "auto_execute"    # 自动执行


@dataclass
class TradeRecord:
    """交易记录"""
    trade_id: str
    timestamp: datetime
    symbol: str
    side: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    sl_order_id: Optional[str] = None      # 止损单ID
    tp_order_id: Optional[str] = None      # 止盈单ID
    status: str = "pending"  # pending, filled, failed, canceled
    pnl: Optional[float] = None
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "order_id": self.order_id,
            "exchange_order_id": self.exchange_order_id,
            "sl_order_id": self.sl_order_id,
            "tp_order_id": self.tp_order_id,
            "status": self.status,
            "pnl": self.pnl,
        }


@dataclass
class RiskLimits:
    """风控限制（默认值从 config 读取，创建实例时可覆盖）"""
    max_trade_amount: float = _config.get_float("risk_max_trade_amount", 100.0)
    max_daily_trades: int = _config.get_int("risk_max_daily_trades", 10)
    max_open_positions: int = _config.get_int("risk_max_open_positions", 3)
    max_daily_loss: float = _config.get_float("risk_max_daily_loss", 200.0)
    min_confidence: int = _config.get_int("risk_min_confidence", 70)


class AutoTrader:
    """
    自动交易执行器
    
    使用示例：
        trader = AutoTrader(
            exchange="binance",
            api_key="xxx",
            api_secret="xxx",
            mode=TradeMode.NOTIFY_ONLY,  # 先用通知模式测试
        )
        
        # 处理信号
        await trader.process_signal(signal)
        
        # 启用自动交易（谨慎！）
        trader.set_mode(TradeMode.AUTO_EXECUTE)
    """
    
    def __init__(
        self,
        exchange: str = "binance",
        api_key: str = "",
        api_secret: str = "",
        passphrase: str = "",      # OKX 需要
        sandbox: bool = True,      # 默认使用测试网
        market_type: str = "future",  # 市场类型: spot / future
        mode: TradeMode = TradeMode.NOTIFY_ONLY,
        risk_limits: Optional[RiskLimits] = None,
        # 完整结算集成（推荐）
        settlement_service: Optional["TradeSettlementService"] = None,
        # OrderTrade 集成（旧版兼容）
        order_trade_service: Optional["OrderTradeService"] = None,
        tenant_id: Optional[int] = None,
        account_id: Optional[int] = None,
    ):
        self.exchange_name = exchange
        self.sandbox = sandbox
        self.market_type = market_type
        self.mode = mode
        self.risk_limits = risk_limits or RiskLimits()
        
        # 交易所客户端（延迟初始化）
        self._trader: Optional[LiveTrader] = None
        self._api_key = api_key
        self._api_secret = api_secret
        self._passphrase = passphrase
        
        # 结算服务（完整交易闭环：OrderTrade → Position → Ledger）
        self._settlement_service = settlement_service
        
        # OrderTrade 集成（旧版兼容）
        self._order_trade_service = order_trade_service
        self._tenant_id = tenant_id
        self._account_id = account_id
        
        # 通知器
        self.notifier = TelegramNotifier()
        
        # 状态
        self.enabled = False
        self.open_positions: Dict[str, TradeRecord] = {}  # symbol -> TradeRecord
        self.trade_history: List[TradeRecord] = []
        
        # 每日统计
        self._daily_trades = 0
        self._daily_pnl = 0.0
        self._last_trade_date: Optional[date] = None
        
        logger.info(
            "auto trader initialized",
            exchange=exchange,
            sandbox=sandbox,
            mode=mode.value,
            settlement_enabled=settlement_service is not None,
            order_trade_enabled=order_trade_service is not None,
        )
    
    def _get_trader(self) -> LiveTrader:
        """获取或创建交易所客户端"""
        if self._trader is None:
            if not self._api_key or not self._api_secret:
                raise ValueError("API credentials not configured")
            
            self._trader = LiveTrader(
                exchange=self.exchange_name,
                api_key=self._api_key,
                api_secret=self._api_secret,
                passphrase=self._passphrase,
                sandbox=self.sandbox,
                market_type=self.market_type,
                # 优先使用完整结算服务
                settlement_service=self._settlement_service,
                # 旧版兼容
                order_trade_service=self._order_trade_service,
                tenant_id=self._tenant_id,
                account_id=self._account_id,
            )
        return self._trader
    
    def _reset_daily_stats(self):
        """重置每日统计"""
        today = date.today()
        if self._last_trade_date != today:
            self._daily_trades = 0
            self._daily_pnl = 0.0
            self._last_trade_date = today
            logger.info("daily stats reset")
    
    def set_mode(self, mode: TradeMode):
        """设置交易模式"""
        old_mode = self.mode
        self.mode = mode
        logger.info("trade mode changed", old=old_mode.value, new=mode.value)
        
        if mode == TradeMode.AUTO_EXECUTE:
            self.notifier.send_alert(
                "mode_change",
                "⚠️ 自动交易模式已启用！\n\n"
                f"交易所: {self.exchange_name}\n"
                f"测试网: {'是' if self.sandbox else '否'}\n"
                f"单笔限额: {self.risk_limits.max_trade_amount} USDT\n"
                f"每日限次: {self.risk_limits.max_daily_trades}",
                level="warning",
            )
    
    def enable(self):
        """启用自动交易"""
        self.enabled = True
        logger.info("auto trader enabled")
    
    def disable(self):
        """禁用自动交易"""
        self.enabled = False
        logger.info("auto trader disabled")
    
    def _check_risk_limits(self, signal: Dict[str, Any]) -> tuple[bool, str]:
        """
        检查风控限制
        
        Returns:
            (是否通过, 原因)
        """
        self._reset_daily_stats()
        
        # 1. 检查置信度
        confidence = signal.get("confidence", 0)
        if confidence < self.risk_limits.min_confidence:
            return False, f"置信度不足: {confidence}% < {self.risk_limits.min_confidence}%"
        
        # 2. 检查每日交易次数
        if self._daily_trades >= self.risk_limits.max_daily_trades:
            return False, f"已达每日交易上限: {self._daily_trades}/{self.risk_limits.max_daily_trades}"
        
        # 3. 检查持仓数量
        if len(self.open_positions) >= self.risk_limits.max_open_positions:
            return False, f"已达最大持仓数: {len(self.open_positions)}/{self.risk_limits.max_open_positions}"
        
        # 4. 检查是否已有该品种持仓
        symbol = signal.get("symbol", "")
        if symbol in self.open_positions:
            return False, f"已有 {symbol} 持仓"
        
        # 5. 检查每日亏损
        if self._daily_pnl <= -self.risk_limits.max_daily_loss:
            return False, f"已达每日亏损上限: {self._daily_pnl:.2f}/{self.risk_limits.max_daily_loss}"
        
        return True, ""
    
    def _calc_quantity(self, signal: Dict[str, Any]) -> float:
        """
        计算下单数量
        
        基于固定金额计算
        """
        entry_price = signal.get("entry_price", 0)
        if entry_price <= 0:
            return 0
        
        # 使用最大交易金额
        amount = self.risk_limits.max_trade_amount
        quantity = amount / entry_price
        
        # 使用交易所精度截断（通过 LiveTrader 处理），此处仅做粗略过滤
        if quantity <= 0:
            return 0
        
        return round(quantity, 6)
    
    async def process_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理交易信号
        
        Args:
            signal: 信号字典
                - symbol: 交易对
                - side: BUY/SELL
                - entry_price: 入场价
                - stop_loss: 止损
                - take_profit: 止盈
                - confidence: 置信度
        
        Returns:
            处理结果
        """
        result = {
            "success": False,
            "action": "none",
            "message": "",
            "trade_id": None,
        }
        
        symbol = signal.get("symbol", "")
        side = signal.get("side", "")
        entry_price = signal.get("entry_price", 0)
        stop_loss = signal.get("stop_loss", 0)
        take_profit = signal.get("take_profit", 0)
        confidence = signal.get("confidence", 0)
        
        logger.info(
            "processing signal",
            symbol=symbol,
            side=side,
            price=entry_price,
            confidence=confidence,
            mode=self.mode.value,
        )
        
        # 1. 风控检查
        passed, reason = self._check_risk_limits(signal)
        if not passed:
            result["message"] = f"风控拦截: {reason}"
            logger.warning("signal blocked by risk", reason=reason)
            return result
        
        # 2. 计算数量
        quantity = self._calc_quantity(signal)
        if quantity <= 0:
            result["message"] = "计算数量无效"
            return result
        
        trade_id = gen_id("trd_")
        
        # 3. 根据模式处理
        if self.mode == TradeMode.NOTIFY_ONLY:
            # 仅通知
            result["action"] = "notify_only"
            result["message"] = f"仅通知模式 - {side} {symbol} @ {entry_price}"
            result["success"] = True
            logger.info("notify only mode, skipping execution")
            
        elif self.mode == TradeMode.CONFIRM_EACH:
            # 需要确认（这里先发通知，实际确认逻辑需要UI支持）
            result["action"] = "pending_confirm"
            result["message"] = f"等待确认 - {side} {symbol} @ {entry_price}"
            result["trade_id"] = trade_id
            
            # 发送确认通知
            self.notifier.send_alert(
                "trade_confirm",
                f"📝 交易确认请求\n\n"
                f"{side} {symbol}\n"
                f"价格: {entry_price}\n"
                f"数量: {quantity}\n"
                f"金额: {entry_price * quantity:.2f} USDT\n"
                f"止损: {stop_loss}\n"
                f"止盈: {take_profit}\n\n"
                f"请通过 API 确认执行",
                level="warning",
            )
            logger.info("waiting for confirmation", trade_id=trade_id)
            
        elif self.mode == TradeMode.AUTO_EXECUTE:
            if not self.enabled:
                result["message"] = "自动交易未启用"
                return result
            
            # 自动执行
            try:
                trader = self._get_trader()
                
                order_side = OrderSide.BUY if side == "BUY" else OrderSide.SELL
                
                # 获取 signal_id（用于 OrderTrade 关联）
                signal_id = signal.get("signal_id")
                
                # 市价单开仓
                order_result = await trader.create_order(
                    symbol=symbol,
                    side=order_side,
                    order_type=OrderType.MARKET,
                    quantity=quantity,
                    signal_id=signal_id,  # 传递 signal_id
                )
                
                if order_result.status in [OrderStatus.FILLED, OrderStatus.PARTIAL]:
                    filled_qty = order_result.filled_quantity
                    filled_price = order_result.filled_price or entry_price
                    
                    # 设置止盈止损单
                    sl_tp_results = {}
                    if stop_loss or take_profit:
                        try:
                            sl_tp_results = await trader.set_sl_tp(
                                symbol=symbol,
                                side=order_side,
                                quantity=filled_qty,
                                stop_loss=stop_loss,
                                take_profit=take_profit,
                            )
                            logger.info(
                                "sl/tp orders set",
                                sl_status=sl_tp_results.get("sl", {}).status if sl_tp_results.get("sl") else None,
                                tp_status=sl_tp_results.get("tp", {}).status if sl_tp_results.get("tp") else None,
                            )
                        except Exception as e:
                            logger.error("failed to set sl/tp", error=str(e))
                    
                    # 记录交易
                    trade = TradeRecord(
                        trade_id=trade_id,
                        timestamp=datetime.now(),
                        symbol=symbol,
                        side=side,
                        quantity=filled_qty,
                        entry_price=filled_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        order_id=order_result.order_id,
                        exchange_order_id=order_result.exchange_order_id,
                        status="filled",
                    )
                    
                    # 保存止盈止损订单ID
                    if sl_tp_results.get("sl"):
                        trade.sl_order_id = sl_tp_results["sl"].exchange_order_id
                    if sl_tp_results.get("tp"):
                        trade.tp_order_id = sl_tp_results["tp"].exchange_order_id
                    
                    self.open_positions[symbol] = trade
                    self.trade_history.append(trade)
                    self._daily_trades += 1
                    
                    result["success"] = True
                    result["action"] = "executed"
                    result["trade_id"] = trade_id
                    result["message"] = f"已执行 {side} {symbol} @ {filled_price}"
                    
                    # 止盈止损状态
                    sl_status = "✅" if sl_tp_results.get("sl") and sl_tp_results["sl"].status == OrderStatus.OPEN else "❌"
                    tp_status = "✅" if sl_tp_results.get("tp") and sl_tp_results["tp"].status == OrderStatus.OPEN else "❌"
                    
                    # 发送成交通知
                    self.notifier.send_alert(
                        "position_opened",
                        f"✅ 订单已成交\n\n"
                        f"{side} {symbol}\n"
                        f"成交价: {filled_price}\n"
                        f"数量: {filled_qty}\n"
                        f"止损: {stop_loss} {sl_status}\n"
                        f"止盈: {take_profit} {tp_status}",
                        level="info",
                    )
                    
                    logger.info(
                        "order executed",
                        trade_id=trade_id,
                        filled_price=filled_price,
                        filled_qty=order_result.filled_quantity,
                    )
                    
                else:
                    result["message"] = f"订单失败: {order_result.error_message}"
                    logger.error("order failed", error=order_result.error_message)
                    
            except Exception as e:
                result["message"] = f"执行异常: {str(e)}"
                logger.error("execution error", error=str(e))
        
        return result
    
    async def close_position(self, symbol: str, reason: str = "manual") -> Dict[str, Any]:
        """
        平仓
        
        Args:
            symbol: 交易对
            reason: 平仓原因 (manual/stop_loss/take_profit)
        """
        if symbol not in self.open_positions:
            return {"success": False, "message": f"无 {symbol} 持仓"}
        
        trade = self.open_positions[symbol]
        
        if self.mode != TradeMode.AUTO_EXECUTE or not self.enabled:
            # 非自动模式，只更新状态
            del self.open_positions[symbol]
            return {"success": True, "message": "持仓已移除（非自动模式）"}
        
        try:
            trader = self._get_trader()
            
            # 反向平仓
            close_side = OrderSide.SELL if trade.side == "BUY" else OrderSide.BUY
            
            order_result = await trader.create_order(
                symbol=symbol,
                side=close_side,
                order_type=OrderType.MARKET,
                quantity=trade.quantity,
            )
            
            if order_result.status in [OrderStatus.FILLED, OrderStatus.PARTIAL]:
                exit_price = order_result.filled_price or 0
                
                # 计算盈亏
                if trade.side == "BUY":
                    pnl = (exit_price - trade.entry_price) * trade.quantity
                else:
                    pnl = (trade.entry_price - exit_price) * trade.quantity
                
                trade.exit_price = exit_price
                trade.exit_time = datetime.now()
                trade.pnl = pnl
                trade.status = "closed"
                
                self._daily_pnl += pnl
                
                del self.open_positions[symbol]
                
                # 发送平仓通知
                pnl_emoji = "📈" if pnl >= 0 else "📉"
                self.notifier.send_alert(
                    "position_closed",
                    f"{pnl_emoji} 仓位已平仓\n\n"
                    f"{trade.side} {symbol}\n"
                    f"入场: {trade.entry_price}\n"
                    f"出场: {exit_price}\n"
                    f"盈亏: {pnl:+.2f} USDT\n"
                    f"原因: {reason}",
                    level="info" if pnl >= 0 else "warning",
                )
                
                logger.info(
                    "position closed",
                    symbol=symbol,
                    pnl=pnl,
                    reason=reason,
                )
                
                return {"success": True, "pnl": pnl, "exit_price": exit_price}
            else:
                return {"success": False, "message": order_result.error_message}
                
        except Exception as e:
            logger.error("close position failed", symbol=symbol, error=str(e))
            return {"success": False, "message": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        self._reset_daily_stats()
        
        return {
            "enabled": self.enabled,
            "mode": self.mode.value,
            "exchange": self.exchange_name,
            "sandbox": self.sandbox,
            "open_positions": len(self.open_positions),
            "daily_trades": self._daily_trades,
            "daily_pnl": round(self._daily_pnl, 2),
            "risk_limits": {
                "max_trade_amount": self.risk_limits.max_trade_amount,
                "max_daily_trades": self.risk_limits.max_daily_trades,
                "max_open_positions": self.risk_limits.max_open_positions,
                "max_daily_loss": self.risk_limits.max_daily_loss,
                "min_confidence": self.risk_limits.min_confidence,
            },
            "positions": [p.to_dict() for p in self.open_positions.values()],
        }
    
    async def close(self):
        """关闭"""
        if self._trader:
            await self._trader.close()
            self._trader = None
        logger.info("auto trader closed")
