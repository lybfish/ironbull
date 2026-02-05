"""
Position Module - 持仓管理模块

职责：
- 标的级别的持仓数量管理（多头/空头、可用/冻结）
- 持仓成本的计算与更新（成本价、浮动盈亏）
- 持仓变动的记录（因成交、调仓、强平等）
- 提供当前持仓快照与历史持仓查询
- 支持多账户、多币种、多市场的持仓隔离

不变量：
1. 持仓 = Σ成交：任一标的的当前持仓数量 = 买入 - 卖出
2. 可用 + 冻结 = 总持仓
3. 卖出 ≤ 可用：防止超卖
4. 成本可追溯：从成交明细反推得出
5. 变动有来源：每笔变动关联到成交/调仓/事件
6. 租户隔离：跨租户不可见
"""

from libs.position.models import Position, PositionChange
from libs.position.states import (
    PositionSide,
    PositionStatus,
    ChangeType,
    PositionValidation,
)
from libs.position.contracts import (
    PositionDTO,
    PositionChangeDTO,
    UpdatePositionDTO,
    FreezePositionDTO,
    PositionFilter,
    PositionSummary,
)
from libs.position.exceptions import (
    PositionError,
    PositionNotFoundError,
    InsufficientPositionError,
    InsufficientAvailableError,
    FreezeExceedsAvailableError,
    InvalidFreezeReleaseError,
    TenantMismatchError,
    InvalidChangeSourceError,
    PositionAlreadyExistsError,
)
from libs.position.repository import PositionRepository, PositionChangeRepository
from libs.position.service import PositionService

__all__ = [
    # Models
    "Position",
    "PositionChange",
    # States
    "PositionSide",
    "PositionStatus",
    "ChangeType",
    "PositionValidation",
    # Contracts (DTOs)
    "PositionDTO",
    "PositionChangeDTO",
    "UpdatePositionDTO",
    "FreezePositionDTO",
    "PositionFilter",
    "PositionSummary",
    # Exceptions
    "PositionError",
    "PositionNotFoundError",
    "InsufficientPositionError",
    "InsufficientAvailableError",
    "FreezeExceedsAvailableError",
    "InvalidFreezeReleaseError",
    "TenantMismatchError",
    "InvalidChangeSourceError",
    "PositionAlreadyExistsError",
    # Repository
    "PositionRepository",
    "PositionChangeRepository",
    # Service
    "PositionService",
]
