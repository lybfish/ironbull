"""
MT5 Exchange Client (v1 Phase 5.1)

MT5 交易连接器 - 基于 MetaTrader5 SDK 实现真实交易

使用示例：
    client = MT5Client(
        login=123456,
        password="your_password",
        server="your_server",
    )
    
    # 下单
    result = client.place_order(
        symbol="EURUSD",
        side="BUY",
        order_type="MARKET",
        volume=0.01,  # 手数
    )
    
    # 查询余额
    balance = client.get_balance()
"""

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from libs.core import get_logger

logger = get_logger("_mt5-client")

# MT5 SDK 可用性检查
try:
    import MetaTrader5 as __mt5
    MT5_AVAILABLE = True
    # MT5 常量值
    _ORDER_TYPE_BUY = __mt5.ORDER_TYPE_BUY
    _ORDER_TYPE_SELL = __mt5.ORDER_TYPE_SELL
    _ORDER_TYPE_BUY_LIMIT = __mt5.ORDER_TYPE_BUY_LIMIT
    _ORDER_TYPE_SELL_LIMIT = __mt5.ORDER_TYPE_SELL_LIMIT
    _ORDER_TYPE_BUY_STOP = __mt5.ORDER_TYPE_BUY_STOP
    _ORDER_TYPE_SELL_STOP = __mt5.ORDER_TYPE_SELL_STOP
    _TRADE_ACTION_DEAL = __mt5.TRADE_ACTION_DEAL
    _TRADE_ACTION_MODIFY = __mt5.TRADE_ACTION_MODIFY
    _ORDER_TIME_GTC = __mt5.ORDER_TIME_GTC
    _ORDER_FILLING_IOC = __mt5.ORDER_FILLING_IOC
    _TRADE_RETCODE_DONE = __mt5.TRADE_RETCODE_DONE
except ImportError:
    MT5_AVAILABLE = False
    # 使用占位符常量（实际不会使用，因为不可用时会返回错误）
    _ORDER_TYPE_BUY = 0
    _ORDER_TYPE_SELL = 1
    _ORDER_TYPE_BUY_LIMIT = 2
    _ORDER_TYPE_SELL_LIMIT = 3
    _ORDER_TYPE_BUY_STOP = 4
    _ORDER_TYPE_SELL_STOP = 5
    _TRADE_ACTION_DEAL = 1
    _TRADE_ACTION_MODIFY = 2
    _ORDER_TIME_GTC = 0
    _ORDER_FILLING_IOC = 1
    _TRADE_RETCODE_DONE = 10009
    logger.warning("MetaTrader5 library not installed, MT5 functionality will be unavailable")


@dataclass
class MT5OrderResult:
    """MT5 下单结果"""
    is_success: bool
    order_id: Optional[str] = None
    deal_id: Optional[str] = None
    filled_price: Optional[float] = None
    filled_quantity: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class MT5Balance:
    """MT5 余额信息"""
    balance: float       # 账户余额
    equity: float         # 账户净值
    margin: float         # 已用保证金
    free_margin: float   # 可用保证金
    profit: float         # 当前浮动盈亏
    leverage: int         # 杠杆


@dataclass
class MT5Position:
    """MT5 持仓信息"""
    ticket: int           # 持仓订单号
    symbol: str           # 品种代码
    side: str             # BUY / SELL
    volume: float         # 持仓手数
    price_open: float     # 开仓价
    price_current: float  # 当前价
    sl: float             # 止损价
    tp: float            # 止盈价
    profit: float         # 浮动盈亏


