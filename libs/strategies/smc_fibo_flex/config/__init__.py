"""
SMC Fibo Flex 策略配置模块
"""

from .validator import validate_config, normalize_config
from .presets import get_preset, merge_preset

__all__ = [
    "validate_config",
    "normalize_config",
    "get_preset",
    "merge_preset",
]
