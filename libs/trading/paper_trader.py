"""
Paper Trader - 模拟交易执行器

用于测试和演示，不实际下单
"""

from datetime import datetime
from typing import Optional, Dict, Any
import random

from libs.core import get_logger, gen_id
from .base import (
    Trader, OrderResult, OrderStatus, OrderSide, OrderType, Balance
)

logger = get_logger("paper-trader")


class PaperTrader(Trader):
    """
    模拟交易执行器
    
    不实际下单，用于：
    - 开发测试
    - 策略验证
    - Demo 演示
    
    使用示例：
        trader = PaperTrader(
            initial_balance={"USDT": 10000, "BTC": 0.1}
        )
        
        result = await trader.market_buy("BTC/USDT", 0.01)
    """
    
    def __init__(
        self,
        initial_balance: Optional[Dict[str, float]] = None,
        commission_rate: float = 0.001,
        slippage: float = 0.0005,  # 滑点
    ):
        """
        Args:
            initial_balance: 初始余额 {"USDT": 10000, "BTC": 0}
            commission_rate: 手续费率
            slippage: 滑点率
        """
        self.balances: Dict[str, Balance] = {}
        self.orders: Dict[str, OrderResult] = {}
        self.commission_rate = commission_rate
        self.slippage = slippage
        
        # 初始化余额
        if initial_balance:
            for asset, amount in initial_balance.items():
                self.balances[asset] = Balance(
                    asset=asset,
                    free=amount,
                    locked=0,
                    total=amount,
                )
        
        # 模拟价格（用于计算）
        self._prices: Dict[str, float] = {
            "BTC/USDT": 98000,
            "ETH/USDT": 3200,
            "BNB/USDT": 680,
        }
        
        logger.info("paper trader initialized", balance=initial_balance)
    
    def set_price(self, symbol: str, price: float):
        """设置模拟价格"""
        self._prices[symbol] = price
    
    def get_price(self, symbol: str) -> float:
        """获取模拟价格"""
        return self._prices.get(symbol, 0)
    
    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        **kwargs,
    ) -> OrderResult:
        """创建模拟订单"""
        order_id = gen_id("paper_")
        
        # 获取执行价格
        if order_type == OrderType.MARKET:
            base_price = self._prices.get(symbol, price or 0)
            # 添加滑点
            if side == OrderSide.BUY:
                exec_price = base_price * (1 + self.slippage)
            else:
                exec_price = base_price * (1 - self.slippage)
        else:
            exec_price = price or 0
        
        if exec_price <= 0:
            return OrderResult(
                order_id=order_id,
                exchange_order_id=None,
                symbol=symbol,
                side=side,
                order_type=order_type,
                status=OrderStatus.REJECTED,
                requested_quantity=quantity,
                requested_price=price,
                error_code="INVALID_PRICE",
                error_message=f"No price available for {symbol}",
            )
        
        # 解析交易对
        base, quote = symbol.split("/") if "/" in symbol else (symbol[:-4], symbol[-4:])
        
        # 计算费用
        cost = quantity * exec_price
        commission = cost * self.commission_rate
        
        # 检查余额
        if side == OrderSide.BUY:
            # 买入需要 quote 货币
            if quote not in self.balances or self.balances[quote].free < cost + commission:
                return OrderResult(
                    order_id=order_id,
                    exchange_order_id=None,
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    status=OrderStatus.REJECTED,
                    requested_quantity=quantity,
                    requested_price=price,
                    error_code="INSUFFICIENT_FUNDS",
                    error_message=f"Insufficient {quote} balance",
                )
            
            # 扣除 quote，增加 base
            self.balances[quote].free -= (cost + commission)
            self.balances[quote].total -= (cost + commission)
            
            if base not in self.balances:
                self.balances[base] = Balance(asset=base, free=0, locked=0, total=0)
            self.balances[base].free += quantity
            self.balances[base].total += quantity
            
        else:
            # 卖出需要 base 货币
            if base not in self.balances or self.balances[base].free < quantity:
                return OrderResult(
                    order_id=order_id,
                    exchange_order_id=None,
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    status=OrderStatus.REJECTED,
                    requested_quantity=quantity,
                    requested_price=price,
                    error_code="INSUFFICIENT_FUNDS",
                    error_message=f"Insufficient {base} balance",
                )
            
            # 扣除 base，增加 quote
            self.balances[base].free -= quantity
            self.balances[base].total -= quantity
            
            if quote not in self.balances:
                self.balances[quote] = Balance(asset=quote, free=0, locked=0, total=0)
            self.balances[quote].free += (cost - commission)
            self.balances[quote].total += (cost - commission)
        
        # 创建结果
        result = OrderResult(
            order_id=order_id,
            exchange_order_id=f"sim_{order_id}",
            symbol=symbol,
            side=side,
            order_type=order_type,
            status=OrderStatus.FILLED,
            requested_quantity=quantity,
            requested_price=price,
            filled_quantity=quantity,
            filled_price=exec_price,
            commission=commission,
            commission_asset=quote,
        )
        
        self.orders[order_id] = result
        
        logger.info(
            "paper order executed",
            order_id=order_id,
            symbol=symbol,
            side=side.value,
            quantity=quantity,
            price=exec_price,
            commission=commission,
        )
        
        return result
    
    async def cancel_order(self, order_id: str, symbol: str) -> OrderResult:
        """取消订单（模拟）"""
        if order_id in self.orders:
            result = self.orders[order_id]
            result.status = OrderStatus.CANCELED
            return result
        
        return OrderResult(
            order_id=order_id,
            exchange_order_id=None,
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            status=OrderStatus.FAILED,
            requested_quantity=0,
            requested_price=None,
            error_code="ORDER_NOT_FOUND",
            error_message="Order not found",
        )
    
    async def get_order(self, order_id: str, symbol: str) -> OrderResult:
        """查询订单"""
        if order_id in self.orders:
            return self.orders[order_id]
        
        return OrderResult(
            order_id=order_id,
            exchange_order_id=None,
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            status=OrderStatus.FAILED,
            requested_quantity=0,
            requested_price=None,
            error_code="ORDER_NOT_FOUND",
            error_message="Order not found",
        )
    
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """查询余额"""
        if asset:
            return {asset: self.balances[asset]} if asset in self.balances else {}
        return self.balances.copy()
    
    async def close(self):
        """关闭（模拟）"""
        logger.info("paper trader closed")
