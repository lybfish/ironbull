"""
Grid Optimizer - 网格搜索参数优化器

通过穷举参数组合找到最优策略参数
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from itertools import product
import time

from libs.core import get_logger

logger = get_logger("grid-optimizer")


@dataclass
class ParameterGrid:
    """
    参数网格定义
    
    示例：
        grid = ParameterGrid({
            "fast_ma": [5, 10, 15, 20],
            "slow_ma": [20, 30, 40, 50],
        })
    """
    params: Dict[str, List[Any]]
    
    def __iter__(self):
        """遍历所有参数组合"""
        keys = list(self.params.keys())
        values = list(self.params.values())
        
        for combo in product(*values):
            yield dict(zip(keys, combo))
    
    def __len__(self):
        """总组合数"""
        total = 1
        for values in self.params.values():
            total *= len(values)
        return total
    
    @classmethod
    def from_ranges(cls, ranges: Dict[str, tuple]) -> "ParameterGrid":
        """
        从范围创建网格
        
        示例：
            grid = ParameterGrid.from_ranges({
                "fast_ma": (5, 25, 5),   # start, stop, step
                "slow_ma": (20, 60, 10),
            })
        """
        params = {}
        for key, (start, stop, step) in ranges.items():
            params[key] = list(range(start, stop + 1, step))
        return cls(params)


@dataclass
class OptimizationResult:
    """优化结果"""
    # 最优参数
    best_params: Dict[str, Any]
    best_score: float
    
    # 最优结果详情
    best_result: Dict[str, Any]
    
    # 所有结果
    all_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # 统计
    total_combinations: int = 0
    elapsed_seconds: float = 0
    
    def to_dict(self) -> dict:
        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "best_result": self.best_result,
            "total_combinations": self.total_combinations,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "top_10": sorted(
                self.all_results,
                key=lambda x: x.get("score", float("-inf")),
                reverse=True
            )[:10],
        }


class GridOptimizer:
    """
    网格搜索优化器
    
    使用方式：
        optimizer = GridOptimizer(
            backtest_func=run_backtest,
            score_func=lambda r: r["total_pnl"],  # 优化目标
        )
        
        grid = ParameterGrid({
            "fast_ma": [5, 10, 15],
            "slow_ma": [20, 30, 40],
        })
        
        result = optimizer.optimize(
            strategy_code="ma_cross",
            symbol="BTC/USDT",
            timeframe="15m",
            candles=candles,
            param_grid=grid,
        )
        
        print(f"最优参数: {result.best_params}")
        print(f"最优收益: {result.best_score}")
    """
    
    def __init__(
        self,
        backtest_func: Callable,
        score_func: Optional[Callable] = None,
        constraints: Optional[Dict[str, Callable]] = None,
    ):
        """
        Args:
            backtest_func: 回测函数，签名为 (strategy_code, config, symbol, timeframe, candles) -> result
            score_func: 评分函数，默认使用总收益
            constraints: 参数约束，如 {"slow_ma": lambda p: p["slow_ma"] > p["fast_ma"]}
        """
        self.backtest_func = backtest_func
        self.score_func = score_func or self._default_score
        self.constraints = constraints or {}
    
    def _default_score(self, result: dict) -> float:
        """默认评分函数：收益 / 最大回撤（夏普风格）"""
        pnl = result.get("total_pnl", 0)
        max_dd = result.get("max_drawdown", 1)
        
        if max_dd == 0:
            return pnl
        
        # 收益回撤比
        return pnl / max(abs(max_dd), 1)
    
    def _check_constraints(self, params: dict) -> bool:
        """检查参数约束"""
        for name, check_func in self.constraints.items():
            try:
                if not check_func(params):
                    return False
            except Exception:
                return False
        return True
    
    def optimize(
        self,
        strategy_code: str,
        symbol: str,
        timeframe: str,
        candles: List[dict],
        param_grid: ParameterGrid,
        base_config: Optional[dict] = None,
        progress_callback: Optional[Callable] = None,
    ) -> OptimizationResult:
        """
        执行网格搜索优化
        
        Args:
            strategy_code: 策略代码
            symbol: 交易对
            timeframe: 时间周期
            candles: K 线数据
            param_grid: 参数网格
            base_config: 基础配置（不变的参数）
            progress_callback: 进度回调 (current, total, params, score)
        
        Returns:
            OptimizationResult
        """
        base_config = base_config or {}
        all_results = []
        
        best_params = None
        best_score = float("-inf")
        best_result = None
        
        total = len(param_grid)
        start_time = time.time()
        
        logger.info(
            "starting optimization",
            strategy=strategy_code,
            symbol=symbol,
            combinations=total,
        )
        
        for i, params in enumerate(param_grid):
            # 检查约束
            if not self._check_constraints(params):
                continue
            
            # 合并配置
            config = {**base_config, **params}
            
            try:
                # 运行回测
                result = self.backtest_func(
                    strategy_code=strategy_code,
                    config=config,
                    symbol=symbol,
                    timeframe=timeframe,
                    candles=candles,
                )
                
                # 计算得分
                score = self.score_func(result)
                
                # 记录结果
                record = {
                    "params": params,
                    "score": score,
                    "total_pnl": result.get("total_pnl", 0),
                    "total_pnl_pct": result.get("total_pnl_pct", 0),
                    "win_rate": result.get("win_rate", 0),
                    "total_trades": result.get("total_trades", 0),
                    "max_drawdown_pct": result.get("max_drawdown_pct", 0),
                }
                all_results.append(record)
                
                # 更新最优
                if score > best_score:
                    best_score = score
                    best_params = params
                    best_result = result
                
                # 进度回调
                if progress_callback:
                    progress_callback(i + 1, total, params, score)
                    
            except Exception as e:
                logger.warning("backtest failed", params=params, error=str(e))
                continue
        
        elapsed = time.time() - start_time
        
        logger.info(
            "optimization completed",
            best_params=best_params,
            best_score=best_score,
            elapsed=f"{elapsed:.2f}s",
        )
        
        return OptimizationResult(
            best_params=best_params or {},
            best_score=best_score,
            best_result=best_result or {},
            all_results=all_results,
            total_combinations=total,
            elapsed_seconds=elapsed,
        )
    
    def optimize_multiple_objectives(
        self,
        strategy_code: str,
        symbol: str,
        timeframe: str,
        candles: List[dict],
        param_grid: ParameterGrid,
        objectives: Dict[str, Callable],
        base_config: Optional[dict] = None,
    ) -> Dict[str, OptimizationResult]:
        """
        多目标优化
        
        Args:
            objectives: 多个优化目标 {"max_pnl": lambda r: r["total_pnl"], "min_drawdown": ...}
        
        Returns:
            每个目标的最优结果
        """
        results = {}
        
        for obj_name, score_func in objectives.items():
            self.score_func = score_func
            results[obj_name] = self.optimize(
                strategy_code=strategy_code,
                symbol=symbol,
                timeframe=timeframe,
                candles=candles,
                param_grid=param_grid,
                base_config=base_config,
            )
        
        return results
