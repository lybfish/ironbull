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
    exit_reason: Optional[str] = None  # "STOP_LOSS", "TAKE_PROFIT", "SIGNAL", "END"
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None


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
    ):
        self.initial_balance = initial_balance
        self.commission_rate = commission_rate
        self.hedge_mode = hedge_mode
        
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
        hedge_strategies = ["hedge", "hedge_conservative", "reversal_hedge"]
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
    
    def _handle_signal(self, signal, current_price: float, current_time: datetime):
        """处理策略信号"""
        
        signal_type = getattr(signal, "signal_type", "OPEN")
        side = getattr(signal, "side", None)
        
        # 对冲信号：同时开多空
        if signal_type == "HEDGE" and side == "BOTH":
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
        
        # 开仓信号
        if signal_type == "OPEN" and side:
            if self.hedge_mode:
                self._handle_hedge_open(signal, current_price, current_time)
            else:
                self._handle_single_open(signal, current_price, current_time)
    
    def _handle_hedge_signal(self, signal, current_price: float, current_time: datetime):
        """处理对冲信号（同时开多空）"""
        
        # 如果没有多仓，开多
        if not self.long_position:
            self._open_long(signal, current_price, current_time)
        
        # 如果没有空仓，开空
        if not self.short_position:
            self._open_short(signal, current_price, current_time)
    
    def _handle_hedge_open(self, signal, current_price: float, current_time: datetime):
        """对冲模式下处理单向开仓"""
        side = signal.side
        
        if side == "BUY":
            if not self.long_position:
                self._open_long(signal, current_price, current_time)
        elif side == "SELL":
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
        commission = entry_price * 1.0 * self.commission_rate
        self.balance -= commission
        
        self.trade_id_counter += 1
        self.position = Trade(
            trade_id=self.trade_id_counter,
            symbol=signal.symbol,
            side=signal.side,
            entry_price=entry_price,
            entry_time=entry_time,
            quantity=1.0,
            stop_loss=getattr(signal, "stop_loss", None),
            take_profit=getattr(signal, "take_profit", None),
        )
    
    def _open_long(self, signal, entry_price: float, entry_time: datetime):
        """开多仓"""
        commission = entry_price * 0.5 * self.commission_rate  # 对冲模式每边 0.5 仓位
        self.balance -= commission
        
        self.trade_id_counter += 1
        self.long_position = Trade(
            trade_id=self.trade_id_counter,
            symbol=signal.symbol,
            side="BUY",
            entry_price=entry_price,
            entry_time=entry_time,
            quantity=0.5,  # 对冲模式每边 0.5
            stop_loss=getattr(signal, "stop_loss", None),
            take_profit=getattr(signal, "take_profit", None),
        )
    
    def _open_short(self, signal, entry_price: float, entry_time: datetime):
        """开空仓"""
        commission = entry_price * 0.5 * self.commission_rate
        self.balance -= commission
        
        self.trade_id_counter += 1
        self.short_position = Trade(
            trade_id=self.trade_id_counter,
            symbol=signal.symbol,
            side="SELL",
            entry_price=entry_price,
            entry_time=entry_time,
            quantity=0.5,
            stop_loss=getattr(signal, "stop_loss", None),
            take_profit=getattr(signal, "take_profit", None),
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
        trade.pnl_pct = (pnl / trade.entry_price) * 100
        
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
        """检查单个持仓的止损止盈"""
        
        # 止损检查
        if position.stop_loss:
            if is_long and low <= position.stop_loss:
                pnl = self._calculate_pnl(position, position.stop_loss)
                self._finalize_trade(position, position.stop_loss, current_time, "STOP_LOSS", pnl)
                self.trades.append(position)
                if self.hedge_mode:
                    if is_long:
                        self.long_position = None
                    else:
                        self.short_position = None
                return "STOP_LOSS"
            
            if not is_long and high >= position.stop_loss:
                pnl = self._calculate_pnl(position, position.stop_loss)
                self._finalize_trade(position, position.stop_loss, current_time, "STOP_LOSS", pnl)
                self.trades.append(position)
                if self.hedge_mode:
                    self.short_position = None
                return "STOP_LOSS"
        
        # 止盈检查
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
