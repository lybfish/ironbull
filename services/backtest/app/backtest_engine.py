"""
Backtest Engine - 回测引擎核心

支持：
1. 单向交易（做多/做空）
2. 双向持仓（对冲模式）
3. 止损止盈
4. 基础指标计算（胜率/收益/回撤/盈亏比）
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Trade:
    """模拟成交记录"""
    trade_id: int
    symbol: str
    side: str                   # BUY / SELL
    entry_price: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    quantity: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_reason: Optional[str] = None  # "STOP_LOSS", "TAKE_PROFIT", "SIGNAL", "END", "TRAILING_STOP"
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    # 移动止损追踪字段
    highest_price: Optional[float] = None   # 多头持仓期间最高价
    lowest_price: Optional[float] = None    # 空头持仓期间最低价
    initial_stop_loss: Optional[float] = None  # 原始止损价（保本模式记录用）


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_code: str
    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    
    # 基础统计
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # 方向统计
    long_trades: int = 0
    short_trades: int = 0
    long_pnl: float = 0.0
    short_pnl: float = 0.0
    
    # 收益统计
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    avg_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    # 风险统计
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    
    # 盈亏比指标
    risk_reward_ratio: float = 0.0    # 盈亏比 = 平均盈利 / |平均亏损|
    profit_factor: float = 0.0        # 盈利因子 = 总盈利 / |总亏损|
    expectancy: float = 0.0           # 期望值 = 每笔交易预期收益
    
    # 账户统计
    initial_balance: float = 10000.0
    final_balance: float = 10000.0
    peak_balance: float = 10000.0
    
    # 交易记录
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict] = field(default_factory=list)


class BacktestEngine:
    """
    回测引擎（支持双向持仓）
    
    功能：
    1. 逐根K线回放
    2. 支持单向交易和双向对冲
    3. 独立的多空止损止盈
    4. 计算基础指标
    """
    
    def __init__(
        self,
        initial_balance: float = 10000.0,
        commission_rate: float = 0.001,  # 0.1% 手续费
        hedge_mode: bool = False,        # 对冲模式（双向持仓）
        risk_per_trade: float = 0.0,     # 每笔交易最大亏损金额（0=固定仓位，>0=以损定仓）
        amount_usdt: float = 0.0,        # 每笔固定名义持仓金额（与线上一致，>0 时覆盖其他模式）
        min_rr: float = 0.0,             # 最小盈亏比过滤（0=不过滤，>0=TP/SL < min_rr 的信号跳过）
        leverage: float = 1.0,           # 杠杆倍数（逐仓模式）
        margin_mode: str = "isolated",   # 保证金模式: isolated=逐仓(默认), cross=全仓
        trailing_stop_pct: float = 0.0,  # 移动止损回撤距离（基于保证金百分比，0=不启用）
        trailing_activation_pct: float = 0.0,  # 移动止损激活阈值（浮盈达到保证金的X%后激活，0=立即激活）
    ):
        self.initial_balance = initial_balance
        self.commission_rate = commission_rate
        self.hedge_mode = hedge_mode
        self.risk_per_trade = risk_per_trade  # 以损定仓：每笔最大亏损
        self.amount_usdt = amount_usdt        # 固定名义持仓（USDT）
        self.min_rr = min_rr                  # 最小盈亏比过滤
        self.rr_filtered = 0                  # 被过滤的信号计数
        self.leverage = leverage              # 杠杆倍数
        self.margin_mode = margin_mode        # 保证金模式
        self.trailing_stop_pct = trailing_stop_pct          # 移动止损距离
        self.trailing_activation_pct = trailing_activation_pct  # 激活阈值
        
        # 账户状态
        self.balance = initial_balance
        self.equity = initial_balance
        self.peak_equity = initial_balance
        
        # 持仓状态（支持双向）
        self.long_position: Optional[Trade] = None
        self.short_position: Optional[Trade] = None
        
        # 单向模式兼容
        self.position: Optional[Trade] = None
        
        # 交易记录
        self.trades: List[Trade] = []
        self.trade_id_counter = 0
        
        # 权益曲线
        self.equity_curve: List[Dict] = []
    
    def _has_sufficient_balance(self, entry_price: float) -> bool:
        """
        检查余额是否足够开仓。
        逐仓模式：需要 amount_usdt / leverage 的保证金
        全仓模式：余额 > 0 即可
        """
        if self.balance <= 0:
            return False
        if self.amount_usdt > 0:
            # 保证金 = 名义金额 / 杠杆
            min_margin = self.amount_usdt / max(self.leverage, 1)
            return self.balance >= min_margin
        else:
            # 非 amount_usdt 模式，至少需要初始资金的 2%
            min_margin = self.initial_balance * 0.02
            return self.balance >= min_margin

    def _calc_position_size(self, entry_price: float, stop_loss: float, base_qty: float = 1.0) -> float:
        """
        计算仓位大小（三种模式，优先级从高到低）
        
        1. 固定名义持仓模式（amount_usdt > 0）：仓位 = amount_usdt / entry_price
           与线上 LiveTrader 一致，直接用 USDT 金额换算数量。
        2. 以损定仓模式（risk_per_trade > 0）：仓位 = 最大亏损 / 止损距离
        3. 固定仓位模式（兜底）：返回 base_qty
        
        安全限制：
        0. 余额不足 → 返回 0（禁止开仓）
        1. 止损距离 < 入场价 0.1% 视为无效（太窄），跳过该信号
        2. 名义价值不超过账户余额的 3 倍（防止杠杆爆炸）
        """
        # ── 余额保护：不足时禁止开仓 ──
        if not self._has_sufficient_balance(entry_price):
            return 0.0
        
        # ── 模式 1: 固定名义持仓（最高优先级）──
        if self.amount_usdt > 0 and entry_price > 0:
            position_size = self.amount_usdt / entry_price
            # 安全阀：名义价值不超过账户余额的 3 倍（余额已确认 > 0）
            max_notional = self.balance * 3
            max_qty = max_notional / entry_price
            position_size = min(position_size, max_qty)
            return round(position_size, 6)
        
        # ── 模式 2: 以损定仓 ──
        if self.risk_per_trade > 0 and stop_loss is not None:
            sl_distance = abs(entry_price - stop_loss)
            if sl_distance == 0:
                return base_qty
            
            # 安全阀 1: 止损距离 < 入场价 0.1%，视为无效止损
            min_sl_distance = entry_price * 0.001
            if sl_distance < min_sl_distance:
                sl_distance = min_sl_distance
            
            # 以损定仓计算
            position_size = self.risk_per_trade / sl_distance
            
            # 安全阀 2: 名义价值不超过账户余额的 3 倍（余额已确认 > 0）
            max_notional = self.balance * 3
            max_qty = max_notional / entry_price if entry_price > 0 else base_qty
            position_size = min(position_size, max_qty)
            
            return round(position_size, 6)
        
        # ── 模式 3: 固定仓位（兜底）──
        return base_qty
    
    def run(
        self,
        strategy,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        lookback: int = 50,
    ) -> BacktestResult:
        """运行回测"""
        
        if len(candles) < lookback + 1:
            raise ValueError(f"K线数据不足：需要至少 {lookback + 1} 根，实际 {len(candles)} 根")
        
        # 检测策略是否需要对冲模式
        self._detect_hedge_mode(strategy)
        
        # 保存策略引用（用于止损冷却回调）
        self._strategy = strategy
        
        # 重置状态
        self._reset()
        
        # 逐根K线回放
        for i in range(lookback, len(candles)):
            history = candles[i - lookback : i + 1]
            current_candle = candles[i]
            current_price = current_candle["close"]
            current_time = self._parse_time(current_candle["timestamp"])
            
            # 检查止损止盈
            self._check_all_stop_loss_take_profit(
                current_candle["high"],
                current_candle["low"],
                current_price,
                current_time,
            )
            
            # 构建持仓信息传给策略
            positions = self._build_positions_info()
            
            # 调用策略分析
            signal = strategy.analyze(
                symbol=symbol,
                timeframe=timeframe,
                candles=history,
                positions=positions,
            )
            
            # 处理信号
            if signal:
                self._handle_signal(signal, current_price, current_time)
            
            # 更新权益曲线
            self._update_equity(current_price, current_time)
        
        # 强制平仓所有持仓
        last_candle = candles[-1]
        last_price = last_candle["close"]
        last_time = self._parse_time(last_candle["timestamp"])
        self._close_all_positions(last_price, last_time, "END")
        
        # 计算回测结果
        return self._calculate_result(
            strategy_code=strategy.code,
            symbol=symbol,
            timeframe=timeframe,
            start_time=self._parse_time(candles[lookback]["timestamp"]),
            end_time=self._parse_time(candles[-1]["timestamp"]),
        )
    
    def _detect_hedge_mode(self, strategy):
        """检测策略是否需要对冲模式"""
        # 根据策略代码自动启用对冲模式
        hedge_strategies = ["hedge", "hedge_conservative", "reversal_hedge", "market_regime"]
        if hasattr(strategy, "code") and strategy.code in hedge_strategies:
            self.hedge_mode = True
    
    def _reset(self):
        """重置回测状态"""
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.peak_equity = self.initial_balance
        self.long_position = None
        self.short_position = None
        self.position = None
        self.trades = []
        self.trade_id_counter = 0
        self.equity_curve = []
        self.rr_filtered = 0
        self.liquidated_count = 0  # 逐仓爆仓计数
    
    def _build_positions_info(self) -> Dict:
        """构建持仓信息传给策略"""
        if self.hedge_mode:
            return {
                "has_long": self.long_position is not None,
                "has_short": self.short_position is not None,
                "long_entry": self.long_position.entry_price if self.long_position else None,
                "short_entry": self.short_position.entry_price if self.short_position else None,
            }
        else:
            return {
                "has_position": self.position is not None,
                "side": self.position.side if self.position else None,
                "entry_price": self.position.entry_price if self.position else None,
            }

    def _parse_time(self, value) -> datetime:
        """兼容 ISO 字符串 / 秒时间戳 / 毫秒时间戳"""
        if isinstance(value, (int, float)):
            ts = float(value)
            if ts > 1e12:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts)
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        raise ValueError(f"Unsupported timestamp type: {type(value)}")
    
    def _check_min_rr(self, signal, current_price: float) -> bool:
        """
        检查信号的盈亏比是否达标。
        返回 True = 通过，False = 被过滤。
        """
        if self.min_rr <= 0:
            return True  # 未启用过滤
        
        sl = getattr(signal, "stop_loss", None)
        tp = getattr(signal, "take_profit", None)
        if sl is None or tp is None or sl == 0 or tp == 0:
            return True  # 没有 SL/TP 信息，放行
        
        sl_dist = abs(current_price - sl)
        tp_dist = abs(tp - current_price)
        if sl_dist <= 0:
            return False
        
        rr = tp_dist / sl_dist
        if rr < self.min_rr:
            self.rr_filtered += 1
            return False
        return True

    def _handle_signal(self, signal, current_price: float, current_time: datetime):
        """处理策略信号"""
        
        signal_type = getattr(signal, "signal_type", "OPEN")
        side = getattr(signal, "side", None)
        
        # 对冲信号：同时开多空
        if signal_type == "HEDGE" and side == "BOTH":
            # 对冲信号也检查盈亏比（用多仓的 SL/TP 代表性检查）
            if not self._check_min_rr(signal, current_price):
                return
            self._handle_hedge_signal(signal, current_price, current_time)
            return
        
        # 平仓信号
        if signal_type == "CLOSE":
            if self.hedge_mode:
                if side == "BUY" and self.long_position:
                    self._close_long(current_price, current_time, "SIGNAL")
                elif side == "SELL" and self.short_position:
                    self._close_short(current_price, current_time, "SIGNAL")
                elif side is None:
                    # 平所有仓
                    self._close_all_positions(current_price, current_time, "SIGNAL")
            else:
                if self.position:
                    self._close_position(current_price, current_time, "SIGNAL")
            return
        
        # 开仓信号（盈亏比不达标则跳过）
        if signal_type == "OPEN" and side:
            if not self._check_min_rr(signal, current_price):
                return
            if self.hedge_mode:
                self._handle_hedge_open(signal, current_price, current_time)
            else:
                self._handle_single_open(signal, current_price, current_time)
    
    def _handle_hedge_signal(self, signal, current_price: float, current_time: datetime):
        """处理对冲信号（同时开多空，各自独立止损止盈）"""
        
        indicators = getattr(signal, "indicators", None) or {}
        
        # 如果没有多仓，开多（使用 indicators 中的独立 SL/TP）
        if not self.long_position:
            long_sl = indicators.get("long_stop_loss", getattr(signal, "stop_loss", None))
            long_tp = indicators.get("long_take_profit", getattr(signal, "take_profit", None))
            self._open_long_with_sl_tp(signal, current_price, current_time, long_sl, long_tp)
        
        # 如果没有空仓，开空（使用 indicators 中的独立 SL/TP）
        if not self.short_position:
            short_sl = indicators.get("short_stop_loss", getattr(signal, "stop_loss", None))
            short_tp = indicators.get("short_take_profit", getattr(signal, "take_profit", None))
            self._open_short_with_sl_tp(signal, current_price, current_time, short_sl, short_tp)
    
    def _handle_hedge_open(self, signal, current_price: float, current_time: datetime):
        """
        对冲模式下处理单向 OPEN 信号（趋势模式切入时）
        
        逻辑：
        - 收到 BUY → 平掉空仓（如果有），开多仓（如果没有）
        - 收到 SELL → 平掉多仓（如果有），开空仓（如果没有）
        - 从震荡对冲切到趋势单边时，先清理反向仓位
        """
        side = signal.side
        
        if side == "BUY":
            # 趋势看多：平掉空仓，保留/开多仓
            if self.short_position:
                self._close_short(current_price, current_time, "SIGNAL")
            if not self.long_position:
                self._open_long(signal, current_price, current_time)
        elif side == "SELL":
            # 趋势看空：平掉多仓，保留/开空仓
            if self.long_position:
                self._close_long(current_price, current_time, "SIGNAL")
            if not self.short_position:
                self._open_short(signal, current_price, current_time)
    
    def _handle_single_open(self, signal, current_price: float, current_time: datetime):
        """单向模式下处理开仓"""
        
        if self.position:
            # 反向信号 → 先平仓再开新仓
            if signal.side != self.position.side:
                self._close_position(current_price, current_time, "SIGNAL")
                self._open_position(signal, current_price, current_time)
        else:
            self._open_position(signal, current_price, current_time)
    
    # ========== 开仓方法 ==========
    
    def _open_position(self, signal, entry_price: float, entry_time: datetime):
        """单向模式开仓"""
        stop_loss = getattr(signal, "stop_loss", None)
        take_profit = getattr(signal, "take_profit", None)
        
        # 以损定仓计算仓位
        quantity = self._calc_position_size(entry_price, stop_loss, base_qty=1.0)
        if quantity <= 0:
            return  # 余额不足，跳过
        
        commission = entry_price * quantity * self.commission_rate
        self.balance -= commission
        
        self.trade_id_counter += 1
        self.position = Trade(
            trade_id=self.trade_id_counter,
            symbol=signal.symbol,
            side=signal.side,
            entry_price=entry_price,
            entry_time=entry_time,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
    
    def _open_long(self, signal, entry_price: float, entry_time: datetime):
        """开多仓（使用信号默认 SL/TP）"""
        stop_loss = getattr(signal, "stop_loss", None)
        take_profit = getattr(signal, "take_profit", None)
        self._open_long_with_sl_tp(signal, entry_price, entry_time, stop_loss, take_profit)
    
    def _open_long_with_sl_tp(self, signal, entry_price: float, entry_time: datetime,
                               stop_loss: float = None, take_profit: float = None):
        """开多仓（指定 SL/TP）"""
        # 以损定仓计算仓位（对冲模式基础仓位0.5）
        quantity = self._calc_position_size(entry_price, stop_loss, base_qty=0.5)
        if quantity <= 0:
            return  # 余额不足，跳过
        
        commission = entry_price * quantity * self.commission_rate
        self.balance -= commission
        
        self.trade_id_counter += 1
        self.long_position = Trade(
            trade_id=self.trade_id_counter,
            symbol=signal.symbol,
            side="BUY",
            entry_price=entry_price,
            entry_time=entry_time,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
    
    def _open_short(self, signal, entry_price: float, entry_time: datetime):
        """开空仓（使用信号默认 SL/TP）"""
        stop_loss = getattr(signal, "stop_loss", None)
        take_profit = getattr(signal, "take_profit", None)
        self._open_short_with_sl_tp(signal, entry_price, entry_time, stop_loss, take_profit)
    
    def _open_short_with_sl_tp(self, signal, entry_price: float, entry_time: datetime,
                                stop_loss: float = None, take_profit: float = None):
        """开空仓（指定 SL/TP）"""
        # 以损定仓计算仓位
        quantity = self._calc_position_size(entry_price, stop_loss, base_qty=0.5)
        if quantity <= 0:
            return  # 余额不足，跳过
        
        commission = entry_price * quantity * self.commission_rate
        self.balance -= commission
        
        self.trade_id_counter += 1
        self.short_position = Trade(
            trade_id=self.trade_id_counter,
            symbol=signal.symbol,
            side="SELL",
            entry_price=entry_price,
            entry_time=entry_time,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
    
    # ========== 平仓方法 ==========
    
    def _close_position(self, exit_price: float, exit_time: datetime, exit_reason: str):
        """单向模式平仓"""
        if not self.position:
            return
        
        pnl = self._calculate_pnl(self.position, exit_price)
        self._finalize_trade(self.position, exit_price, exit_time, exit_reason, pnl)
        self.trades.append(self.position)
        self.position = None
    
    def _close_long(self, exit_price: float, exit_time: datetime, exit_reason: str):
        """平多仓"""
        if not self.long_position:
            return
        
        pnl = self._calculate_pnl(self.long_position, exit_price)
        self._finalize_trade(self.long_position, exit_price, exit_time, exit_reason, pnl)
        self.trades.append(self.long_position)
        self.long_position = None
    
    def _close_short(self, exit_price: float, exit_time: datetime, exit_reason: str):
        """平空仓"""
        if not self.short_position:
            return
        
        pnl = self._calculate_pnl(self.short_position, exit_price)
        self._finalize_trade(self.short_position, exit_price, exit_time, exit_reason, pnl)
        self.trades.append(self.short_position)
        self.short_position = None
    
    def _close_all_positions(self, exit_price: float, exit_time: datetime, exit_reason: str):
        """平所有仓位"""
        if self.position:
            self._close_position(exit_price, exit_time, exit_reason)
        if self.long_position:
            self._close_long(exit_price, exit_time, exit_reason)
        if self.short_position:
            self._close_short(exit_price, exit_time, exit_reason)
    
    def _calculate_pnl(self, trade: Trade, exit_price: float) -> float:
        """计算盈亏"""
        if trade.side == "BUY":
            pnl = (exit_price - trade.entry_price) * trade.quantity
        else:
            pnl = (trade.entry_price - exit_price) * trade.quantity
        
        # 扣除平仓手续费
        commission = abs(pnl) * self.commission_rate if pnl > 0 else 0
        pnl -= commission
        
        return pnl
    
    def _finalize_trade(self, trade: Trade, exit_price: float, exit_time: datetime, 
                        exit_reason: str, pnl: float):
        """完成交易记录"""
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.exit_reason = exit_reason
        trade.pnl = pnl
        
        # 逐仓模式: pnl_pct 基于保证金（名义/杠杆）
        if self.margin_mode == "isolated" and self.leverage > 1 and self.amount_usdt > 0:
            margin = self.amount_usdt / self.leverage
            trade.pnl_pct = (pnl / margin) * 100 if margin > 0 else 0
        else:
            trade.pnl_pct = (pnl / (trade.entry_price * trade.quantity)) * 100
        
        # 更新账户余额
        self.balance += pnl
    
    # ========== 止损止盈检查 ==========
    
    def _check_all_stop_loss_take_profit(self, high: float, low: float, 
                                          close: float, current_time: datetime):
        """检查所有持仓的止损止盈"""
        
        if self.hedge_mode:
            # 检查多仓
            if self.long_position:
                self._check_position_sl_tp(self.long_position, high, low, current_time, is_long=True)
            # 检查空仓
            if self.short_position:
                self._check_position_sl_tp(self.short_position, high, low, current_time, is_long=False)
        else:
            # 单向模式
            if self.position:
                is_long = self.position.side == "BUY"
                result = self._check_position_sl_tp(self.position, high, low, current_time, is_long)
                if result:
                    self.position = None
    
    def _check_position_sl_tp(self, position: Trade, high: float, low: float, 
                               current_time: datetime, is_long: bool) -> Optional[str]:
        """检查单个持仓的止损止盈（含移动止损逻辑）"""
        
        # ── 移动止损: 更新极值并动态调整 SL ──
        if self.trailing_stop_pct > 0:
            self._update_trailing_stop(position, high, low, is_long)
        
        # ── 止损检查（含移动止损触发）──
        if position.stop_loss:
            triggered = False
            exit_price = position.stop_loss
            
            if is_long and low <= position.stop_loss:
                triggered = True
            elif not is_long and high >= position.stop_loss:
                triggered = True
            
            if triggered:
                # 判断是原始止损还是移动止损触发
                is_trailing = (
                    self.trailing_stop_pct > 0
                    and position.initial_stop_loss is not None
                    and position.stop_loss != position.initial_stop_loss
                )
                reason = "TRAILING_STOP" if is_trailing else "STOP_LOSS"
                pnl = self._calculate_pnl(position, exit_price)
                self._finalize_trade(position, exit_price, current_time, reason, pnl)
                self.trades.append(position)
                if self.hedge_mode:
                    if is_long:
                        self.long_position = None
                    else:
                        self.short_position = None
                # 通知策略进入冷却（如果策略支持）
                if reason == "STOP_LOSS" and hasattr(self, '_strategy') and hasattr(self._strategy, 'set_cooldown'):
                    self._strategy.set_cooldown()
                return reason
        
        # ── 止盈检查 ──
        if position.take_profit:
            if is_long and high >= position.take_profit:
                pnl = self._calculate_pnl(position, position.take_profit)
                self._finalize_trade(position, position.take_profit, current_time, "TAKE_PROFIT", pnl)
                self.trades.append(position)
                if self.hedge_mode:
                    self.long_position = None
                return "TAKE_PROFIT"
            
            if not is_long and low <= position.take_profit:
                pnl = self._calculate_pnl(position, position.take_profit)
                self._finalize_trade(position, position.take_profit, current_time, "TAKE_PROFIT", pnl)
                self.trades.append(position)
                if self.hedge_mode:
                    self.short_position = None
                return "TAKE_PROFIT"
        
        return None
    
    def _update_trailing_stop(self, position: Trade, high: float, low: float, is_long: bool):
        """
        移动止损逻辑
        
        - 追踪持仓期间的最高价（多头）/ 最低价（空头）
        - 当浮盈达到激活阈值后，开始动态调整 SL
        - trailing_stop_pct 是基于保证金百分比的回撤距离
          例: 0.30 = 保证金的 30%, 20X 杠杆下 = 价格回撤 1.5%
        """
        entry = position.entry_price
        
        # 计算回撤距离（价格百分比）
        trail_dist_pct = self.trailing_stop_pct / max(self.leverage, 1)
        
        # 计算激活阈值（价格百分比）
        activation_dist_pct = self.trailing_activation_pct / max(self.leverage, 1)
        
        # 保存初始 SL（首次调用时）
        if position.initial_stop_loss is None:
            position.initial_stop_loss = position.stop_loss
        
        if is_long:
            # 更新最高价
            if position.highest_price is None:
                position.highest_price = high
            elif high > position.highest_price:
                position.highest_price = high
            
            # 检查是否达到激活阈值
            profit_pct = (position.highest_price - entry) / entry
            if profit_pct < activation_dist_pct:
                return  # 未达到激活阈值，保持原始 SL
            
            # 计算新的移动止损价
            new_sl = position.highest_price * (1 - trail_dist_pct)
            
            # SL 只能上移，不能下移
            if position.stop_loss is None or new_sl > position.stop_loss:
                position.stop_loss = round(new_sl, 2)
        else:
            # 空头: 更新最低价
            if position.lowest_price is None:
                position.lowest_price = low
            elif low < position.lowest_price:
                position.lowest_price = low
            
            # 检查是否达到激活阈值
            profit_pct = (entry - position.lowest_price) / entry
            if profit_pct < activation_dist_pct:
                return  # 未达到激活阈值，保持原始 SL
            
            # 计算新的移动止损价
            new_sl = position.lowest_price * (1 + trail_dist_pct)
            
            # SL 只能下移（对空头来说），不能上移
            if position.stop_loss is None or new_sl < position.stop_loss:
                position.stop_loss = round(new_sl, 2)
    
    # ========== 权益计算 ==========
    
    def _update_equity(self, current_price: float, current_time: datetime):
        """更新权益曲线"""
        
        equity = self.balance
        
        # 计算所有持仓的浮盈
        if self.position:
            equity += self._unrealized_pnl(self.position, current_price)
        if self.long_position:
            equity += self._unrealized_pnl(self.long_position, current_price)
        if self.short_position:
            equity += self._unrealized_pnl(self.short_position, current_price)
        
        self.equity = equity
        
        if equity > self.peak_equity:
            self.peak_equity = equity
        
        self.equity_curve.append({
            "time": current_time.isoformat(),
            "equity": equity,
            "balance": self.balance,
        })
    
    def _unrealized_pnl(self, position: Trade, current_price: float) -> float:
        """计算未实现盈亏"""
        if position.side == "BUY":
            return (current_price - position.entry_price) * position.quantity
        else:
            return (position.entry_price - current_price) * position.quantity
    
    # ========== 结果计算 ==========
    
    def _calculate_result(self, strategy_code: str, symbol: str, timeframe: str,
                          start_time: datetime, end_time: datetime) -> BacktestResult:
        """计算回测结果"""
        
        result = BacktestResult(
            strategy_code=strategy_code,
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            initial_balance=self.initial_balance,
            final_balance=self.balance,
            peak_balance=self.peak_equity,
            trades=self.trades,
            equity_curve=self.equity_curve,
        )
        
        result.total_trades = len(self.trades)
        
        if result.total_trades == 0:
            return result
        
        # 胜率统计
        winning_trades = [t for t in self.trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl and t.pnl <= 0]
        
        result.winning_trades = len(winning_trades)
        result.losing_trades = len(losing_trades)
        result.win_rate = (result.winning_trades / result.total_trades) * 100
        
        # 方向统计
        long_trades = [t for t in self.trades if t.side == "BUY"]
        short_trades = [t for t in self.trades if t.side == "SELL"]
        result.long_trades = len(long_trades)
        result.short_trades = len(short_trades)
        result.long_pnl = sum(t.pnl for t in long_trades if t.pnl)
        result.short_pnl = sum(t.pnl for t in short_trades if t.pnl)
        
        # 收益统计
        result.total_pnl = sum(t.pnl for t in self.trades if t.pnl)
        result.total_pnl_pct = (result.total_pnl / self.initial_balance) * 100
        result.avg_pnl = result.total_pnl / result.total_trades
        
        if winning_trades:
            result.avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades)
        if losing_trades:
            result.avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades)
        
        # 盈亏比指标
        if result.avg_win > 0 and result.avg_loss < 0:
            result.risk_reward_ratio = abs(result.avg_win / result.avg_loss)
            
            total_win = sum(t.pnl for t in winning_trades)
            total_loss = abs(sum(t.pnl for t in losing_trades))
            if total_loss > 0:
                result.profit_factor = total_win / total_loss
            
            win_rate = result.win_rate / 100
            result.expectancy = win_rate * result.avg_win + (1 - win_rate) * result.avg_loss
        
        # 最大回撤
        if self.equity_curve:
            result.max_drawdown = self.peak_equity - min(e["equity"] for e in self.equity_curve)
            result.max_drawdown_pct = (result.max_drawdown / self.peak_equity) * 100
        
        return result
