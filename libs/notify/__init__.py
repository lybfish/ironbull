"""
通知模块 - 支持多渠道信号推送

支持的渠道：
- Telegram Bot
- 企业微信（待实现）
- 飞书（待实现）
"""

from .telegram import TelegramNotifier
from .base import NotifierBase, NotifyResult

__all__ = [
    "TelegramNotifier",
    "NotifierBase",
    "NotifyResult",
]
