"""
通知器基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class NotifyResult:
    """通知结果"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message_id": self.message_id,
            "error": self.error,
        }


class NotifierBase(ABC):
    """通知器基类"""
    
    @abstractmethod
    def send(self, title: str, content: str, **kwargs) -> NotifyResult:
        """发送通知"""
        pass
    
    @abstractmethod
    def send_signal(self, signal: Dict[str, Any]) -> NotifyResult:
        """发送交易信号通知"""
        pass
    
    @abstractmethod
    def send_alert(self, alert_type: str, message: str, **kwargs) -> NotifyResult:
        """发送告警通知"""
        pass
