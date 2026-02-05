"""
Genetic Algorithm Optimizer

遗传算法参数优化器
比网格搜索更高效地探索大参数空间
"""

import random
import math
from typing import Dict, List, Callable, Any, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class Individual:
    """个体（一组参数）"""
    genes: Dict[str, Any]  # 参数值
    fitness: float = 0.0   # 适应度分数
    metrics: Dict = field(default_factory=dict)  # 回测指标


@dataclass 
class GeneticConfig:
    """遗传算法配置"""
    population_size: int = 50      # 种群大小
    generations: int = 20          # 迭代代数
    elite_ratio: float = 0.1       # 精英比例（直接保留）
    crossover_rate: float = 0.8    # 交叉概率
    mutation_rate: float = 0.2     # 变异概率
    tournament_size: int = 3       # 锦标赛选择大小
    early_stop_generations: int = 5  # 连续N代无改进则停止


@dataclass
class GeneticResult:
    """遗传算法优化结果"""
    best_params: Dict[str, Any]
    best_fitness: float
    best_metrics: Dict
    generations_run: int
    population_history: List[Dict]  # 每代统计
    all_individuals: List[Dict]     # 所有测试过的个体


class ParameterSpace:
    """参数空间定义"""
    
    def __init__(self):
        self.params: Dict[str, Dict] = {}
    
    def add_int(self, name: str, low: int, high: int, step: int = 1):
        """添加整数参数"""
        self.params[name] = {
            "type": "int",
            "low": low,
            "high": high,
            "step": step,
        }
        return self
    
    def add_float(self, name: str, low: float, high: float, precision: int = 2):
        """添加浮点参数"""
        self.params[name] = {
            "type": "float",
            "low": low,
            "high": high,
            "precision": precision,
        }
        return self
    
    def add_choice(self, name: str, choices: List[Any]):
        """添加选择参数"""
        self.params[name] = {
            "type": "choice",
            "choices": choices,
        }
        return self
    
    def random_value(self, name: str) -> Any:
        """生成随机参数值"""
        spec = self.params[name]
        
        if spec["type"] == "int":
            steps = (spec["high"] - spec["low"]) // spec["step"]
            return spec["low"] + random.randint(0, steps) * spec["step"]
        
        elif spec["type"] == "float":
            value = random.uniform(spec["low"], spec["high"])
            return round(value, spec["precision"])
        
        elif spec["type"] == "choice":
            return random.choice(spec["choices"])
        
        return None
    
    def mutate_value(self, name: str, current: Any) -> Any:
        """变异参数值"""
        spec = self.params[name]
        
        if spec["type"] == "int":
            # 在当前值附近变异
            delta = random.choice([-2, -1, 1, 2]) * spec["step"]
            new_val = current + delta
            return max(spec["low"], min(spec["high"], new_val))
        
        elif spec["type"] == "float":
            # 高斯变异
            range_size = spec["high"] - spec["low"]
            delta = random.gauss(0, range_size * 0.1)
            new_val = current + delta
            new_val = max(spec["low"], min(spec["high"], new_val))
            return round(new_val, spec["precision"])
        
        elif spec["type"] == "choice":
            # 随机选择另一个
            return random.choice(spec["choices"])
        
        return current
    
    def random_individual(self) -> Dict[str, Any]:
        """生成随机个体"""
        return {name: self.random_value(name) for name in self.params}


