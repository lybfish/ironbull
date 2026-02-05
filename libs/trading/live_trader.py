"""
Live Trader - 真实交易执行器

基于 ccxt 实现真实交易所下单
支持可选的 TradeSettlementService 集成，实现完整交易闭环：
  OrderTrade → Position → Ledger
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, TYPE_CHECKING

import ccxt.async_support as ccxt

from libs.core import get_logger, gen_id
from .base import (
    Trader, OrderResult, OrderStatus, OrderSide, OrderType, Balance
)

# 延迟导入避免循环依赖
if TYPE_CHECKING:
    from libs.order_trade import OrderTradeService
    from libs.trading.settlement import TradeSettlementService

logger = get_logger("live-trader")


class LiveTrader(Trader):
    """
    真实交易执行器
    
    使用 ccxt 连接交易所执行真实订单
    
    支持的交易所：
    - binance
    - okx
    - bybit
    
    使用示例：
        trader = LiveTrader(
            exchange="binance",
            api_key="xxx",
            api_secret="xxx",
        )
        
        result = await trader.market_buy("BTC/USDT", 0.001)
        
        await trader.close()
    """
    
    SUPPORTED_EXCHANGES = ["binance", "binanceusdm", "okx", "bybit", "gate", "huobi"]
    
    def __init__(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,  # OKX 需要
        sandbox: bool = False,              # 是否使用沙盒/测试网
        market_type: str = "future",        # 市场类型: spot / future
        options: Optional[Dict[str, Any]] = None,
        # OrderTrade 集成（可选，旧版兼容）
        order_trade_service: Optional["OrderTradeService"] = None,
        tenant_id: Optional[int] = None,
        account_id: Optional[int] = None,
        # 完整结算集成（推荐）
        settlement_service: Optional["TradeSettlementService"] = None,
    ):
        """
        Args:
            exchange: 交易所名称 (binance/okx/bybit)
            api_key: API Key
            api_secret: API Secret
            passphrase: API Passphrase (OKX 需要)
            sandbox: 是否使用测试网
            market_type: 市场类型 (spot=现货, future=合约)
            options: ccxt 额外选项
            order_trade_service: OrderTradeService 实例（可选，旧版兼容）
            tenant_id: 租户ID
            account_id: 账户ID
            settlement_service: TradeSettlementService 实例（推荐，完整交易闭环）
        """
        self.exchange_name = exchange.lower()
        self.sandbox = sandbox
        self.market_type = market_type
        
        # 结算服务（完整交易闭环：OrderTrade → Position → Ledger）
        self._settlement_service = settlement_service
        
        # OrderTrade 集成（旧版兼容）
        self._order_trade_service = order_trade_service
        self._tenant_id = tenant_id
        self._account_id = account_id
        
        if self.exchange_name not in self.SUPPORTED_EXCHANGES:
            raise ValueError(f"Unsupported exchange: {exchange}")
        
        # 构建 ccxt 配置
        config = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": options or {},
        }
        
        if passphrase:
            config["password"] = passphrase
        
        # 合约交易配置
        if market_type == "future":
            if self.exchange_name == "binance":
                # Binance USDT 永续合约
                self.exchange_name = "binanceusdm"
                config["options"]["defaultType"] = "future"
            elif self.exchange_name == "okx":
                config["options"]["defaultType"] = "swap"
            elif self.exchange_name == "bybit":
                config["options"]["defaultType"] = "linear"
        
        # 创建交易所实例
        exchange_class = getattr(ccxt, self.exchange_name)
        self.exchange: ccxt.Exchange = exchange_class(config)
        
        # 启用沙盒模式
        if sandbox:
            self.exchange.set_sandbox_mode(True)
            logger.info("sandbox mode enabled", exchange=exchange)
        
        logger.info("live trader initialized", exchange=exchange, sandbox=sandbox)
    
    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        position_side: Optional[str] = None,  # LONG / SHORT (双向持仓模式)
        signal_id: Optional[str] = None,      # 关联信号ID（用于 OrderTrade 记录）
        **kwargs,
    ) -> OrderResult:
        """创建订单"""
        order_id = gen_id("ord_")
        db_order_id = None  # 数据库订单ID（如果使用 OrderTradeService）
        
        try:
            # 如果启用 OrderTradeService，先创建订单记录
            if self._order_trade_service and self._tenant_id and self._account_id:
                db_order_id = await self._create_order_record(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    position_side=position_side,
                    signal_id=signal_id,
                )
                if db_order_id:
                    order_id = db_order_id  # 使用数据库订单ID
            
            # 转换订单类型
            ccxt_type = "market" if order_type == OrderType.MARKET else "limit"
            ccxt_side = side.value
            
            # 合约交易参数
            params = dict(kwargs)
            if self.market_type == "future":
                # 双向持仓模式：需要指定 positionSide
                if position_side:
                    params["positionSide"] = position_side
                else:
                    # 默认：买入开多，卖出开空
                    params["positionSide"] = "LONG" if side == OrderSide.BUY else "SHORT"
            
            logger.info(
                "creating order",
                order_id=order_id,
                symbol=symbol,
                side=ccxt_side,
                type=ccxt_type,
                quantity=quantity,
                price=price,
                params=params,
            )
            
            # 调用 ccxt 下单
            if order_type == OrderType.MARKET:
                response = await self.exchange.create_order(
                    symbol=symbol,
                    type=ccxt_type,
                    side=ccxt_side,
                    amount=quantity,
                    params=params,
                )
            else:
                if price is None:
                    raise ValueError("Price is required for limit orders")
                response = await self.exchange.create_order(
                    symbol=symbol,
                    type=ccxt_type,
                    side=ccxt_side,
                    amount=quantity,
                    price=price,
                    params=params,
                )
            
            # 解析响应
            result = self._parse_order_response(order_id, symbol, side, order_type, quantity, price, response)
            
            logger.info(
                "order created",
                order_id=order_id,
                exchange_order_id=result.exchange_order_id,
                status=result.status.value,
                filled_quantity=result.filled_quantity,
                filled_price=result.filled_price,
            )
            
            # 更新订单状态并结算（支持 settlement_service 或 order_trade_service）
            if (self._settlement_service or self._order_trade_service) and db_order_id:
                await self._update_order_after_submit(
                    order_id=db_order_id,
                    exchange_order_id=result.exchange_order_id,
                    result=result,
                    position_side=params.get("positionSide", "NONE"),
                )
            
            return result
            
        except ccxt.InsufficientFunds as e:
            logger.error("insufficient funds", order_id=order_id, error=str(e))
            if self._order_trade_service and db_order_id:
                await self._fail_order_record(db_order_id, "INSUFFICIENT_FUNDS", str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "INSUFFICIENT_FUNDS", str(e))
        
        except ccxt.InvalidOrder as e:
            logger.error("invalid order", order_id=order_id, error=str(e))
            if self._order_trade_service and db_order_id:
                await self._fail_order_record(db_order_id, "INVALID_ORDER", str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "INVALID_ORDER", str(e))
        
        except ccxt.OrderNotFound as e:
            logger.error("order not found", order_id=order_id, error=str(e))
            if self._order_trade_service and db_order_id:
                await self._fail_order_record(db_order_id, "ORDER_NOT_FOUND", str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "ORDER_NOT_FOUND", str(e))
        
        except ccxt.NetworkError as e:
            logger.error("network error", order_id=order_id, error=str(e))
            if self._order_trade_service and db_order_id:
                await self._fail_order_record(db_order_id, "NETWORK_ERROR", str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "NETWORK_ERROR", str(e))
        
        except ccxt.ExchangeError as e:
            logger.error("exchange error", order_id=order_id, error=str(e))
            if self._order_trade_service and db_order_id:
                await self._fail_order_record(db_order_id, "EXCHANGE_ERROR", str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "EXCHANGE_ERROR", str(e))
        
        except Exception as e:
            logger.error("unexpected error", order_id=order_id, error=str(e))
            if self._order_trade_service and db_order_id:
                await self._fail_order_record(db_order_id, "UNKNOWN_ERROR", str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "UNKNOWN_ERROR", str(e))
    
    async def set_stop_loss(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        stop_price: float,
        position_side: Optional[str] = None,
    ) -> OrderResult:
        """
        设置止损单（STOP_MARKET）
        
        Args:
            symbol: 交易对
            side: 平仓方向 (做多持仓用SELL平仓，做空持仓用BUY平仓)
            quantity: 数量
            stop_price: 触发价格
            position_side: 持仓方向 (LONG/SHORT)
        """
        order_id = gen_id("sl_")
        
        try:
            params = {
                "stopPrice": stop_price,
            }
            
            # 双向持仓模式
            if self.market_type == "future":
                if position_side:
                    params["positionSide"] = position_side
                else:
                    # 止损：做多持仓用SELL平仓，所以positionSide是LONG
                    params["positionSide"] = "LONG" if side == OrderSide.SELL else "SHORT"
            else:
                # 单向持仓模式才需要 reduceOnly
                params["reduceOnly"] = True
            
            logger.info(
                "setting stop loss",
                order_id=order_id,
                symbol=symbol,
                side=side.value,
                quantity=quantity,
                stop_price=stop_price,
                params=params,
            )
            
            response = await self.exchange.create_order(
                symbol=symbol,
                type="STOP_MARKET",
                side=side.value,
                amount=quantity,
                params=params,
            )
            
            logger.info("stop loss set", order_id=order_id, exchange_id=response.get("id"))
            
            return OrderResult(
                order_id=order_id,
                exchange_order_id=response.get("id"),
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                status=OrderStatus.OPEN,
                requested_quantity=quantity,
                requested_price=stop_price,
                raw_response=response,
            )
            
        except ccxt.ExchangeError as e:
            logger.error("set stop loss failed (exchange)", order_id=order_id, error=str(e))
            return self._error_result(order_id, symbol, side, OrderType.MARKET, quantity, stop_price, "SL_FAILED", str(e))
        except Exception as e:
            logger.error("set stop loss failed", order_id=order_id, error=str(e), error_type=type(e).__name__)
            return self._error_result(order_id, symbol, side, OrderType.MARKET, quantity, stop_price, "SL_FAILED", str(e))
    
    async def set_take_profit(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        take_profit_price: float,
        position_side: Optional[str] = None,
    ) -> OrderResult:
        """
        设置止盈单（TAKE_PROFIT_MARKET）
        
        Args:
            symbol: 交易对
            side: 平仓方向 (做多持仓用SELL平仓，做空持仓用BUY平仓)
            quantity: 数量
            take_profit_price: 触发价格
            position_side: 持仓方向 (LONG/SHORT)
        """
        order_id = gen_id("tp_")
        
        try:
            params = {
                "stopPrice": take_profit_price,
            }
            
            # 双向持仓模式
            if self.market_type == "future":
                if position_side:
                    params["positionSide"] = position_side
                else:
                    params["positionSide"] = "LONG" if side == OrderSide.SELL else "SHORT"
            else:
                # 单向持仓模式才需要 reduceOnly
                params["reduceOnly"] = True
            
            logger.info(
                "setting take profit",
                order_id=order_id,
                symbol=symbol,
                side=side.value,
                quantity=quantity,
                take_profit_price=take_profit_price,
                params=params,
            )
            
            response = await self.exchange.create_order(
                symbol=symbol,
                type="TAKE_PROFIT_MARKET",
                side=side.value,
                amount=quantity,
                params=params,
            )
            
            logger.info("take profit set", order_id=order_id, exchange_id=response.get("id"))
            
            return OrderResult(
                order_id=order_id,
                exchange_order_id=response.get("id"),
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                status=OrderStatus.OPEN,
                requested_quantity=quantity,
                requested_price=take_profit_price,
                raw_response=response,
            )
            
        except ccxt.ExchangeError as e:
            logger.error("set take profit failed (exchange)", order_id=order_id, error=str(e))
            return self._error_result(order_id, symbol, side, OrderType.MARKET, quantity, take_profit_price, "TP_FAILED", str(e))
        except Exception as e:
            logger.error("set take profit failed", order_id=order_id, error=str(e), error_type=type(e).__name__)
            return self._error_result(order_id, symbol, side, OrderType.MARKET, quantity, take_profit_price, "TP_FAILED", str(e))
    
    async def set_sl_tp(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        position_side: Optional[str] = None,
    ) -> Dict[str, OrderResult]:
        """
        同时设置止盈止损
        
        Args:
            symbol: 交易对
            side: 开仓方向 (BUY=做多, SELL=做空)
            quantity: 数量
            stop_loss: 止损价
            take_profit: 止盈价
            position_side: 持仓方向
            
        Returns:
            {"sl": OrderResult, "tp": OrderResult}
        """
        results = {}
        
        # 平仓方向与开仓方向相反
        close_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
        # 持仓方向
        pos_side = position_side or ("LONG" if side == OrderSide.BUY else "SHORT")
        
        if stop_loss:
            results["sl"] = await self.set_stop_loss(
                symbol=symbol,
                side=close_side,
                quantity=quantity,
                stop_price=stop_loss,
                position_side=pos_side,
            )
        
        if take_profit:
            results["tp"] = await self.set_take_profit(
                symbol=symbol,
                side=close_side,
                quantity=quantity,
                take_profit_price=take_profit,
                position_side=pos_side,
            )
        
        return results

    async def cancel_order(self, order_id: str, symbol: str) -> OrderResult:
        """取消订单"""
        try:
            response = await self.exchange.cancel_order(order_id, symbol)
            
            return OrderResult(
                order_id=order_id,
                exchange_order_id=response.get("id"),
                symbol=symbol,
                side=OrderSide(response.get("side", "buy")),
                order_type=OrderType.LIMIT,
                status=OrderStatus.CANCELED,
                requested_quantity=response.get("amount", 0),
                requested_price=response.get("price"),
                filled_quantity=response.get("filled", 0),
                filled_price=response.get("average", 0),
                raw_response=response,
            )
            
        except Exception as e:
            logger.error("cancel order failed", order_id=order_id, error=str(e))
            return OrderResult(
                order_id=order_id,
                exchange_order_id=order_id,
                symbol=symbol,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                status=OrderStatus.FAILED,
                requested_quantity=0,
                requested_price=None,
                error_code="CANCEL_FAILED",
                error_message=str(e),
            )
    
    async def get_order(self, order_id: str, symbol: str) -> OrderResult:
        """查询订单"""
        try:
            response = await self.exchange.fetch_order(order_id, symbol)
            
            status_map = {
                "open": OrderStatus.OPEN,
                "closed": OrderStatus.FILLED,
                "canceled": OrderStatus.CANCELED,
                "expired": OrderStatus.EXPIRED,
                "rejected": OrderStatus.REJECTED,
            }
            
            return OrderResult(
                order_id=order_id,
                exchange_order_id=response.get("id"),
                symbol=symbol,
                side=OrderSide(response.get("side", "buy")),
                order_type=OrderType.MARKET if response.get("type") == "market" else OrderType.LIMIT,
                status=status_map.get(response.get("status"), OrderStatus.PENDING),
                requested_quantity=response.get("amount", 0),
                requested_price=response.get("price"),
                filled_quantity=response.get("filled", 0),
                filled_price=response.get("average", 0),
                commission=response.get("fee", {}).get("cost", 0) if response.get("fee") else 0,
                commission_asset=response.get("fee", {}).get("currency", "") if response.get("fee") else "",
                raw_response=response,
            )
            
        except Exception as e:
            logger.error("get order failed", order_id=order_id, error=str(e))
            return OrderResult(
                order_id=order_id,
                exchange_order_id=order_id,
                symbol=symbol,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                status=OrderStatus.FAILED,
                requested_quantity=0,
                requested_price=None,
                error_code="QUERY_FAILED",
                error_message=str(e),
            )
    
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """查询余额"""
        try:
            response = await self.exchange.fetch_balance()
            
            balances = {}
            for currency, data in response.get("total", {}).items():
                if data and data > 0:
                    free = response.get("free", {}).get(currency, 0) or 0
                    locked = response.get("used", {}).get(currency, 0) or 0
                    total = data
                    
                    if asset and currency != asset:
                        continue
                    
                    balances[currency] = Balance(
                        asset=currency,
                        free=free,
                        locked=locked,
                        total=total,
                    )
            
            return balances
            
        except Exception as e:
            logger.error("get balance failed", error=str(e))
            return {}
    
    async def close(self):
        """关闭连接"""
        try:
            await self.exchange.close()
            logger.info("live trader closed", exchange=self.exchange_name)
        except Exception as e:
            logger.warning("close failed", error=str(e))
    
    def _parse_order_response(
        self,
        order_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float],
        response: Dict[str, Any],
    ) -> OrderResult:
        """解析订单响应"""
        status_map = {
            "open": OrderStatus.OPEN,
            "closed": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELED,
            "expired": OrderStatus.EXPIRED,
            "rejected": OrderStatus.REJECTED,
        }
        
        status = status_map.get(response.get("status"), OrderStatus.PENDING)
        
        # 如果有成交量，可能是部分成交
        filled = response.get("filled", 0)
        if filled > 0 and filled < quantity:
            status = OrderStatus.PARTIAL
        elif filled >= quantity:
            status = OrderStatus.FILLED
        
        return OrderResult(
            order_id=order_id,
            exchange_order_id=response.get("id"),
            symbol=symbol,
            side=side,
            order_type=order_type,
            status=status,
            requested_quantity=quantity,
            requested_price=price,
            filled_quantity=filled,
            filled_price=response.get("average", response.get("price", 0)) or 0,
            commission=response.get("fee", {}).get("cost", 0) if response.get("fee") else 0,
            commission_asset=response.get("fee", {}).get("currency", "") if response.get("fee") else "",
            raw_response=response,
        )
    
    def _error_result(
        self,
        order_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float],
        error_code: str,
        error_message: str,
    ) -> OrderResult:
        """创建错误结果"""
        return OrderResult(
            order_id=order_id,
            exchange_order_id=None,
            symbol=symbol,
            side=side,
            order_type=order_type,
            status=OrderStatus.FAILED,
            requested_quantity=quantity,
            requested_price=price,
            error_code=error_code,
            error_message=error_message,
        )
    
    # ============ OrderTradeService 集成方法 ============
    
    async def _create_order_record(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float],
        position_side: Optional[str],
        signal_id: Optional[str],
    ) -> Optional[str]:
        """创建订单记录（PENDING 状态）"""
        order_type_str = "MARKET" if order_type == OrderType.MARKET else "LIMIT"
        
        # 优先使用 settlement_service
        if self._settlement_service:
            try:
                order_dto = self._settlement_service.create_order(
                    symbol=symbol,
                    exchange=self.exchange_name,
                    side=side.value.upper(),
                    order_type=order_type_str,
                    quantity=Decimal(str(quantity)),
                    price=Decimal(str(price)) if price else None,
                    signal_id=signal_id,
                    position_side=position_side or "NONE",
                    market_type=self.market_type,
                )
                logger.debug("order record created (settlement)", order_id=order_dto.order_id)
                return order_dto.order_id
            except Exception as e:
                logger.warning("failed to create order record (settlement)", error=str(e))
                return None
        
        # 旧版：使用 order_trade_service
        if not self._order_trade_service:
            return None
        
        try:
            from libs.order_trade import CreateOrderDTO
            
            order_dto = self._order_trade_service.create_order(CreateOrderDTO(
                tenant_id=self._tenant_id,
                account_id=self._account_id,
                symbol=symbol,
                exchange=self.exchange_name,
                side=side.value.upper(),
                order_type=order_type_str,
                quantity=quantity,
                price=price,
                signal_id=signal_id,
                market_type=self.market_type,
                position_side=position_side,
            ))
            
            logger.debug("order record created", order_id=order_dto.order_id)
            return order_dto.order_id
            
        except Exception as e:
            logger.warning("failed to create order record", error=str(e))
            return None
    
    async def _update_order_after_submit(
        self,
        order_id: str,
        exchange_order_id: Optional[str],
        result: OrderResult,
        position_side: Optional[str] = None,
    ) -> None:
        """
        提交后更新订单状态并记录成交
        
        如果配置了 settlement_service，会触发完整的交易闭环：
        OrderTrade → Position → Ledger
        """
        # 优先使用 settlement_service（完整交易闭环）
        if self._settlement_service:
            try:
                # 更新交易所订单号
                if exchange_order_id:
                    self._settlement_service.submit_order(
                        order_id=order_id,
                        exchange_order_id=exchange_order_id,
                    )
                
                # 如果有成交，触发完整结算
                if result.filled_quantity > 0:
                    settlement_result = self._settlement_service.settle_fill(
                        order_id=order_id,
                        symbol=result.symbol,
                        exchange=self.exchange_name,
                        side=result.side.value.upper(),
                        quantity=Decimal(str(result.filled_quantity)),
                        price=Decimal(str(result.filled_price)),
                        fee=Decimal(str(result.commission)) if result.commission else Decimal("0"),
                        fee_currency=result.commission_asset or "USDT",
                        exchange_trade_id=exchange_order_id,
                        filled_at=datetime.utcnow(),
                        position_side=position_side or "NONE",
                        market_type=self.market_type,
                    )
                    
                    if settlement_result.success:
                        logger.info(
                            "settlement completed",
                            order_id=order_id,
                            fill_id=settlement_result.fill_id,
                            position_after=settlement_result.position_quantity_after,
                            balance_after=settlement_result.balance_after,
                            realized_pnl=settlement_result.realized_pnl,
                        )
                    else:
                        logger.warning(
                            "settlement failed",
                            order_id=order_id,
                            error=settlement_result.error,
                        )
                
            except Exception as e:
                logger.warning("settlement service error", order_id=order_id, error=str(e))
            return
        
        # 旧版：仅使用 order_trade_service
        if not self._order_trade_service:
            return
        
        try:
            # 更新交易所订单号
            if exchange_order_id:
                self._order_trade_service.submit_order(
                    order_id=order_id,
                    tenant_id=self._tenant_id,
                    exchange_order_id=exchange_order_id,
                    submitted_at=datetime.utcnow(),
                )
            
            # 如果有成交，记录成交
            if result.filled_quantity > 0:
                from libs.order_trade import RecordFillDTO
                
                # 获取订单信息
                order = self._order_trade_service.get_order(order_id, self._tenant_id)
                
                self._order_trade_service.record_fill(RecordFillDTO(
                    order_id=order_id,
                    tenant_id=self._tenant_id,
                    account_id=self._account_id,
                    symbol=result.symbol,
                    side=result.side.value.upper(),
                    quantity=result.filled_quantity,
                    price=result.filled_price,
                    filled_at=datetime.utcnow(),
                    exchange_trade_id=exchange_order_id,
                    fee=result.commission,
                    fee_currency=result.commission_asset,
                ))
                
                logger.debug("fill recorded", order_id=order_id, filled_quantity=result.filled_quantity)
            
        except Exception as e:
            logger.warning("failed to update order record", order_id=order_id, error=str(e))
    
    async def _fail_order_record(
        self,
        order_id: str,
        error_code: str,
        error_message: str,
    ) -> None:
        """标记订单失败"""
        # 优先使用 settlement_service
        if self._settlement_service:
            try:
                self._settlement_service.fail_order(
                    order_id=order_id,
                    error_code=error_code,
                    error_message=error_message,
                )
                logger.debug("order marked as failed (settlement)", order_id=order_id)
            except Exception as e:
                logger.warning("failed to mark order as failed (settlement)", order_id=order_id, error=str(e))
            return
        
        # 旧版：使用 order_trade_service
        if not self._order_trade_service:
            return
        
        try:
            self._order_trade_service.fail_order(
                order_id=order_id,
                tenant_id=self._tenant_id,
                error_code=error_code,
                error_message=error_message,
            )
            logger.debug("order marked as failed", order_id=order_id)
        except Exception as e:
            logger.warning("failed to mark order as failed", order_id=order_id, error=str(e))
