"""
IronBull v0 Contract Definitions

模块间通信的数据结构定义，v0.1 已冻结。

规则：
- 不允许修改现有字段语义
- 只能新增 v1 扩展 Contract
- 不允许破坏向后兼容性
"""

from .signal import Signal
from .strategy_output import StrategyOutput
from .account_context import AccountContext, Position
from .risk_result import RiskResult
from .execution_task import ExecutionTask
from .execution_result import ExecutionResult
from .node_task import NodeTask
from .node_result import NodeResult
from .follow_task import FollowTask, FollowTaskResult

__all__ = [
    # Signal Layer
    "Signal",
    "StrategyOutput",
    
    # Risk Layer
    "AccountContext",
    "Position",
    "RiskResult",
    
    # Execution Layer
    "ExecutionTask",
    "ExecutionResult",
    
    # Node Layer
    "NodeTask",
    "NodeResult",
    
    # Follow Layer
    "FollowTask",
    "FollowTaskResult",
]

__version__ = "0.1"