class GeneticOptimizer:
    """
    遗传算法优化器
    
    使用方法：
    1. 定义参数空间 ParameterSpace
    2. 提供回测函数 backtest_func(params) -> metrics
    3. 提供适应度函数 fitness_func(metrics) -> float
    4. 调用 optimize() 获取最优参数
    """
    
    def __init__(
        self,
        param_space: ParameterSpace,
        backtest_func: Callable[[Dict], Dict],
        fitness_func: Callable[[Dict], float],
        config: GeneticConfig = None,
        constraints: List[Callable[[Dict], bool]] = None,
    ):
        self.param_space = param_space
        self.backtest_func = backtest_func
        self.fitness_func = fitness_func
        self.config = config or GeneticConfig()
        self.constraints = constraints or []
        
        self._all_individuals: List[Individual] = []
        self._population_history: List[Dict] = []
        self._best_fitness = float("-inf")
        self._generations_without_improvement = 0
    
    def _is_valid(self, genes: Dict) -> bool:
        """检查参数是否满足约束"""
        for constraint in self.constraints:
            if not constraint(genes):
                return False
        return True
    
    def _create_individual(self, genes: Dict) -> Individual:
        """创建并评估个体"""
        try:
            metrics = self.backtest_func(genes)
            fitness = self.fitness_func(metrics)
        except Exception as e:
            metrics = {"error": str(e)}
            fitness = float("-inf")
        
        individual = Individual(genes=genes, fitness=fitness, metrics=metrics)
        self._all_individuals.append(individual)
        return individual
    
    def _initialize_population(self) -> List[Individual]:
        """初始化种群"""
        population = []
        attempts = 0
        max_attempts = self.config.population_size * 10
        
        while len(population) < self.config.population_size and attempts < max_attempts:
            genes = self.param_space.random_individual()
            if self._is_valid(genes):
                individual = self._create_individual(genes)
                population.append(individual)
            attempts += 1
        
        return population
    
    def _tournament_select(self, population: List[Individual]) -> Individual:
        """锦标赛选择"""
        tournament = random.sample(population, min(self.config.tournament_size, len(population)))
        return max(tournament, key=lambda x: x.fitness)
    
    def _crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Dict, Dict]:
        """交叉操作（均匀交叉）"""
        child1_genes = {}
        child2_genes = {}
        
        for name in self.param_space.params:
            if random.random() < 0.5:
                child1_genes[name] = parent1.genes[name]
                child2_genes[name] = parent2.genes[name]
            else:
                child1_genes[name] = parent2.genes[name]
                child2_genes[name] = parent1.genes[name]
        
        return child1_genes, child2_genes
    
    def _mutate(self, genes: Dict) -> Dict:
        """变异操作"""
        mutated = genes.copy()
        
        for name in self.param_space.params:
            if random.random() < self.config.mutation_rate:
                mutated[name] = self.param_space.mutate_value(name, mutated[name])
        
        return mutated
    
    def _evolve(self, population: List[Individual]) -> List[Individual]:
        """进化一代"""
        # 按适应度排序
        population.sort(key=lambda x: x.fitness, reverse=True)
        
        # 精英保留
        elite_count = max(1, int(self.config.population_size * self.config.elite_ratio))
        new_population = population[:elite_count]
        
        # 生成新个体
        while len(new_population) < self.config.population_size:
            # 选择父代
            parent1 = self._tournament_select(population)
            parent2 = self._tournament_select(population)
            
            # 交叉
            if random.random() < self.config.crossover_rate:
                child1_genes, child2_genes = self._crossover(parent1, parent2)
            else:
                child1_genes = parent1.genes.copy()
                child2_genes = parent2.genes.copy()
            
            # 变异
            child1_genes = self._mutate(child1_genes)
            child2_genes = self._mutate(child2_genes)
            
            # 验证约束并添加
            for genes in [child1_genes, child2_genes]:
                if len(new_population) < self.config.population_size and self._is_valid(genes):
                    individual = self._create_individual(genes)
                    new_population.append(individual)
        
        return new_population
    
    def _record_generation(self, generation: int, population: List[Individual]):
        """记录每代统计信息"""
        fitnesses = [ind.fitness for ind in population if ind.fitness > float("-inf")]
        
        if not fitnesses:
            return
        
        best = max(population, key=lambda x: x.fitness)
        
        stats = {
            "generation": generation,
            "best_fitness": best.fitness,
            "best_params": best.genes,
            "avg_fitness": sum(fitnesses) / len(fitnesses),
            "min_fitness": min(fitnesses),
            "max_fitness": max(fitnesses),
            "population_size": len(population),
            "unique_individuals": len(self._all_individuals),
        }
        
        self._population_history.append(stats)
        
        # 检查是否有改进
        if best.fitness > self._best_fitness:
            self._best_fitness = best.fitness
            self._generations_without_improvement = 0
        else:
            self._generations_without_improvement += 1
    
    def optimize(self, verbose: bool = True) -> GeneticResult:
        """
        运行遗传算法优化
        
        Args:
            verbose: 是否打印进度
        
        Returns:
            GeneticResult
        """
        if verbose:
            print(f"🧬 遗传算法优化开始")
            print(f"   种群大小: {self.config.population_size}")
            print(f"   最大代数: {self.config.generations}")
            print(f"   参数数量: {len(self.param_space.params)}")
            print()
        
        # 初始化种群
        population = self._initialize_population()
        self._record_generation(0, population)
        
        if verbose:
            best = max(population, key=lambda x: x.fitness)
            print(f"Gen 0: Best={best.fitness:.4f}, Params={best.genes}")
        
        # 迭代进化
        for gen in range(1, self.config.generations + 1):
            population = self._evolve(population)
            self._record_generation(gen, population)
            
            best = max(population, key=lambda x: x.fitness)
            
            if verbose:
                print(f"Gen {gen}: Best={best.fitness:.4f}, Avg={self._population_history[-1]['avg_fitness']:.4f}")
            
            # 早停检查
            if self._generations_without_improvement >= self.config.early_stop_generations:
                if verbose:
                    print(f"\n⚡ 早停: 连续 {self.config.early_stop_generations} 代无改进")
                break
        
        # 找出全局最优
        best_individual = max(self._all_individuals, key=lambda x: x.fitness)
        
        if verbose:
            print(f"\n✅ 优化完成!")
            print(f"   最优适应度: {best_individual.fitness:.4f}")
            print(f"   最优参数: {best_individual.genes}")
            print(f"   总评估次数: {len(self._all_individuals)}")
        
        return GeneticResult(
            best_params=best_individual.genes,
            best_fitness=best_individual.fitness,
            best_metrics=best_individual.metrics,
            generations_run=len(self._population_history) - 1,
            population_history=self._population_history,
            all_individuals=[
                {"params": ind.genes, "fitness": ind.fitness, "metrics": ind.metrics}
                for ind in self._all_individuals
            ],
        )