class MT5Client:
    """
    MT5 交易客户端
    
    支持：
    - 真实交易下单（市价/限价/止损）
    - 止损止盈设置
    - 持仓查询
    - 平仓操作
    - 余额查询
    """
    
    # 支持的订单类型映射
    ORDER_TYPE_MAP = {
        'MARKET': 'buy',      # 市价单
        'LIMIT': 'buy_limit', # 限价买单
        'STOP': 'buy_stop',   # 止损买单
    }
    
    # MT5 内部订单类型映射
    _MT5_ORDER_TYPE = {
        'buy': _ORDER_TYPE_BUY,
        'sell': _ORDER_TYPE_SELL,
        'buy_limit': _ORDER_TYPE_BUY_LIMIT,
        'sell_limit': _ORDER_TYPE_SELL_LIMIT,
        'buy_stop': _ORDER_TYPE_BUY_STOP,
        'sell_stop': _ORDER_TYPE_SELL_STOP,
    }
    
    def __init__(
        self,
        login: int,
        password: str,
        server: str,
        path: str = "",  # MT5 终端路径，可选
    ):
        """
        初始化 MT5 客户端
        
        Args:
            login: MT5 账户登录名
            password: 账户密码
            server: 交易服务器名称
            path: MT5 终端路径（可选，默认使用系统安装版本）
        """
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        self.connected = False
        
        # 缓存账户信息
        self._account_info: Optional[Dict] = None
    
    def connect(self) -> bool:
        """连接 MT5 服务器"""
        if not MT5_AVAILABLE:
            logger.error("MT5 library not installed")
            return False
        
        if self.connected:
            return True
        
        try:
            # 初始化 MT5
            if self.path:
                if not _mt5.initialize(path=self.path):
                    logger.error(f"MT5 initialize failed: {_mt5.last_error()}")
                    return False
            else:
                if not _mt5.initialize():
                    logger.error(f"MT5 initialize failed: {_mt5.last_error()}")
                    return False
            
            # 登录账户
            if not _mt5.login(self.login, password=self.password, server=self.server):
                logger.error(f"MT5 login failed: {_mt5.last_error()}")
                _mt5.shutdown()
                return False
            
            self.connected = True
            logger.info(f"MT5 connected: {self.login}@{self.server}")
            return True
            
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            return False
    
    def disconnect(self):
        """断开 MT5 连接"""
        if self.connected and MT5_AVAILABLE:
            _mt5.shutdown()
            self.connected = False
            logger.info("MT5 disconnected")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()
        return False
    
    def _ensure_connected(self) -> bool:
        """确保已连接"""
        if not self.connected:
            return self.connect()
        return True
    
    def _parse_order_type(self, order_type: str, side: str) -> int:
        """
        解析订单类型
        
        Args:
            order_type: MARKET / LIMIT / STOP
            side: BUY / SELL
            
        Returns:
            MT5 订单类型枚举值
        """
        # 构建内部订单类型 key
        order_type_lower = order_type.lower() if order_type else 'market'
        
        if order_type_lower == 'market':
            key = 'buy' if side.upper() == 'BUY' else 'sell'
        elif order_type_lower == 'limit':
            key = f'{side.lower()}_limit'
        elif order_type_lower == 'stop':
            key = f'{side.lower()}_stop'
        else:
            # 默认市价单
            key = 'buy' if side.upper() == 'BUY' else 'sell'
        
        return self._MT5_ORDER_TYPE.get(key, _mt5.ORDER_TYPE_BUY)
    
    def get_balance(self) -> Optional[MT5Balance]:
        """
        获取账户余额信息
        
        Returns:
            MT5Balance 或 None（获取失败时）
        """
        if not self._ensure_connected():
            return None
        
        try:
            account = _mt5.account_info()
            if account is None:
                logger.error("Failed to get account info")
                return None
            
            return MT5Balance(
                balance=account.balance,
                equity=account.equity,
                margin=account.margin,
                free_margin=account.margin_free,
                profit=account.profit,
                leverage=account.leverage,
            )
        except Exception as e:
            logger.error(f"Get balance failed: {e}")
            return None
    
    def get_positions(self) -> List[MT5Position]:
        """
        获取当前持仓列表
        
        Returns:
            MT5Position 列表
        """
        if not self._ensure_connected():
            return []
        
        try:
            positions = _mt5.positions_get()
            if positions is None:
                return []
            
            result = []
            for pos in positions:
                result.append(MT5Position(
                    ticket=pos.ticket,
                    symbol=pos.symbol,
                    side='BUY' if pos.type == 0 else 'SELL',
                    volume=pos.volume,
                    price_open=pos.price_open,
                    price_current=pos.price_current,
                    sl=pos.sl,
                    tp=pos.tp,
                    profit=pos.profit,
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Get positions failed: {e}")
            return []
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取品种信息
        
        Args:
            symbol: 品种代码，如 EURUSD, XAUUSD
            
        Returns:
            品种信息字典
        """
        if not self._ensure_connected():
            return None
        
        try:
            # 确保品种可见
            if not _mt5.symbol_select(symbol, True):
                logger.error(f"Symbol not available: {symbol}")
                return None
            
            info = _mt5.symbol_info(symbol)
            if info is None:
                return None
            
            return {
                'symbol': info.symbol,
                'bid': info.bid,
                'ask': info.ask,
                'last': info.last,
                'volume_step': info.volume_step,
                'trade_stops_level': info.trade_stops_level,
                'point': info.point,
                'spread': info.spread,
            }
        except Exception as e:
            logger.error(f"Get symbol info failed: {e}")
            return None
    
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        volume: float,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: str = "",
        deviation: int = 20,
    ) -> MT5OrderResult:
        """
        下单交易
        
        Args:
            symbol: 品种代码
            side: BUY / SELL
            order_type: MARKET / LIMIT / STOP
            volume: 手数（如 0.01 手）
            price: 限价单价格（限价/止损单需要）
            stop_loss: 止损价
            take_profit: 止盈价
            comment: 订单注释
            deviation: 价格滑点（点数）
            
        Returns:
            MT5OrderResult 下单结果
        """
        if not self._ensure_connected():
            return MT5OrderResult(
                is_success=False,
                error_code="NOT_CONNECTED",
                error_message="MT5 not connected",
            )
        
        try:
            # 确保品种可见
            if not _mt5.symbol_select(symbol, True):
                return MT5OrderResult(
                    is_success=False,
                    error_code="SYMBOL_NOT_FOUND",
                    error_message=f"Symbol not found: {symbol}",
                )
            
            # 解析订单类型
            _mt5_order_type = self._parse_order_type(order_type, side)
            
            # 构建订单请求
            request = {
                "action": _mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": _mt5_order_type,
                "deviation": deviation,
                "magic": 234000,  # 策略标识
                "comment": comment,
                "type_time": _mt5.ORDER_TIME_GTC,
                "type_filling": _mt5.ORDER_FILLING_IOC,
            }
            
            # 市价单使用当前价格
            if order_type.upper() == 'MARKET':
                # 市价单不需要指定价格，MT5 会用当前市场价格
                pass
            else:
                # 限价/止损单需要指定价格
                if price:
                    request["price"] = price
                else:
                    return MT5OrderResult(
                        is_success=False,
                        error_code="MISSING_PRICE",
                        error_message=f"Price required for {order_type} order",
                    )
            
            # 设置止损止盈
            if stop_loss and stop_loss > 0:
                request["sl"] = stop_loss
            if take_profit and take_profit > 0:
                request["tp"] = take_profit
            
            # 发送订单
            result = _mt5.order_send(request)
            
            if result is None:
                return MT5OrderResult(
                    is_success=False,
                    error_code="NULL_RESULT",
                    error_message="order_send returned None",
                )
            
            # 检查订单结果
            if result.retcode != _mt5.TRADE_RETCODE_DONE:
                return MT5OrderResult(
                    is_success=False,
                    error_code=f"RETCODE_{result.retcode}",
                    error_message=result.comment or f"Order failed with retcode {result.retcode}",
                )
            
            logger.info(f"MT5 order placed: {result.order} {side} {symbol} {volume}@{price or 'market'}")
            
            return MT5OrderResult(
                is_success=True,
                order_id=str(result.order),
                deal_id=str(result.deal),
                filled_price=result.price,
                filled_quantity=result.volume,
            )
            
        except Exception as e:
            logger.error(f"Place order failed: {e}")
            return MT5OrderResult(
                is_success=False,
                error_code="EXCEPTION",
                error_message=str(e),
            )
    
    def close_position(
        self,
        ticket: int,
        volume: Optional[float] = None,
        comment: str = "python close",
    ) -> MT5OrderResult:
        """
        平仓操作
        
        Args:
            ticket: 持仓订单号
            volume: 平仓手数（可选，默认全平）
            comment: 注释
            
        Returns:
            MT5OrderResult 平仓结果
        """
        if not self._ensure_connected():
            return MT5OrderResult(
                is_success=False,
                error_code="NOT_CONNECTED",
                error_message="MT5 not connected",
            )
        
        try:
            # 获取持仓信息
            positions = _mt5.positions_get(ticket=ticket)
            if not positions or len(positions) == 0:
                return MT5OrderResult(
                    is_success=False,
                    error_code="POSITION_NOT_FOUND",
                    error_message=f"Position not found: {ticket}",
                )
            
            position = positions[0]
            
            # 确定平仓方向（与持仓方向相反）
            close_type = _mt5.ORDER_TYPE_SELL if position.type == 0 else _mt5.ORDER_TYPE_BUY
            close_volume = volume if volume else position.volume
            
            request = {
                "action": _mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": close_volume,
                "type": close_type,
                "position": ticket,
                "deviation": 20,
                "magic": 234000,
                "comment": comment,
                "type_time": _mt5.ORDER_TIME_GTC,
                "type_filling": _mt5.ORDER_FILLING_IOC,
            }
            
            result = _mt5.order_send(request)
            
            if result.retcode != _mt5.TRADE_RETCODE_DONE:
                return MT5OrderResult(
                    is_success=False,
                    error_code=f"RETCODE_{result.retcode}",
                    error_message=result.comment or f"Close failed with retcode {result.retcode}",
                )
            
            logger.info(f"MT5 position closed: {ticket} {close_volume} lots")
            
            return MT5OrderResult(
                is_success=True,
                order_id=str(result.order),
                deal_id=str(result.deal),
                filled_price=result.price,
                filled_quantity=result.volume,
            )
            
        except Exception as e:
            logger.error(f"Close position failed: {e}")
            return MT5OrderResult(
                is_success=False,
                error_code="EXCEPTION",
                error_message=str(e),
            )
    
    def modify_position(
        self,
        ticket: int,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> MT5OrderResult:
        """
        修改持仓的止损止盈
        
        Args:
            ticket: 持仓订单号
            sl: 新止损价（可选）
            tp: 新止盈价（可选）
            
        Returns:
            MT5OrderResult 修改结果
        """
        if not self._ensure_connected():
            return MT5OrderResult(
                is_success=False,
                error_code="NOT_CONNECTED",
                error_message="MT5 not connected",
            )
        
        try:
            positions = _mt5.positions_get(ticket=ticket)
            if not positions or len(positions) == 0:
                return MT5OrderResult(
                    is_success=False,
                    error_code="POSITION_NOT_FOUND",
                    error_message=f"Position not found: {ticket}",
                )
            
            position = positions[0]
            
            request = {
                "action": _mt5.TRADE_ACTION_MODIFY,
                "position": ticket,
                "sl": sl if sl is not None else position.sl,
                "tp": tp if tp is not None else position.tp,
            }
            
            result = _mt5.order_send(request)
            
            if result.retcode != _mt5.TRADE_RETCODE_DONE:
                return MT5OrderResult(
                    is_success=False,
                    error_code=f"RETCODE_{result.retcode}",
                    error_message=result.comment or f"Modify failed with retcode {result.retcode}",
                )
            
            logger.info(f"MT5 position modified: {ticket} SL={sl} TP={tp}")
            
            return MT5OrderResult(
                is_success=True,
                order_id=str(result.order),
            )
            
        except Exception as e:
            logger.error(f"Modify position failed: {e}")
            return MT5OrderResult(
                is_success=False,
                error_code="EXCEPTION",
                error_message=str(e),
            )
    
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取品种最新行情
        
        Args:
            symbol: 品种代码
            
        Returns:
            包含 bid/ask/last 的字典
        """
        if not self._ensure_connected():
            return None
        
        try:
            tick = _mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            
            return {
                'symbol': symbol,
                'bid': float(tick.bid),
                'ask': float(tick.ask),
                'last': float(tick.last),
                'time': int(tick.time),
            }
        except Exception as e:
            logger.error(f"Get ticker failed: {e}")
            return None


# ==================== 便捷函数 ====================


def create__mt5_client(
    login: int,
    password: str,
    server: str,
    path: str = "",
) -> Optional[MT5Client]:
    """
    创建 MT5 客户端（工厂函数）
    
    Args:
        login: 账户登录名
        password: 账户密码
        server: 交易服务器
        path: MT5 终端路径（可选）
        
    Returns:
        MT5Client 实例，连接失败返回 None
    """
    client = MT5Client(login=login, password=password, server=server, path=path)
    if not client.connect():
        return None
    return client
