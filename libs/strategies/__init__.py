"""
IronBull Strategies Library

策略基类和具体策略实现。
从 old3 迁移的所有策略。
"""

from .base import StrategyBase

# 基础策略
from .ma_cross import MACrossStrategy
from .macd_strategy import MACDStrategy
from .rsi_strategy import RSIStrategy
from .rsi_boll import RSIBollStrategy
from .boll_squeeze import BollSqueezeStrategy
from .breakout import BreakoutStrategy
from .momentum import MomentumStrategy

# 趋势策略
from .trend_aggressive import TrendAggressiveStrategy
from .trend_add import TrendAddStrategy
from .swing import SwingStrategy
from .ma_dense import MADenseStrategy

# 震荡/反转策略
from .reversal import ReversalStrategy
from .scalping import ScalpingStrategy
from .arbitrage import ArbitrageStrategy

# 对冲策略
from .hedge import HedgeStrategy
from .hedge_conservative import HedgeConservativeStrategy
from .reversal_hedge import ReversalHedgeStrategy

# 高级策略
from .smc import SMCStrategy
from .mtf import MTFStrategy
from .sr_break import SRBreakStrategy
from .grid import GridStrategy
from .hft import HFTStrategy

# 经典量化策略
from .ema_cross import EMACrossStrategy
from .turtle import TurtleStrategy
from .mean_reversion import MeanReversionStrategy
from .keltner import KeltnerStrategy
from .supertrend import SuperTrendStrategy

# 策略组合
from .portfolio import PortfolioStrategy

__all__ = [
    "StrategyBase",
    # 基础策略
    "MACrossStrategy",
    "MACDStrategy",
    "RSIStrategy",
    "RSIBollStrategy",
    "BollSqueezeStrategy",
    "BreakoutStrategy",
    "MomentumStrategy",
    # 趋势策略
    "TrendAggressiveStrategy",
    "TrendAddStrategy",
    "SwingStrategy",
    "MADenseStrategy",
    # 震荡/反转策略
    "ReversalStrategy",
    "ScalpingStrategy",
    "ArbitrageStrategy",
    # 对冲策略
    "HedgeStrategy",
    "HedgeConservativeStrategy",
    "ReversalHedgeStrategy",
    # 高级策略
    "SMCStrategy",
    "MTFStrategy",
    "SRBreakStrategy",
    "GridStrategy",
    "HFTStrategy",
    # 经典量化策略
    "EMACrossStrategy",
    "TurtleStrategy",
    "MeanReversionStrategy",
    "KeltnerStrategy",
    "SuperTrendStrategy",
    # 策略组合
    "PortfolioStrategy",
]

# 策略注册表（strategy_code -> Strategy Class）
STRATEGY_REGISTRY = {
    # 基础策略
    "ma_cross": MACrossStrategy,
    "macd": MACDStrategy,
    "rsi": RSIStrategy,
    "rsi_boll": RSIBollStrategy,
    "boll_squeeze": BollSqueezeStrategy,
    "breakout": BreakoutStrategy,
    "momentum": MomentumStrategy,
    # 趋势策略
    "trend_aggressive": TrendAggressiveStrategy,
    "trend_add": TrendAddStrategy,
    "swing": SwingStrategy,
    "ma_dense": MADenseStrategy,
    # 震荡/反转策略
    "reversal": ReversalStrategy,
    "scalping": ScalpingStrategy,
    "arbitrage": ArbitrageStrategy,
    # 对冲策略
    "hedge": HedgeStrategy,
    "hedge_conservative": HedgeConservativeStrategy,
    "reversal_hedge": ReversalHedgeStrategy,
    # 高级策略
    "smc": SMCStrategy,
    "mtf": MTFStrategy,
    "sr_break": SRBreakStrategy,
    "grid": GridStrategy,
    "hft": HFTStrategy,
    # 经典量化策略
    "ema_cross": EMACrossStrategy,
    "turtle": TurtleStrategy,
    "mean_reversion": MeanReversionStrategy,
    "keltner": KeltnerStrategy,
    "supertrend": SuperTrendStrategy,
    # 策略组合
    "portfolio": PortfolioStrategy,
}


def get_strategy(strategy_code: str, config: dict = None) -> StrategyBase:
    """
    根据 strategy_code 获取策略实例
    
    Args:
        strategy_code: 策略代码
        config: 策略配置
    
    Returns:
        StrategyBase 实例
    
    Raises:
        ValueError: 未知的策略代码
    """
    if strategy_code not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy: {strategy_code}")
    
    cls = STRATEGY_REGISTRY[strategy_code]
    return cls(config or {})


def list_strategies() -> list:
    """
    列出所有可用策略
    
    Returns:
        策略信息列表
    """
    strategies = []
    for code, cls in STRATEGY_REGISTRY.items():
        instance = cls()
        strategies.append({
            "code": code,
            "name": instance.name,
            "version": instance.version,
        })
    return strategies