# 预定义的适应度函数
def fitness_pnl(metrics: Dict) -> float:
    """以收益为适应度"""
    return metrics.get("total_pnl", float("-inf"))


def fitness_sharpe(metrics: Dict) -> float:
    """以夏普率为适应度"""
    pnl = metrics.get("total_pnl", 0)
    trades = metrics.get("total_trades", 0)
    win_rate = metrics.get("win_rate", 0)
    drawdown = metrics.get("max_drawdown_pct", 100)
    
    if trades < 3:
        return float("-inf")
    
    # 简化夏普估算
    if drawdown == 0:
        return pnl * 0.1
    return (pnl / (drawdown + 1)) * math.sqrt(trades)


def fitness_calmar(metrics: Dict) -> float:
    """以卡尔玛比率为适应度（收益/最大回撤）"""
    pnl_pct = metrics.get("total_pnl_pct", 0)
    drawdown = metrics.get("max_drawdown_pct", 100)
    trades = metrics.get("total_trades", 0)
    
    if trades < 3 or drawdown == 0:
        return float("-inf") if trades < 3 else pnl_pct
    
    return pnl_pct / drawdown


def fitness_composite(metrics: Dict) -> float:
    """综合适应度（平衡收益、胜率、回撤）"""
    pnl = metrics.get("total_pnl", 0)
    pnl_pct = metrics.get("total_pnl_pct", 0)
    trades = metrics.get("total_trades", 0)
    win_rate = metrics.get("win_rate", 0)
    drawdown = metrics.get("max_drawdown_pct", 100)
    
    if trades < 3:
        return float("-inf")
    
    # 归一化各指标
    pnl_score = pnl_pct / 100  # 100% 收益 = 1
    win_score = win_rate / 100  # 100% 胜率 = 1
    dd_score = max(0, 1 - drawdown / 50)  # 0% 回撤 = 1, 50%+ = 0
    trade_score = min(1, trades / 20)  # 20笔交易 = 1
    
    # 加权组合
    return (pnl_score * 0.4 + win_score * 0.2 + dd_score * 0.3 + trade_score * 0.1)
