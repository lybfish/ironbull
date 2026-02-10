"""
信号质量评分模块

实现信号评分系统、时间衰减、重复信号过滤等
"""

from typing import Dict, List, Optional
from collections import deque


class SignalScorer:
    """信号评分器"""
    
    def __init__(self, config: Dict):
        self.enable_signal_score = config.get("enable_signal_score", True)
        self.score_components = config.get("score_components", {
            "structure": 1.0,
            "ob": 1.0,
            "fvg": 1.0,
            "liquidity": 1.0,
            "pattern": 1.0,
        })
        self.min_signal_score = config.get("min_signal_score", 0.0)
        self.score_decay_bars = config.get("score_decay_bars", 10)
        self.duplicate_signal_filter_bars = config.get("duplicate_signal_filter_bars", 3)
        
        # 记录最近信号（用于重复过滤）
        self._recent_signals = deque(maxlen=100)
    
    def calculate_score(
        self,
        has_structure: bool,
        has_ob: bool,
        has_fvg: bool,
        has_liquidity: bool,
        pattern_score: float = 0.0,
        bars_since_signal: int = 0
    ) -> float:
        """
        计算信号综合评分
        
        Args:
            has_structure: 是否有结构信号
            has_ob: 是否有订单块
            has_fvg: 是否有FVG
            has_liquidity: 是否有流动性扫除
            pattern_score: 形态评分
            bars_since_signal: 信号产生后的K线数（用于时间衰减）
        
        Returns:
            综合评分
        """
        if not self.enable_signal_score:
            return 1.0
        
        score = 0.0
        
        if has_structure:
            score += self.score_components.get("structure", 1.0)
        if has_ob:
            score += self.score_components.get("ob", 1.0)
        if has_fvg:
            score += self.score_components.get("fvg", 1.0)
        if has_liquidity:
            score += self.score_components.get("liquidity", 1.0)
        if pattern_score > 0:
            score += pattern_score * self.score_components.get("pattern", 1.0)
        
        # 时间衰减
        if bars_since_signal > 0:
            decay_factor = max(0.5, 1.0 - (bars_since_signal / self.score_decay_bars) * 0.5)
            score *= decay_factor
        
        return score
    
    def check_duplicate(
        self,
        symbol: str,
        side: str,
        current_bar_index: int
    ) -> bool:
        """
        检查是否是重复信号
        
        Args:
            symbol: 交易对
            side: 交易方向
            current_bar_index: 当前K线索引
        
        Returns:
            是否是重复信号（True=重复，应过滤）
        """
        key = f"{symbol}_{side}"
        
        for signal in self._recent_signals:
            if signal["key"] == key:
                bars_diff = current_bar_index - signal["bar_index"]
                if bars_diff <= self.duplicate_signal_filter_bars:
                    return True
        
        # 记录新信号
        self._recent_signals.append({
            "key": key,
            "bar_index": current_bar_index,
        })
        
        return False
    
    def meets_min_score(self, score: float) -> bool:
        """检查是否满足最小评分要求"""
        return score >= self.min_signal_score
