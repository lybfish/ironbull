"""
Trading Base - 交易基类和数据结构

定义统一的交易接口和返回结构
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class OrderSide(str, Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"       # 待处理
    OPEN = "open"             # 已提交，等待成交
    FILLED = "filled"         # 完全成交
    PARTIAL = "partial"       # 部分成交
    CANCELED = "canceled"     # 已取消
    REJECTED = "rejected"     # 被拒绝
    EXPIRED = "expired"       # 已过期
    FAILED = "failed"         # 失败


@dataclass
class OrderResult:
    """订单执行结果"""
    order_id: str                           # 内部订单 ID
    exchange_order_id: Optional[str]        # 交易所订单 ID
    symbol: str                             # 交易对
    side: OrderSide                         # 方向
    order_type: OrderType                   # 类型
    status: OrderStatus                     # 状态
    
    # 请求参数
    requested_quantity: float               # 请求数量
    requested_price: Optional[float]        # 请求价格（限价单）
    
    # 执行结果
    filled_quantity: float = 0.0            # 成交数量
    filled_price: float = 0.0               # 成交均价
    commission: float = 0.0                 # 手续费
    commission_asset: str = ""              # 手续费币种
    
    # 时间
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 错误信息
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # 原始响应
    raw_response: Optional[Dict[str, Any]] = None
    
    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.status in (OrderStatus.FILLED, OrderStatus.PARTIAL, OrderStatus.OPEN)
    
    @property
    def is_filled(self) -> bool:
        """是否完全成交"""
        return self.status == OrderStatus.FILLED
    
    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "order_id": self.order_id,
            "exchange_order_id": self.exchange_order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "requested_quantity": self.requested_quantity,
            "requested_price": self.requested_price,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "commission": self.commission,
            "commission_asset": self.commission_asset,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error_code": self.error_code,
            "error_message": self.error_message,
            "is_success": self.is_success,
            "is_filled": self.is_filled,
        }


@dataclass
class Balance:
    """账户余额"""
    asset: str          # 币种
    free: float         # 可用
    locked: float       # 冻结
    total: float        # 总计
    # 合约账户扩展字段
    unrealized_pnl: float = 0       # 未实现盈亏
    margin_used: float = 0          # 占用保证金
    margin_ratio: float = 0         # 保证金使用率 (0~1)
    equity: float = 0               # 权益 (total + unrealized_pnl)


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    side: str           # long / short
    quantity: float
    entry_price: float
    unrealized_pnl: float
    leverage: int = 1


class Trader(ABC):
    """
    交易执行器基类
    
    子类需实现：
    - create_order: 创建订单
    - cancel_order: 取消订单
    - get_order: 查询订单
    - get_balance: 查询余额
    """
    
    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        **kwargs,
    ) -> OrderResult:
        """
        创建订单
        
        Args:
            symbol: 交易对 (BTC/USDT)
            side: 买/卖
            order_type: 订单类型
            quantity: 数量
            price: 价格（限价单必填）
        
        Returns:
            OrderResult
        """
        pass
    
    @abstractmethod
    async def cancel_order(
        self,
        order_id: str,
        symbol: str,
    ) -> OrderResult:
        """取消订单"""
        pass
    
    @abstractmethod
    async def get_order(
        self,
        order_id: str,
        symbol: str,
    ) -> OrderResult:
        """查询订单"""
        pass
    
    @abstractmethod
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """查询余额"""
        pass
    
    @abstractmethod
    async def close(self):
        """关闭连接"""
        pass
    
    # 便捷方法
    async def market_buy(self, symbol: str, quantity: float, **kwargs) -> OrderResult:
        """市价买入"""
        return await self.create_order(symbol, OrderSide.BUY, OrderType.MARKET, quantity, **kwargs)
    
    async def market_sell(self, symbol: str, quantity: float, **kwargs) -> OrderResult:
        """市价卖出"""
        return await self.create_order(symbol, OrderSide.SELL, OrderType.MARKET, quantity, **kwargs)
    
    async def limit_buy(self, symbol: str, quantity: float, price: float, **kwargs) -> OrderResult:
        """限价买入"""
        return await self.create_order(symbol, OrderSide.BUY, OrderType.LIMIT, quantity, price, **kwargs)
    
    async def limit_sell(self, symbol: str, quantity: float, price: float, **kwargs) -> OrderResult:
        """限价卖出"""
        return await self.create_order(symbol, OrderSide.SELL, OrderType.LIMIT, quantity, price, **kwargs)
