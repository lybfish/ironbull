"""
参数验证器

实现类型验证、范围验证、枚举值验证，以及 camelCase/snake_case 兼容转换。
"""

from typing import Any, Dict, List, Optional, Union
import re


def _camel_to_snake(name: str) -> str:
    """将 camelCase 转换为 snake_case"""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化配置：将 camelCase 转换为 snake_case，并合并
    
    Args:
        config: 原始配置字典（可能包含 camelCase 和 snake_case）
    
    Returns:
        标准化后的配置字典（全部为 snake_case）
    """
    normalized = {}
    
    # 先处理所有键，转换为 snake_case
    for key, value in config.items():
        snake_key = _camel_to_snake(key)
        # 如果同时存在 camelCase 和 snake_case，优先使用 snake_case
        if snake_key not in normalized or key == snake_key:
            normalized[snake_key] = value
    
    return normalized


def validate_type(value: Any, expected_type: type, param_name: str) -> Any:
    """类型验证"""
    if value is None:
        return None
    
    if expected_type == bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)
    
    if expected_type == float:
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError(f"参数 {param_name} 必须是浮点数，当前值: {value}")
    
    if expected_type == int:
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValueError(f"参数 {param_name} 必须是整数，当前值: {value}")
    
    if expected_type == str:
        return str(value)
    
    if expected_type == list:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # 支持逗号分隔的字符串，如 "0.5,0.618,0.705"
            return [x.strip() for x in value.split(",") if x.strip()]
        return [value]
    
    return value


def validate_range(
    value: float,
    param_name: str,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None
) -> float:
    """范围验证"""
    if min_val is not None and value < min_val:
        return min_val
    if max_val is not None and value > max_val:
        return max_val
    return value


def validate_enum(
    value: str,
    param_name: str,
    allowed_values: List[str],
    default: Optional[str] = None
) -> str:
    """枚举值验证"""
    if value is None:
        return default or allowed_values[0]
    
    value_lower = str(value).lower()
    for allowed in allowed_values:
        if value_lower == allowed.lower():
            return allowed
    
    # 如果不在允许列表中，返回默认值
    if default:
        return default
    return allowed_values[0]


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证并标准化配置参数
    
    参考文档第12章：参数验证规则
    
    Args:
        config: 原始配置字典
    
    Returns:
        验证并标准化后的配置字典
    """
    # 先标准化键名
    normalized = normalize_config(config)
    validated = {}
    
    # ========== Old1 对齐参数验证 ==========
    
    # 基础回测/交易参数
    validated["order_type"] = validate_enum(
        normalized.get("order_type"),
        "order_type",
        ["limit", "market", "post_only"],
        "limit"
    )
    validated["tif_bars"] = max(1, validate_type(normalized.get("tif_bars"), int, "tif_bars") or 20)
    validated["direction"] = validate_enum(
        normalized.get("direction"),
        "direction",
        ["both", "buy", "sell", "long", "short"],
        "both"
    )
    validated["cooldown_bars"] = max(0, validate_type(normalized.get("cooldown_bars"), int, "cooldown_bars") or 0)
    validated["signal_cooldown"] = max(0, validate_type(normalized.get("signal_cooldown"), int, "signal_cooldown") or 0)
    
    # 资金管理/RR参数
    validated["rr"] = validate_range(
        validate_type(normalized.get("rr"), float, "rr") or 2.0,
        "rr",
        0.1,
        10.0
    )
    validated["risk_pct"] = validate_range(
        validate_type(normalized.get("risk_pct"), float, "risk_pct") or 1.0,
        "risk_pct",
        0.1,
        10.0
    )
    validated["max_loss"] = validate_type(
        normalized.get("max_loss") or normalized.get("risk_cash"),
        float,
        "max_loss"
    ) or 100.0
    validated["max_leverage"] = validate_range(
        validate_type(normalized.get("max_leverage"), float, "max_leverage") or 10.0,
        "max_leverage",
        1.0,
        100.0
    )
    validated["min_rr"] = validate_range(
        validate_type(
            normalized.get("min_rr") or normalized.get("minRr"),
            float,
            "min_rr"
        ) or 2.0,
        "min_rr",
        0.5,
        5.0
    )
    
    # Fibo/入场核心参数
    fibo_levels_raw = normalized.get("fibo_levels") or normalized.get("fiboLevels")
    if isinstance(fibo_levels_raw, str):
        fibo_levels_list = [float(x.strip()) for x in fibo_levels_raw.split(",") if x.strip()]
    elif isinstance(fibo_levels_raw, list):
        fibo_levels_list = [float(x) for x in fibo_levels_raw if 0 < x < 1]
    else:
        fibo_levels_list = [0.5, 0.618, 0.705]
    validated["fibo_levels"] = sorted(set(fibo_levels_list))
    
    validated["fibo_tolerance"] = validate_range(
        validate_type(normalized.get("fibo_tolerance"), float, "fibo_tolerance") or 0.005,
        "fibo_tolerance",
        0.001,
        0.02
    )
    validated["entry_source"] = validate_enum(
        normalized.get("entry_source") or normalized.get("entry"),
        "entry_source",
        ["auto", "ob", "swing", "fvg", "confluence", "any"],
        "auto"
    )
    validated["entry_mode"] = validate_enum(
        normalized.get("entry_mode") or normalized.get("confirm_mode"),
        "entry_mode",
        ["limit", "market", "retest", "auto"],
        "limit"
    )
    validated["session"] = validate_enum(
        normalized.get("session"),
        "session",
        ["all", "london", "ny", "asia", "custom", "auto"],
        "all"
    )
    validated["htf_timeframe"] = validate_type(
        normalized.get("htf_timeframe") or normalized.get("htfTimeframe"),
        str,
        "htf_timeframe"
    ) or "1h"
    validated["fibo_fallback"] = validate_type(
        normalized.get("fibo_fallback") or normalized.get("fiboFallback"),
        bool,
        "fibo_fallback"
    ) if normalized.get("fibo_fallback") is not None or normalized.get("fiboFallback") is not None else True
    
    # 结构/趋势偏好参数
    validated["structure"] = validate_enum(
        normalized.get("structure"),
        "structure",
        ["bos", "choch", "both"],
        "both"
    )
    validated["bias"] = validate_enum(
        normalized.get("bias"),
        "bias",
        ["with_trend", "counter", "both"],
        "with_trend"
    )
    swing_raw = normalized.get("swing")
    if swing_raw == "auto" or (isinstance(swing_raw, str) and swing_raw.lower() == "auto"):
        validated["swing"] = "auto"
    else:
        validated["swing"] = max(1, validate_type(swing_raw, int, "swing") or 3)
    
    htf_swing_raw = normalized.get("htf_swing") or normalized.get("htfSwing")
    if htf_swing_raw == "auto" or (isinstance(htf_swing_raw, str) and htf_swing_raw.lower() == "auto"):
        validated["htf_swing"] = "auto"
    else:
        validated["htf_swing"] = max(1, validate_type(htf_swing_raw, int, "htf_swing") or 3)
    
    validated["auto_profile"] = validate_enum(
        normalized.get("auto_profile") or normalized.get("autoProfile"),
        "auto_profile",
        ["off", "conservative", "medium", "aggressive"],
        "off"
    )
    
    # 止损/止盈/回踩确认参数
    # 与 old1 对齐：stopBufferPct=0.05 表示 0.05%，内部需要除以 100 变成 0.0005
    raw_sl_buffer = validate_type(
        normalized.get("stop_buffer_pct") or normalized.get("stopBufferPct"),
        float,
        "stop_buffer_pct"
    ) or 0.05
    # 如果 raw 值 >= 0.01，说明用户传的是百分比形式（如 0.05 = 0.05%），需要 /100
    if raw_sl_buffer >= 0.01:
        validated["stop_buffer_pct"] = validate_range(
            raw_sl_buffer / 100.0, "stop_buffer_pct", 0.00005, 0.01
        )
    else:
        # 已经是小数形式（如 0.0005）
        validated["stop_buffer_pct"] = validate_range(
            raw_sl_buffer, "stop_buffer_pct", 0.00005, 0.01
        )
    # 止损缓冲模式: "fixed" = 固定百分比, "atr" = ATR动态缓冲
    validated["stop_buffer_mode"] = validate_enum(
        normalized.get("stop_buffer_mode"),
        "stop_buffer_mode",
        ["fixed", "atr"],
        "fixed"
    )
    # ATR乘数(仅 stop_buffer_mode="atr" 时生效): SL = swing - ATR * multiplier
    validated["sl_atr_multiplier"] = validate_range(
        validate_type(normalized.get("sl_atr_multiplier"), float, "sl_atr_multiplier") or 0.5,
        "sl_atr_multiplier",
        0.1,
        3.0
    )
    validated["stop_source"] = validate_enum(
        normalized.get("stop_source") or normalized.get("stopSource"),
        "stop_source",
        ["auto", "ob", "swing", "structure"],
        "auto"
    )
    validated["tp_mode"] = validate_enum(
        normalized.get("tp_mode") or normalized.get("tpMode"),
        "tp_mode",
        ["swing", "rr", "fibo"],
        "swing"
    )
    validated["retest_bars"] = max(1, validate_type(
        normalized.get("retest_bars") or normalized.get("retestBars"),
        int,
        "retest_bars"
    ) or 20)
    validated["retest_cancel_order"] = validate_type(
        normalized.get("retest_cancel_order") or normalized.get("retestCancelOrder"),
        bool,
        "retest_cancel_order"
    ) if normalized.get("retest_cancel_order") is not None or normalized.get("retestCancelOrder") is not None else False
    validated["retest_ignore_stop_touch"] = validate_type(
        normalized.get("retest_ignore_stop_touch") or normalized.get("retestIgnoreStopTouch"),
        bool,
        "retest_ignore_stop_touch"
    ) if normalized.get("retest_ignore_stop_touch") is not None or normalized.get("retestIgnoreStopTouch") is not None else False
    validated["pinbar_ratio"] = validate_range(
        validate_type(
            normalized.get("pinbar_ratio") or normalized.get("pinbarRatio"),
            float,
            "pinbar_ratio"
        ) or 1.5,
        "pinbar_ratio",
        1.0,
        4.0
    )
    validated["allow_engulf"] = validate_type(
        normalized.get("allow_engulf") or normalized.get("allowEngulf"),
        bool,
        "allow_engulf"
    ) if normalized.get("allow_engulf") is not None or normalized.get("allowEngulf") is not None else True
    validated["market_reject"] = validate_type(
        normalized.get("market_reject") or normalized.get("marketReject"),
        bool,
        "market_reject"
    ) if normalized.get("market_reject") is not None or normalized.get("marketReject") is not None else True
    validated["market_max_dev_atr"] = validate_range(
        validate_type(
            normalized.get("market_max_dev_atr") or normalized.get("marketMaxDevAtr"),
            float,
            "market_max_dev_atr"
        ) or 0.3,
        "market_max_dev_atr",
        0.0,
        2.0
    )
    
    # SMC扩展参数（OB/FVG/流动性）
    validated["liquidity"] = validate_enum(
        normalized.get("liquidity"),
        "liquidity",
        ["external", "internal", "both", "none", "auto"],
        "external"
    )
    validated["ob_type"] = validate_enum(
        normalized.get("ob_type") or normalized.get("obType"),
        "ob_type",
        ["reversal", "continuation"],
        "reversal"
    )
    validated["wick_ob"] = validate_type(
        normalized.get("wick_ob") or normalized.get("wickOb"),
        bool,
        "wick_ob"
    ) if normalized.get("wick_ob") is not None or normalized.get("wickOb") is not None else True
    use_ob_raw = normalized.get("use_ob") or normalized.get("useOb")
    if use_ob_raw == "auto" or (isinstance(use_ob_raw, str) and use_ob_raw.lower() == "auto"):
        validated["use_ob"] = "auto"
    else:
        validated["use_ob"] = validate_type(use_ob_raw, bool, "use_ob") if use_ob_raw is not None else True
    validated["ob_lookback"] = max(2, validate_type(
        normalized.get("ob_lookback") or normalized.get("obLookback"),
        int,
        "ob_lookback"
    ) or 20)
    validated["ob_min_body_ratio"] = validate_range(
        validate_type(normalized.get("ob_min_body_ratio"), float, "ob_min_body_ratio") or 0.5,
        "ob_min_body_ratio",
        0.1,
        1.0
    )
    validated["ob_max_tests"] = max(1, validate_type(normalized.get("ob_max_tests"), int, "ob_max_tests") or 3)
    validated["ob_valid_bars"] = max(10, validate_type(normalized.get("ob_valid_bars"), int, "ob_valid_bars") or 100)
    
    use_fvg_raw = normalized.get("use_fvg") or normalized.get("useFvg")
    if use_fvg_raw == "auto" or (isinstance(use_fvg_raw, str) and use_fvg_raw.lower() == "auto"):
        validated["use_fvg"] = "auto"
    else:
        validated["use_fvg"] = validate_type(use_fvg_raw, bool, "use_fvg") if use_fvg_raw is not None else True
    validated["fvg_min_pct"] = validate_range(
        validate_type(
            normalized.get("fvg_min_pct") or normalized.get("fvgMinPct"),
            float,
            "fvg_min_pct"
        ) or 0.15,
        "fvg_min_pct",
        0.01,
        1.0
    ) / 100.0  # 转换为小数
    validated["fvg_valid_bars"] = max(10, validate_type(normalized.get("fvg_valid_bars"), int, "fvg_valid_bars") or 50)
    validated["fvg_fill_mode"] = validate_enum(
        normalized.get("fvg_fill_mode"),
        "fvg_fill_mode",
        ["touch", "full", "partial"],
        "touch"
    )
    
    use_sweep_raw = normalized.get("use_sweep") or normalized.get("useSweep")
    if use_sweep_raw == "auto" or (isinstance(use_sweep_raw, str) and use_sweep_raw.lower() == "auto"):
        validated["use_sweep"] = "auto"
    else:
        validated["use_sweep"] = validate_type(use_sweep_raw, bool, "use_sweep") if use_sweep_raw is not None else True
    validated["sweep_len"] = max(1, validate_type(
        normalized.get("sweep_len") or normalized.get("sweepLen"),
        int,
        "sweep_len"
    ) or 5)
    validated["limit_offset_pct"] = validate_range(
        validate_type(
            normalized.get("limit_offset_pct") or normalized.get("limitOffsetPct"),
            float,
            "limit_offset_pct"
        ) or 0.2,
        "limit_offset_pct",
        0.0,
        0.8
    )
    validated["limit_tol_atr"] = validate_range(
        validate_type(
            normalized.get("limit_tol_atr") or normalized.get("limitTolAtr"),
            float,
            "limit_tol_atr"
        ) or 0.2,
        "limit_tol_atr",
        0.0,
        2.0
    )
    validated["atr_period"] = max(2, validate_type(
        normalized.get("atr_period") or normalized.get("atrPeriod"),
        int,
        "atr_period"
    ) or 14)
    
    # ========== 回踩确认形态参数 ==========
    validated["enable_pinbar"] = validate_type(normalized.get("enable_pinbar"), bool, "enable_pinbar") if normalized.get("enable_pinbar") is not None else True
    validated["enable_engulfing"] = validated.get("allow_engulf", True)
    validated["enable_morning_star"] = validate_type(normalized.get("enable_morning_star"), bool, "enable_morning_star") if normalized.get("enable_morning_star") is not None else True
    validated["enable_evening_star"] = validate_type(normalized.get("enable_evening_star"), bool, "enable_evening_star") if normalized.get("enable_evening_star") is not None else True
    validated["enable_close_reject"] = validate_type(normalized.get("enable_close_reject"), bool, "enable_close_reject") if normalized.get("enable_close_reject") is not None else True
    validated["enable_golden_k"] = validate_type(normalized.get("enable_golden_k"), bool, "enable_golden_k") if normalized.get("enable_golden_k") is not None else False
    validated["enable_inside_bar"] = validate_type(normalized.get("enable_inside_bar"), bool, "enable_inside_bar") if normalized.get("enable_inside_bar") is not None else False
    validated["enable_wick_reject"] = validate_type(normalized.get("enable_wick_reject"), bool, "enable_wick_reject") if normalized.get("enable_wick_reject") is not None else False
    validated["wick_min_ratio"] = validate_range(
        validate_type(normalized.get("wick_min_ratio"), float, "wick_min_ratio") or 1.5,
        "wick_min_ratio",
        1.0,
        4.0
    )
    validated["enable_fakey"] = validate_type(normalized.get("enable_fakey"), bool, "enable_fakey") if normalized.get("enable_fakey") is not None else False
    validated["pattern_weights"] = normalized.get("pattern_weights") or {}
    validated["pattern_min_score"] = validate_range(
        validate_type(normalized.get("pattern_min_score"), float, "pattern_min_score") or 1.0,
        "pattern_min_score",
        0.0,
        10.0
    )
    validated["require_retest"] = validate_type(normalized.get("require_retest"), bool, "require_retest") if normalized.get("require_retest") is not None else True
    
    # ========== 方案C: 限价先成交，确认后决定去留 ==========
    # confirm_after_fill=True: 限价单触碰即成交，随后 N 根K线检查确认形态
    #   有确认 → 持有（保留 SL/TP）
    #   无确认 → 平仓（UNCONFIRMED）
    validated["confirm_after_fill"] = validate_type(
        normalized.get("confirm_after_fill"), bool, "confirm_after_fill"
    ) if normalized.get("confirm_after_fill") is not None else False
    validated["post_fill_confirm_bars"] = max(1, validate_type(
        normalized.get("post_fill_confirm_bars"), int, "post_fill_confirm_bars"
    ) or 5)
    
    # ========== 流动性参数 ==========
    validated["allow_external"] = validate_type(normalized.get("allow_external"), bool, "allow_external") if normalized.get("allow_external") is not None else True
    validated["allow_internal"] = validate_type(normalized.get("allow_internal"), bool, "allow_internal") if normalized.get("allow_internal") is not None else True
    validated["liquidity_lookback"] = max(5, validate_type(normalized.get("liquidity_lookback"), int, "liquidity_lookback") or 20)
    validated["htf_liquidity_timeframe"] = validate_type(normalized.get("htf_liquidity_timeframe"), str, "htf_liquidity_timeframe") or "4h"
    validated["session_mode"] = validate_enum(
        normalized.get("session_mode"),
        "session_mode",
        ["none", "forex", "custom"],
        "forex"
    )
    validated["session_hl_lookback"] = max(1, validate_type(normalized.get("session_hl_lookback"), int, "session_hl_lookback") or 1)
    validated["fake_break_min_ratio"] = validate_range(
        validate_type(normalized.get("fake_break_min_ratio"), float, "fake_break_min_ratio") or 0.3,
        "fake_break_min_ratio",
        0.0,
        1.0
    )
    validated["fake_break_max_bars"] = max(1, validate_type(normalized.get("fake_break_max_bars"), int, "fake_break_max_bars") or 5)
    validated["sweep_confirm_pattern"] = validate_enum(
        normalized.get("sweep_confirm_pattern"),
        "sweep_confirm_pattern",
        ["rejection", "structure_only", "both"],
        "rejection"
    )
    validated["sweep_min_rr"] = validate_range(
        validate_type(normalized.get("sweep_min_rr"), float, "sweep_min_rr") or 1.5,
        "sweep_min_rr",
        0.5,
        5.0
    )
    validated["sweep_mtf_confirm"] = validate_type(normalized.get("sweep_mtf_confirm"), bool, "sweep_mtf_confirm") if normalized.get("sweep_mtf_confirm") is not None else False
    
    # ========== 外汇理论参数 ==========
    validated["enable_session_filter"] = validate_type(normalized.get("enable_session_filter"), bool, "enable_session_filter") if normalized.get("enable_session_filter") is not None else False
    validated["allowed_sessions"] = normalized.get("allowed_sessions") or ["london", "ny"]
    validated["enable_news_filter"] = validate_type(normalized.get("enable_news_filter"), bool, "enable_news_filter") if normalized.get("enable_news_filter") is not None else False
    validated["news_impact_levels"] = normalized.get("news_impact_levels") or ["high"]
    validated["news_blackout_minutes"] = max(0, validate_type(normalized.get("news_blackout_minutes"), int, "news_blackout_minutes") or 30)
    validated["amd_entry_mode"] = validate_enum(
        normalized.get("amd_entry_mode"),
        "amd_entry_mode",
        ["off", "basic", "advanced"],
        "off"
    )
    validated["amd_phase_filter"] = normalized.get("amd_phase_filter") or []
    validated["exit_level"] = validate_enum(
        normalized.get("exit_level"),
        "exit_level",
        ["basic", "intermediate", "advanced"],
        "basic"
    )
    validated["direction_htf_timeframe"] = validate_type(normalized.get("direction_htf_timeframe"), str, "direction_htf_timeframe") or "4h"
    validated["direction_mtf_confirm"] = validate_type(normalized.get("direction_mtf_confirm"), bool, "direction_mtf_confirm") if normalized.get("direction_mtf_confirm") is not None else True
    validated["direction_kline_combo"] = validate_type(normalized.get("direction_kline_combo"), bool, "direction_kline_combo") if normalized.get("direction_kline_combo") is not None else True
    
    # ========== 风险管理参数 ==========
    validated["daily_max_loss"] = validate_type(normalized.get("daily_max_loss"), float, "daily_max_loss") or 300.0
    validated["daily_max_loss_pct"] = validate_range(
        validate_type(normalized.get("daily_max_loss_pct"), float, "daily_max_loss_pct") or 5.0,
        "daily_max_loss_pct",
        1.0,
        20.0
    )
    validated["max_consecutive_loss"] = max(1, validate_type(normalized.get("max_consecutive_loss"), int, "max_consecutive_loss") or 3)
    validated["account_risk_mode"] = validate_enum(
        normalized.get("account_risk_mode"),
        "account_risk_mode",
        ["fixed_cash", "fixed_pct", "hybrid"],
        "fixed_cash"
    )
    validated["sl_trailing_mode"] = validate_enum(
        normalized.get("sl_trailing_mode"),
        "sl_trailing_mode",
        ["off", "fixed_atr", "structure"],
        "off"
    )
    validated["sl_trailing_atr_mult"] = validate_range(
        validate_type(normalized.get("sl_trailing_atr_mult"), float, "sl_trailing_atr_mult") or 1.5,
        "sl_trailing_atr_mult",
        0.5,
        5.0
    )
    validated["partial_take_profit_levels"] = normalized.get("partial_take_profit_levels") or [1.0, 2.0]
    validated["partial_tp_ratios"] = normalized.get("partial_tp_ratios") or [0.5, 0.5]
    validated["hard_tp_rr"] = validate_range(
        validate_type(normalized.get("hard_tp_rr"), float, "hard_tp_rr") or 3.0,
        "hard_tp_rr",
        1.0,
        10.0
    )
    
    # ========== 实盘优化参数 ==========
    validated["spread_points"] = max(0.0, validate_type(normalized.get("spread_points"), float, "spread_points") or 0.0)
    validated["slippage_mode"] = validate_enum(
        normalized.get("slippage_mode"),
        "slippage_mode",
        ["fixed", "percentage", "volatility_based"],
        "fixed"
    )
    validated["slippage_value"] = validate_range(
        validate_type(normalized.get("slippage_value"), float, "slippage_value") or 0.5,
        "slippage_value",
        0.0,
        10.0
    )
    validated["post_only"] = validate_type(normalized.get("post_only"), bool, "post_only") if normalized.get("post_only") is not None else False
    validated["price_protection_pct"] = validate_range(
        validate_type(normalized.get("price_protection_pct"), float, "price_protection_pct") or 0.3,
        "price_protection_pct",
        0.0,
        5.0
    )
    
    # ========== 信号质量参数 ==========
    validated["enable_signal_score"] = validate_type(normalized.get("enable_signal_score"), bool, "enable_signal_score") if normalized.get("enable_signal_score") is not None else True
    validated["score_components"] = normalized.get("score_components") or {
        "structure": 1.0,
        "ob": 1.0,
        "fvg": 1.0,
        "liquidity": 1.0,
        "pattern": 1.0
    }
    validated["min_signal_score"] = validate_range(
        validate_type(normalized.get("min_signal_score"), float, "min_signal_score") or 0.0,
        "min_signal_score",
        0.0,
        10.0
    )
    validated["score_decay_bars"] = max(1, validate_type(normalized.get("score_decay_bars"), int, "score_decay_bars") or 10)
    validated["duplicate_signal_filter_bars"] = max(0, validate_type(normalized.get("duplicate_signal_filter_bars"), int, "duplicate_signal_filter_bars") or 3)
    
    # ========== 动量模块参数 ==========
    validated["enable_momentum"] = validate_type(normalized.get("enable_momentum"), bool, "enable_momentum") if normalized.get("enable_momentum") is not None else False
    
    # ========== 自适应参数 ==========
    validated["volatility_thresholds"] = normalized.get("volatility_thresholds") or {}
    validated["rr_auto_adjust"] = validate_type(normalized.get("rr_auto_adjust"), bool, "rr_auto_adjust") if normalized.get("rr_auto_adjust") is not None else False
    validated["sl_buffer_auto_adjust"] = validate_type(normalized.get("sl_buffer_auto_adjust"), bool, "sl_buffer_auto_adjust") if normalized.get("sl_buffer_auto_adjust") is not None else False
    validated["preset_profile"] = validate_enum(
        normalized.get("preset_profile"),
        "preset_profile",
        ["none", "conservative", "balanced", "aggressive", "forex_specific"],
        "none"
    )
    validated["preset_overrides_allowed"] = validate_type(
        normalized.get("preset_overrides_allowed"),
        bool,
        "preset_overrides_allowed"
    ) if normalized.get("preset_overrides_allowed") is not None else True
    
    # ========== HTF 相关参数 ==========
    validated["htf_multiplier"] = max(1, validate_type(normalized.get("htf_multiplier"), int, "htf_multiplier") or 4)
    validated["htf_ema_fast"] = max(1, validate_type(normalized.get("htf_ema_fast"), int, "htf_ema_fast") or 20)
    validated["htf_ema_slow"] = max(1, validate_type(normalized.get("htf_ema_slow"), int, "htf_ema_slow") or 50)
    validated["require_htf_filter"] = validate_type(
        normalized.get("require_htf_filter"),
        bool,
        "require_htf_filter"
    ) if normalized.get("require_htf_filter") is not None else True
    
    # ========== OB/FVG 联动参数 ==========
    validated["sd_reversal_required"] = validate_type(normalized.get("sd_reversal_required"), bool, "sd_reversal_required") if normalized.get("sd_reversal_required") is not None else False
    validated["ob_fvg_confluence"] = validate_type(normalized.get("ob_fvg_confluence"), bool, "ob_fvg_confluence") if normalized.get("ob_fvg_confluence") is not None else True
    validated["ob_fvg_min_overlap_pct"] = validate_range(
        validate_type(normalized.get("ob_fvg_min_overlap_pct"), float, "ob_fvg_min_overlap_pct") or 0.3,
        "ob_fvg_min_overlap_pct",
        0.0,
        1.0
    )
    
    return validated
