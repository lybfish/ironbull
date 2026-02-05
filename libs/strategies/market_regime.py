"""
Market Regime Strategy - 市场状态识别策略

功能：
1. 自动识别市场状态（震荡/趋势）
2. 震荡市场 → 双向开仓（对冲）
3. 趋势市场 → 单边开仓（顺势）

识别方法（多指标融合）：
- ADX: < 20 震荡，> 25 趋势
- 布林带宽: 收窄=震荡，扩张=趋势
- 均线排列: 缠绕=震荡，多头/空头排列=趋势
- ATR变化: 萎缩=震荡，放大=趋势
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from libs.contracts import StrategyOutput
from libs.indicators import sma, ema, atr
from libs.indicators.bollinger import bollinger
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
    - adx_trend_threshold: ADX趋势阈值（默认25）
    - adx_range_threshold: ADX震荡阈值（默认20）
    - bb_period: 布林带周期（默认20）
    - bb_squeeze_threshold: 布林带收窄阈值（默认0.02 = 2%）
    - ma_periods: 均线周期列表（默认[10, 20, 50]）
    
    资金管理参数：
    - max_position: 最大持仓金额（默认1000）
    - risk_pct: 每笔风险比例（保守1%，激进2%）
    - atr_mult_sl: ATR止损倍数（默认2.0）
    - atr_mult_tp: ATR止盈倍数（默认3.0）
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "market_regime"
        self.name = "市场状态识别策略"
        
        # 市场识别参数
        self.adx_period = self.config.get("adx_period", 14)
        self.adx_trend_threshold = self.config.get("adx_trend_threshold", 25)
        self.adx_range_threshold = self.config.get("adx_range_threshold", 20)
        self.bb_period = self.config.get("bb_period", 20)
        self.bb_std = self.config.get("bb_std", 2.0)
        self.bb_squeeze_threshold = self.config.get("bb_squeeze_threshold", 0.02)
        self.ma_periods = self.config.get("ma_periods", [10, 20, 50])
        
        # 资金管理参数
        self.max_position = self.config.get("max_position", 1000)
        self.risk_pct = self.config.get("risk_pct", 0.01)  # 1%保守，2%激进
        self.tp_pct_min = self.config.get("tp_pct_min", 0.45)  # 45%
        self.tp_pct_max = self.config.get("tp_pct_max", 0.70)  # 70%
        self.sl_pct = self.config.get("sl_pct", 0.70)  # -70%
        
        # ATR 参数
        self.atr_period = self.config.get("atr_period", 14)
        self.atr_mult_sl = self.config.get("atr_mult_sl", 2.0)
        self.atr_mult_tp = self.config.get("atr_mult_tp", 3.0)
    
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
        
        current_price = candles[-1]["close"]
        atr_val = atr(candles, self.atr_period) or current_price * 0.02
        
        # 1. 识别市场状态
        state = self._detect_market_state(candles)
        
        # 2. 根据状态产生信号
        signal = None
        
        if state.regime == "ranging":
            # 震荡市场 → 单向开仓（根据方向），使用 ATR 止损
            # 震荡市场中逆向操作（低买高卖）
            if state.direction == "bearish":
                # 价格偏低，做多
                side = "BUY"
                stop_loss = current_price - atr_val * self.atr_mult_sl
                take_profit = current_price + atr_val * self.atr_mult_tp
            else:
                # 价格偏高，做空
                side = "SELL"
                stop_loss = current_price + atr_val * self.atr_mult_sl
                take_profit = current_price - atr_val * self.atr_mult_tp
            
            signal = StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side=side,
                entry_price=current_price,
                stop_loss=round(stop_loss, 2),
                take_profit=round(take_profit, 2),
                confidence=int(state.strength),
                reason=f"震荡市场{side}: ADX={state.adx:.1f}, BB宽={state.bb_width:.2%}, MA={state.ma_alignment}",
                indicators={
                    "regime": state.regime,
                    "direction": state.direction,
                    "adx": round(state.adx, 2),
                    "bb_width": round(state.bb_width, 4),
                    "ma_alignment": state.ma_alignment,
                    "strength": state.strength,
                    "mode": "ranging_reversal",
                    "atr": round(atr_val, 2),
                },
            )
        
        elif state.regime == "trending":
            # 趋势市场 → 单边顺势
            if state.direction == "bullish":
                side = "BUY"
                stop_loss = current_price - atr_val * self.atr_mult_sl
                take_profit = current_price + atr_val * self.atr_mult_tp
            else:
                side = "SELL"
                stop_loss = current_price + atr_val * self.atr_mult_sl
                take_profit = current_price - atr_val * self.atr_mult_tp
            
            signal = StrategyOutput(
                symbol=symbol,
                signal_type="OPEN",
                side=side,
                entry_price=current_price,
                stop_loss=round(stop_loss, 2),
                take_profit=round(take_profit, 2),
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
                },
            )
        
        # uncertain 状态不开仓
        
        return signal
