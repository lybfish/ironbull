"""
Position Module - 状态定义与校验逻辑

定义持仓状态、方向、变动类型及校验规则
"""

from enum import Enum
from decimal import Decimal
from typing import Optional


class PositionSide(str, Enum):
    """持仓方向"""
    LONG = "LONG"      # 多头（做多）
    SHORT = "SHORT"    # 空头（做空）
    NONE = "NONE"      # 无方向（现货）


class PositionStatus(str, Enum):
    """持仓状态"""
    OPEN = "OPEN"          # 有持仓
    CLOSED = "CLOSED"      # 已平仓
    LIQUIDATED = "LIQUIDATED"  # 已强平


class ChangeType(str, Enum):
    """持仓变动类型"""
    # 正常交易
    OPEN = "OPEN"              # 开仓（新建持仓）
    ADD = "ADD"                # 加仓
    REDUCE = "REDUCE"          # 减仓
    CLOSE = "CLOSE"            # 平仓
    
    # 冻结操作
    FREEZE = "FREEZE"          # 冻结（下单锁定）
    UNFREEZE = "UNFREEZE"      # 解冻（撤单释放）
    
    # 特殊场景
    LIQUIDATION = "LIQUIDATION"    # 强平
    ADJUSTMENT = "ADJUSTMENT"      # 调仓/调账
    TRANSFER = "TRANSFER"          # 划转
    
    # 初始化
    INIT = "INIT"              # 初始导入


class PositionValidation:
    """持仓校验规则"""
    
    @staticmethod
    def validate_quantity(quantity: Decimal) -> bool:
        """验证数量非负"""
        return quantity >= 0
    
    @staticmethod
    def validate_available_frozen(
        total: Decimal,
        available: Decimal,
        frozen: Decimal
    ) -> bool:
        """
        不变量：可用 + 冻结 = 总持仓
        """
        return total == available + frozen
    
    @staticmethod
    def validate_sell_quantity(
        sell_quantity: Decimal,
        available_quantity: Decimal
    ) -> bool:
        """
        不变量：卖出 ≤ 可用
        """
        return sell_quantity <= available_quantity
    
    @staticmethod
    def validate_freeze_quantity(
        freeze_quantity: Decimal,
        available_quantity: Decimal
    ) -> bool:
        """
        验证冻结数量不超过可用数量
        """
        return freeze_quantity <= available_quantity
    
    @staticmethod
    def calculate_avg_cost(
        current_quantity: Decimal,
        current_cost: Decimal,
        add_quantity: Decimal,
        add_price: Decimal,
    ) -> Decimal:
        """
        计算加仓后的平均成本（加权平均法）
        
        公式：新成本 = (现有数量 * 现有成本 + 新增数量 * 新增价格) / (现有数量 + 新增数量)
        """
        if current_quantity + add_quantity == 0:
            return Decimal("0")
        
        total_cost = current_quantity * current_cost + add_quantity * add_price
        new_quantity = current_quantity + add_quantity
        
        return total_cost / new_quantity
    
    @staticmethod
    def calculate_realized_pnl(
        close_quantity: Decimal,
        close_price: Decimal,
        avg_cost: Decimal,
        side: PositionSide,
    ) -> Decimal:
        """
        计算已实现盈亏
        
        多头：(平仓价 - 成本价) * 平仓数量
        空头：(成本价 - 平仓价) * 平仓数量
        """
        if side == PositionSide.LONG or side == PositionSide.NONE:
            return (close_price - avg_cost) * close_quantity
        else:  # SHORT
            return (avg_cost - close_price) * close_quantity
    
    @staticmethod
    def calculate_unrealized_pnl(
        quantity: Decimal,
        avg_cost: Decimal,
        market_price: Decimal,
        side: PositionSide,
    ) -> Decimal:
        """
        计算未实现盈亏（浮盈浮亏）
        
        多头：(市场价 - 成本价) * 持仓数量
        空头：(成本价 - 市场价) * 持仓数量
        """
        if quantity == 0:
            return Decimal("0")
        
        if side == PositionSide.LONG or side == PositionSide.NONE:
            return (market_price - avg_cost) * quantity
        else:  # SHORT
            return (avg_cost - market_price) * quantity
