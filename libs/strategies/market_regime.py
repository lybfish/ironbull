"""
Market Regime Strategy - 市场状态识别策略

功能：
1. 自动识别市场状态（震荡/趋势）
2. 震荡市场 → 多空双开（对冲），各自独立止损止盈
3. 趋势市场 → 单边开仓（顺势）

识别方法（多指标融合）：
- ADX: < 20 震荡，> 25 趋势
- 布林带宽: 收窄=震荡，扩张=趋势
- 均线排列: 缠绕=震荡，多头/空头排列=趋势
- ATR变化: 萎缩=震荡，放大=趋势

对冲模式说明（震荡市场）：
- 同时开多仓和空仓
- 多仓: SL = 入场 - ATR×2, TP = 入场 + ATR×3
- 空仓: SL = 入场 + ATR×2, TP = 入场 - ATR×3
- 价格上涨 → 多仓止盈 + 空仓止损 → 净赚 ATR×1
- 价格下跌 → 空仓止盈 + 多仓止损 → 净赚 ATR×1
- 风险: 剧烈波动来回扫损，两边都止损

优化 v2 新增：
- RSI 过滤: 避免追涨杀跌（BUY 时 RSI>阈值不进，SELL 时 RSI<阈值不进）
- MACD 方向确认: 趋势信号要求 MACD 柱方向一致
- 成交量确认: 趋势信号要求量比 > 阈值（放量确认）
- 最低置信度: strength < 阈值不开仓
- 止损冷却: 被止损后等 N 根 K 线再进场
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from libs.contracts import StrategyOutput
from libs.indicators import sma, ema, atr, rsi, macd
from libs.indicators.bollinger import bollinger
from libs.indicators.volume import volume_ratio
from .base import StrategyBase


@dataclass
class MarketState:
    """市场状态"""
    regime: str          # "trending" / "ranging" / "uncertain"
    direction: str       # "bullish" / "bearish" / "neutral"
    strength: float      # 0-100 强度
    adx: float
    bb_width: float
    ma_alignment: str


class MarketRegimeStrategy(StrategyBase):
    """
    市场状态识别策略
    
    震荡市场 → 逆势开仓（低买高卖）
    趋势市场 → 单边开仓（顺势）
    
    ⚠️ 重要：回测时需设置 lookback >= 60（建议 100）
    
    识别参数：
    - adx_period: ADX周期（默认14）
    - adx_trend_threshold: ADX趋势阈值（默认25，优化值）
    - adx_range_threshold: ADX震荡阈值（默认15）
    - bb_period: 布林带周期（默认20）
    - bb_squeeze_threshold: 布林带收窄阈值（默认0.02 = 2%）
    - ma_periods: 均线周期列表（默认[10, 20, 50]）
    
    资金管理参数：
    - max_position: 最大持仓金额（默认1000）
    - risk_pct: 每笔风险比例（保守1%，激进2%）
    - atr_mult_sl: ATR止损倍数（默认2.0）
    - atr_mult_tp: ATR止盈倍数（默认3.0）
    
    逐仓保证金模式（sl_tp_mode="margin_pct"，优化默认）：
    - leverage: 杠杆倍数（默认20）
    - tp_pct: 止盈 = 保证金的百分比（默认1.20 = 120%，优化值）
    - sl_pct: 止损 = 保证金的百分比（默认0.30 = 30%，优化值）
    - 保证金 = max_position × risk_pct
    - 仓位 = 保证金 × leverage
    - TP价格 = entry × (1 ± tp_pct / leverage)
    - SL价格 = entry × (1 ∓ sl_pct / leverage)
    
    优化 v2 新增过滤器：
    - rsi_filter: 启用 RSI 过滤（默认 False，优化结论：RSI 对该策略无正面效果）
    - rsi_overbought: RSI 超买阈值（默认 70）
    - rsi_oversold: RSI 超卖阈值（默认 30）
    - macd_filter: 启用 MACD 方向确认（默认 True，优化开启）
    - volume_filter: 启用量比过滤（默认 True，优化开启）
    - volume_min_ratio: 量比阈值（默认 1.0 = 高于均量才进场）
    - min_confidence: 最低置信度（默认 0 = 不过滤）
    - cooldown_bars: 止损后冷却 K 线数（默认 12 = 12根K线冷却，优化值）
    """
    
    # ══════════ 周期预设参数（网格搜索优化结果）══════════
    # 主力: 1h   辅助: 15m
    # 用法: config 里传 timeframe="15m" 自动切换预设，也可手动覆盖任何参数
    TIMEFRAME_PRESETS = {
        "1h": {
            "tp_pct": 1.20,           # 保证金120%止盈 — 盈亏比 3.66:1
            "sl_pct": 0.30,           # 保证金30%止损
            "adx_trend_threshold": 25, # 更早捕捉趋势
            "cooldown_bars": 12,       # 12根=12小时冷却
        },
        "15m": {
            "tp_pct": 0.60,           # 保证金60%止盈 — 盈亏比 1.77:1（波动小）
            "sl_pct": 0.40,           # 保证金40%止损
            "adx_trend_threshold": 25,
            "cooldown_bars": 20,       # 20根=5小时冷却
        },
    }
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "market_regime"
        self.name = "市场状态识别策略"
        
        # ── 周期预设: 先加载预设，再让 config 覆盖 ──
        timeframe = self.config.get("timeframe", "1h")
        preset = self.TIMEFRAME_PRESETS.get(timeframe, self.TIMEFRAME_PRESETS["1h"])
        
        def _get(key, fallback):
            """优先 config 显式传入 > 预设 > 硬编码默认"""
            if key in self.config:
                return self.config[key]
            return preset.get(key, fallback)
        
        # 市场识别参数
        self.adx_period = self.config.get("adx_period", 14)
        self.adx_trend_threshold = _get("adx_trend_threshold", 25)
        self.adx_range_threshold = _get("adx_range_threshold", 15)
        self.bb_period = self.config.get("bb_period", 20)
        self.bb_std = self.config.get("bb_std", 2.0)
        self.bb_squeeze_threshold = self.config.get("bb_squeeze_threshold", 0.02)
        self.ma_periods = self.config.get("ma_periods", [10, 20, 50])
        
        # 资金管理参数
        self.max_position = self.config.get("max_position", 1000)
        self.risk_pct = self.config.get("risk_pct", 0.01)  # 1%保守，2%激进
        
        # TP/SL 模式: "atr"=ATR倍数, "margin_pct"=逐仓保证金百分比（优化默认）
        self.sl_tp_mode = self.config.get("sl_tp_mode", "margin_pct")
        
        # 逐仓保证金百分比参数
        self.leverage = self.config.get("leverage", 20)
        self.tp_pct = _get("tp_pct", 1.20)
        self.sl_pct = _get("sl_pct", 0.30)
        
        # 分治模式: 可为震荡/趋势分别设置 TP/SL（不设则回退到 tp_pct/sl_pct）
        self.ranging_tp_pct = self.config.get("ranging_tp_pct", None)
        self.ranging_sl_pct = self.config.get("ranging_sl_pct", None)
        self.trending_tp_pct = self.config.get("trending_tp_pct", None)
        self.trending_sl_pct = self.config.get("trending_sl_pct", None)
        
        # 是否跳过震荡行情（True=只做趋势单边，不做对冲）
        self.skip_ranging = self.config.get("skip_ranging", False)
        
        # ATR 参数（sl_tp_mode="atr" 时使用）
        self.atr_period = self.config.get("atr_period", 14)
        self.atr_mult_sl = self.config.get("atr_mult_sl", 1.2)
        self.atr_mult_tp = self.config.get("atr_mult_tp", 4.5)
        
        # ══════════ 优化 v2: 信号过滤器 ══════════
        
        # RSI 过滤: 避免追涨杀跌（优化结论：不建议开启）
        self.rsi_filter = self.config.get("rsi_filter", False)
        self.rsi_period = self.config.get("rsi_period", 14)
        self.rsi_overbought = self.config.get("rsi_overbought", 70)
        self.rsi_oversold = self.config.get("rsi_oversold", 30)
        
        # MACD 方向确认: 趋势信号要求 MACD 柱方向一致
        self.macd_filter = self.config.get("macd_filter", True)   # 优化默认开启
        
        # 成交量确认: 要求量比 > 阈值
        self.volume_filter = self.config.get("volume_filter", True)   # 优化默认开启
        self.volume_min_ratio = self.config.get("volume_min_ratio", 1.0)
        
        # 最低置信度: strength < 阈值不开仓
        self.min_confidence = self.config.get("min_confidence", 0)
        
        # 止损冷却: 被止损后等 N 根 K 线再进场
        self.cooldown_bars = _get("cooldown_bars", 12)
        self._cooldown_until = 0  # 内部计数: 冷却到第几根 bar
        self._bar_index = 0       # 内部计数: 当前 bar 序号
        
        # 统计（供回测分析用）
        self.filtered_by_rsi = 0
        self.filtered_by_macd = 0
        self.filtered_by_volume = 0
        self.filtered_by_confidence = 0
        self.filtered_by_cooldown = 0
    
    def _calc_adx(self, candles: List[Dict], period: int = 14) -> Optional[float]:
        """
        计算 ADX (Average Directional Index)
        
        ADX > 25: 趋势市场
        ADX < 20: 震荡市场
        """
        if len(candles) < period * 2:
            return None
        
        # 计算 +DM, -DM
        plus_dm = []
        minus_dm = []
        tr_list = []
        
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            close = candles[i]["close"]
            prev_high = candles[i-1]["high"]
            prev_low = candles[i-1]["low"]
            prev_close = candles[i-1]["close"]
            
            # True Range
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            tr_list.append(tr)
            
            # +DM / -DM
            up_move = high - prev_high
            down_move = prev_low - low
            
            if up_move > down_move and up_move > 0:
                plus_dm.append(up_move)
            else:
                plus_dm.append(0)
            
            if down_move > up_move and down_move > 0:
                minus_dm.append(down_move)
            else:
                minus_dm.append(0)
        
        if len(tr_list) < period:
            return None
        
        # 平滑 TR, +DM, -DM
        def smooth(values, period):
            if len(values) < period:
                return None
            result = sum(values[:period])
            smoothed = [result]
            for i in range(period, len(values)):
                result = result - (result / period) + values[i]
                smoothed.append(result)
            return smoothed
        
        smoothed_tr = smooth(tr_list, period)
        smoothed_plus_dm = smooth(plus_dm, period)
        smoothed_minus_dm = smooth(minus_dm, period)
        
        if not all([smoothed_tr, smoothed_plus_dm, smoothed_minus_dm]):
            return None
        
        # +DI / -DI
        plus_di = []
        minus_di = []
        dx_list = []
        
        for i in range(len(smoothed_tr)):
            if smoothed_tr[i] == 0:
                plus_di.append(0)
                minus_di.append(0)
            else:
                pdi = 100 * smoothed_plus_dm[i] / smoothed_tr[i]
                mdi = 100 * smoothed_minus_dm[i] / smoothed_tr[i]
                plus_di.append(pdi)
                minus_di.append(mdi)
            
            # DX
            if plus_di[-1] + minus_di[-1] == 0:
                dx_list.append(0)
            else:
                dx = 100 * abs(plus_di[-1] - minus_di[-1]) / (plus_di[-1] + minus_di[-1])
                dx_list.append(dx)
        
        if len(dx_list) < period:
            return None
        
        # ADX = SMA of DX
        adx = sum(dx_list[-period:]) / period
        return adx
    
    def _calc_bb_width(self, candles: List[Dict]) -> Optional[float]:
        """
        计算布林带宽度百分比
        
        宽度 < 2%: 震荡/盘整（squeeze）
        宽度 > 4%: 趋势/波动
        """
        closes = [c["close"] for c in candles]
        bb = bollinger(closes, self.bb_period, self.bb_std)
        if not bb:
            return None
        
        middle = bb["middle"]
        if middle == 0:
            return None
        
        width = (bb["upper"] - bb["lower"]) / middle
        return width
    
    def _check_ma_alignment(self, candles: List[Dict]) -> str:
        """
        检查均线排列
        
        多头排列: 短期MA > 中期MA > 长期MA
        空头排列: 短期MA < 中期MA < 长期MA
        缠绕: 其他情况
        """
        if len(candles) < max(self.ma_periods) + 1:
            return "neutral"
        
        closes = [c["close"] for c in candles]
        mas = []
        
        for period in self.ma_periods:
            ma_val = ema(closes, period)
            if ma_val is None:
                return "neutral"
            mas.append(ma_val)
        
        # 检查排列
        # 多头: ma10 > ma20 > ma50
        if all(mas[i] > mas[i+1] for i in range(len(mas)-1)):
            return "bullish"
        # 空头: ma10 < ma20 < ma50
        elif all(mas[i] < mas[i+1] for i in range(len(mas)-1)):
            return "bearish"
        else:
            return "neutral"
    
    def _detect_market_state(self, candles: List[Dict]) -> MarketState:
        """
        综合判断市场状态
        
        返回: MarketState
        """
        # 计算各指标
        adx = self._calc_adx(candles, self.adx_period) or 0
        bb_width = self._calc_bb_width(candles) or 0.03
        ma_alignment = self._check_ma_alignment(candles)
        
        # 评分系统（每个指标 0-100，然后加权平均）
        adx_score = 0       # ADX 强度得分
        bb_score = 0        # 布林带得分
        ma_score = 0        # 均线排列得分
        
        trending_vote = 0   # 趋势票数
        ranging_vote = 0    # 震荡票数
        
        # 1. ADX 判断（权重 40%）
        # ADX 越高，趋势越强；越低，越震荡
        if adx >= self.adx_trend_threshold:  # >= 25
            trending_vote += 1
            # ADX 25-50 映射到 50-100
            adx_score = min(100, 50 + (adx - self.adx_trend_threshold) * 2)
        elif adx <= self.adx_range_threshold:  # <= 20
            ranging_vote += 1
            # ADX 0-20 映射到 50-100（越低越震荡）
            adx_score = min(100, 50 + (self.adx_range_threshold - adx) * 2.5)
        else:
            # 20-25 中间区域，较弱信号
            adx_score = 40
        
        # 2. 布林带宽度判断（权重 30%）
        if bb_width < self.bb_squeeze_threshold:  # < 2%
            ranging_vote += 1
            # 越窄越震荡，0-2% 映射到 60-100
            squeeze_ratio = (self.bb_squeeze_threshold - bb_width) / self.bb_squeeze_threshold
            bb_score = 60 + squeeze_ratio * 40
        elif bb_width > self.bb_squeeze_threshold * 2:  # > 4%
            trending_vote += 1
            # 越宽越趋势，4-10% 映射到 60-100
            expand_ratio = min(1, (bb_width - self.bb_squeeze_threshold * 2) / 0.06)
            bb_score = 60 + expand_ratio * 40
        else:
            # 2-4% 中间区域
            bb_score = 50
        
        # 3. 均线排列判断（权重 30%）
        if ma_alignment in ["bullish", "bearish"]:
            trending_vote += 1
            ma_score = 80  # 明确排列
        else:
            ranging_vote += 1
            ma_score = 70  # 缠绕
        
        # 确定市场状态
        if trending_vote >= 2:
            regime = "trending"
        elif ranging_vote >= 2:
            regime = "ranging"
        else:
            regime = "uncertain"
        
        # 计算综合置信度（加权平均）
        # 只计算支持当前判断的指标得分
        if regime == "trending":
            weights = []
            scores = []
            if adx >= self.adx_trend_threshold:
                weights.append(0.4)
                scores.append(adx_score)
            if bb_width > self.bb_squeeze_threshold * 1.5:
                weights.append(0.3)
                scores.append(bb_score)
            if ma_alignment in ["bullish", "bearish"]:
                weights.append(0.3)
                scores.append(ma_score)
            
            if weights:
                total_weight = sum(weights)
                strength = sum(w * s for w, s in zip(weights, scores)) / total_weight
            else:
                strength = 50
        elif regime == "ranging":
            weights = []
            scores = []
            if adx <= self.adx_range_threshold:
                weights.append(0.4)
                scores.append(adx_score)
            if bb_width < self.bb_squeeze_threshold:
                weights.append(0.3)
                scores.append(bb_score)
            if ma_alignment == "neutral":
                weights.append(0.3)
                scores.append(ma_score)
            
            if weights:
                total_weight = sum(weights)
                strength = sum(w * s for w, s in zip(weights, scores)) / total_weight
            else:
                strength = 50
        else:
            strength = 40  # 不确定状态，较低置信度
        
        # 确定方向
        if ma_alignment == "bullish":
            direction = "bullish"
        elif ma_alignment == "bearish":
            direction = "bearish"
        else:
            closes = [c["close"] for c in candles[-20:]]
            if closes[-1] > sum(closes) / len(closes):
                direction = "bullish"
            else:
                direction = "bearish"
        
        return MarketState(
            regime=regime,
            direction=direction,
            strength=int(strength),
            adx=adx,
            bb_width=bb_width,
            ma_alignment=ma_alignment,
        )
    
    def _check_filters(self, candles: List[Dict], state: 'MarketState') -> Optional[str]:
        """
        检查所有过滤器，返回过滤原因（字符串）或 None（通过）
        """
        closes = [c["close"] for c in candles]
        
        # ── 冷却检查 ──
        if self.cooldown_bars > 0 and self._bar_index < self._cooldown_until:
            self.filtered_by_cooldown += 1
            return "cooldown"
        
        # ── 最低置信度 ──
        if self.min_confidence > 0 and state.strength < self.min_confidence:
            self.filtered_by_confidence += 1
            return "low_confidence"
        
        # ── RSI 过滤（仅趋势单边有意义）──
        if self.rsi_filter and state.regime == "trending":
            rsi_val = rsi(closes, self.rsi_period)
            if rsi_val is not None:
                if state.direction == "bullish" and rsi_val > self.rsi_overbought:
                    self.filtered_by_rsi += 1
                    return "rsi_overbought"
                if state.direction == "bearish" and rsi_val < self.rsi_oversold:
                    self.filtered_by_rsi += 1
                    return "rsi_oversold"
        
        # ── MACD 方向确认（仅趋势）──
        if self.macd_filter and state.regime == "trending":
            macd_val = macd(closes)
            if macd_val is not None:
                hist = macd_val["histogram"]
                if state.direction == "bullish" and hist < 0:
                    self.filtered_by_macd += 1
                    return "macd_bearish"
                if state.direction == "bearish" and hist > 0:
                    self.filtered_by_macd += 1
                    return "macd_bullish"
        
        # ── 量比过滤（仅趋势）──
        if self.volume_filter and state.regime == "trending":
            volumes = [c.get("volume", 0) for c in candles]
            vol_r = volume_ratio(volumes, period=20)
            if vol_r is not None and vol_r < self.volume_min_ratio:
                self.filtered_by_volume += 1
                return "low_volume"
        
        return None  # 全部通过
    
    def set_cooldown(self):
        """外部（回测引擎）通知策略：刚被止损，触发冷却"""
        if self.cooldown_bars > 0:
            self._cooldown_until = self._bar_index + self.cooldown_bars
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析市场状态并产生信号"""
        
        if len(candles) < 60:
            return None
        
        self._bar_index += 1
        
        current_price = candles[-1]["close"]
        atr_val = atr(candles, self.atr_period) or current_price * 0.02
        
        # 1. 识别市场状态
        state = self._detect_market_state(candles)
        
        # 1.5 过滤器检查
        filter_reason = self._check_filters(candles, state)
        if filter_reason:
            return None
        
        # 2. 计算 TP/SL（支持分治模式）
        if self.sl_tp_mode == "margin_pct":
            # 逐仓保证金百分比模式
            # 分治: 震荡/趋势可用不同参数
            if state.regime == "ranging":
                _tp = self.ranging_tp_pct if self.ranging_tp_pct is not None else self.tp_pct
                _sl = self.ranging_sl_pct if self.ranging_sl_pct is not None else self.sl_pct
            else:
                _tp = self.trending_tp_pct if self.trending_tp_pct is not None else self.tp_pct
                _sl = self.trending_sl_pct if self.trending_sl_pct is not None else self.sl_pct
            tp_dist_pct = _tp / self.leverage if _tp and _tp > 0 else 0
            sl_dist_pct = _sl / self.leverage
        else:
            tp_dist_pct = None  # 使用 ATR 模式
            sl_dist_pct = None
        
        # 3. 根据状态产生信号
        signal = None
        
        if state.regime == "ranging":
            if self.skip_ranging:
                return None  # 跳过震荡行情，只做趋势
            
            # 震荡市场 → 多空双开（对冲），各自独立止损止盈
            if self.sl_tp_mode == "margin_pct":
                long_stop_loss = round(current_price * (1 - sl_dist_pct), 2)
                long_take_profit = round(current_price * (1 + tp_dist_pct), 2) if tp_dist_pct > 0 else None
                short_stop_loss = round(current_price * (1 + sl_dist_pct), 2)
                short_take_profit = round(current_price * (1 - tp_dist_pct), 2) if tp_dist_pct > 0 else None
            else:
                long_stop_loss = round(current_price - atr_val * self.atr_mult_sl, 2)
                long_take_profit = round(current_price + atr_val * self.atr_mult_tp, 2)
                short_stop_loss = round(current_price + atr_val * self.atr_mult_sl, 2)
                short_take_profit = round(current_price - atr_val * self.atr_mult_tp, 2)
            
            signal = StrategyOutput(
                symbol=symbol,
                signal_type="HEDGE",
                side="BOTH",
                entry_price=current_price,
                stop_loss=long_stop_loss,         # 默认给多仓的 SL（兼容旧引擎）
                take_profit=long_take_profit,     # 默认给多仓的 TP（None=纯靠移动止损出场）
                confidence=int(state.strength),
                reason=f"震荡对冲: ADX={state.adx:.1f}, BB宽={state.bb_width:.2%}, MA={state.ma_alignment}",
                indicators={
                    "regime": state.regime,
                    "direction": state.direction,
                    "adx": round(state.adx, 2),
                    "bb_width": round(state.bb_width, 4),
                    "ma_alignment": state.ma_alignment,
                    "strength": state.strength,
                    "mode": "hedge",
                    "atr": round(atr_val, 2),
                    "sl_tp_mode": self.sl_tp_mode,
                    # 多空独立止损止盈
                    "long_stop_loss": long_stop_loss,
                    "long_take_profit": long_take_profit,
                    "short_stop_loss": short_stop_loss,
                    "short_take_profit": short_take_profit,
                },
            )
        
        elif state.regime == "trending":
            # 趋势市场 → 单边顺势
            if state.direction == "bullish":
                side = "BUY"
                if self.sl_tp_mode == "margin_pct":
                    stop_loss = current_price * (1 - sl_dist_pct)
                    take_profit = current_price * (1 + tp_dist_pct) if tp_dist_pct > 0 else None
                else:
                    stop_loss = current_price - atr_val * self.atr_mult_sl
                    take_profit = current_price + atr_val * self.atr_mult_tp
            else:
                side = "SELL"
                if self.sl_tp_mode == "margin_pct":
                    stop_loss = current_price * (1 + sl_dist_pct)
                    take_profit = current_price * (1 - tp_dist_pct) if tp_dist_pct > 0 else None
                else:
                    stop_loss = current_price + atr_val * self.atr_mult_sl
                    take_profit = current_price - atr_val * self.atr_mult_tp
            
            signal = StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side=side,
                entry_price=current_price,
                stop_loss=round(stop_loss, 2),
                take_profit=round(take_profit, 2) if take_profit is not None else None,
                confidence=int(state.strength),
                reason=f"趋势市场{side}: ADX={state.adx:.1f}, BB宽={state.bb_width:.2%}, MA={state.ma_alignment}",
                indicators={
                    "regime": state.regime,
                    "direction": state.direction,
                    "adx": round(state.adx, 2),
                    "bb_width": round(state.bb_width, 4),
                    "ma_alignment": state.ma_alignment,
                    "strength": state.strength,
                    "mode": "single",
                    "atr": round(atr_val, 2),
                    "sl_tp_mode": self.sl_tp_mode,
                },
            )
        
        # uncertain 状态不开仓
        
        return signal
