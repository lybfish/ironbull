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
from .utils.trend_detection import detect_trend, get_htf_trend, get_htf_structure_trend
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
from .modules.order_blocks import find_order_blocks, find_nearest_order_block, find_breaker_blocks, BreakerBlock
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
        
        # 方案C: 限价先成交 → 确认后决定去留
        self._post_fill_state = None  # {side, zone_low, zone_high, fill_step, confirm_bars}
        
        # 统计计数
        self.signal_count = 0
        self._debug_bos_count = 0
        self._debug_choch_count = 0
        self._debug_fallback_count = 0
        self._debug_limit_fill_count = 0
        self._debug_limit_expire_count = 0
        self._debug_limit_stop_count = 0
        self._debug_post_fill_confirmed = 0   # 方案C: 成交后确认成功
        self._debug_post_fill_unconfirmed = 0 # 方案C: 成交后未确认→平仓

        
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
        
        # 递增步骤计数器（必须在所有逻辑之前，确保方案C的计时正确）
        self._step_counter += 1
        
        # ─── 持仓感知（严格对齐 old1）───
        # old1 line 1537: `if not open_order and not open_trade and pos == 0 and not pending`
        # old1 有持仓时绝不产生新信号，也不处理 pending
        # 这是 old1 回撤仅 6.9% 的核心原因：严格一次只做一笔交易
        if positions:
            has_pos = positions.get("has_position", False)
            has_long = positions.get("has_long", False)
            has_short = positions.get("has_short", False)
            if has_pos or has_long or has_short:
                # 方案C: 持仓中但需要确认 → 检查是否有拒绝形态
                if self._post_fill_state:
                    return self._check_post_fill_confirmation(symbol, candles)
                # 已有持仓 → 取消 pending，直接返回（对齐 old1 严格单仓）
                # old1 的 pending retest 也要求 `not open_trade and pos == 0`
                self._pending = None
                return None
        
        # 持仓已清（SL/TP/手动平仓） → 清除方案C状态
        if self._post_fill_state:
            self._post_fill_state = None
        
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
        
        # 检查待确认订单（限价单 / 回踩确认）
        entry_mode = self.config.get("entry_mode", "retest")
        if self._pending:
            if entry_mode == "limit":
                result = self._check_pending_limit(symbol, candles)
            else:
                result = self._check_pending(symbol, candles, current_timestamp)
            if isinstance(result, StrategyOutput):
                return result
            if result == "waiting":
                return None
        
        # ====== 对齐 old1 的延迟 swing 更新机制 ======
        # old1 流程：1) 找到包含当前 bar 的 swing candidate
        #            2) 用**旧的** swing_high/low 做 BOS 检测
        #            3) 生成信号
        #            4) 才更新 swing_high/low = candidate
        # 所以 BOS 检测用的是上一根 K 线时的 swing 点
        candle_count = len(candles)
        last_candle_hash = candles[-1].get("timestamp") if candles else None
        swing = self.config.get("swing", 5)
        
        # 保存"旧的"swing 点用于 BOS 检测（对齐 old1 的延迟更新）
        bos_swing_highs = list(self._cache["swing_highs"]) if self._cache["swing_highs"] else None
        bos_swing_lows = list(self._cache["swing_lows"]) if self._cache["swing_lows"] else None
        
        # 更新 swing 点（包含当前 K 线）
        if (self._cache["last_candle_count"] == candle_count - 1 and 
            self._cache["swing_highs"] is not None and 
            self._cache["swing_lows"] is not None and
            self._cache["last_swing_param"] == swing and
            candle_count > swing * 2):
            # 增量更新：realtime 模式只需检查新增的最后一根K线
            swing_highs = self._cache["swing_highs"]
            swing_lows = self._cache["swing_lows"]
            
            from .utils.swing_points import SwingPoint
            i = candle_count - 1
            if i >= swing:
                hi = candles[i]["high"]
                lo = candles[i]["low"]
                
                if all(hi >= candles[j]["high"] for j in range(i - swing, i + 1)):
                    swing_highs.append(SwingPoint(index=i, price=hi, type="high", timestamp=candles[i].get("timestamp")))
                
                if all(lo <= candles[j]["low"] for j in range(i - swing, i + 1)):
                    swing_lows.append(SwingPoint(index=i, price=lo, type="low", timestamp=candles[i].get("timestamp")))
            
            self._cache["swing_highs"] = swing_highs
            self._cache["swing_lows"] = swing_lows
            self._cache["last_candle_count"] = candle_count
            self._cache["last_candle_hash"] = last_candle_hash
            self._cache["last_swing_param"] = swing
        else:
            # 完全重新计算
            swing_highs, swing_lows = find_swing_points(
                candles,
                swing,
                realtime_mode=True
            )
            self._cache["swing_highs"] = swing_highs
            self._cache["swing_lows"] = swing_lows
            self._cache["last_candle_count"] = candle_count
            self._cache["last_candle_hash"] = last_candle_hash
            self._cache["last_swing_param"] = swing
            
            # 首次计算时，"旧"swing 也用当前（不含最后一个可能的 swing）
            if swing_highs:
                bos_swing_highs = swing_highs[:-1] if swing_highs[-1].index == candle_count - 1 else list(swing_highs)
            if swing_lows:
                bos_swing_lows = swing_lows[:-1] if swing_lows[-1].index == candle_count - 1 else list(swing_lows)
        
        # 用于 BOS 检测的 swing 点：不含当前 bar 可能新增的 swing
        # 对齐 old1：BOS 检测在 swing 更新之前
        if bos_swing_highs is None:
            bos_swing_highs = swing_highs
        if bos_swing_lows is None:
            bos_swing_lows = swing_lows
        
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
            # Step 2 升级：优先使用大周期 K 线结构 (Swing Structure) 判断方向
            # 对应文档："大周期定方向 → 看 K 线结构（HH/HL 或 LH/LL）"
            htf_trend = get_htf_structure_trend(
                candles,
                self.config.get("htf_multiplier", 4),
                self.config.get("htf_swing_count", 3)
            )
            # 如果结构判断为 neutral（数据不足或无明确结构），回退到 EMA
            if htf_trend == "neutral":
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
        
        # 结构检测（使用"旧"swing 点，对齐 old1 延迟更新逻辑）
        bos = detect_bos(candles, bos_swing_highs, bos_swing_lows)
        choch = detect_choch(candles, bos_swing_highs, bos_swing_lows, trend)

        if bos: self._debug_bos_count += 1
        if choch: self._debug_choch_count += 1
        
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
        fibo_side_fallback = False
        if not side and self.config.get("fibo_fallback", True):
            side, fibo_side_fallback = apply_fibo_fallback(side, trend, htf_trend)
            if fibo_side_fallback:
                self._debug_fallback_count += 1
        
        # Bias过滤（使用更新后的 trend，而非原始 trend）
        if side:
            side = filter_by_bias(
                side,
                self.config.get("bias", "with_trend"),
                htf_trend if htf_trend != "neutral" else trend
            )
        
        if not side:
            return None
        
        # 对齐 old1: fallback 模式下，价格必须在折价/溢价区内
        # old1 line 1601-1605: BUY 时 bar["l"] 必须 <= mid_price, SELL 时 bar["h"] 必须 >= mid_price
        if fibo_side_fallback and len(swing_highs) >= 1 and len(swing_lows) >= 1:
            mid_price = (swing_highs[-1].price + swing_lows[-1].price) / 2.0
            current_bar = candles[-1]
            if side == "BUY" and current_bar["low"] > mid_price:
                return None
            if side == "SELL" and current_bar["high"] < mid_price:
                return None
        
        # 识别Order Block / FVG / 流动性

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
        
        # 计算斐波那契回撤位（对齐 old1：用 BOS 检测时的旧 swing 点）
        recent_high = bos_swing_highs[-1].price if bos_swing_highs and len(bos_swing_highs) >= 1 else swing_highs[-1].price
        recent_low = bos_swing_lows[-1].price if bos_swing_lows and len(bos_swing_lows) >= 1 else swing_lows[-1].price
        swing_range = recent_high - recent_low
        
        if swing_range <= 0:
            return None

        # 根据 entry_source 选择入场逻辑
        entry_source = self.config.get("entry_source", "auto")
        candidates = []

        # 传给候选函数的 swing 点用 bos 版本（对齐 old1）
        _sh = bos_swing_highs if bos_swing_highs and len(bos_swing_highs) >= 2 else swing_highs
        _sl = bos_swing_lows if bos_swing_lows and len(bos_swing_lows) >= 2 else swing_lows
        
        if entry_source == "ob":
            candidates = self._find_ob_candidates(
                candles, side, trend, htf_trend,
                order_blocks, fvgs, _sh, _sl
            )
        elif entry_source == "fvg":
            candidates = self._find_fvg_candidates(
                candles, side, trend, htf_trend,
                order_blocks, fvgs, _sh, _sl
            )
        elif entry_source == "swing":
            candidates = self._find_fibo_candidates(
                candles, side, trend, htf_trend,
                order_blocks, fvgs, _sh, _sl
            )
        else: # auto / fibo
            candidates = self._find_fibo_candidates(
                candles, side, trend, htf_trend,
                order_blocks, fvgs, _sh, _sl
            )
        
        if not candidates:
            # 像old1一样：如果没有合适的斐波那契候选，使用mid_price作为fallback
            # 这样可以确保至少有一个信号，即使价格不在斐波那契位
            mid_price = (recent_high + recent_low) / 2.0
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
            _atr_val_fb = 0.0
            _atr_mult_fb = self.config.get("sl_atr_multiplier", 0.5)
            if self.config.get("stop_buffer_mode") == "atr":
                _atr_val_fb = atr(candles, period=self.config.get("atr_period", 14)) or 0.0
            stop_loss = calculate_stop_loss(
                side,
                entry,
                None,  # 没有OB
                recent_high,
                recent_low,
                self.config.get("stop_source", "auto"),
                self.config["stop_buffer_pct"],
                atr_value=_atr_val_fb,
                atr_multiplier=_atr_mult_fb,
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
                symbol=symbol,
                signal_type="OPEN",
                side=side,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                # position_size=position_size, # StrategyOutput 不包含 position_size，放入 indicators
                indicators={
                    "position_size": position_size,
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
        
        # 检查冷却期：避免频繁交易（对齐 old1 的 cooldown_bars）
        # 注意：冷却从上次成交时刻算起，而非信号创建时刻
        if (self._last_signal_index > 0 and 
            self._step_counter - self._last_signal_index < self._signal_cooldown):
            return None  # 冷却期内，跳过所有方向信号
        
        # 回踩确认 / 限价单挂单
        _entry_mode = self.config.get("entry_mode", "retest")
        _need_pending = _entry_mode in ("retest", "limit") or self.config.get("require_retest", True)
        if _need_pending:
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
            self._pending_created_at = self._step_counter
            self.signal_count += 1
            return None  # 等待限价触达 / 回踩确认
        
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
    
    def _find_fibo_candidates(
        self, candles, side, trend, htf_trend,
        order_blocks, fvgs, swing_highs, swing_lows
    ) -> List[Dict]:
        """寻找 Fibonacci 入场候选"""
        candidates = []
        recent_high = swing_highs[-1].price
        recent_low = swing_lows[-1].price
        swing_range = recent_high - recent_low
        mid_price = (recent_high + recent_low) / 2.0
        current_price = candles[-1]["close"]
        
        fibo_levels_list = self.config.get("fibo_levels", [0.5, 0.618, 0.705])
        
        for fibo_level in fibo_levels_list:
            if side == "BUY":
                entry = recent_high - swing_range * fibo_level
                if entry > mid_price: continue
            else:
                entry = recent_low + swing_range * fibo_level
                if entry < mid_price: continue
            
            # 检查价格是否在斐波那契区域
            price_in_zone = abs(entry - current_price) / current_price <= self.config.get("fibo_tolerance", 0.005)
            if price_in_zone:
                entry = current_price
            
            # 找到最近的Order Block
            ob = None
            if order_blocks:
                ob = find_nearest_order_block(
                    order_blocks, side, entry,
                    self.config.get("ob_max_tests", 3),
                    self.config.get("ob_valid_bars", 100),
                    len(candles) - 1
                )
            
            # 计算止损
            _atr_val = 0.0
            _atr_mult = self.config.get("sl_atr_multiplier", 0.5)
            if self.config.get("stop_buffer_mode") == "atr":
                _atr_val = atr(candles, period=self.config.get("atr_period", 14)) or 0.0
            stop_loss = calculate_stop_loss(
                side, entry, ob, recent_high, recent_low,
                self.config.get("stop_source", "auto"),
                self.config["stop_buffer_pct"],
                atr_value=_atr_val,
                atr_multiplier=_atr_mult,
            )
            
            if entry == stop_loss: continue
            
            # 计算止盈
            fibo_extension_dict = calculate_fibo_extension(recent_high, recent_low)
            take_profit = calculate_take_profit(
                side, entry, stop_loss,
                self.config.get("tp_mode", "swing"),
                recent_high, recent_low,
                self.config.get("rr", 2.0),
                fibo_extension_dict
            )
            
            # 确保最小RR
            take_profit, rr_ratio = ensure_min_rr(
                side, entry, stop_loss, take_profit,
                self.config.get("min_rr", 2.0)
            )
            
            if rr_ratio < self.config.get("min_rr", 2.0): continue
            
            # 计算仓位
            position_size = calculate_position_size(
                entry, stop_loss, self.config.get("max_loss", 100)
            )
            
            if position_size <= 0: continue
            
            candidates.append({
                "entry": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "rr_ratio": rr_ratio,
                "fibo_level": fibo_level,
                "position_size": position_size,
                "ob": ob,
            })
        return candidates

    def _find_ob_candidates(
        self, candles, side, trend, htf_trend,
        order_blocks, fvgs, swing_highs, swing_lows
    ) -> List[Dict]:
        """
        寻找 Order Block + Breaker Block 入场候选
        
        Step 3 升级：除了新鲜 OB，还检查 Breaker Block (供需反转区)
        对应文档："突破后原供区转为需区，类似支撑阻力转换"
        """
        candidates = []
        recent_high = swing_highs[-1].price
        recent_low = swing_lows[-1].price
        target_type = "bullish" if side == "BUY" else "bearish"
        
        # === Part A: 新鲜 Order Block ===
        if order_blocks:
            for ob in order_blocks:
                if ob.type != target_type: continue
                if len(candles) - 1 - ob.index > self.config.get("ob_valid_bars", 100): continue
                
                entry = ob.high if side == "BUY" else ob.low
                stop_buffer = entry * self.config["stop_buffer_pct"]
                stop_loss = (ob.low - stop_buffer) if side == "BUY" else (ob.high + stop_buffer)
                
                fibo_extension_dict = calculate_fibo_extension(recent_high, recent_low)
                take_profit = calculate_take_profit(
                    side, entry, stop_loss,
                    self.config.get("tp_mode", "swing"),
                    recent_high, recent_low,
                    self.config.get("rr", 2.0),
                    fibo_extension_dict
                )
                
                take_profit, rr_ratio = ensure_min_rr(
                    side, entry, stop_loss, take_profit,
                    self.config.get("min_rr", 2.0)
                )
                
                if rr_ratio < self.config.get("min_rr", 2.0): continue
                
                position_size = calculate_position_size(
                    entry, stop_loss, self.config.get("max_loss", 100)
                )
                
                if position_size <= 0: continue
                
                candidates.append({
                    "entry": entry,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "rr_ratio": rr_ratio,
                    "fibo_level": 0.0,
                    "position_size": position_size,
                    "ob": ob,
                    "source": "fresh_ob",
                })
        
        # === Part B: Breaker Block (供需反转区) ===
        if self.config.get("use_breaker", True):
            breaker_lookback = self.config.get("breaker_lookback", 50)
            breakers = find_breaker_blocks(
                candles,
                ob_lookback=breaker_lookback,
                ob_min_body_ratio=self.config.get("ob_min_body_ratio", 0.5),
            )
            
            current_index = len(candles) - 1
            current_price = candles[-1]["close"]
            
            for bb in breakers:
                if bb.type != target_type: continue
                # Breaker 必须是在突破之后才有效，且不能太旧
                if current_index - bb.break_index > self.config.get("breaker_valid_bars", 80): continue
                if bb.tests >= self.config.get("breaker_max_tests", 2): continue
                
                # 价格必须在 Breaker 附近才有意义
                # BUY: 价格接近 Breaker 上沿 (回踩支撑)
                # SELL: 价格接近 Breaker 下沿 (回踩阻力)
                if side == "BUY":
                    # 价格回踩到 Breaker 区域内
                    if not (bb.low <= current_price <= bb.high * 1.005):
                        continue
                    entry = bb.body_high  # 在 Breaker 实体上沿挂单
                else:
                    if not (bb.low * 0.995 <= current_price <= bb.high):
                        continue
                    entry = bb.body_low  # 在 Breaker 实体下沿挂单
                
                stop_buffer = entry * self.config["stop_buffer_pct"]
                stop_loss = (bb.low - stop_buffer) if side == "BUY" else (bb.high + stop_buffer)
                
                fibo_extension_dict = calculate_fibo_extension(recent_high, recent_low)
                take_profit = calculate_take_profit(
                    side, entry, stop_loss,
                    self.config.get("tp_mode", "swing"),
                    recent_high, recent_low,
                    self.config.get("rr", 2.0),
                    fibo_extension_dict
                )
                
                take_profit, rr_ratio = ensure_min_rr(
                    side, entry, stop_loss, take_profit,
                    self.config.get("min_rr", 2.0)
                )
                
                if rr_ratio < self.config.get("min_rr", 2.0): continue
                
                position_size = calculate_position_size(
                    entry, stop_loss, self.config.get("max_loss", 100)
                )
                
                if position_size <= 0: continue
                
                candidates.append({
                    "entry": entry,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "rr_ratio": rr_ratio,
                    "fibo_level": 0.0,
                    "position_size": position_size,
                    "ob": None,  # Breaker 不算传统 OB
                    "source": "breaker_block",
                })
        
        return candidates

    def _find_fvg_candidates(
        self, candles, side, trend, htf_trend,
        order_blocks, fvgs, swing_highs, swing_lows
    ) -> List[Dict]:
        """寻找 FVG 入场候选 (忽略 Fibo)"""
        candidates = []
        if not fvgs:
            return candidates
            
        recent_high = swing_highs[-1].price
        recent_low = swing_lows[-1].price
        target_type = "bullish" if side == "BUY" else "bearish"
        
        for fvg in fvgs:
            if fvg.type != target_type: continue
            if fvg.filled: continue
            if len(candles) - 1 - fvg.index > self.config.get("fvg_valid_bars", 50): continue
            
            # 挂单在FVG边界
            entry = fvg.high if side == "BUY" else fvg.low
            
            # 止损放FVG另一侧 + buffer
            stop_buffer = entry * self.config["stop_buffer_pct"]
            stop_loss = (fvg.low - stop_buffer) if side == "BUY" else (fvg.high + stop_buffer)
            
            # 计算止盈
            fibo_extension_dict = calculate_fibo_extension(recent_high, recent_low)
            take_profit = calculate_take_profit(
                side, entry, stop_loss,
                self.config.get("tp_mode", "swing"),
                recent_high, recent_low,
                self.config.get("rr", 2.0),
                fibo_extension_dict
            )
            
            take_profit, rr_ratio = ensure_min_rr(
                side, entry, stop_loss, take_profit,
                self.config.get("min_rr", 2.0)
            )
            
            if rr_ratio < self.config.get("min_rr", 2.0): continue
            
            position_size = calculate_position_size(
                entry, stop_loss, self.config.get("max_loss", 100)
            )
            
            if position_size <= 0: continue
            
            candidates.append({
                "entry": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "rr_ratio": rr_ratio,
                "fibo_level": 0.0, # FVG模式无Fibo
                "position_size": position_size,
                "ob": None,
            })
        return candidates

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
            
            # old1 核心逻辑 (line 1454):
            # close_reject AND (pinbar OR engulf OR morning_star OR evening_star)
            has_rejection_pattern = rejection_result.get("meets_min_score", False)
            has_close_reject = rejection_result.get("close_reject", False)
            
            # AND 逻辑: 必须同时满足 close_reject 和至少一个形态
            if has_close_reject and has_rejection_pattern:
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
    
    def _check_pending_limit(
        self,
        symbol: str,
        candles: List[Dict],
    ) -> Any:
        """
        限价单模式 — 完全对齐 old1 的两步确认流程:
        
        old1 核心逻辑 (backtest_engine.py line 1437-1454):
          Step 1: 价格触达区间 → 标记 touched
          Step 2: 触达后 (当根或后续K线) 检测拒绝形态
                  要求: close_reject AND (pinbar OR engulf OR morning_star OR evening_star)
        
        关键差异修复:
          旧 flex: 仅当价格在 entry_price 时检查确认 (miss post-touch bars)
          旧 flex: close_reject OR pattern (太宽松 → 3x 多余成交 → 低胜率 → 高回撤)
          新 flex: 触达后 ALL subsequent bars 检查 + close_reject AND pattern
        """
        if not self._pending:
            return "no_pending"
        
        bars_waited = self._step_counter - self._pending_created_at
        retest_bars = self.config.get("retest_bars", 20)
        
        # 超时检查
        if bars_waited > retest_bars:
            self._pending = None
            self._debug_limit_expire_count += 1
            return "expired"
        
        current = candles[-1]
        prev = candles[-2] if len(candles) >= 2 else None
        prev2 = candles[-3] if len(candles) >= 3 else None
        side = self._pending["side"]
        entry_price = self._pending["entry"]
        
        # 止损触及检查 (对齐 old1 line 1425-1434)
        if not self.config.get("retest_ignore_stop_touch", False):
            if side == "BUY" and current["low"] <= self._pending["stop_loss"]:
                self._pending = None
                self._debug_limit_stop_count += 1
                return "stop_touched"
            if side == "SELL" and current["high"] >= self._pending["stop_loss"]:
                self._pending = None
                self._debug_limit_stop_count += 1
                return "stop_touched"
        
        # ── Step 1: 触达检测 (对齐 old1 line 1437-1440) ──
        # old1 用 zone (entry~stop 区间)，这里用 entry_price 作为触达点
        zone_low = min(entry_price, self._pending["stop_loss"])
        zone_high = max(entry_price, self._pending["stop_loss"])
        
        # 检查价格是否触达区间
        touched_now = current["low"] <= zone_high and current["high"] >= zone_low
        if touched_now and not self._pending.get("touched"):
            self._pending["touched"] = True
            self._pending["touch_index"] = self._step_counter
        
        # ── Step 2: 触达后处理 ──
        if not self._pending.get("touched"):
            return "waiting"
        
        # ══════════════════════════════════════════════════════════
        # 方案C: confirm_after_fill — 限价先成交，确认后决定去留
        # 真实交易: 限价单触碰即成交 → 持仓后再看确认信号
        # ══════════════════════════════════════════════════════════
        if self.config.get("confirm_after_fill", False):
            self._debug_limit_fill_count += 1
            position_size = self._pending["position_size"]
            rr_ratio = self._pending["rr_ratio"]
            
            self._last_signal_side = side
            self._last_signal_index = self._step_counter
            
            # 创建 post-fill 确认状态（成交后监控 N 根K线的确认形态）
            self._post_fill_state = {
                "side": side,
                "zone_low": zone_low,
                "zone_high": zone_high,
                "fill_step": self._step_counter,
                "confirm_bars": self.config.get("post_fill_confirm_bars", 5),
            }
            
            signal = StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side=side,
                entry_price=round(entry_price, 5),
                stop_loss=round(self._pending["stop_loss"], 5),
                take_profit=round(self._pending["take_profit"], 5),
                confidence=70,
                reason=f"SMC+Fibo{side}: 限价成交@{self._pending['fibo_level']:.1%}(待确认{self._post_fill_state['confirm_bars']}K), RR{rr_ratio:.2f}",
                indicators={
                    "fibo_level": self._pending["fibo_level"],
                    "rr_ratio": round(rr_ratio, 2),
                    "position_size": position_size,
                    "bars_waited": bars_waited,
                    "confirmed_fill": True,
                    "needs_post_confirmation": True,
                },
            )
            self._pending = None
            return signal
        
        # ══════════════════════════════════════════════════════════
        # 传统模式: 触达后检测拒绝形态 (对齐 old1 line 1442-1454)
        # 关键: 一旦 touched=True，后续每根 K 线都检查
        # ══════════════════════════════════════════════════════════
        rejection_result = detect_rejection(
            current, prev, prev2, side,
            zone_low, zone_high,
            self.config
        )
        
        has_close_reject = rejection_result.get("close_reject", False)
        has_pattern = rejection_result.get("meets_min_score", False)
        
        # 核心: AND 逻辑 (对齐 old1 line 1454)
        if has_close_reject and has_pattern:
            # ✅ 回踩确认成功
            self._debug_limit_fill_count += 1
            position_size = self._pending["position_size"]
            rr_ratio = self._pending["rr_ratio"]
            
            self._last_signal_side = side
            self._last_signal_index = self._step_counter
            
            patterns = "+".join(rejection_result.get("patterns", []))
            
            signal = StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side=side,
                entry_price=round(entry_price, 5),
                stop_loss=round(self._pending["stop_loss"], 5),
                take_profit=round(self._pending["take_profit"], 5),
                confidence=80,
                reason=f"SMC+Fibo{side}: 限价确认@{self._pending['fibo_level']:.1%} {patterns}({bars_waited}K), RR{rr_ratio:.2f}",
                indicators={
                    "fibo_level": self._pending["fibo_level"],
                    "rr_ratio": round(rr_ratio, 2),
                    "position_size": position_size,
                    "bars_waited": bars_waited,
                    "confirmed_fill": True,
                },
            )
            self._pending = None
            return signal
        
        # 触达但未确认 → 继续等待后续K线
        return "waiting"
    
    def _check_post_fill_confirmation(
        self,
        symbol: str,
        candles: List[Dict],
    ) -> Optional[StrategyOutput]:
        """
        方案C: 限价成交后的确认检查
        
        时间线:
          Bar N:   BOS → 挂限价
          Bar N+M: 限价触碰 → 成交（持仓）
          Bar N+M+1..+K: 检查拒绝形态
            ✅ 有 close_reject + pattern → 持仓（return None）
            ❌ K根K线内无确认 → 平仓（return CLOSE 信号）
        """
        state = self._post_fill_state
        if not state:
            return None
        
        bars_since_fill = self._step_counter - state["fill_step"]
        
        current = candles[-1]
        prev = candles[-2] if len(candles) >= 2 else None
        prev2 = candles[-3] if len(candles) >= 3 else None
        
        # 检测拒绝形态（和传统模式完全相同的 detect_rejection）
        rejection_result = detect_rejection(
            current, prev, prev2, state["side"],
            state["zone_low"], state["zone_high"],
            self.config
        )
        
        has_close_reject = rejection_result.get("close_reject", False)
        has_pattern = rejection_result.get("meets_min_score", False)
        
        if has_close_reject and has_pattern:
            # ✅ 确认成功 → 持有仓位（保留原始 SL/TP）
            self._debug_post_fill_confirmed += 1
            self._post_fill_state = None
            return None  # None = 不做任何操作 = 继续持有
        
        # 检查超时
        if bars_since_fill >= state["confirm_bars"]:
            # ❌ 超时未确认 → 发出 CLOSE 信号
            self._debug_post_fill_unconfirmed += 1
            self._post_fill_state = None
            return StrategyOutput(
                symbol=symbol,
                signal_type="CLOSE",
                side=state["side"],
                entry_price=0,
                stop_loss=None,
                take_profit=None,
                confidence=50,
                reason=f"未确认平仓: {state['side']} 成交后{bars_since_fill}K无拒绝形态",
                indicators={"unconfirmed_close": True},
            )
        
        # 还在确认窗口内 → 继续等待
        return None
    
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