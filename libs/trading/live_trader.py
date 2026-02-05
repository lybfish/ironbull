"""
Live Trader - 真实交易执行器

基于 ccxt 实现真实交易所下单
"""

from datetime import datetime
from typing import Optional, Dict, Any

import ccxt.async_support as ccxt

from libs.core import get_logger, gen_id
from .base import (
    Trader, OrderResult, OrderStatus, OrderSide, OrderType, Balance
)

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
    
    SUPPORTED_EXCHANGES = ["binance", "okx", "bybit", "gate", "huobi"]
    
    def __init__(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,  # OKX 需要
        sandbox: bool = False,              # 是否使用沙盒/测试网
        options: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            exchange: 交易所名称 (binance/okx/bybit)
            api_key: API Key
            api_secret: API Secret
            passphrase: API Passphrase (OKX 需要)
            sandbox: 是否使用测试网
            options: ccxt 额外选项
        """
        self.exchange_name = exchange.lower()
        self.sandbox = sandbox
        
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
        **kwargs,
    ) -> OrderResult:
        """创建订单"""
        order_id = gen_id("ord_")
        
        try:
            # 转换订单类型
            ccxt_type = "market" if order_type == OrderType.MARKET else "limit"
            ccxt_side = side.value
            
            logger.info(
                "creating order",
                order_id=order_id,
                symbol=symbol,
                side=ccxt_side,
                type=ccxt_type,
                quantity=quantity,
                price=price,
            )
            
            # 调用 ccxt 下单
            if order_type == OrderType.MARKET:
                response = await self.exchange.create_order(
                    symbol=symbol,
                    type=ccxt_type,
                    side=ccxt_side,
                    amount=quantity,
                    params=kwargs,
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
                    params=kwargs,
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
            
            return result
            
        except ccxt.InsufficientFunds as e:
            logger.error("insufficient funds", order_id=order_id, error=str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "INSUFFICIENT_FUNDS", str(e))
        
        except ccxt.InvalidOrder as e:
            logger.error("invalid order", order_id=order_id, error=str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "INVALID_ORDER", str(e))
        
        except ccxt.OrderNotFound as e:
            logger.error("order not found", order_id=order_id, error=str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "ORDER_NOT_FOUND", str(e))
        
        except ccxt.NetworkError as e:
            logger.error("network error", order_id=order_id, error=str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "NETWORK_ERROR", str(e))
        
        except ccxt.ExchangeError as e:
            logger.error("exchange error", order_id=order_id, error=str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "EXCHANGE_ERROR", str(e))
        
        except Exception as e:
            logger.error("unexpected error", order_id=order_id, error=str(e))
            return self._error_result(order_id, symbol, side, order_type, quantity, price, "UNKNOWN_ERROR", str(e))
    
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
