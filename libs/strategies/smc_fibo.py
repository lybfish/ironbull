"""
SMC + Fibonacci Strategy - 以损定仓版本 + 多时间框架过滤

核心逻辑：
- SMC (Smart Money Concepts) 识别订单块和流动性区域
- Fibonacci 回撤位确认入场点（0.382/0.5/0.618）
- 以损定仓：根据固定止损金额计算仓位
- 盈亏比过滤：< min_rr 不开仓
- 多时间框架(MTF)：只在大周期趋势方向一致时开仓
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

from libs.contracts import StrategyOutput
from libs.indicators import atr, sma, ema
from libs.indicators.fibo import fibo_levels, price_in_fibo_zone, fibo_extension
from .base import StrategyBase


@dataclass
class OrderBlock:
    """订单块"""
    index: int
    type: str            # bullish / bearish
    high: float
    low: float
    body_high: float
    body_low: float
    strength: float


@dataclass 
class SwingPoint:
    """摆动点"""
    index: int
    price: float
    type: str  # high / low


class SMCFiboStrategy(StrategyBase):
    """
    SMC + 斐波那契回踩策略（以损定仓版 + MTF过滤）
    
    入场条件（做多）：
    1. 大周期趋势看涨（HTF Filter）
    2. 识别上升趋势中的摆动高低点
    3. 价格回踩到斐波那契关键位（0.382/0.5/0.618）
    4. 有看涨订单块支撑
    5. 盈亏比 >= min_rr
    
    入场条件（做空）：
    1. 大周期趋势看跌（HTF Filter）
    2. 识别下降趋势中的摆动高低点
    3. 价格反弹到斐波那契关键位
    4. 有看跌订单块阻力
    5. 盈亏比 >= min_rr
    
    仓位计算：
    - 仓位 = 固定亏损金额 / 止损距离
    - 止损设在订单块外侧
    - 止盈 = 入场 + (止损距离 × 盈亏比)
    
    多时间框架过滤：
    - 使用 htf_multiplier 倍的K线聚合为大周期
    - 例如 1h 图 + htf_multiplier=4 = 模拟 4h 大周期
    - 大周期使用 EMA 判断趋势方向
    
    参数：
    - max_loss: 每单最大亏损（默认 100 USDT）
    - min_rr: 最小盈亏比（默认 1.5）
    - fibo_levels: 关键回撤位（默认 [0.382, 0.5, 0.618]）
    - fibo_tolerance: 回撤位容差（默认 0.5%）
    - lookback: 回看周期（默认 50）
    - htf_multiplier: 大周期倍数（默认 4，即 1h->4h）
    - htf_ema_fast: 大周期快EMA（默认 20）
    - htf_ema_slow: 大周期慢EMA（默认 50）
    - require_htf_filter: 是否要求大周期过滤（默认 True）
    
    回踩拒绝确认（移植自 old1 版本）：
    - require_retest: 是否要求回踩拒绝确认入场（默认 True）
    - retest_bars: 信号产生后最多等待多少根K线确认（默认 20）
    - pinbar_ratio: Pin Bar 影线/实体最小比值（默认 1.5）
    - allow_engulf: 是否允许吞没形态作为确认（默认 True）
    - retest_ignore_stop_touch: 回踩期间触及止损是否忽略（默认 False）
    
    确认流程：
    1. 识别信号（Fibo + OB）→ 不立即入场，存为 pending
    2. 后续K线检测：价格是否触达回踩区间
    3. 触达后检测拒绝K线形态（Pin Bar / 吞没 / 晨星 / 暮星）
    4. 确认后以当前收盘价入场；超时或触及止损则撤单
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.code = "smc_fibo"
        self.name = "SMC斐波那契回踩策略(MTF)"
        
        # 资金管理参数（与 old1 配置对齐）
        self.max_loss = self.config.get("max_loss", 100)       # 每单最大亏损 USDT（old1: risk_cash=100）
        self.min_rr = self.config.get("min_rr", 2.0)           # 最小盈亏比（old1: FIBO_MIN_RR=2）
        
        # 斐波那契参数（old1默认值）
        self.fibo_entry_levels = self.config.get("fibo_levels", [0.5, 0.618, 0.705])  # old1默认
        self.fibo_tolerance = self.config.get("fibo_tolerance", 0.005)  # 0.5%
        
        # SMC 参数
        self.lookback = self.config.get("lookback", 50)
        self.swing_left = self.config.get("swing_left", 5)
        self.swing_right = self.config.get("swing_right", 3)
        self.ob_min_body_ratio = self.config.get("ob_min_body_ratio", 0.5)
        
        # 止损缓冲（与old1保持一致：0.05% → 参数值 0.05 需除以 100 得到小数）
        # old1 中 stopBufferPct=0.05 表示 0.05%，内部 /100 → 0.0005
        # _sl_buffer_raw: 保留原始配置值，传递给 old1 引擎（old1 自行 /100）
        # sl_buffer_pct:  native 模式使用的实际小数值
        raw_sl_buffer = self.config.get("sl_buffer_pct", 0.05)
        self._sl_buffer_raw = raw_sl_buffer  # 原始值，给 old1 引擎用
        # 兼容：如果用户传入的已经是小数形式（<0.01），不再除 100
        if raw_sl_buffer >= 0.01:
            self.sl_buffer_pct = raw_sl_buffer / 100.0   # 0.05 → 0.0005
        else:
            self.sl_buffer_pct = raw_sl_buffer            # 已经是 0.0005 形式
        
        # 多时间框架参数
        self.htf_multiplier = self.config.get("htf_multiplier", 4)      # 大周期倍数
        self.htf_ema_fast = self.config.get("htf_ema_fast", 20)         # 大周期快EMA
        self.htf_ema_slow = self.config.get("htf_ema_slow", 50)         # 大周期慢EMA
        self.require_htf_filter = self.config.get("require_htf_filter", True)  # 是否强制大周期过滤
        
        # 回踩确认参数（移植自 old1 版本 detect_rejection）
        self.require_retest = self.config.get("require_retest", True)              # 是否要求回踩拒绝确认
        self.retest_bars = self.config.get("retest_bars", 20)                      # 最大等待K线数（old1: FIBO_RETEST_BARS=20）
        self.pinbar_ratio = self.config.get("pinbar_ratio", 1.5)                   # Pin Bar 影线/实体比（old1: 1.5）
        self.allow_engulf = self.config.get("allow_engulf", True)                  # 是否允许吞没形态确认
        self.retest_ignore_stop_touch = self.config.get("retest_ignore_stop_touch", False)
        
        # 斐波那契 Fallback 机制（old1 特性）
        self.fibo_fallback = self.config.get("fibo_fallback", True)                # 是否启用斐波那契 Fallback
        
        # 止损止盈配置（old1 特性）
        self.stop_source = self.config.get("stop_source", "auto")                 # 止损来源: auto/ob/swing
        self.tp_mode = self.config.get("tp_mode", "swing")                        # 止盈模式: swing/rr/fibo（默认swing，与old1一致）

        # 结构与方向过滤（与 old1 对齐）
        # structure: "bos"（只做结构突破）、"choch"（只做结构反转）、"both"（默认，二者都要）
        self.structure = (self.config.get("structure") or "both").lower()
        # bias: "with_trend"（顺势，默认）、"counter"（逆势）、"both"（不限制）
        self.bias = (self.config.get("bias") or "with_trend").lower()

        # old1 严格对齐（使用内置 old1 逻辑生成信号）
        # 注意：该模式会在每次 analyze 中运行 smc_backtest，性能较慢但结果最接近 old1
        self.use_old1_engine = self.config.get("use_old1_engine", True)
        # 需要完整历史以对齐 old1 信号序列
        self.requires_full_history = True
        
        # 回踩状态（跨 analyze 调用保持）
        self._pending = None
        # old1 严格模式下已发出的信号时间戳
        self._old1_last_signal_ts = None
        self._old1_emitted_ids = set()

    # ====================== old1 对齐模式 ======================
    def _to_old1_candles(self, candles: List[Dict]) -> List[Dict[str, Any]]:
        out = []
        for c in candles:
            ts = c.get("time") if "time" in c else c.get("timestamp")
            if isinstance(ts, str):
                try:
                    ts = int(datetime.fromisoformat(ts).timestamp())
                except Exception:
                    ts = None
            out.append({
                "ts": int(ts) if ts is not None else 0,
                "o": float(c.get("open")),
                "h": float(c.get("high")),
                "l": float(c.get("low")),
                "c": float(c.get("close")),
                "v": float(c.get("volume", 0)),
            })
        return out

    def _aggregate_htf_old1(self, candles: List[Dict[str, Any]], ltf: str, htf: str) -> List[Dict[str, Any]]:
        def tf_to_seconds(tf: str) -> int:
            t = (tf or "").lower()
            if t.endswith("m"):
                return int(t[:-1]) * 60
            if t.endswith("h"):
                return int(t[:-1]) * 3600
            if t.endswith("d"):
                return int(t[:-1]) * 86400
            return 60

        ltf_sec = tf_to_seconds(ltf)
        htf_sec = tf_to_seconds(htf)
        if htf_sec <= ltf_sec or ltf_sec <= 0:
            return []
        # 使用时间戳分桶，避免缺失K线导致聚合偏移
        buckets: Dict[int, Dict[str, Any]] = {}
        for c in candles:
            ts = int(c["ts"])
            htf_ts = (ts // htf_sec) * htf_sec
            b = buckets.get(htf_ts)
            if not b:
                buckets[htf_ts] = {
                    "ts": htf_ts,
                    "o": c["o"],
                    "h": c["h"],
                    "l": c["l"],
                    "c": c["c"],
                    "v": c["v"],
                }
            else:
                b["h"] = max(b["h"], c["h"])
                b["l"] = min(b["l"], c["l"])
                b["c"] = c["c"]
                b["v"] += c["v"]
        return [buckets[k] for k in sorted(buckets.keys())]

    def _old1_params(self, symbol: str, timeframe: str, htf_timeframe: str) -> Dict[str, Any]:
        return {
            "strategy": "smc_fibo",
            "symbol": symbol,
            "timeframe": timeframe,
            "htf_timeframe": htf_timeframe,
            "entry_mode": "retest",
            "order_type": "limit",
            "tif_bars": 20,
            "risk_cash": self.max_loss,
            "rr": self.min_rr,
            # 增量调用模式必须开启 realtime_mode：
            # 非实时模式下 swing 检测需要 "未来 K 线" 确认，
            # 增量调用时最后几根 K 线的 swing 永远检测不到，导致信号丢失
            "realtime_mode": True,
            "smc": {
                "fiboLevels": self.fibo_entry_levels,
                "fiboFallback": self.fibo_fallback,
                "retestBars": self.retest_bars,
                "minRr": self.min_rr,
                "pinbarRatio": self.pinbar_ratio,
                "allowEngulf": self.allow_engulf,
                "stopBufferPct": self._sl_buffer_raw,  # old1 内部会 /100
                "stopSource": self.stop_source,
                "tpMode": self.tp_mode,
                "structure": self.structure,
                "bias": self.bias,
                "entry": "auto",
                "session": "all",
                "useOb": True,
                "useFvg": True,
                "useSweep": True,
            },
        }

    def _analyze_with_old1(self, symbol: str, timeframe: str, candles: List[Dict]) -> Optional[StrategyOutput]:
        try:
            from .smc_fibo_old1 import smc_backtest
        except Exception:
            return None

        old1_candles = self._to_old1_candles(candles)
        # 推断 HTF
        htf_timeframe = "1h"
        if timeframe.endswith("m"):
            try:
                mult = self.htf_multiplier
                minutes = int(timeframe[:-1]) * mult
                if minutes % 60 == 0:
                    htf_timeframe = f"{minutes // 60}h"
                else:
                    htf_timeframe = f"{minutes}m"
            except Exception:
                htf_timeframe = "1h"
        params = self._old1_params(symbol, timeframe, htf_timeframe)
        htf_candles = self._aggregate_htf_old1(old1_candles, timeframe, htf_timeframe)
        result = smc_backtest(params, old1_candles, htf_candles=htf_candles)
        signals = result.get("signals") or []
        order_zones = result.get("orderZones") or []
        if not signals or not old1_candles:
            return None
        # 仅在"当前K线"触发信号，确保时序对齐
        current_ts = old1_candles[-1].get("ts")
        candidates = [s for s in signals if s.get("bar_ts") == current_ts]
        if not candidates:
            return None
        hit = None
        for s in candidates:
            sid = (s.get("bar_ts"), s.get("side"), s.get("entry_intent"))
            if sid not in self._old1_emitted_ids:
                hit = s
                self._old1_emitted_ids.add(sid)
                break
        if not hit:
            return None
        last_ts = hit.get("bar_ts") or hit.get("ts")
        if last_ts is not None:
            self._old1_last_signal_ts = last_ts
        side = hit.get("side")
        entry = hit.get("entry_intent")
        if not side or entry is None:
            return None

        # 从 orderZones 中提取止损止盈（按 bar_ts + side 匹配）
        stop_loss = None
        take_profit = None
        for z in reversed(order_zones):
            if z.get("bar_ts") == hit.get("bar_ts") and z.get("side") == side:
                stop_loss = z.get("stop")
                take_profit = z.get("tp")
                break

        return StrategyOutput(
            symbol=symbol,
            signal_type="OPEN",
            side=side,
            entry_price=float(entry),
            stop_loss=float(stop_loss) if stop_loss is not None else None,
            take_profit=float(take_profit) if take_profit is not None else None,
            confidence=70,
            reason=f"old1 strict: {hit.get('reason')}",
            indicators={
                "old1_signal": hit,
                # 不要求 BacktestEngine 做回踩确认（old1 引擎自行处理）
                "require_retest": False,
            },
        )
    
    def _aggregate_to_htf(self, candles: List[Dict]) -> List[Dict]:
        """
        将小周期K线聚合为大周期
        
        例如：4根1h K线 -> 1根4h K线
        """
        if len(candles) < self.htf_multiplier:
            return []
        
        htf_candles = []
        n = self.htf_multiplier
        
        # 从后往前聚合，确保最新的K线完整
        for i in range(0, len(candles) - n + 1, n):
            chunk = candles[i:i + n]
            
            htf_candle = {
                "time": chunk[0].get("time"),
                "open": chunk[0]["open"],
                "high": max(c["high"] for c in chunk),
                "low": min(c["low"] for c in chunk),
                "close": chunk[-1]["close"],
                "volume": sum(c.get("volume", 0) for c in chunk),
            }
            htf_candles.append(htf_candle)
        
        return htf_candles
    
    def _get_htf_trend(self, candles: List[Dict]) -> str:
        """
        判断大周期趋势方向
        
        使用 EMA 交叉判断：
        - bullish: 快EMA > 慢EMA（大周期上升趋势）
        - bearish: 快EMA < 慢EMA（大周期下降趋势）
        - neutral: EMA 非常接近（横盘震荡）
        """
        # 聚合到大周期
        htf_candles = self._aggregate_to_htf(candles)
        
        min_candles = self.htf_ema_slow + 5
        if len(htf_candles) < min_candles:
            # 数据不足时，退化为使用原始K线计算
            closes = [c["close"] for c in candles]
            if len(closes) < self.htf_ema_slow * self.htf_multiplier:
                return "neutral"
            ema_fast = ema(closes, self.htf_ema_fast * self.htf_multiplier)
            ema_slow = ema(closes, self.htf_ema_slow * self.htf_multiplier)
        else:
            # 计算大周期EMA
            closes = [c["close"] for c in htf_candles]
            ema_fast = ema(closes, self.htf_ema_fast)
            ema_slow = ema(closes, self.htf_ema_slow)
        
        if ema_fast is None or ema_slow is None:
            return "neutral"
        
        # 计算EMA差距百分比
        ema_diff_pct = (ema_fast - ema_slow) / ema_slow * 100
        
        # 判断趋势（差距超过0.5%才确认趋势）
        if ema_diff_pct > 0.5:
            return "bullish"
        elif ema_diff_pct < -0.5:
            return "bearish"
        
        return "neutral"
    
    def _find_swing_points(self, candles: List[Dict]) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """识别摆动高低点"""
        swing_highs = []
        swing_lows = []
        left = self.swing_left
        right = self.swing_right
        
        for i in range(left, len(candles) - right):
            high = candles[i]["high"]
            low = candles[i]["low"]
            
            # 摆动高点
            is_swing_high = True
            for j in range(i - left, i + right + 1):
                if j != i and candles[j]["high"] >= high:
                    is_swing_high = False
                    break
            if is_swing_high:
                swing_highs.append(SwingPoint(index=i, price=high, type="high"))
            
            # 摆动低点
            is_swing_low = True
            for j in range(i - left, i + right + 1):
                if j != i and candles[j]["low"] <= low:
                    is_swing_low = False
                    break
            if is_swing_low:
                swing_lows.append(SwingPoint(index=i, price=low, type="low"))
        
        return swing_highs, swing_lows
    
    def _find_order_blocks(self, candles: List[Dict]) -> List[OrderBlock]:
        """识别订单块"""
        order_blocks = []
        
        for i in range(2, len(candles) - 1):
            c0 = candles[i - 1]
            c1 = candles[i]
            
            body0 = abs(c0["close"] - c0["open"])
            body1 = abs(c1["close"] - c1["open"])
            range0 = c0["high"] - c0["low"]
            range1 = c1["high"] - c1["low"]
            
            if range0 == 0 or range1 == 0:
                continue
            
            body_ratio1 = body1 / range1
            
            # 看涨订单块
            if (c0["close"] < c0["open"] and
                c1["close"] > c1["open"] and
                body_ratio1 >= self.ob_min_body_ratio and
                c1["close"] > c0["high"]):
                
                strength = min(100, (c1["close"] - c0["high"]) / c0["high"] * 1000)
                order_blocks.append(OrderBlock(
                    index=i - 1,
                    type="bullish",
                    high=c0["high"],
                    low=c0["low"],
                    body_high=max(c0["open"], c0["close"]),
                    body_low=min(c0["open"], c0["close"]),
                    strength=strength,
                ))
            
            # 看跌订单块
            if (c0["close"] > c0["open"] and
                c1["close"] < c1["open"] and
                body_ratio1 >= self.ob_min_body_ratio and
                c1["close"] < c0["low"]):
                
                strength = min(100, (c0["low"] - c1["close"]) / c0["low"] * 1000)
                order_blocks.append(OrderBlock(
                    index=i - 1,
                    type="bearish",
                    high=c0["high"],
                    low=c0["low"],
                    body_high=max(c0["open"], c0["close"]),
                    body_low=min(c0["open"], c0["close"]),
                    strength=strength,
                ))
        
        return order_blocks
    
    def _get_trend(self, candles: List[Dict], swing_highs: List[SwingPoint], swing_lows: List[SwingPoint]) -> str:
        """判断趋势 - 基于摆动点结构"""
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "neutral"
        
        # 高点和低点都在上升 = 上升趋势
        hh = swing_highs[-1].price > swing_highs[-2].price  # Higher High
        hl = swing_lows[-1].price > swing_lows[-2].price    # Higher Low
        
        # 高点和低点都在下降 = 下降趋势
        lh = swing_highs[-1].price < swing_highs[-2].price  # Lower High
        ll = swing_lows[-1].price < swing_lows[-2].price    # Lower Low
        
        if hh and hl:
            return "bullish"
        elif lh and ll:
            return "bearish"
        
        return "neutral"
    
    def _calc_position_size(self, entry: float, stop_loss: float) -> float:
        """
        以损定仓：根据固定亏损金额计算仓位
        
        仓位 = 最大亏损 / 止损距离
        """
        sl_distance = abs(entry - stop_loss)
        if sl_distance == 0:
            return 0
        
        # 仓位大小（合约数量）
        position_size = self.max_loss / sl_distance
        return round(position_size, 4)
    
    def _calc_rr_ratio(self, entry: float, stop_loss: float, take_profit: float) -> float:
        """计算盈亏比"""
        sl_distance = abs(entry - stop_loss)
        tp_distance = abs(take_profit - entry)
        
        if sl_distance == 0:
            return 0
        
        return tp_distance / sl_distance
    
    def _calc_stop_loss(self, side: str, entry: float, order_block: Optional[OrderBlock], 
                       recent_high: float, recent_low: float) -> float:
        """
        根据 stop_source 计算止损价
        
        Args:
            side: BUY/SELL
            entry: 入场价
            order_block: 支撑/阻力的订单块（做多为 supporting_ob，做空为 resisting_ob）
            recent_high: 最近摆动高点
            recent_low: 最近摆动低点
            
        Returns:
            止损价
        """
        if self.stop_source == "ob":
            # 仅使用订单块
            if order_block:
                if side == "BUY":
                    return order_block.low * (1 - self.sl_buffer_pct)
                else:
                    return order_block.high * (1 + self.sl_buffer_pct)
            # 没有订单块时，fallback 到摆动点
            if side == "BUY":
                return recent_low * (1 - self.sl_buffer_pct)
            else:
                return recent_high * (1 + self.sl_buffer_pct)
        elif self.stop_source == "swing":
            # 仅使用摆动点
            if side == "BUY":
                return recent_low * (1 - self.sl_buffer_pct)
            else:
                return recent_high * (1 + self.sl_buffer_pct)
        else:
            # auto: 优先订单块，fallback 到摆动点
            if order_block:
                if side == "BUY":
                    return order_block.low * (1 - self.sl_buffer_pct)
                else:
                    return order_block.high * (1 + self.sl_buffer_pct)
            else:
                if side == "BUY":
                    return recent_low * (1 - self.sl_buffer_pct)
                else:
                    return recent_high * (1 + self.sl_buffer_pct)
    
    def _calc_take_profit(self, side: str, entry: float, stop_loss: float, 
                         recent_high: float, recent_low: float, swing_range: float) -> float:
        """
        根据 tp_mode 计算止盈价
        
        Args:
            side: BUY/SELL
            entry: 入场价
            stop_loss: 止损价
            recent_high: 最近摆动高点
            recent_low: 最近摆动低点
            swing_range: 摆动范围
            
        Returns:
            止盈价
        """
        sl_distance = abs(entry - stop_loss)
        
        if self.tp_mode == "swing":
            # 回到摆动点
            if side == "BUY":
                tp = recent_high
            else:
                tp = recent_low
        elif self.tp_mode == "rr":
            # 固定盈亏比
            if side == "BUY":
                tp = entry + sl_distance * self.min_rr
            else:
                tp = entry - sl_distance * self.min_rr
        else:
            # fibo: 斐波那契扩展位（默认）
            extension = fibo_extension(recent_high, recent_low, [1.272, 1.618])
            if side == "BUY":
                # 优先使用 1.272 扩展位，fallback 到固定盈亏比
                tp = extension.get(1.272, entry + sl_distance * self.min_rr)
            else:
                # 做空：从低点向下扩展
                fibo_tp = recent_low - (swing_range * 0.272)
                tp = fibo_tp if fibo_tp < entry else entry - sl_distance * self.min_rr
        
        # 确保满足最小盈亏比（old1的ensure_min_rr机制）
        return self._ensure_min_rr(side, entry, stop_loss, tp)
    
    def _ensure_min_rr(self, side: str, entry: float, stop_loss: float, tp: float) -> float:
        """
        确保止盈满足最小盈亏比要求（old1的ensure_min_rr机制）
        
        如果初始止盈的盈亏比不够，自动调整止盈价格以满足min_rr要求
        
        Args:
            side: BUY/SELL
            entry: 入场价
            stop_loss: 止损价
            tp: 初始止盈价
            
        Returns:
            调整后的止盈价
        """
        # 计算当前盈亏比
        rr_ratio = self._calc_rr_ratio(entry, stop_loss, tp)
        
        # 如果已经满足最小盈亏比，直接返回
        if rr_ratio >= self.min_rr:
            return tp
        
        # 否则，调整止盈以满足最小盈亏比
        sl_distance = abs(entry - stop_loss)
        target_rr = max(self.min_rr * 1.2, self.min_rr + 0.3)  # 目标盈亏比（略高于最小值）
        
        # 尝试调整止盈（最多5次）
        for _ in range(5):
            if side == "BUY":
                tp = entry + target_rr * sl_distance
            else:
                tp = entry - target_rr * sl_distance
            
            # 重新计算盈亏比
            rr_ratio = self._calc_rr_ratio(entry, stop_loss, tp)
            if rr_ratio >= self.min_rr:
                return tp
            
            # 如果还不够，增加目标盈亏比
            target_rr *= 1.35
        
        # 如果5次调整后仍不满足，返回调整后的止盈（至少尝试了）
        return tp
    
    # ================================================================
    #  回踩拒绝确认系统（移植自 old1 版本 detect_rejection）
    # ================================================================

    def _detect_rejection(
        self,
        candle: Dict,
        prev: Optional[Dict],
        prev2: Optional[Dict],
        side: str,
        zone_low: float,
        zone_high: float,
    ) -> Dict[str, bool]:
        """
        检测回踩拒绝K线形态
        
        支持四种形态：
        - Pin Bar：长影线 + 小实体，影线朝止损方向
        - 吞没（Engulfing）：后一根完全包住前一根，方向反转
        - 晨星（Morning Star）：三根K线看涨反转（做多）
        - 暮星（Evening Star）：三根K线看跌反转（做空）
        """
        o = candle["open"]
        c = candle["close"]
        h = candle["high"]
        l = candle["low"]
        body = max(1e-8, abs(c - o))
        upper = h - max(o, c)
        lower = min(o, c) - l

        # 1. Close Reject：收盘价拒绝区间
        if side == "BUY":
            close_reject = c > zone_high and c > o   # 阳线收在区间上方
            pinbar = lower >= self.pinbar_ratio * body and lower >= upper * 1.2
        else:
            close_reject = c < zone_low and c < o    # 阴线收在区间下方
            pinbar = upper >= self.pinbar_ratio * body and upper >= lower * 1.2

        # 2. Engulfing（吞没形态）
        engulf = False
        if self.allow_engulf and prev:
            po, pc = prev["open"], prev["close"]
            if side == "BUY":
                engulf = c > o and pc < po and c >= po and o <= pc
            else:
                engulf = c < o and pc > po and o >= pc and c <= po

        # 3. Morning Star / Evening Star（晨星 / 暮星）
        morning_star = False
        evening_star = False
        if prev and prev2:
            c1o, c1c = prev2["open"], prev2["close"]
            c2o, c2c = prev["open"], prev["close"]
            body1 = abs(c1c - c1o)
            body2 = abs(c2c - c2o)
            if side == "BUY":
                if c1c < c1o and body1 > 0 and body2 < body1 * 0.5:
                    if c > o and body > 0 and c >= (c1o + c1c) / 2.0:
                        morning_star = True
            else:
                if c1c > c1o and body1 > 0 and body2 < body1 * 0.5:
                    if c < o and body > 0 and c <= (c1o + c1c) / 2.0:
                        evening_star = True

        return {
            "close_reject": close_reject,
            "pinbar": pinbar,
            "engulf": engulf,
            "morning_star": morning_star,
            "evening_star": evening_star,
        }

    def _check_pending(self, symbol: str, candles: List[Dict]):
        """
        检查待确认信号的回踩状态
        
        返回:
        - StrategyOutput: 回踩确认成功，立即入场
        - None: 无待确认信号，BacktestEngine 应直接按限价单填充
        - "waiting": 仍在等待确认
        - "expired" / "stop_touched" / "rr_insufficient": 信号取消
        """
        p = self._pending
        if not p:
            # 无待确认的回踩信号 → 返回 None 让 BacktestEngine 直接按限价单填充
            # 这在 use_old1_engine=True 模式下至关重要：old1 引擎自行处理回踩确认，
            # 不会设置 self._pending，所以此处必须返回 None（而非 "no_pending"）
            return None

        # bars_waited应该基于当前K线索引，而不是candles长度
        # 注意：这里传入的candles可能只是最近几根，需要从外部传入当前索引
        # 暂时使用candles长度作为近似值（如果传入的是完整历史，则正确）
        bars_waited = len(candles) - p["created_at"]
        
        # 如果candles长度小于created_at，说明传入的不是完整历史
        # 这种情况下，我们需要使用其他方式计算
        if bars_waited < 0:
            bars_waited = len(candles)  # 使用传入的candles长度作为近似

        # ── 超时检查 ──
        if bars_waited > self.retest_bars:
            self._pending = None
            return "expired"

        current = candles[-1]
        prev = candles[-2] if len(candles) >= 2 else None
        prev2 = candles[-3] if len(candles) >= 3 else None
        side = p["side"]

        # ── 回踩期间触及止损 → 撤单 ──
        if not self.retest_ignore_stop_touch:
            if side == "BUY" and current["low"] <= p["stop_loss"]:
                self._pending = None
                return "stop_touched"
            if side == "SELL" and current["high"] >= p["stop_loss"]:
                self._pending = None
                return "stop_touched"

        # ── 检测价格是否触达回踩区间 ──
        touched = current["low"] <= p["zone_high"] and current["high"] >= p["zone_low"]
        if touched and not p["touched"]:
            p["touched"] = True

        # ── 触达后检测拒绝形态 ──
        if p["touched"]:
            rej = self._detect_rejection(
                current, prev, prev2, side,
                p["zone_low"], p["zone_high"],
            )
            has_pattern = (
                rej["pinbar"] or rej["engulf"]
                or rej["morning_star"] or rej["evening_star"]
            )
            if rej["close_reject"] and has_pattern:
                # ── 回踩确认成功！以当前收盘价入场 ──
                entry_price = current["close"]

                # 重新检查盈亏比
                rr_ratio = self._calc_rr_ratio(
                    entry_price, p["stop_loss"], p["take_profit"]
                )
                if rr_ratio < self.min_rr:
                    self._pending = None
                    return "rr_insufficient"

                # 重新计算仓位
                position_size = self._calc_position_size(entry_price, p["stop_loss"])

                # 确定拒绝形态名称
                patterns = []
                if rej["pinbar"]:
                    patterns.append("PinBar")
                if rej["engulf"]:
                    patterns.append("吞没")
                if rej["morning_star"]:
                    patterns.append("晨星")
                if rej["evening_star"]:
                    patterns.append("暮星")
                pattern_str = "+".join(patterns)

                # 更新指标
                indicators = dict(p["indicators"])
                indicators["confirmation"] = pattern_str
                indicators["bars_waited"] = bars_waited
                indicators["rr_ratio"] = round(rr_ratio, 2)
                indicators["position_size"] = position_size

                side_label = "做多" if side == "BUY" else "做空"
                fibo_level = p.get("fibo_level", 0)

                signal = StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side=side,
                    entry_price=entry_price,
                    stop_loss=round(p["stop_loss"], 2),
                    take_profit=round(p["take_profit"], 2),
                    confidence=min(95, p["confidence"] + 5),
                    reason=(
                        f"SMC+Fibo{side_label}: 回踩{fibo_level:.1%}位"
                        f" {pattern_str}确认({bars_waited}根K线), "
                        f"盈亏比{rr_ratio:.2f}, 仓位{position_size}"
                    ),
                    indicators=indicators,
                )
                self._pending = None
                return signal

        return "waiting"

    # ================================================================

    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        positions: Optional[Dict] = None
    ) -> Optional[StrategyOutput]:
        """分析 SMC + Fibonacci 信号"""
        
        if len(candles) < self.lookback:
            return None

        # old1 严格对齐模式优先
        if self.use_old1_engine:
            return self._analyze_with_old1(symbol, timeframe, candles)
        
        # ── 回踩确认检查（优先处理待确认信号）──
        if self.require_retest and self._pending:
            result = self._check_pending(symbol, candles)
            if isinstance(result, StrategyOutput):
                return result          # 确认成功，返回入场信号
            if result == "waiting":
                return None            # 仍在等待，不检测新信号
            # expired / stop_touched / rr_insufficient → pending 已清除，继续检测新信号
        
        current = candles[-1]
        current_price = current["close"]
        atr_val = atr(candles, period=14)
        
        # 0. 大周期趋势过滤
        htf_trend = self._get_htf_trend(candles)
        
        # 1. 识别摆动点
        swing_highs, swing_lows = self._find_swing_points(candles)
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None
        
        # 2. 判断小周期趋势
        trend = self._get_trend(candles, swing_highs, swing_lows)
        
        if trend == "neutral":
            return None
        
        # 3. 大周期过滤检查
        # 只过滤"逆势"交易，允许顺势和中性
        if self.require_htf_filter:
            # 做多时：大周期不能看跌（允许 bullish 和 neutral）
            if trend == "bullish" and htf_trend == "bearish":
                return None
            # 做空时：大周期不能看涨（允许 bearish 和 neutral）
            if trend == "bearish" and htf_trend == "bullish":
                return None
        
        # 4. 识别订单块
        order_blocks = self._find_order_blocks(candles[-self.lookback:])
        
        # 5. 计算斐波那契 + 结构信号（BOS / CHoCH）
        signal = None
        side = None  # 交易方向
        fibo_side_fallback = False  # 是否使用了斐波那契 Fallback
        
        # ========== 结构检测（与 old1 一致：BOS / CHoCH）==========
        # 使用最近的摆动高低点
        last_swing_high = swing_highs[-1]
        last_swing_low = swing_lows[-1]
        
        # 是否突破摆动高/低
        up_break = current["high"] > last_swing_high.price
        down_break = current["low"] < last_swing_low.price
        
        bos = None   # 结构突破（Break of Structure）
        choch = None # 结构反转（Change of Character）
        
        if up_break:
            bos = "BUY"
        elif down_break:
            bos = "SELL"
        
        # 将内部趋势标记映射为 bull/bear，方便对齐 old1 逻辑
        trend_base = "bull" if trend == "bullish" else ("bear" if trend == "bearish" else "neutral")
        
        # CHoCH：在原趋势下，出现反向突破
        if trend_base == "bull" and down_break:
            choch = "SELL"
        elif trend_base == "bear" and up_break:
            choch = "BUY"
        
        # 根据 structure 参数决定使用 BOS / CHoCH / both
        structure_mode = self.structure
        if structure_mode == "bos":
            side = bos
        elif structure_mode == "choch":
            side = choch
        else:  # "both"（默认）：优先 BOS，其次 CHoCH
            side = bos or choch
        
        # 斐波那契 Fallback：如果结构没有给出方向，再根据趋势/大周期兜底
        if not side and self.fibo_fallback:
            # 先用小周期趋势，其次用大周期趋势
            if trend == "bullish":
                side = "BUY"
            elif trend == "bearish":
                side = "SELL"
            else:
                if htf_trend == "bullish":
                    side = "BUY"
                elif htf_trend == "bearish":
                    side = "SELL"
            if side:
                fibo_side_fallback = True
        
        # 方向偏好过滤（with_trend / counter / both）
        if side:
            # 使用大周期趋势优先，其次小周期趋势
            bias_trend = htf_trend if htf_trend in ("bullish", "bearish") else trend
            if self.bias == "with_trend":
                if bias_trend == "bullish" and side != "BUY":
                    side = None
                elif bias_trend == "bearish" and side != "SELL":
                    side = None
            elif self.bias == "counter":
                if bias_trend == "bullish" and side != "SELL":
                    side = None
                elif bias_trend == "bearish" and side != "BUY":
                    side = None
        
        if not side:
            return None
        
        # ========== 做多逻辑（与old1一致：计算所有斐波那契回撤位候选）==========
        if side == "BUY":
            # 找最近的摆动高低点
            recent_high = swing_highs[-1].price
            recent_low = swing_lows[-1].price
            mid_price = (recent_high + recent_low) / 2.0
            swing_range = recent_high - recent_low
            
            # 斐波那契 Fallback 检查：价格不能太高
            if fibo_side_fallback and current_price > mid_price:
                return None
            
            # 确保高点在低点之后（正常的上升波段）
            if swing_highs[-1].index > swing_lows[-1].index and swing_range > 0:
                # ========== old1逻辑：计算所有斐波那契回撤位候选 ==========
                fib_candidates = []
                
                for level in self.fibo_entry_levels:
                    # 计算回撤位价格（从高点往下回撤）
                    entry = recent_high - swing_range * level
                    
                    # 做多时，入场价不能高于mid_price
                    if entry > mid_price:
                        continue
                    
                    # 计算止损（old1逻辑）
                    base_stop = recent_low * (1 - self.sl_buffer_pct)
                    tp = recent_high  # 默认止盈在摆动高点
                    
                    # 使用stop_source计算实际止损
                    stop_loss = self._calc_stop_loss("BUY", entry, None, recent_high, recent_low)
                    
                    # 安全检查：入场价不能等于止损价
                    if entry == stop_loss:
                        continue
                    
                    # 使用tp_mode计算实际止盈
                    take_profit = self._calc_take_profit("BUY", entry, stop_loss, recent_high, recent_low, swing_range)
                    
                    # 确保满足最小盈亏比
                    take_profit = self._ensure_min_rr("BUY", entry, stop_loss, take_profit)
                    rr_ratio = self._calc_rr_ratio(entry, stop_loss, take_profit)
                    
                    if rr_ratio < self.min_rr:
                        continue
                    
                    # 添加到候选列表（按盈亏比排序）
                    fib_candidates.append((rr_ratio, entry, stop_loss, take_profit, level))
                
                # 如果没有候选，尝试使用mid_price（old1逻辑）
                if not fib_candidates:
                    entry = mid_price
                    base_stop = recent_low * (1 - self.sl_buffer_pct)
                    stop_loss = self._calc_stop_loss("BUY", entry, None, recent_high, recent_low)
                    if entry != stop_loss:
                        tp = recent_high
                        take_profit = self._calc_take_profit("BUY", entry, stop_loss, recent_high, recent_low, swing_range)
                        take_profit = self._ensure_min_rr("BUY", entry, stop_loss, take_profit)
                        rr_ratio = self._calc_rr_ratio(entry, stop_loss, take_profit)
                        if rr_ratio >= self.min_rr:
                            fib_candidates.append((rr_ratio, entry, stop_loss, take_profit, 0.5))
                
                # 如果没有候选，返回None
                if not fib_candidates:
                    return None
                
                # 选择最优候选（按盈亏比排序，取最高）
                fib_candidates.sort(key=lambda x: x[0], reverse=True)
                rr_ratio, entry, stop_loss, take_profit, fibo_level = fib_candidates[0]
                
                # 最终检查盈亏比
                take_profit = self._ensure_min_rr("BUY", entry, stop_loss, take_profit)
                rr_ratio = self._calc_rr_ratio(entry, stop_loss, take_profit)
                if rr_ratio < self.min_rr:
                    return None
                
                # 计算仓位
                position_size = self._calc_position_size(entry, stop_loss)
                
                # 计算置信度
                conf_score = 50
                if abs(fibo_level - 0.5) < 0.05:
                    conf_score += 15
                elif abs(fibo_level - 0.618) < 0.05:
                    conf_score += 12
                else:
                    conf_score += 8
                
                rr_bonus = min(10, (rr_ratio - self.min_rr) * 5)
                conf_score += int(rr_bonus)
                
                if htf_trend == trend:
                    conf_score += 10
                elif htf_trend == "neutral":
                    conf_score += 5
                
                confidence = min(95, max(50, conf_score))
                
                signal = StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="BUY",
                    entry_price=entry,  # 使用计算出的最优入场价（可能不是当前价格）
                    stop_loss=round(stop_loss, 2),
                    take_profit=round(take_profit, 2),
                    confidence=confidence,
                    reason=f"SMC+Fibo做多: 回踩{fibo_level:.3f}位, " + 
                           f"盈亏比{rr_ratio:.2f}, 仓位{position_size}",
                    indicators={
                        "htf_trend": htf_trend,
                        "ltf_trend": trend,
                        "fibo_level": fibo_level,
                        "fibo_price": round(entry, 2),
                        "swing_high": round(recent_high, 2),
                        "swing_low": round(recent_low, 2),
                        "rr_ratio": round(rr_ratio, 2),
                        "position_size": position_size,
                        "max_loss": self.max_loss,
                        "sl_distance": round(entry - stop_loss, 2),
                        "atr": round(atr_val, 2) if atr_val else None,
                    },
                )
        
        # ========== 做空逻辑（与old1一致：计算所有斐波那契回撤位候选）==========
        elif side == "SELL":
            recent_high = swing_highs[-1].price
            recent_low = swing_lows[-1].price
            mid_price = (recent_high + recent_low) / 2.0
            swing_range = recent_high - recent_low
            
            # 斐波那契 Fallback 检查：价格不能太低
            if fibo_side_fallback and current_price < mid_price:
                return None
            
            # 确保低点在高点之后（正常的下降波段）
            if swing_lows[-1].index > swing_highs[-1].index and swing_range > 0:
                # ========== old1逻辑：计算所有斐波那契回撤位候选 ==========
                fib_candidates = []
                
                for level in self.fibo_entry_levels:
                    # 计算回撤位价格（从低点往上回撤）
                    entry = recent_low + swing_range * level
                    
                    # 做空时，入场价不能低于mid_price
                    if entry < mid_price:
                        continue
                    
                    # 计算止损（old1逻辑）
                    base_stop = recent_high * (1 + self.sl_buffer_pct)
                    tp = recent_low  # 默认止盈在摆动低点
                    
                    # 使用stop_source计算实际止损
                    stop_loss = self._calc_stop_loss("SELL", entry, None, recent_high, recent_low)
                    
                    # 安全检查：入场价不能等于止损价
                    if entry == stop_loss:
                        continue
                    
                    # 使用tp_mode计算实际止盈
                    take_profit = self._calc_take_profit("SELL", entry, stop_loss, recent_high, recent_low, swing_range)
                    
                    # 确保满足最小盈亏比
                    take_profit = self._ensure_min_rr("SELL", entry, stop_loss, take_profit)
                    rr_ratio = self._calc_rr_ratio(entry, stop_loss, take_profit)
                    
                    if rr_ratio < self.min_rr:
                        continue
                    
                    # 添加到候选列表（按盈亏比排序）
                    fib_candidates.append((rr_ratio, entry, stop_loss, take_profit, level))
                
                # 如果没有候选，尝试使用mid_price（old1逻辑）
                if not fib_candidates:
                    entry = mid_price
                    base_stop = recent_high * (1 + self.sl_buffer_pct)
                    stop_loss = self._calc_stop_loss("SELL", entry, None, recent_high, recent_low)
                    if entry != stop_loss:
                        tp = recent_low
                        take_profit = self._calc_take_profit("SELL", entry, stop_loss, recent_high, recent_low, swing_range)
                        take_profit = self._ensure_min_rr("SELL", entry, stop_loss, take_profit)
                        rr_ratio = self._calc_rr_ratio(entry, stop_loss, take_profit)
                        if rr_ratio >= self.min_rr:
                            fib_candidates.append((rr_ratio, entry, stop_loss, take_profit, 0.5))
                
                # 如果没有候选，返回None
                if not fib_candidates:
                    return None
                
                # 选择最优候选（按盈亏比排序，取最高）
                fib_candidates.sort(key=lambda x: x[0], reverse=True)
                rr_ratio, entry, stop_loss, take_profit, fibo_level = fib_candidates[0]
                
                # 最终检查盈亏比
                take_profit = self._ensure_min_rr("SELL", entry, stop_loss, take_profit)
                rr_ratio = self._calc_rr_ratio(entry, stop_loss, take_profit)
                if rr_ratio < self.min_rr:
                    return None
                
                # 计算仓位
                position_size = self._calc_position_size(entry, stop_loss)
                
                # 计算置信度
                conf_score = 50
                if abs(fibo_level - 0.5) < 0.05:
                    conf_score += 15
                elif abs(fibo_level - 0.618) < 0.05:
                    conf_score += 12
                else:
                    conf_score += 8
                
                rr_bonus = min(10, (rr_ratio - self.min_rr) * 5)
                conf_score += int(rr_bonus)
                
                if htf_trend == trend:
                    conf_score += 10
                elif htf_trend == "neutral":
                    conf_score += 5
                
                confidence = min(95, max(50, conf_score))
                
                signal = StrategyOutput(
                    symbol=symbol,
                    signal_type="OPEN",
                    side="SELL",
                    entry_price=entry,  # 使用计算出的最优入场价（可能不是当前价格）
                    stop_loss=round(stop_loss, 2),
                    take_profit=round(take_profit, 2),
                    confidence=confidence,
                    reason=f"SMC+Fibo做空: 反弹{fibo_level:.3f}位, " +
                           f"盈亏比{rr_ratio:.2f}, 仓位{position_size}",
                    indicators={
                        "htf_trend": htf_trend,
                        "ltf_trend": trend,
                        "fibo_level": fibo_level,
                        "fibo_price": round(entry, 2),
                        "swing_high": round(recent_high, 2),
                        "swing_low": round(recent_low, 2),
                        "rr_ratio": round(rr_ratio, 2),
                        "position_size": position_size,
                        "max_loss": self.max_loss,
                        "sl_distance": round(stop_loss - entry, 2),
                        "atr": round(atr_val, 2) if atr_val else None,
                    },
                )
        
        # ── 回踩确认模式：返回信号让回测引擎创建限价单，然后在回踩确认时处理 ──
        # 注意：即使require_retest=True，也返回信号，让回测引擎创建限价单
        # 回踩确认逻辑在回测引擎的限价单触达时处理（通过_check_pending_orders）
        if signal is not None:
            # 在indicators中标记require_retest，让回测引擎知道需要回踩确认
            if not signal.indicators:
                signal.indicators = {}
            signal.indicators["require_retest"] = self.require_retest
            signal.indicators["retest_bars"] = self.retest_bars
            signal.indicators["retest_ignore_stop_touch"] = self.retest_ignore_stop_touch
            
            if self.require_retest:
                # 保存信号信息到_pending，用于后续回踩确认检查
                fibo_level = signal.indicators.get("fibo_level", 0)
                self._pending = {
                    "symbol": symbol,
                    "side": signal.side,
                    "entry_price": signal.entry_price,
                    "stop_loss": float(signal.stop_loss),
                    "take_profit": float(signal.take_profit),
                    "zone_low": min(signal.entry_price, float(signal.stop_loss)),
                    "zone_high": max(signal.entry_price, float(signal.stop_loss)),
                    "created_at": len(candles),
                    "touched": False,      # 初始未触达，等待价格触达entry_price
                    "confidence": signal.confidence,
                    "indicators": signal.indicators or {},
                    "fibo_level": fibo_level,
                }
            # 返回信号，让回测引擎创建限价单（entry_price可能不等于current_price）
            return signal
        
        return signal
