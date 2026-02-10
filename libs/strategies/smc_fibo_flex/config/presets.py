"""
参数预设模板

提供四套预设配置：conservative（保守）、balanced（中等）、aggressive（激进）、forex_specific（外汇专用）
参考文档第11章：参数配置示例
"""

from typing import Dict, Any


def get_preset(preset_name: str) -> Dict[str, Any]:
    """
    获取预设配置
    
    Args:
        preset_name: 预设名称（conservative/balanced/aggressive/forex_specific）
    
    Returns:
        预设配置字典
    """
    presets = {
        "conservative": _get_conservative_preset(),
        "balanced": _get_balanced_preset(),
        "aggressive": _get_aggressive_preset(),
        "forex_specific": _get_forex_specific_preset(),
    }
    
    return presets.get(preset_name.lower(), {})


def merge_preset(user_config: Dict[str, Any], preset_name: str = None) -> Dict[str, Any]:
    """
    合并预设配置和用户配置
    
    Args:
        user_config: 用户配置
        preset_name: 预设名称（如果为 None，则从 user_config 中读取 preset_profile）
    
    Returns:
        合并后的配置（用户配置优先）
    """
    if preset_name is None:
        preset_name = user_config.get("preset_profile", "none")
    
    if preset_name == "none":
        return user_config.copy()
    
    preset_config = get_preset(preset_name)
    if not preset_config:
        return user_config.copy()
    
    # 合并：用户配置优先
    merged = preset_config.copy()
    merged.update(user_config)
    
    return merged


def _get_conservative_preset() -> Dict[str, Any]:
    """保守配置（低风险）"""
    return {
        "max_loss": 50,
        "min_rr": 2.0,
        "fibo_levels": [0.5, 0.618, 0.705],
        "fibo_tolerance": 0.003,
        "structure": "both",
        "bias": "with_trend",
        "stop_buffer_pct": 0.05,
        "tp_mode": "swing",
        "require_retest": True,
        "retest_bars": 20,
        "pinbar_ratio": 2.0,
        "allow_engulf": True,
        "use_ob": "auto",
        "use_fvg": "auto",
        "use_sweep": "auto",
        "auto_profile": "conservative",
        "require_htf_filter": True,
        "htf_multiplier": 4,
        "enable_signal_score": True,
        "min_signal_score": 1.5,
    }


def _get_balanced_preset() -> Dict[str, Any]:
    """中等配置（平衡）"""
    return {
        "max_loss": 100,
        "min_rr": 1.8,
        "fibo_levels": [0.382, 0.5, 0.618, 0.705],
        "fibo_tolerance": 0.005,
        "structure": "both",
        "bias": "with_trend",
        "stop_buffer_pct": 0.05,
        "tp_mode": "swing",
        "require_retest": True,
        "retest_bars": 20,
        "pinbar_ratio": 2.0,
        "allow_engulf": True,
        "use_ob": True,
        "use_fvg": True,
        "use_sweep": "auto",
        "htf_multiplier": 4,
        "require_htf_filter": True,
        "auto_profile": "medium",
        "enable_signal_score": True,
        "min_signal_score": 1.0,
    }


def _get_aggressive_preset() -> Dict[str, Any]:
    """激进配置（高风险高收益）"""
    return {
        "max_loss": 150,
        "min_rr": 1.5,
        "fibo_levels": [0.382, 0.5, 0.618],
        "fibo_tolerance": 0.008,
        "structure": "both",
        "bias": "both",
        "stop_buffer_pct": 0.04,
        "tp_mode": "rr",
        "rr": 3.0,
        "require_retest": False,
        "use_ob": True,
        "use_fvg": True,
        "use_sweep": True,
        "liquidity": "both",
        "htf_multiplier": 3,
        "require_htf_filter": False,
        "auto_profile": "aggressive",
        "enable_signal_score": False,
        "min_signal_score": 0.0,
    }


def _get_forex_specific_preset() -> Dict[str, Any]:
    """外汇市场专用配置"""
    return {
        "max_loss": 100,
        "min_rr": 2.0,
        "fibo_levels": [0.5, 0.618, 0.705],
        "structure": "both",
        "bias": "with_trend",
        "stop_buffer_pct": 0.05,
        "tp_mode": "swing",
        "use_ob": "auto",
        "use_fvg": "auto",
        "use_sweep": "auto",
        "liquidity": "external",
        "htf_multiplier": 4,
        "require_htf_filter": True,
        "enable_session_filter": True,
        "allowed_sessions": ["london", "ny"],
        "enable_news_filter": True,
        "news_impact_levels": ["high"],
        "news_blackout_minutes": 30,
        "amd_entry_mode": "basic",
        "direction_htf_timeframe": "4h",
        "direction_mtf_confirm": True,
        "auto_profile": "medium",
    }
