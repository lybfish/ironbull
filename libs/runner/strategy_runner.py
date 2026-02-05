"""
Strategy Runner

定时/事件驱动的策略执行器。
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import httpx

from libs.strategies import get_strategy, STRATEGY_REGISTRY
from libs.contracts import StrategyOutput


logger = logging.getLogger(__name__)


@dataclass
class StrategyTask:
    """
    策略任务配置
    
    定义一个策略运行任务的所有参数。
    """
    # 必填字段（无默认值）
    task_id: str
    strategy_code: str
    symbol: str
    timeframe: str
    
    # 可选字段（有默认值）
    strategy_config: Dict = field(default_factory=dict)
    interval_seconds: int = 60
    candle_limit: int = 100
    auto_submit: bool = True
    enabled: bool = True
    
    # 运行状态（自动管理）
    last_run: Optional[float] = None
    last_signal: Optional[StrategyOutput] = None
    run_count: int = 0
    signal_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None


class StrategyRunner:
    """
    策略运行器
    
    管理多个策略任务的定时执行。
    """
    
    def __init__(
        self,
        data_provider_url: str = "http://localhost:8010",
        signal_hub_url: str = "http://localhost:8001",
    ):
        self.data_provider_url = data_provider_url.rstrip("/")
        self.signal_hub_url = signal_hub_url.rstrip("/")
        
        self._tasks: Dict[str, StrategyTask] = {}
        self._running = False
        self._http_client: Optional[httpx.AsyncClient] = None
        
        # 回调函数
        self._on_signal: Optional[Callable[[StrategyTask, StrategyOutput], Any]] = None
        self._on_error: Optional[Callable[[StrategyTask, Exception], Any]] = None
    
    def add_task(self, task: StrategyTask) -> None:
        """添加策略任务"""
        if task.strategy_code not in STRATEGY_REGISTRY:
            raise ValueError(f"Unknown strategy: {task.strategy_code}")
        self._tasks[task.task_id] = task
        logger.info(f"Added task: {task.task_id} ({task.strategy_code} on {task.symbol}/{task.timeframe})")
    
    def remove_task(self, task_id: str) -> bool:
        """移除策略任务"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            logger.info(f"Removed task: {task_id}")
            return True
        return False
    
    def get_task(self, task_id: str) -> Optional[StrategyTask]:
        """获取策略任务"""
        return self._tasks.get(task_id)
    
    def list_tasks(self) -> List[StrategyTask]:
        """列出所有任务"""
        return list(self._tasks.values())
    
    def set_on_signal(self, callback: Callable[[StrategyTask, StrategyOutput], Any]) -> None:
        """设置信号回调"""
        self._on_signal = callback
    
    def set_on_error(self, callback: Callable[[StrategyTask, Exception], Any]) -> None:
        """设置错误回调"""
        self._on_error = callback
    
    async def _fetch_candles(self, symbol: str, timeframe: str, limit: int) -> Optional[List[Dict]]:
        """从 data-provider 获取 K 线数据"""
        try:
            # 替换 localhost 为 127.0.0.1 避免 IPv6 解析问题
            url = self.data_provider_url.replace("localhost", "127.0.0.1")
            url = f"{url}/api/candles"
            params = {"symbol": symbol, "timeframe": timeframe, "limit": limit}
            
            resp = await self._http_client.get(url, params=params, timeout=10.0)
            resp.raise_for_status()
            
            data = resp.json()
            return data.get("candles", [])
        except Exception as e:
            logger.error(f"Failed to fetch candles: {e}")
            return None
    
    async def _submit_signal(self, task: StrategyTask, output: StrategyOutput) -> bool:
        """提交信号到 signal-hub"""
        try:
            # 替换 localhost 为 127.0.0.1 避免 IPv6 解析问题
            url = self.signal_hub_url.replace("localhost", "127.0.0.1")
            url = f"{url}/api/signals"
            payload = {
                "strategy_code": task.strategy_code,
                "timeframe": task.timeframe,
                "output": {
                    "symbol": output.symbol,
                    "signal_type": output.signal_type,
                    "side": output.side,
                    "entry_price": output.entry_price,
                    "stop_loss": output.stop_loss,
                    "take_profit": output.take_profit,
                    "confidence": output.confidence,
                    "reason": output.reason,
                    "indicators": output.indicators,
                },
            }
            
            resp = await self._http_client.post(url, json=payload, timeout=10.0)
            resp.raise_for_status()
            
            result = resp.json()
            logger.info(f"Signal submitted: {result.get('signal_id', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Failed to submit signal: {e}")
            return False
    
    async def _run_task(self, task: StrategyTask) -> Optional[StrategyOutput]:
        """执行单个策略任务"""
        try:
            # 获取 K 线数据
            candles = await self._fetch_candles(task.symbol, task.timeframe, task.candle_limit)
            if not candles:
                logger.warning(f"No candles for {task.task_id}")
                return None
            
            # 获取策略实例
            strategy = get_strategy(task.strategy_code, task.strategy_config)
            
            # 运行分析
            output = strategy.analyze(task.symbol, task.timeframe, candles)
            
            # 更新任务状态
            task.last_run = time.time()
            task.run_count += 1
            
            if output:
                task.last_signal = output
                task.signal_count += 1
                
                logger.info(
                    f"[{task.task_id}] Signal: {output.side} {output.signal_type} "
                    f"@ {output.entry_price:.2f} (confidence: {output.confidence})"
                )
                
                # 回调
                if self._on_signal:
                    self._on_signal(task, output)
                
                # 自动提交
                if task.auto_submit:
                    await self._submit_signal(task, output)
            else:
                logger.debug(f"[{task.task_id}] No signal")
            
            return output
            
        except Exception as e:
            task.error_count += 1
            task.last_error = str(e)
            logger.error(f"[{task.task_id}] Error: {e}")
            
            if self._on_error:
                self._on_error(task, e)
            
            return None
    
    async def run_once(self, task_id: str) -> Optional[StrategyOutput]:
        """手动运行一次指定任务"""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        # 确保 HTTP 客户端存在
        if not self._http_client:
            self._http_client = httpx.AsyncClient()
        
        return await self._run_task(task)
    
    async def _scheduler_loop(self) -> None:
        """调度循环"""
        while self._running:
            now = time.time()
            
            for task in self._tasks.values():
                if not task.enabled:
                    continue
                
                # 检查是否到达运行时间
                if task.last_run is None or (now - task.last_run) >= task.interval_seconds:
                    asyncio.create_task(self._run_task(task))
            
            # 每秒检查一次
            await asyncio.sleep(1)
    
    async def start(self) -> None:
        """启动运行器"""
        if self._running:
            logger.warning("Runner already started")
            return
        
        self._running = True
        self._http_client = httpx.AsyncClient()
        
        logger.info(f"StrategyRunner started with {len(self._tasks)} tasks")
        
        await self._scheduler_loop()
    
    async def stop(self) -> None:
        """停止运行器"""
        self._running = False
        
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        
        logger.info("StrategyRunner stopped")
    
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    
    def get_stats(self) -> Dict:
        """获取运行统计"""
        total_runs = sum(t.run_count for t in self._tasks.values())
        total_signals = sum(t.signal_count for t in self._tasks.values())
        total_errors = sum(t.error_count for t in self._tasks.values())
        
        return {
            "running": self._running,
            "task_count": len(self._tasks),
            "enabled_tasks": sum(1 for t in self._tasks.values() if t.enabled),
            "total_runs": total_runs,
            "total_signals": total_signals,
            "total_errors": total_errors,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "strategy": t.strategy_code,
                    "symbol": t.symbol,
                    "timeframe": t.timeframe,
                    "interval": t.interval_seconds,
                    "enabled": t.enabled,
                    "run_count": t.run_count,
                    "signal_count": t.signal_count,
                    "error_count": t.error_count,
                    "last_run": datetime.fromtimestamp(t.last_run).isoformat() if t.last_run else None,
                }
                for t in self._tasks.values()
            ],
        }
