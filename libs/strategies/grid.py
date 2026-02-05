"""
Grid Trading Strategy

网格交易策略。
"""

from typing import Dict, List, Optional

from libs.contracts import StrategyOutput
from .base import StrategyBase


class GridStrategy(StrategyBase):
    """
    网格交易策略
    
    在指定价格区间内设置多层网格，低买高卖。
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "grid"
        self.name = "网格交易策略"
        
        # 网格参数
        self.grid_count = max(1, self.config.get("grid_count", 10))
        price_range_pct = self.config.get("price_range", 5.0)  # 百分比
        self.price_range = max(0.1, abs(price_range_pct)) / 100
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析并输出网格设置信号"""
        
        if len(candles) < 1:
            return None
        
        prices = [c["close"] for c in candles]
        current_price = prices[-1]
        
        # 计算网格区间
        upper_price = current_price * (1 + self.price_range)
        lower_price = current_price * (1 - self.price_range)
        grid_size = (upper_price - lower_price) / self.grid_count
        
        # 网格策略返回设置信号
        return StrategyOutput(
            symbol=symbol,
            signal_type="GRID",
            side="BUY",  # 网格通常从买入开始
            entry_price=current_price,
            stop_loss=lower_price * 0.95,
            take_profit=upper_price,
            confidence=75,
            reason=f"建立{self.grid_count}层网格，价格区间 {lower_price:.2f} - {upper_price:.2f}",
            indicators={
                "grid_count": self.grid_count,
                "upper_price": upper_price,
                "lower_price": lower_price,
                "grid_size": grid_size,
            },
        )
