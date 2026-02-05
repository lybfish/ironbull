"""
Strategy Base Class

所有策略的基类。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from libs.contracts import StrategyOutput


class StrategyBase(ABC):
    """
    策略基类
    
    所有策略必须继承此类并实现 analyze 方法。
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.code = "base"
        self.name = "基础策略"
        self.version = "1.0.0"
    
    @abstractmethod
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """
        分析策略，返回 StrategyOutput
        
        Args:
            symbol: 交易对
            timeframe: 时间周期
            candles: K线数据 [{'open', 'high', 'low', 'close', 'volume', 'timestamp'}, ...]
            positions: 当前持仓状态（可选）
        
        Returns:
            StrategyOutput 或 None（无信号时）
        """
        pass
