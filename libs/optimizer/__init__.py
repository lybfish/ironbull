"""
IronBull Optimizer Module

策略参数优化器

组件：
- GridOptimizer: 网格搜索优化（穷举）
- GeneticOptimizer: 遗传算法优化（智能搜索）
"""

from .grid_optimizer import GridOptimizer, OptimizationResult, ParameterGrid
from .genetic_optimizer import (
    GeneticOptimizer,
    GeneticConfig,
    GeneticResult,
    ParameterSpace,
    Individual,
    fitness_pnl,
    fitness_sharpe,
    fitness_calmar,
    fitness_composite,
)

__all__ = [
    # 网格搜索
    "GridOptimizer",
    "OptimizationResult",
    "ParameterGrid",
    # 遗传算法
    "GeneticOptimizer",
    "GeneticConfig",
    "GeneticResult",
    "ParameterSpace",
    "Individual",
    "fitness_pnl",
    "fitness_sharpe",
    "fitness_calmar",
    "fitness_composite",
]
