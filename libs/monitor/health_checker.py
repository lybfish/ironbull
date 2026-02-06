"""
Health Checker - 服务健康巡检器

并发 HTTP GET 各服务 /health 端点，返回每个服务的 status/latency/error。
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from libs.core.logger import get_logger

log = get_logger("health-checker")


@dataclass
class ServiceStatus:
    name: str
    url: str
    healthy: bool = False
    latency_ms: float = 0.0
    error: Optional[str] = None
    checked_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "healthy": self.healthy,
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
            "checked_at": self.checked_at,
        }


class HealthChecker:
    """服务健康巡检器"""

    def __init__(self, services: List[Dict[str, str]], timeout: float = 5.0):
        """
        Args:
            services: [{"name": "data-api", "url": "http://127.0.0.1:8026/health"}, ...]
            timeout: HTTP 超时秒数
        """
        self.services = services
        self.timeout = timeout

    def _check_one(self, svc: Dict[str, str]) -> ServiceStatus:
        """检查单个服务"""
        name = svc["name"]
        url = svc["url"]
        start = time.time()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url)
            latency = (time.time() - start) * 1000
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok":
                    return ServiceStatus(name=name, url=url, healthy=True, latency_ms=latency)
                return ServiceStatus(name=name, url=url, healthy=False, latency_ms=latency, error=f"status={data.get('status')}")
            return ServiceStatus(name=name, url=url, healthy=False, latency_ms=latency, error=f"HTTP {resp.status_code}")
        except httpx.ConnectError:
            latency = (time.time() - start) * 1000
            return ServiceStatus(name=name, url=url, healthy=False, latency_ms=latency, error="连接被拒绝")
        except httpx.TimeoutException:
            latency = (time.time() - start) * 1000
            return ServiceStatus(name=name, url=url, healthy=False, latency_ms=latency, error="超时")
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ServiceStatus(name=name, url=url, healthy=False, latency_ms=latency, error=str(e))

    def check_all(self) -> List[ServiceStatus]:
        """并发检查所有服务"""
        results: List[ServiceStatus] = []
        with ThreadPoolExecutor(max_workers=min(len(self.services), 10)) as pool:
            futures = {pool.submit(self._check_one, svc): svc for svc in self.services}
            for future in as_completed(futures):
                results.append(future.result())
        # 按原始顺序排列
        order = {svc["name"]: i for i, svc in enumerate(self.services)}
        results.sort(key=lambda s: order.get(s.name, 999))
        return results
