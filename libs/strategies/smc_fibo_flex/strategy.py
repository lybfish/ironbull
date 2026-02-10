"""
SMC Fibo Flex 策略主类

全新的、独立的 SMC Fibonacci 策略实现
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from libs.contracts import StrategyOutput
from libs.strategies.base import StrategyBase
from libs.indicators import atr

from .config.validator import validate_config
from .config.presets import merge_preset
from .utils.swing_points import find_swing_points
from .utils.trend_detection import detect_trend, get_htf_trend
from .modules.structure import detect_bos, detect_choch, filter_by_structure, filter_by_bias
from .modules.fibonacci import calculate_fibo_levels, price_in_fibo_zone, calculate_fibo_extension, apply_fibo_fallback
from .modules.rejection_patterns import detect_rejection
from .modules.risk_manager import (
    calculate_position_size,
    calculate_stop_loss,
    calculate_take_profit,
    ensure_min_rr,
    calculate_rr_ratio
)
from .modules.order_blocks import find_order_blocks, find_nearest_order_block
from .modules.fvg import find_fvgs, find_nearest_fvg
from .modules.liquidity import detect_liquidity_sweep, detect_fake_break
from .modules.session_filter import check_session_filter, check_news_filter, get_session_risk_factor
from .modules.amd_theory import detect_amd_phase, check_amd_entry
from .modules.signal_scorer import SignalScorer
from .modules.auto_adjust import apply_auto_profile, auto_adjust_rr, auto_adjust_sl_buffer


class SMCFiboFlexStrategy(StrategyBase):
    """
    SMC Fibo Flex 策略
    
    全新的、独立的 SMC Fibonacci 策略，实现完整参数文档中的所有功能
    适用于外汇和加密货币市场
    """
    
    # 需要完整历史，配合增量缓存：每步只检查新增K线附近的摆动点 → O(1)/步
    # 列表切片 candles[:i+1] 仅复制指针，2000根仅~20ms，不是瓶颈
    requires_full_history = True
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "smc_fibo_flex"
        self.name = "SMC斐波那契灵活策略"
        self.version = "1.0.0"
        
        # 加载预设并合并用户配置
        user_config = config or {}
        preset_name = user_config.get("preset_profile", "none")
        if preset_name != "none":
            merged_config = merge_preset(user_config, preset_name)
        else:
            merged_config = user_config.copy()
        
        # 验证并标准化配置
        self.config = validate_config(merged_config)
        
        # 应用自适应参数调整
        # 注意：这里先不应用，等有candles数据后再应用
        
        # 初始化信号评分器
        self.signal_scorer = SignalScorer(self.config)
        
        # 回踩确认状态管理
        self._pending = None
        self._pending_created_at = None
        
        # 步骤计数器：替代 len(candles)-1，在固定窗口模式下跟踪绝对位置
        self._step_counter = 0
        
        # 信号去重：记录最近一次信号的方向和时间
        self._last_signal_side = None
        self._last_signal_index = -1
        self._signal_cooldown = self.config.get("signal_cooldown", 5)  # 默认5根K线冷却期
        
        # 统计计数
        self.signal_count = 0

        
        # 像old1一样：持久化趋势状态
        self._persistent_trend = "neutral"
        
        # 性能优化：缓存上次的计算结果
        self._cache = {
            "last_candle_count": 0,
            "last_candle_hash": None,
            "swing_highs": None,
            "swing_lows": None,
            "trend": None,
            "htf_trend": None,
            "last_swing_param": None,       # 缓存 swing 参数，变了就全量重算
            "auto_profile_config": None,    # 缓存 auto_profile 结果
            "auto_profile_step": 0,         # 上次 auto_profile 计算的步数
        }
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """
        分析策略，返回 StrategyOutput
        
        完整流程：
        1. 参数验证与预设加载
        2. 自适应参数调整（如果启用）
        3. 时区/新闻过滤（如果启用）
        4. 识别摆动点
        5. 判断趋势（LTF + HTF）
        6. 结构检测（BOS/CHoCH）
        7. 方向过滤（bias, structure）
        8. 识别 Order Block / FVG / 流动性
        9. 计算斐波那契回撤位
        10. 生成信号候选（entry, stop, tp）
        11. 风险管理检查（min_rr, 仓位计算）
        12. 回踩确认（如果 require_retest=True）
        13. 信号质量评分（如果启用）
        14. 返回 StrategyOutput 或 None
        """
        if len(candles) < 50:
            return None
        
        # ─── 持仓感知（与 old1 对齐）───
        # old1: `if not open_order and not open_trade and pos == 0 and not pending`
        # 有持仓时不产生新信号，避免频繁翻转导致过度交易
        if positions:
            has_pos = positions.get("has_position", False)
            has_long = positions.get("has_long", False)
            has_short = positions.get("has_short", False)
            if has_pos or has_long or has_short:
                # 已有持仓 → 仅处理回踩确认（pending），不产生新信号
                if self.config.get("require_retest", True) and self._pending:
                    return self._check_pending_result(symbol, candles)
                return None
        
        # 递增步骤计数器（绝对位置标记，不依赖 len(candles)）
        self._step_counter += 1
        
        # 应用自适应参数调整（性能优化：每 50 步才重算，波动率不会逐根K线剧变）
        if self._step_counter - self._cache["auto_profile_step"] >= 50 or self._cache["auto_profile_config"] is None:
            self.config = apply_auto_profile(self.config, candles)
            if self.config.get("rr_auto_adjust", False):
                self.config["min_rr"] = auto_adjust_rr(self.config, candles, self.config["min_rr"])
            if self.config.get("sl_buffer_auto_adjust", False):
                self.config["stop_buffer_pct"] = auto_adjust_sl_buffer(
                    self.config, candles, self.config["stop_buffer_pct"]
                )
            self._cache["auto_profile_config"] = self.config
            self._cache["auto_profile_step"] = self._step_counter
        else:
            self.config = self._cache["auto_profile_config"]
        
        current = candles[-1]
        current_price = current["close"]
        current_timestamp = current.get("timestamp") or current.get("time")
        if isinstance(current_timestamp, str):
            try:
                current_timestamp = int(datetime.fromisoformat(current_timestamp).timestamp())
            except:
                current_timestamp = int(datetime.now().timestamp())
        
        # 时区/新闻过滤
        if not check_session_filter(
            current_timestamp,
            self.config.get("enable_session_filter", False),
            self.config.get("allowed_sessions", [])
        ):
            return None
        
        if not check_news_filter(
            current_timestamp,
            self.config.get("enable_news_filter", False),
            self.config.get("news_impact_levels", [])
        ):
            return None
        
        # AMD理论过滤
        if self.config.get("amd_entry_mode") != "off":
            amd_phase = detect_amd_phase(candles)
            if not check_amd_entry(
                self.config.get("amd_entry_mode", "off"),
                self.config.get("amd_phase_filter", []),
                amd_phase
            ):
                return None
        
        # 检查回踩确认状态
        if self.config.get("require_retest", True) and self._pending:
            result = self._check_pending(symbol, candles, current_timestamp)
            if isinstance(result, StrategyOutput):
                return result
            if result == "waiting":
                return None
        
        # 识别摆动点（性能优化：增量更新）
        candle_count = len(candles)
        last_candle_hash = candles[-1].get("timestamp") if candles else None
        swing = self.config.get("swing", 5)  # 默认改为5，对齐old1
        
        # 如果只是新增了一根K线且swing参数未变，增量更新
        if (self._cache["last_candle_count"] == candle_count - 1 and 
            self._cache["swing_highs"] is not None and 
            self._cache["swing_lows"] is not None and
            self._cache["last_swing_param"] == swing and
            candle_count > swing * 2):
            # 增量更新：检查最后swing*2+1根K线（因为新K线可能影响之前的摆动点）
            swing_highs = self._cache["swing_highs"].copy()
            swing_lows = self._cache["swing_lows"].copy()
            
            # 需要重新检查的范围：从倒数swing*2+1根K线开始
            check_start = max(swing, candle_count - swing * 2 - 1)
            
            # 移除受影响的旧摆动点（保留 index < check_start 的部分，已有序）
            # 用截断代替 listcomp：因为列表按 index 排序，找到分界点直接切片
            cut_h = len(swing_highs)
            for k in range(len(swing_highs) - 1, -1, -1):
                if swing_highs[k].index < check_start:
                    break
                cut_h = k
            swing_highs = swing_highs[:cut_h]
            
            cut_l = len(swing_lows)
            for k in range(len(swing_lows) - 1, -1, -1):
                if swing_lows[k].index < check_start:
                    break
                cut_l = k
            swing_lows = swing_lows[:cut_l]
            
            # 重新检查这个范围内的所有K线（按 index 递增，结果天然有序，无需排序）
            from .utils.swing_points import SwingPoint
            for i in range(check_start, candle_count - swing):
                hi = candles[i]["high"]
                lo = candles[i]["low"]
                
                # 检查高点（回测模式：检查左右两侧）
                is_swing_high = all(hi >= candles[j]["high"] for j in range(i - swing, i + swing + 1))
                if is_swing_high:
                    swing_highs.append(SwingPoint(index=i, price=hi, type="high", timestamp=candles[i].get("timestamp")))
                
                # 检查低点
                is_swing_low = all(lo <= candles[j]["low"] for j in range(i - swing, i + swing + 1))
                if is_swing_low:
                    swing_lows.append(SwingPoint(index=i, price=lo, type="low", timestamp=candles[i].get("timestamp")))
            
            self._cache["swing_highs"] = swing_highs
            self._cache["swing_lows"] = swing_lows
            self._cache["last_candle_count"] = candle_count
            self._cache["last_candle_hash"] = last_candle_hash
            self._cache["last_swing_param"] = swing
        else:
            # 完全重新计算（确保正确性）
            swing_highs, swing_lows = find_swing_points(
                candles,
                swing,
                realtime_mode=False
            )
            self._cache["swing_highs"] = swing_highs
            self._cache["swing_lows"] = swing_lows
            self._cache["last_candle_count"] = candle_count
            self._cache["last_candle_hash"] = last_candle_hash
            self._cache["last_swing_param"] = swing
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None
        
        # 判断趋势（像old1一样：优先使用持久化趋势）
        if self._persistent_trend == "neutral":
             # 初始状态尝试从摆动点检测
            self._persistent_trend = detect_trend(candles, swing_highs, swing_lows)
        
        trend = self._persistent_trend
        
        # HTF趋势（性能优化：每 20 步更新一次，HTF趋势变化缓慢）
        if self._cache["htf_trend"] is not None and self._step_counter % 20 != 0:
            htf_trend = self._cache["htf_trend"]
        else:
            htf_trend = get_htf_trend(
                candles,
                self.config.get("htf_multiplier", 4),
                self.config.get("htf_ema_fast", 20),
                self.config.get("htf_ema_slow", 50)
            )
            self._cache["htf_trend"] = htf_trend
        
        # HTF过滤
        if self.config.get("require_htf_filter", True):
            if trend == "bullish" and htf_trend == "bearish":
                return None
            if trend == "bearish" and htf_trend == "bullish":
                return None
        
        # 结构检测
        bos = detect_bos(candles, swing_highs, swing_lows)
        choch = detect_choch(candles, swing_highs, swing_lows, trend)

        # DEBUG: 打印 BOS 检测情况
        if self._step_counter % 500 == 0:
            print(f"Step {self._step_counter}: Trend={trend}, BOS={bos}, CHoCH={choch}, Swings(H/L)={len(swing_highs)}/{len(swing_lows)}")
        
        # 像 old1 一样：BOS/CHoCH 检测后立即更新持久化趋势
        if bos == "BUY":
            self._persistent_trend = "bullish"
        elif bos == "SELL":
            self._persistent_trend = "bearish"
        if choch == "SELL":
            self._persistent_trend = "bearish"
        elif choch == "BUY":
            self._persistent_trend = "bullish"
            
        trend = self._persistent_trend

        
        # 方向过滤
        side = filter_by_structure(
            None,
            self.config.get("structure", "both"),
            bos,
            choch
        )
        
        # 斐波那契Fallback
        if not side and self.config.get("fibo_fallback", True):
            side, _ = apply_fibo_fallback(side, trend, htf_trend)
        
        # Bias过滤（使用更新后的 trend，而非原始 trend）
        if side:
            side = filter_by_bias(
                side,
                self.config.get("bias", "with_trend"),
                htf_trend if htf_trend != "neutral" else trend
            )
        
        if not side:
            # print(f"Step {self._step_counter}: No side (bias/structure filtered)")
            return None
        
        # 识别Order Block / FVG / 流动性
        # 注意：OB和FVG的查找函数内部已经做了lookback限制，不需要我们再次限制

        order_blocks = []
        if self.config.get("use_ob") in (True, "auto"):
            order_blocks = find_order_blocks(
                candles,
                self.config.get("ob_type", "reversal"),
                self.config.get("ob_lookback", 20),
                self.config.get("ob_min_body_ratio", 0.5),
                self.config.get("wick_ob", True)
            )
        
        fvgs = []
        if self.config.get("use_fvg") in (True, "auto"):
            fvgs = find_fvgs(
                candles,
                self.config.get("fvg_min_pct", 0.15),
                self.config.get("ob_lookback", 20)
            )
        
        # 计算斐波那契回撤位
        recent_high = swing_highs[-1].price
        recent_low = swing_lows[-1].price
        swing_range = recent_high - recent_low
        
        if swing_range <= 0:
            return None
        
        # 像old1一样：计算斐波那契位
        # old1的计算方式：
        # BUY: entry = swing_high - swing_range * level
        # SELL: entry = swing_low + swing_range * level
        fibo_levels_list = self.config.get("fibo_levels", [0.5, 0.618, 0.705])
        mid_price = (recent_high + recent_low) / 2.0
        
        # 像old1一样：检测到结构后，遍历所有合适的斐波那契位，生成限价单
        current_price = candles[-1]["close"]
        allow_limit_orders = self.config.get("allow_limit_orders", True)
        
        # 生成信号候选
        candidates = []
        
        # 遍历所有斐波那契位（像old1一样）
        for fibo_level in fibo_levels_list:
            if side == "BUY":
                # BUY信号：从高点回撤
                entry = recent_high - swing_range * fibo_level
                # 只使用下半部分的斐波那契位
                if entry > mid_price:
                    continue
            else:
                # SELL信号：从低点反弹（old1的计算方式）
                entry = recent_low + swing_range * fibo_level
                # 只使用上半部分的斐波那契位
                if entry < mid_price:
                    continue
            
            # 检查价格是否在斐波那契区域（用于立即入场，否则是限价单）
            price_in_zone = abs(entry - current_price) / current_price <= self.config.get("fibo_tolerance", 0.005)
            if price_in_zone:
                # 如果价格在区域，使用当前价格（立即入场）
                entry = current_price
            
            # 找到最近的Order Block
            ob = None
            if order_blocks:
                ob = find_nearest_order_block(
                    order_blocks,
                    side,
                    entry,
                    self.config.get("ob_max_tests", 3),
                    self.config.get("ob_valid_bars", 100),
                    len(candles) - 1
                )
            
            # 计算止损（stop_buffer_pct 已在 validator 中标准化为小数）
            stop_loss = calculate_stop_loss(
                side,
                entry,
                ob,
                recent_high,
                recent_low,
                self.config.get("stop_source", "auto"),
                self.config["stop_buffer_pct"]
            )
            
            if entry == stop_loss:
                continue
            
            # 计算止盈
            fibo_extension_dict = calculate_fibo_extension(recent_high, recent_low)
            take_profit = calculate_take_profit(
                side,
                entry,
                stop_loss,
                self.config.get("tp_mode", "swing"),
                recent_high,
                recent_low,
                self.config.get("rr", 2.0),
                fibo_extension_dict
            )
            
            # 确保最小RR
            take_profit, rr_ratio = ensure_min_rr(
                side,
                entry,
                stop_loss,
                take_profit,
                self.config.get("min_rr", 2.0)
            )
            
            if rr_ratio < self.config.get("min_rr", 2.0):
                # if self._step_counter < 1000: print(f"Step {self._step_counter}: Candidate RR {rr_ratio} < min_rr")
                continue
            
            # 计算仓位
            position_size = calculate_position_size(
                entry,
                stop_loss,
                self.config.get("max_loss", 100)
            )
            
            if position_size <= 0:
                # if self._step_counter < 1000: print(f"Step {self._step_counter}: Position size {position_size} <= 0")
                continue
            
            candidates.append({
                "entry": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "rr_ratio": rr_ratio,
                "fibo_level": fibo_level,
                "position_size": position_size,
                "ob": ob,
            })
        
        if not candidates:
            # 像old1一样：如果没有合适的斐波那契候选，使用mid_price作为fallback
            # 这样可以确保至少有一个信号，即使价格不在斐波那契位
            entry = mid_price
            # stop_buffer_pct 已在 validator.py 中标准化为小数（如 0.0005）
            _buf = self.config["stop_buffer_pct"]
            if side == "BUY":
                base_stop = recent_low * (1 - _buf)
                tp = recent_high
            else:
                base_stop = recent_high * (1 + _buf)
                tp = recent_low
            
            # 计算止损（stop_buffer_pct 已在 validator 中标准化为小数）
            stop_loss = calculate_stop_loss(
                side,
                entry,
                None,  # 没有OB
                recent_high,
                recent_low,
                self.config.get("stop_source", "auto"),
                self.config["stop_buffer_pct"]
            )
            
            if entry == stop_loss:
                return None
            
            # 计算止盈
            fibo_extension_dict = calculate_fibo_extension(recent_high, recent_low)
            take_profit = calculate_take_profit(
                side,
                entry,
                stop_loss,
                self.config.get("tp_mode", "swing"),
                recent_high,
                recent_low,
                self.config.get("rr", 2.0),
                fibo_extension_dict
            )
            
            # 确保最小RR
            take_profit, rr_ratio = ensure_min_rr(
                side,
                entry,
                stop_loss,
                take_profit,
                self.config.get("min_rr", 2.0)
            )
            
            if rr_ratio < self.config.get("min_rr", 2.0):
                return None
            
            # 计算仓位
            position_size = calculate_position_size(
                entry,
                stop_loss,
                self.config.get("max_loss", 100)
            )
            
            if position_size <= 0:
                return None
            
            # 使用mid_price作为entry（当前价格）
            entry = current_price
            
            # 创建信号（StrategyOutput已经在文件顶部导入）
            return StrategyOutput(
                signal_type="OPEN",
                side=side,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size=position_size,
                indicators={
                    "structure": "fallback",
                    "entry_source": "mid_price",
                    "require_retest": self.config.get("require_retest", True),
                    "retest_bars": self.config.get("retest_bars", 20),
                }
            )
        
        # 选择最优候选（按RR排序）
        candidates.sort(key=lambda x: x["rr_ratio"], reverse=True)
        best = candidates[0]
        
        # 信号质量评分
        has_ob = best["ob"] is not None
        has_fvg = any(fvg.low <= best["entry"] <= fvg.high for fvg in fvgs if not fvg.filled)
        
        # 流动性扫除检测
        has_liquidity = detect_liquidity_sweep(
            candles,
            swing_highs,
            swing_lows,
            side,
            self.config.get("sweep_len", 5),
            self.config.get("allow_internal", True),
            self.config.get("allow_external", True),
            None,  # htf_swing_highs (可扩展)
            None   # htf_swing_lows (可扩展)
        ) is not None
        
        signal_score = self.signal_scorer.calculate_score(
            has_structure=True,
            has_ob=has_ob,
            has_fvg=has_fvg,
            has_liquidity=has_liquidity,
            pattern_score=0.0,
            bars_since_signal=0
        )
        
        if not self.signal_scorer.meets_min_score(signal_score):
            return None
        
        # 检查重复信号（信号评分器的去重）
        if self.signal_scorer.check_duplicate(symbol, side, self._step_counter):
            return None
        
        # 检查冷却期：避免连续产生同方向信号
        if (self._last_signal_side == side and 
            self._step_counter - self._last_signal_index < self._signal_cooldown):
            return None  # 冷却期内，跳过同方向信号
        
        # 回踩确认
        if self.config.get("require_retest", True):
            self._pending = {
                "symbol": symbol,
                "side": side,
                "entry": best["entry"],
                "stop_loss": best["stop_loss"],
                "take_profit": best["take_profit"],
                "zone_low": min(best["entry"], best["stop_loss"]),
                "zone_high": max(best["entry"], best["stop_loss"]),
                "fibo_level": best["fibo_level"],
                "position_size": best["position_size"],
                "rr_ratio": best["rr_ratio"],
            }
            # print(f"DEBUG: Pending created at {self._step_counter} for {side} (Entry: {best['entry']})")
            print(f"DEBUG: Pending created at {self._step_counter} for {side}")
            self._pending_created_at = self._step_counter
            self.signal_count += 1
            return None  # 等待回踩确认
        
        # 计算置信度
        confidence = min(95, max(50, int(signal_score * 20 + 50)))
        
        # 构建原因字符串
        reason_parts = [
            f"SMC+Fibo{side}",
            f"回撤{best['fibo_level']:.1%}位",
            f"RR{best['rr_ratio']:.2f}",
        ]
        if has_ob:
            reason_parts.append("OB")
        if has_fvg:
            reason_parts.append("FVG")
        if has_liquidity:
            reason_parts.append("流动性扫除")
        reason = " | ".join(reason_parts)
        
        # 更新最后信号记录
        self._last_signal_side = side
        self._last_signal_index = self._step_counter
        
        return StrategyOutput(
            symbol=symbol,
            signal_type="OPEN",
            side=side,
            entry_price=round(best["entry"], 5),
            stop_loss=round(best["stop_loss"], 5),
            take_profit=round(best["take_profit"], 5),
            confidence=confidence,
            reason=reason,
            indicators={
                "fibo_level": best["fibo_level"],
                "rr_ratio": best["rr_ratio"],
                "position_size": best["position_size"],
                "signal_score": round(signal_score, 2),
                "trend": trend,
                "htf_trend": htf_trend,
                "has_ob": has_ob,
                "has_fvg": has_fvg,
                "has_liquidity": has_liquidity,
            },
        )
    
    def _check_pending(
        self,
        symbol: str,
        candles: List[Dict],
        current_timestamp: Optional[int] = None,
    ) -> Any:
        """
        检查待确认信号的回踩状态
        
        Returns:
            StrategyOutput: 回踩确认成功
            "waiting": 仍在等待
            "expired" / "stop_touched" / "rr_insufficient": 信号取消
            None: 如果没有pending且require_retest=False，允许直接开仓
        """
        if not self._pending:
            # 如果没有pending且require_retest=False，返回None让回测引擎直接开仓
            # 这是限价单触达后的处理（require_retest=False时不需要回踩确认）
            if not self.config.get("require_retest", True):
                return None
            return "no_pending"
        
        # 回测引擎可能不会传 current_timestamp，这里自动从当前K线解析
        if current_timestamp is None and candles:
            ts = candles[-1].get("timestamp") or candles[-1].get("time")
            if isinstance(ts, str):
                try:
                    current_timestamp = int(datetime.fromisoformat(ts).timestamp())
                except Exception:
                    current_timestamp = int(datetime.now().timestamp())
            elif isinstance(ts, (int, float)):
                current_timestamp = int(ts)
            else:
                current_timestamp = int(datetime.now().timestamp())

        bars_waited = self._step_counter - self._pending_created_at
        
        # 超时检查
        if bars_waited > self.config.get("retest_bars", 20):
            self._pending = None
            print(f"DEBUG: Pending expired at {self._step_counter} (waited {bars_waited})")
            return "expired"
        
        current = candles[-1]
        prev = candles[-2] if len(candles) >= 2 else None
        prev2 = candles[-3] if len(candles) >= 3 else None
        side = self._pending["side"]
        
        # 止损触及检查
        if not self.config.get("retest_ignore_stop_touch", False):
            if side == "BUY" and current["low"] <= self._pending["stop_loss"]:
                self._pending = None
                print(f"DEBUG: Pending cancelled at {self._step_counter} (STOP TOUCHED)")
                return "stop_touched"
            if side == "SELL" and current["high"] >= self._pending["stop_loss"]:
                self._pending = None
                print(f"DEBUG: Pending cancelled at {self._step_counter} (STOP TOUCHED)")
                return "stop_touched"
        
        # 检测价格是否触达回踩区间
        current_touched = current["low"] <= self._pending["zone_high"] and current["high"] >= self._pending["zone_low"]
        
        # 记录触达状态（像old1一样：一旦触达，后续K线即使离开区间也允许确认）
        if current_touched and not self._pending.get("touched"):
            self._pending["touched"] = True
            self._pending["touch_index"] = self._step_counter
            
        if self._pending.get("touched", False):
            # 检测拒绝形态
            rejection_result = detect_rejection(
                current,
                prev,
                prev2,
                side,
                self._pending["zone_low"],
                self._pending["zone_high"],
                self.config
            )
            print(f"DEBUG: Rejection check at {self._step_counter}: {rejection_result.get('close_reject')} {rejection_result.get('score')}")
            
            # 检查是否满足最小评分（放宽条件：只要有拒绝形态或close_reject即可）
            # old1逻辑：只要 close_reject 且有任意形态（pinbar/engulf/etc）就进场
            # flex逻辑：评分或close_reject
            has_rejection_pattern = rejection_result.get("meets_min_score", False)
            has_close_reject = rejection_result.get("close_reject", False)
            
            # 如果检测到拒绝形态，或者有close_reject，都可以确认
            if has_rejection_pattern or has_close_reject:
                # 回踩确认成功
                # 像old1一样：使用原始 pending entry 价格入场（假设在回踩时成交）
                # old1 logic: entry = pending["entry"] (Line 1456)
                entry_price = self._pending["entry"]
                
                # 重新检查RR (使用原始 entry)
                rr_ratio = self._pending["rr_ratio"]
                
                # 重新计算仓位 (使用原始 entry)
                position_size = self._pending["position_size"]
                
                patterns = "+".join(rejection_result.get("patterns", []))
                confidence = min(95, 70 + int(rejection_result.get("score", 0) * 5))
                
                signal = StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side=side,
                    entry_price=round(entry_price, 5),
                    stop_loss=round(self._pending["stop_loss"], 5),
                    take_profit=round(self._pending["take_profit"], 5),
                    confidence=confidence,
                    reason=f"SMC+Fibo{side}: 回踩{self._pending['fibo_level']:.1%}位 {patterns}确认({bars_waited}根K线), RR{rr_ratio:.2f}",
                    indicators={
                        "fibo_level": self._pending["fibo_level"],
                        "rr_ratio": round(rr_ratio, 2),
                        "position_size": position_size,
                        "patterns": patterns,
                        "bars_waited": bars_waited,
                    },
                )
                
                self._pending = None
                return signal
        
        return "waiting"
    
    def _check_pending_result(
        self,
        symbol: str,
        candles: List[Dict],
    ) -> Optional[StrategyOutput]:
        """有持仓时仅处理已挂起的回踩确认，不产生新信号"""
        if not self._pending:
            return None
        current_timestamp = None
        if candles:
            ts = candles[-1].get("timestamp") or candles[-1].get("time")
            if isinstance(ts, str):
                try:
                    current_timestamp = int(datetime.fromisoformat(ts).timestamp())
                except Exception:
                    current_timestamp = int(datetime.now().timestamp())
        result = self._check_pending(symbol, candles, current_timestamp)
        if isinstance(result, StrategyOutput):
            return result
        return None