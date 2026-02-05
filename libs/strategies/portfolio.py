"""
Strategy Portfolio - 策略组合

多策略信号融合，综合多个策略的信号做出交易决策。

融合方式：
- voting: 投票法（多数同意）
- weighted: 加权法（按权重计算）
- unanimous: 一致法（所有策略同意）
- any: 任意法（任一策略触发）
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from libs.contracts import StrategyOutput
from .base import StrategyBase


@dataclass
class StrategyVote:
    """策略投票结果"""
    strategy_code: str
    signal: Optional[StrategyOutput]
    side: Optional[str]  # BUY / SELL / None
    confidence: float
    weight: float


class PortfolioStrategy(StrategyBase):
    """
    策略组合
    
    将多个策略的信号融合，产生综合交易信号。
    
    参数：
    - strategies: 策略列表 [{"code": "ma_cross", "weight": 0.3, "config": {...}}, ...]
    - fusion_mode: 融合方式 voting / weighted / unanimous / any
    - min_agreement: 最小同意比例（voting 模式使用）
    - min_confidence: 最小置信度阈值
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "portfolio"
        self.name = "策略组合"
        
        # 获取子策略配置
        self.strategy_configs = self.config.get("strategies", [])
        self.fusion_mode = self.config.get("fusion_mode", "voting")
        self.min_agreement = self.config.get("min_agreement", 0.5)
        self.min_confidence = self.config.get("min_confidence", 60)
        
        # 初始化子策略
        self.strategies: List[Tuple[StrategyBase, float]] = []
        self._init_strategies()
    
    def _init_strategies(self):
        """初始化子策略"""
        from libs.strategies import get_strategy
        
        total_weight = 0
        for cfg in self.strategy_configs:
            code = cfg.get("code")
            weight = cfg.get("weight", 1.0)
            strategy_config = cfg.get("config", {})
            
            if code:
                try:
                    strategy = get_strategy(code, strategy_config)
                    self.strategies.append((strategy, weight))
                    total_weight += weight
                except Exception as e:
                    print(f"Warning: Failed to load strategy {code}: {e}")
        
        # 归一化权重
        if total_weight > 0:
            self.strategies = [
                (s, w / total_weight) for s, w in self.strategies
            ]
        
        # 更新名称
        codes = [s.code for s, _ in self.strategies]
        self.name = f"策略组合({'+'.join(codes)})"
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析综合信号"""
        
        if not self.strategies:
            return None
        
        # 收集所有子策略的信号
        votes: List[StrategyVote] = []
        
        for strategy, weight in self.strategies:
            try:
                signal = strategy.analyze(
                    symbol=symbol,
                    timeframe=timeframe,
                    candles=candles,
                    positions=positions,
                )
                
                side = signal.side if signal else None
                confidence = signal.confidence if signal else 0
                
                votes.append(StrategyVote(
                    strategy_code=strategy.code,
                    signal=signal,
                    side=side,
                    confidence=confidence,
                    weight=weight,
                ))
            except Exception as e:
                # 策略分析失败，记录为无信号
                votes.append(StrategyVote(
                    strategy_code=strategy.code,
                    signal=None,
                    side=None,
                    confidence=0,
                    weight=weight,
                ))
        
        # 根据融合方式产生最终信号
        if self.fusion_mode == "voting":
            return self._fusion_voting(votes, symbol, candles)
        elif self.fusion_mode == "weighted":
            return self._fusion_weighted(votes, symbol, candles)
        elif self.fusion_mode == "unanimous":
            return self._fusion_unanimous(votes, symbol, candles)
        elif self.fusion_mode == "any":
            return self._fusion_any(votes, symbol, candles)
        else:
            return self._fusion_voting(votes, symbol, candles)
    
    def _fusion_voting(self, votes: List[StrategyVote], symbol: str, 
                       candles: List[Dict]) -> Optional[StrategyOutput]:
        """投票法融合"""
        
        buy_votes = sum(1 for v in votes if v.side == "BUY")
        sell_votes = sum(1 for v in votes if v.side == "SELL")
        total = len(votes)
        
        buy_ratio = buy_votes / total if total > 0 else 0
        sell_ratio = sell_votes / total if total > 0 else 0
        
        # 检查是否达到最小同意比例
        if buy_ratio >= self.min_agreement and buy_ratio > sell_ratio:
            return self._create_signal(
                votes, "BUY", symbol, candles,
                reason=f"投票融合: {buy_votes}/{total} 看多 ({buy_ratio*100:.0f}%)"
            )
        
        if sell_ratio >= self.min_agreement and sell_ratio > buy_ratio:
            return self._create_signal(
                votes, "SELL", symbol, candles,
                reason=f"投票融合: {sell_votes}/{total} 看空 ({sell_ratio*100:.0f}%)"
            )
        
        return None
    
    def _fusion_weighted(self, votes: List[StrategyVote], symbol: str,
                         candles: List[Dict]) -> Optional[StrategyOutput]:
        """加权法融合"""
        
        buy_score = sum(v.weight * v.confidence for v in votes if v.side == "BUY")
        sell_score = sum(v.weight * v.confidence for v in votes if v.side == "SELL")
        
        # 计算买入和卖出的加权比例
        total_weight = sum(v.weight for v in votes)
        buy_ratio = buy_score / (total_weight * 100) if total_weight > 0 else 0
        sell_ratio = sell_score / (total_weight * 100) if total_weight > 0 else 0
        
        if buy_ratio >= self.min_agreement and buy_score > sell_score:
            return self._create_signal(
                votes, "BUY", symbol, candles,
                reason=f"加权融合: 多头得分 {buy_score:.0f} > 空头得分 {sell_score:.0f}"
            )
        
        if sell_ratio >= self.min_agreement and sell_score > buy_score:
            return self._create_signal(
                votes, "SELL", symbol, candles,
                reason=f"加权融合: 空头得分 {sell_score:.0f} > 多头得分 {buy_score:.0f}"
            )
        
        return None
    
    def _fusion_unanimous(self, votes: List[StrategyVote], symbol: str,
                          candles: List[Dict]) -> Optional[StrategyOutput]:
        """一致法融合（所有策略同意）"""
        
        active_votes = [v for v in votes if v.side is not None]
        
        if not active_votes:
            return None
        
        # 检查是否所有活跃信号一致
        sides = set(v.side for v in active_votes)
        
        if len(sides) == 1:
            side = list(sides)[0]
            return self._create_signal(
                votes, side, symbol, candles,
                reason=f"一致融合: {len(active_votes)} 策略一致看{('多' if side == 'BUY' else '空')}"
            )
        
        return None
    
    def _fusion_any(self, votes: List[StrategyVote], symbol: str,
                    candles: List[Dict]) -> Optional[StrategyOutput]:
        """任意法融合（任一策略触发）"""
        
        # 找到置信度最高的信号
        best_vote = None
        for v in votes:
            if v.signal and v.confidence >= self.min_confidence:
                if best_vote is None or v.confidence > best_vote.confidence:
                    best_vote = v
        
        if best_vote and best_vote.side:
            return self._create_signal(
                votes, best_vote.side, symbol, candles,
                reason=f"任意融合: {best_vote.strategy_code} 触发 (置信度 {best_vote.confidence:.0f}%)"
            )
        
        return None
    
    def _create_signal(self, votes: List[StrategyVote], side: str, symbol: str,
                       candles: List[Dict], reason: str) -> StrategyOutput:
        """创建融合信号"""
        
        current_price = candles[-1]["close"]
        
        # 综合置信度（取同方向信号的加权平均）
        same_side_votes = [v for v in votes if v.side == side]
        if same_side_votes:
            total_weight = sum(v.weight for v in same_side_votes)
            confidence = sum(v.weight * v.confidence for v in same_side_votes) / total_weight
        else:
            confidence = 60
        
        # 综合止损止盈（取同方向信号的平均）
        stop_losses = [v.signal.stop_loss for v in same_side_votes 
                       if v.signal and v.signal.stop_loss]
        take_profits = [v.signal.take_profit for v in same_side_votes 
                        if v.signal and v.signal.take_profit]
        
        stop_loss = sum(stop_losses) / len(stop_losses) if stop_losses else None
        take_profit = sum(take_profits) / len(take_profits) if take_profits else None
        
        # 构建投票详情
        vote_details = {}
        for v in votes:
            vote_details[v.strategy_code] = {
                "side": v.side,
                "confidence": v.confidence,
                "weight": v.weight,
            }
        
        return StrategyOutput(
            symbol=symbol,
            signal_type="OPEN",
            side=side,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=min(95, confidence),
            reason=reason,
            indicators={
                "fusion_mode": self.fusion_mode,
                "votes": vote_details,
                "strategies_count": len(votes),
            },
        )
