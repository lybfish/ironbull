"""
MT5 Node Agent - Windows 端节点代理

职责：
- 主动连接 Linux 服务器 (WebSocket)
- 保持心跳 (30秒)
- 接收并执行交易命令
- 采集 K 线数据上报服务器
- 采集账户/持仓数据上报服务器

使用方式：
    python main.py
    # 或双击 mt5-node-agent.exe (打包后)
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import websockets
import yaml
from pydantic import BaseModel, Field

# 版本信息
VERSION = "1.0.0"

# ============== 配置模型 ==============

class MT5Config(BaseModel):
    """MT5 配置"""
    login: int
    password: str
    server: str
    path: str = ""  # MT5 终端路径，可选


class AgentConfig(BaseModel):
    """Agent 完整配置"""
    # 服务器配置
    server_url: str = "localhost:9102"  # Linux 服务器地址
    node_id: str = "node_001"            # 节点 ID (唯一标识)
    
    # MT5 配置
    mt5: MT5Config
    
    # 监控品种 (K 线采集)
    symbols: List[str] = Field(default_factory=lambda: ["EURUSD", "XAUUSD"])
    
    # K 线时间周期
    timeframe: str = "H1"  # H1, M5, M15, D1, etc.
    
    # 采集间隔 (秒)
    heartbeat_interval: int = 30
    kline_interval: int = 60
    balance_interval: int = 300  # 余额上报间隔
    
    # 日志级别
    log_level: str = "INFO"


# ============== 日志配置 ==============

def setup_logging(level: str = "INFO") -> logging.Logger:
    """配置日志"""
    log_format = "%(asctime)s | %(levelname)-8s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    return logging.getLogger("mt5-node-agent")


# ============== MT5 客户端封装 ==============

class MT5Client:
    """MT5 客户端封装 (本地调用)"""
    
    def __init__(self, config: MT5Config):
        self.config = config
        self._mt5 = None
        self.connected = False
    
    def connect(self) -> bool:
        """连接 MT5"""
        try:
            import MetaTrader5 as mt5
            self._mt5 = mt5
            
            # 初始化
            if self.config.path:
                if not mt5.initialize(path=self.config.path):
                    return False
            else:
                if not mt5.initialize():
                    return False
            
            # 登录
            if not mt5.login(
                login=self.config.login,
                password=self.config.password,
                server=self.config.server,
            ):
                return False
            
            self.connected = True
            return True
            
        except ImportError:
            logging.warning("MetaTrader5 library not installed, running in mock mode")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.connected and self._mt5:
            self._mt5.shutdown()
            self.connected = False
    
    def is_available(self) -> bool:
        """检查 MT5 是否可用"""
        try:
            import MetaTrader5
            return True
        except ImportError:
            return False
    
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取品种行情"""
        if not self.connected:
            return None
        
        try:
            tick = self._mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            
            return {
                "symbol": symbol,
                "bid": float(tick.bid),
                "ask": float(tick.ask),
                "last": float(tick.last),
                "time": int(tick.time),
            }
        except Exception as e:
            logging.error(f"Get ticker failed: {e}")
            return None
    
    def get_balance(self) -> Optional[Dict[str, Any]]:
        """获取账户余额"""
        if not self.connected:
            return None
        
        try:
            account = self._mt5.account_info()
            if account is None:
                return None
            
            return {
                "balance": account.balance,
                "equity": account.equity,
                "margin": account.margin,
                "free_margin": account.margin_free,
                "profit": account.profit,
                "leverage": account.leverage,
            }
        except Exception as e:
            logging.error(f"Get balance failed: {e}")
            return None
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓列表"""
        if not self.connected:
            return []
        
        try:
            positions = self._mt5.positions_get()
            if positions is None:
                return []
            
            result = []
            for pos in positions:
                result.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "side": "BUY" if pos.type == 0 else "SELL",
                    "volume": pos.volume,
                    "price_open": pos.price_open,
                    "price_current": pos.price_current,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "profit": pos.profit,
                })
            
            return result
            
        except Exception as e:
            logging.error(f"Get positions failed: {e}")
            return []
    
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
    ) -> Dict[str, Any]:
        """下单交易"""
        if not self.connected:
            return {
                "success": False,
                "error_code": "NOT_CONNECTED",
                "error_message": "MT5 not connected",
            }
        
        try:
            # 确保品种可见
            if not self._mt5.symbol_select(symbol, True):
                return {
                    "success": False,
                    "error_code": "SYMBOL_NOT_FOUND",
                    "error_message": f"Symbol not found: {symbol}",
                }
            
            # 解析订单类型
            order_type_lower = order_type.lower() if order_type else 'market'
            
            if order_type_lower == 'market':
                mt5_order_type = self._mt5.ORDER_TYPE_BUY if side.upper() == "BUY" else self._mt5.ORDER_TYPE_SELL
            elif order_type_lower == 'limit':
                mt5_order_type = self._mt5.ORDER_TYPE_BUY_LIMIT if side.upper() == "BUY" else self._mt5.ORDER_TYPE_SELL_LIMIT
            elif order_type_lower == 'stop':
                mt5_order_type = self._mt5.ORDER_TYPE_BUY_STOP if side.upper() == "BUY" else self._mt5.ORDER_TYPE_SELL_STOP
            else:
                mt5_order_type = self._mt5.ORDER_TYPE_BUY if side.upper() == "BUY" else self._mt5.ORDER_TYPE_SELL
            
            # 构建订单请求
            request = {
                "action": self._mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5_order_type,
                "deviation": 20,
                "magic": 234000,
                "comment": comment,
                "type_time": self._mt5.ORDER_TIME_GTC,
                "type_filling": self._mt5.ORDER_FILLING_IOC,
            }
            
            # 市价单不需要指定价格
            if order_type_lower != 'market':
                if price:
                    request["price"] = price
                else:
                    return {
                        "success": False,
                        "error_code": "MISSING_PRICE",
                        "error_message": f"Price required for {order_type} order",
                    }
            
            # 设置止损止盈
            if stop_loss and stop_loss > 0:
                request["sl"] = stop_loss
            if take_profit and take_profit > 0:
                request["tp"] = take_profit
            
            # 发送订单
            result = self._mt5.order_send(request)
            
            if result is None:
                return {
                    "success": False,
                    "error_code": "NULL_RESULT",
                    "error_message": "order_send returned None",
                }
            
            if result.retcode != self._mt5.TRADE_RETCODE_DONE:
                return {
                    "success": False,
                    "error_code": f"RETCODE_{result.retcode}",
                    "error_message": result.comment or f"Order failed with retcode {result.retcode}",
                }
            
            logging.info(f"Order placed: {result.order} {side} {symbol} {volume}")
            
            return {
                "success": True,
                "order_id": str(result.order),
                "deal_id": str(result.deal),
                "filled_price": result.price,
                "filled_quantity": result.volume,
            }
            
        except Exception as e:
            logging.error(f"Place order failed: {e}")
            return {
                "success": False,
                "error_code": "EXCEPTION",
                "error_message": str(e),
            }
    
    def get_klines(self, symbol: str, timeframe: str, count: int = 100) -> List[Dict[str, Any]]:
        """获取 K 线数据"""
        if not self.connected:
            return []
        
        try:
            # 时间周期映射
            timeframe_map = {
                "M1": self._mt5.TIMEFRAME_M1,
                "M5": self._mt5.TIMEFRAME_M5,
                "M15": self._mt5.TIMEFRAME_M15,
                "M30": self._mt5.TIMEFRAME_M30,
                "H1": self._mt5.TIMEFRAME_H1,
                "H4": self._mt5.TIMEFRAME_H4,
                "D1": self._mt5.TIMEFRAME_D1,
                "W1": self._mt5.TIMEFRAME_W1,
                "MN1": self._mt5.TIMEFRAME_MN1,
            }
            
            tf = timeframe_map.get(timeframe.upper(), self._mt5.TIMEFRAME_H1)
            
            # 获取 K 线
            rates = self._mt5.copy_rates_from_pos(symbol, tf, 0, count)
            
            if rates is None:
                return []
            
            result = []
            for rate in rates:
                result.append({
                    "time": int(rate["time"]),
                    "open": rate["open"],
                    "high": rate["high"],
                    "low": rate["low"],
                    "close": rate["close"],
                    "volume": rate["tick_volume"],
                })
            
            return result
            
        except Exception as e:
            logging.error(f"Get klines failed: {e}")
            return []


# ============== MT5 Node Agent ==============

class MT5NodeAgent:
    """MT5 节点代理"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.ws = None
        self.mt5_client = None
        self.running = False
        self.logger = logging.getLogger("mt5-node-agent")
        self.node_id = config.node_id
        
        # 初始化 MT5 客户端
        if config.mt5:
            self.mt5_client = MT5Client(config.mt5)
    
    async def connect_server(self) -> bool:
        """连接 Linux 服务器"""
        try:
            # 确定协议
            if self.config.server_url.startswith("wss://") or self.config.server_url.startswith("ws://"):
                ws_url = self.config.server_url
            else:
                # 默认使用 wss (HTTPS) 如果端口是 443
                if ":443" in self.config.server_url:
                    ws_url = f"wss://{self.config.server_url}/ws/node/{self.node_id}"
                else:
                    ws_url = f"ws://{self.config.server_url}/ws/node/{self.node_id}"
            
            self.logger.info(f"Connecting to server: {ws_url}")
            self.ws = await websockets.connect(ws_url)
            self.logger.info(f"Connected to server")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to server: {e}")
            return False
    
    async def register(self) -> bool:
        """注册节点"""
        try:
            register_msg = {
                "type": "REGISTER",
                "node_id": self.node_id,
                "broker": self.config.mt5.server if self.config.mt5 else "",
                "account": str(self.config.mt5.login) if self.config.mt5 else "",
                "platform": "mt5",
                "version": VERSION,
                "capabilities": ["trade", "kline", "balance", "position"],
            }
            
            await self.ws.send(json.dumps(register_msg))
            
            # 等待注册确认
            response = await asyncio.wait_for(self.ws.recv(), timeout=30)
            data = json.loads(response)
            
            if data.get("type") == "REGISTER_ACK":
                self.logger.info(f"Registered successfully: {data.get('server_time')}")
                return True
            else:
                self.logger.error(f"Registration failed: {data}")
                return False
                
        except asyncio.TimeoutError:
            self.logger.error("Registration timeout")
            return False
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return False
    
    async def heartbeat_loop(self):
        """心跳保活"""
        while self.running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                if self.ws and self.ws.open:
                    await self.ws.send(json.dumps({
                        "type": "HEARTBEAT",
                        "status": "connected",
                        "mt5_connected": self.mt5_client.connected if self.mt5_client else False,
                    }))
                    self.logger.debug("Heartbeat sent")
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                break
    
    async def kline_collect_loop(self):
        """K 线采集上报"""
        while self.running:
            try:
                await asyncio.sleep(self.config.kline_interval)
                
                if not self.mt5_client or not self.mt5_client.connected:
                    continue
                
                for symbol in self.config.symbols:
                    try:
                        klines = self.mt5_client.get_klines(symbol, self.config.timeframe, 10)
                        
                        if klines:
                            await self.send_message({
                                "type": "KLINE",
                                "symbol": symbol,
                                "timeframe": self.config.timeframe,
                                "data": klines,
                            })
                            self.logger.debug(f"Kline sent: {symbol}")
                            
                    except Exception as e:
                        self.logger.error(f"Failed to send kline for {symbol}: {e}")
                        
            except Exception as e:
                self.logger.error(f"Kline collect error: {e}")
    
    async def balance_report_loop(self):
        """余额/持仓上报"""
        while self.running:
            try:
                await asyncio.sleep(self.config.balance_interval)
                
                if not self.mt5_client or not self.mt5_client.connected:
                    continue
                
                # 上报余额
                try:
                    balance = self.mt5_client.get_balance()
                    if balance:
                        await self.send_message({
                            "type": "BALANCE",
                            "balance": balance,
                        })
                        self.logger.debug("Balance reported")
                except Exception as e:
                    self.logger.error(f"Failed to report balance: {e}")
                
                # 上报持仓
                try:
                    positions = self.mt5_client.get_positions()
                    if positions:
                        await self.send_message({
                            "type": "POSITION",
                            "positions": positions,
                        })
                        self.logger.debug(f"Positions reported: {len(positions)}")
                except Exception as e:
                    self.logger.error(f"Failed to report positions: {e}")
                    
            except Exception as e:
                self.logger.error(f"Balance report error: {e}")
    
    async def send_message(self, message: dict):
        """发送消息到服务器"""
        if self.ws and self.ws.open:
            try:
                await self.ws.send(json.dumps(message))
            except Exception as e:
                self.logger.error(f"Failed to send message: {e}")
    
    async def handle_message(self, message: dict):
        """处理服务器命令"""
        msg_type = message.get("type")
        
        if msg_type == "PING":
            # 心跳请求
            await self.send_message({
                "type": "PONG",
                "timestamp": int(time.time()),
            })
            
        elif msg_type == "TRADE":
            # 交易命令
            task_id = message.get("task_id", "")
            order = message.get("order", {})
            
            self.logger.info(
                f"Trade command received: {task_id} {order.get('side')} {order.get('symbol')} {order.get('quantity')}"
            )
            
            # 执行交易
            if self.mt5_client and self.mt5_client.connected:
                result = self.mt5_client.place_order(
                    symbol=order.get("symbol"),
                    side=order.get("side"),
                    order_type=order.get("order_type", "MARKET"),
                    volume=order.get("quantity", 0.01),
                    price=order.get("price"),
                    stop_loss=order.get("stop_loss"),
                    take_profit=order.get("take_profit"),
                    comment=order.get("comment", f"ironbull:{task_id}"),
                )
            else:
                # Mock 模式
                result = {
                    "success": True,
                    "order_id": f"mock_{int(time.time() * 1000)}",
                    "filled_price": order.get("price", 100.0),
                    "filled_quantity": order.get("quantity", 0.01),
                }
                self.logger.info(f"Mock order executed: {result}")
            
            # 上报结果
            await self.send_message({
                "type": "TRADE_RESULT",
                "task_id": task_id,
                "result": result,
            })
            
        elif msg_type == "CONFIG_UPDATE":
            # 配置更新
            self.logger.info(f"Config update received: {message}")
            # TODO: 更新配置并重启
        
        else:
            self.logger.warning(f"Unknown message type: {msg_type}")
    
    async def run(self):
        """运行 agent"""
        self.running = True
        self.logger.info(f"Starting MT5 Node Agent v{VERSION}")
        self.logger.info(f"Node ID: {self.node_id}")
        
        # 连接 MT5
        if self.mt5_client:
            if self.mt5_client.connect():
                self.logger.info(f"MT5 connected: {self.config.mt5.server}")
            else:
                self.logger.warning("MT5 connection failed, running in mock mode")
                self.mt5_client = None
        
        # 连接服务器
        if not await self.connect_server():
            self.logger.error("Failed to connect to server")
            return
        
        # 注册
        if not await self.register():
            self.logger.error("Failed to register")
            return
        
        # 启动后台任务
        tasks = [
            asyncio.create_task(self.heartbeat_loop()),
            asyncio.create_task(self.kline_collect_loop()),
            asyncio.create_task(self.balance_report_loop()),
        ]
        
        self.logger.info("Agent started successfully")
        
        # 消息循环
        try:
            async for msg in self.ws:
                await self.handle_message(json.loads(msg))
        except websockets.ConnectionClosed:
            self.logger.warning("Connection closed")
        except Exception as e:
            self.logger.error(f"Message loop error: {e}")
        finally:
            self.running = False
            
            # 取消后台任务
            for task in tasks:
                task.cancel()
            
            # 断开连接
            if self.ws:
                await self.ws.close()
            
            if self.mt5_client:
                self.mt5_client.disconnect()
            
            self.logger.info("Agent stopped")


