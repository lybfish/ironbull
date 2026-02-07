"""
Position Module - 数据传输对象（DTOs）

定义 API 层面的数据契约，与数据库模型解耦
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List


@dataclass
class PositionDTO:
    """持仓数据传输对象"""
    position_id: str
    tenant_id: int
    account_id: int
    symbol: str
    exchange: str
    market_type: str
    position_side: str
    quantity: float
    available: float
    frozen: float
    avg_cost: float
    total_cost: float
    realized_pnl: float
    leverage: Optional[int] = None
    margin: Optional[float] = None
    liquidation_price: Optional[float] = None
    # 自管止盈止损
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_code: Optional[str] = None
    status: str = "OPEN"
    close_reason: Optional[str] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 计算字段（需要行情价格）
    unrealized_pnl: Optional[float] = None
    market_value: Optional[float] = None


@dataclass
class PositionChangeDTO:
    """持仓变动数据传输对象"""
    change_id: str
    position_id: str
    tenant_id: int
    account_id: int
    symbol: str
    position_side: str
    change_type: str
    quantity_change: float
    available_change: float
    frozen_change: float
    quantity_after: float
    available_after: float
    frozen_after: float
    avg_cost_after: float
    price: Optional[float] = None
    realized_pnl: Optional[float] = None
    source_type: str = ""
    source_id: Optional[str] = None
    changed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    remark: Optional[str] = None


@dataclass
class UpdatePositionDTO:
    """
    更新持仓请求（由成交驱动）
    
    通过成交记录更新持仓，自动判断是开仓/加仓/减仓/平仓
    """
    tenant_id: int
    account_id: int
    symbol: str
    exchange: str
    market_type: str = "spot"
    position_side: str = "NONE"     # LONG/SHORT/NONE
    side: str = ""                  # BUY/SELL
    quantity: Decimal = Decimal("0")
    price: Decimal = Decimal("0")
    fee: Decimal = Decimal("0")
    
    # 来源关联
    fill_id: Optional[str] = None   # 关联的成交ID
    order_id: Optional[str] = None  # 关联的订单ID
    
    # 时间
    filled_at: Optional[datetime] = None
    
    # 合约专用
    leverage: Optional[int] = None


@dataclass
class FreezePositionDTO:
    """冻结/解冻持仓请求"""
    tenant_id: int
    account_id: int
    symbol: str
    exchange: str
    position_side: str = "NONE"
    quantity: Decimal = Decimal("0")  # 冻结/解冻数量
    
    # 来源关联
    order_id: Optional[str] = None    # 关联的订单ID
    
    # 时间
    freeze_at: Optional[datetime] = None


@dataclass
class PositionFilter:
    """持仓查询过滤条件"""
    tenant_id: int                    # 必填：租户隔离
    account_id: Optional[int] = None
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    market_type: Optional[str] = None
    position_side: Optional[str] = None
    status: Optional[str] = None      # OPEN/CLOSED/LIQUIDATED
    close_reason: Optional[str] = None  # SL/TP/SIGNAL/MANUAL/LIQUIDATION
    has_position: Optional[bool] = None  # True: quantity > 0
    
    # 分页
    limit: int = 100
    offset: int = 0


@dataclass
class PositionChangeFilter:
    """持仓变动查询过滤条件"""
    tenant_id: int                    # 必填：租户隔离
    account_id: Optional[int] = None
    position_id: Optional[str] = None
    symbol: Optional[str] = None
    change_type: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    
    # 时间范围
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # 分页
    limit: int = 100
    offset: int = 0


@dataclass
class PositionSummary:
    """持仓汇总"""
    tenant_id: int
    account_id: int
    total_positions: int = 0          # 持仓标的数
    total_quantity: float = 0         # 总持仓数量
    total_cost: float = 0             # 总成本
    total_realized_pnl: float = 0     # 累计已实现盈亏
    
    # 按市场类型
    spot_positions: int = 0
    future_positions: int = 0
    
    # 按方向（合约）
    long_positions: int = 0
    short_positions: int = 0


@dataclass 
class PositionKey:
    """持仓唯一键"""
    tenant_id: int
    account_id: int
    symbol: str
    exchange: str
    position_side: str = "NONE"
    
    def __hash__(self):
        return hash((self.tenant_id, self.account_id, self.symbol, self.exchange, self.position_side))
    
    def __eq__(self, other):
        if not isinstance(other, PositionKey):
            return False
        return (
            self.tenant_id == other.tenant_id and
            self.account_id == other.account_id and
            self.symbol == other.symbol and
            self.exchange == other.exchange and
            self.position_side == other.position_side
        )