# ============== 配置加载 ==============

def load_config(config_path: Optional[str] = None) -> AgentConfig:
    """加载配置"""
    if config_path is None:
        # 查找配置文件
        possible_paths = [
            "config.yaml",
            "config.yml",
            "../config.yaml",
            Path(__file__).parent / "config.yaml",
            Path(__file__).parent / "config.yml",
        ]
        
        for path in possible_paths:
            p = Path(path)
            if p.exists():
                config_path = str(p)
                break
    
    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        
        # 解析 MT5 配置
        mt5_config_data = config_data.get("mt5", {})
        mt5_config = MT5Config(
            login=mt5_config_data.get("login", 0),
            password=mt5_config_data.get("password", ""),
            server=mt5_config_data.get("server", ""),
            path=mt5_config_data.get("path", ""),
        )
        
        # 解析完整配置
        config = AgentConfig(
            server_url=config_data.get("server_url", "localhost:9102"),
            node_id=config_data.get("node_id", "node_001"),
            mt5=mt5_config,
            symbols=config_data.get("symbols", ["EURUSD", "XAUUSD"]),
            timeframe=config_data.get("timeframe", "H1"),
            heartbeat_interval=config_data.get("heartbeat_interval", 30),
            kline_interval=config_data.get("kline_interval", 60),
            balance_interval=config_data.get("balance_interval", 300),
            log_level=config_data.get("log_level", "INFO"),
        )
        
        logging.info(f"Config loaded from: {config_path}")
        return config
    
    # 默认配置 (Mock 模式)
    logging.info("Using default mock config")
    return AgentConfig(
        server_url="localhost:9102",
        node_id="node_001",
        mt5=MT5Config(login=0, password="", server=""),
        symbols=["EURUSD"],
        timeframe="H1",
    )


# ============== 主程序 ==============

async def main():
    """主入口"""
    # 加载配置
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    config = load_config(config_path)
    
    # 配置日志
    logger = setup_logging(config.log_level)
    
    # 创建并运行 agent
    agent = MT5NodeAgent(config)
    
    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
