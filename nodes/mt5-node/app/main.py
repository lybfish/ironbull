"""
MT5 Node - MT5 交易执行节点 (中控端)

MT5 交易执行器 - 基于 MetaTrader5 SDK 实现真实交易

职责：
- 接收来自 execution-dispatcher 的交易任务
- 管理 Windows 节点连接 (WebSocket)
- 路由交易命令到对应节点
- 接收节点上报的 K 线、余额、持仓数据
"""

from dataclasses import asdict, dataclass
from typing import Optional, Dict, Any, List
import time
import json
import asyncio
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from libs.contracts import NodeResult
from libs.core import get_config, get_logger, setup_logging, gen_id, time_now, AppError
from libs.exchange.mt5 import MT5Client, MT5_AVAILABLE


# ============== Pydantic Models ==============

class NodeTaskModel(BaseModel):
    """节点任务模型"""
    task_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # MT5 凭证
    mt5_login: Optional[int] = None
    mt5_password: Optional[str] = None
    mt5_server: Optional[str] = None
    
    # 兼容旧字段（用于从 api_key/api_secret 解析）
    api_key: str = ""
    api_secret: str = ""
    passphrase: Optional[str] = None
    exchange: str = ""
    timeout_ms: int = 30000
    
    # 节点路由
    node_id: Optional[str] = None  # 指定执行节点，不指定则使用默认节点


class NodeResultResponse(BaseModel):
    """节点结果响应"""
    result: dict


class BalanceRequest(BaseModel):
    """余额查询请求"""
    mt5_login: Optional[int] = None
    mt5_password: Optional[str] = None
    mt5_server: Optional[str] = None


class BalanceResponse(BaseModel):
    """余额查询响应"""
    mode: str  # live / mock
    available: bool
    balance: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class NodeRegisterRequest(BaseModel):
    """节点注册请求"""
    node_id: str
    broker: str
    account: str
    platform: str = "mt5"
    version: str = "1.0.0"
    capabilities: List[str] = Field(default_factory=list)


class NodeInfo(BaseModel):
    """节点信息"""
    node_id: str
    broker: str
    account: str
    platform: str
    version: str
    capabilities: List[str]
    status: str  # connected / disconnected
    connected_at: str
    last_heartbeat: str


class CommandRequest(BaseModel):
    """向节点发送命令请求"""
    command: dict


class TradeCommand(BaseModel):
    """交易命令"""
    task_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: str = ""


# ============== 配置 ==============

config = get_config()
service_name = "mt5-node"
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name=service_name,
)
logger = get_logger(service_name)

# 交易模式: live / mock
TRADING_MODE = config.get_str("trading_mode", "mock")

# WebSocket 超时时间 (秒)
WS_TIMEOUT = 300

# MT5 客户端缓存（实际生产应该用连接池）
_mt5_clients: Dict[str, MT5Client] = {}

# 模拟交易状态（单例）
_mock_balance: Dict[str, float] = {
    "balance": 10000.0,  # 初始模拟余额 10000 USD
    "equity": 10000.0,
    "margin": 0.0,
    "free_margin": 10000.0,
    "profit": 0.0,
}
_mock_positions: Dict[str, Dict] = {}  # symbol -> position


# ============== WebSocket 连接管理 ==============

class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # node_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # node_id -> 节点信息
        self.node_info: Dict[str, NodeInfo] = {}
        # task_id -> node_id (用于追踪任务)
        self.task_routing: Dict[str, str] = {}
        # 任务结果回调
        self.pending_tasks: Dict[str, asyncio.Future] = {}
    
    async def connect(self, node_id: str, websocket: WebSocket, info: NodeInfo):
        """建立连接"""
        await websocket.accept()
        self.active_connections[node_id] = websocket
        self.node_info[node_id] = info
        logger.info(f"Node connected: {node_id}")
        
        # 广播节点状态变化
        await self.broadcast_node_status()
    
    def disconnect(self, node_id: str):
        """断开连接"""
        if node_id in self.active_connections:
            del self.active_connections[node_id]
        
        # 更新节点状态
        if node_id in self.node_info:
            self.node_info[node_id].status = "disconnected"
        
        logger.info(f"Node disconnected: {node_id}")
        
        # 取消挂起的任务
        tasks_to_cancel = [tid for tid, nid in self.task_routing.items() if nid == node_id]
        for tid in tasks_to_cancel:
            if tid in self.pending_tasks:
                self.pending_tasks[tid].cancel()
                del self.pending_tasks[tid]
            if tid in self.task_routing:
                del self.task_routing[tid]
        
        # 广播节点状态变化
        asyncio.create_task(self.broadcast_node_status())
    
    async def send_message(self, node_id: str, message: dict) -> bool:
        """发送消息到节点"""
        if node_id not in self.active_connections:
            logger.warning(f"Node not connected: {node_id}")
            return False
        
        try:
            await self.active_connections[node_id].send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {node_id}: {e}")
            return False
    
    async def broadcast_message(self, message: dict):
        """广播消息到所有连接"""
        for node_id in self.active_connections:
            await self.send_message(node_id, message)
    
    async def broadcast_node_status(self):
        """广播节点状态变化"""
        await self.broadcast_message({
            "type": "NODE_STATUS",
            "nodes": [
                {
                    "node_id": info.node_id,
                    "status": info.status,
                    "broker": info.broker,
                }
                for info in self.node_info.values()
            ]
        })
    
    def get_connected_nodes(self) -> List[NodeInfo]:
        """获取所有已连接的节点"""
        return [
            info for info in self.node_info.values()
            if info.status == "connected"
        ]
    
    def is_connected(self, node_id: str) -> bool:
        """检查节点是否连接"""
        return node_id in self.active_connections


# 全局连接管理器
manager = ConnectionManager()


# ============== 工具函数 ==============

def _get_mt5_client(login: int, password: str, server: str) -> Optional[MT5Client]:
    """获取或创建 MT5 客户端"""
    if not MT5_AVAILABLE:
        logger.error("MT5 library not installed")
        return None
    
    key = f"{login}@{server}"
    
    if key not in _mt5_clients:
        client = MT5Client(
            login=login,
            password=password,
            server=server,
        )
        if not client.connect():
            logger.error(f"MT5 connection failed: {login}@{server}")
            return None
        _mt5_clients[key] = client
        logger.info(f"MT5 client created: {key}")
    
    return _mt5_clients[key]


def _get_credentials(task: NodeTaskModel) -> tuple:
    """
    从任务中获取 MT5 凭证
    
    优先使用专门的 mt5 字段，其次从 api_key/api_secret 解析
    """
    # 优先使用专门的 MT5 字段
    if task.mt5_login and task.mt5_password and task.mt5_server:
        return (task.mt5_login, task.mt5_password, task.mt5_server)
    
    # 兼容旧格式：api_key 可能是 login，api_secret 可能是 password
    # 格式: login@server:password
    if task.api_key and task.api_secret:
        if "@" in task.api_key and ":" in task.api_secret:
            parts = task.api_key.split("@")
            server = parts[1] if len(parts) > 1 else ""
            login_parts = parts[0].split(":")
            login = int(login_parts[0]) if login_parts[0].isdigit() else 0
            password = task.api_secret
            return (login, password, server)
    
    return (None, None, None)


def _update_mock_balance(side: str, volume: float, price: float):
    """更新模拟余额（简化版）"""
    # 计算保证金（假设杠杆 100 倍）
    margin_required = price * volume * 100  # 简化计算
    fee = price * volume * 0.0001  # 万分之一手续费
    
    if side.upper() == "BUY":
        _mock_balance["free_margin"] -= (margin_required + fee)
        _mock_balance["margin"] += margin_required
    else:
        # 卖单保证金计算
        _mock_balance["free_margin"] -= (margin_required + fee)
        _mock_balance["margin"] += margin_required
    
    _mock_balance["equity"] = _mock_balance["balance"] + _mock_balance["profit"]


def _create_mock_result(task: NodeTaskModel, request_id: str) -> NodeResult:
    """创建模拟交易结果"""
    symbol = task.symbol
    
    # 更新模拟持仓
    position_key = f"{symbol}_{task.side}"
    
    if position_key in _mock_positions:
        # 更新现有持仓
        pos = _mock_positions[position_key]
        pos["volume"] += task.quantity
        pos["price_open"] = (pos["price_open"] * (pos["volume"] - task.quantity) + 
                           task.price * task.quantity) / pos["volume"]
    else:
        # 创建新持仓
        _mock_positions[position_key] = {
            "symbol": symbol,
            "side": task.side,
            "volume": task.quantity,
            "price_open": task.price or 100.0,
        }
    
    # 更新模拟余额
    if task.price:
        _update_mock_balance(task.side, task.quantity, task.price)
    
    return NodeResult(
        task_id=task.task_id,
        success=True,
        exchange_order_id=f"mock_{int(time.time() * 1000)}",
        filled_price=task.price or 100.0,
        filled_quantity=task.quantity,
        executed_at=time_now(),
        execution_ms=1,
    )


# ============== FastAPI App ==============

app = FastAPI(title="mt5-node")


def _error_payload(code: str, message: str, detail: Optional[dict] = None, request_id: Optional[str] = None) -> dict:
    payload = {"code": code, "message": message, "detail": detail or {}}
    if request_id:
        payload["request_id"] = request_id
    return payload


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=422,
        content=_error_payload("VALIDATION_ERROR", "Validation failed", {"errors": exc.errors()}, request_id),
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=400,
        content=_error_payload(exc.code, exc.message, exc.detail, request_id),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", None)
    detail = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload("HTTP_ERROR", "HTTP error", detail, request_id),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.error("unhandled exception", request_id=request_id, error=str(exc))
    return JSONResponse(
        status_code=500,
        content=_error_payload("INTERNAL_ERROR", "Internal error", {"error": str(exc)}, request_id),
    )


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or gen_id("req_")
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


# ============== WebSocket 端点 ==============

@app.websocket("/ws/node/{node_id}")
async def websocket_endpoint(websocket: WebSocket, node_id: str):
    """
    WebSocket 端点 - 节点连接和通信

    消息流：
    1. 节点发送 REGISTER 进行注册
    2. 节点定期发送 HEARTBEAT 心跳
    3. 服务器发送 TRADE 下发交易命令
    4. 节点返回 TRADE_RESULT 交易结果
    5. 节点上报 KLINE/BALANCE/POSITION 数据
    """
    try:
        # 先接受连接
        await websocket.accept()
        
        # 等待注册消息
        register_data = await asyncio.wait_for(websocket.receive_json(), timeout=30)

        if register_data.get("type") != "REGISTER":
            await websocket.close(code=4000, reason="First message must be REGISTER")
            return

        # 解析节点信息
        node_info = NodeInfo(
            node_id=register_data.get("node_id", node_id),
            broker=register_data.get("broker", ""),
            account=register_data.get("account", ""),
            platform=register_data.get("platform", "mt5"),
            version=register_data.get("version", "1.0.0"),
            capabilities=register_data.get("capabilities", []),
            status="connected",
            connected_at=datetime.now().isoformat(),
            last_heartbeat=datetime.now().isoformat(),
        )

        # 建立连接（添加到管理器）
        # 注意：连接已经在前面 accept 了，这里只需要注册到管理器
        manager.active_connections[node_id] = websocket
        manager.node_info[node_id] = node_info
        logger.info(f"Node connected: {node_id}")

        # 发送注册确认
        await websocket.send_json({
            "type": "REGISTER_ACK",
            "node_id": node_id,
            "status": "ok",
            "server_time": datetime.now().isoformat(),
        })
        
        # 消息循环
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=WS_TIMEOUT)
                
                msg_type = data.get("type")
                
                if msg_type == "HEARTBEAT":
                    # 更新心跳时间
                    if node_id in manager.node_info:
                        manager.node_info[node_id].last_heartbeat = datetime.now().isoformat()
                    # 回复心跳
                    await websocket.send_json({"type": "PONG", "timestamp": int(time.time())})
                    
                elif msg_type == "TRADE_RESULT":
                    # 交易结果回报
                    task_id = data.get("task_id")
                    result_data = data.get("result", {})
                    
                    logger.info(
                        "Trade result received",
                        node_id=node_id,
                        task_id=task_id,
                        success=result_data.get("success"),
                    )
                    
                    # 如果有挂起的任务，设置结果
                    if task_id in manager.pending_tasks:
                        future = manager.pending_tasks[task_id]
                        if not future.done():
                            future.set_result(data)
                    
                    # 从路由表中移除
                    if task_id in manager.task_routing:
                        del manager.task_routing[task_id]
                    
                elif msg_type == "KLINE":
                    # K 线上报 - 转发到数据处理服务
                    symbol = data.get("symbol")
                    logger.info(
                        "Kline received",
                        node_id=node_id,
                        symbol=symbol,
                        bars=len(data.get("data", [])),
                    )
                    # TODO: 转发到 influxdb 或数据聚合服务
                    
                elif msg_type == "BALANCE":
                    # 余额上报
                    logger.info(
                        "Balance received",
                        node_id=node_id,
                        balance=data.get("balance"),
                    )
                    # TODO: 存储到数据库
                    
                elif msg_type == "POSITION":
                    # 持仓上报
                    logger.info(
                        "Position received",
                        node_id=node_id,
                        positions=len(data.get("positions", [])),
                    )
                    # TODO: 存储到数据库
                    
                else:
                    logger.warning(f"Unknown message type: {msg_type}")
                    
            except asyncio.TimeoutError:
                # 发送心跳检测
                await websocket.send_json({"type": "PING"})
                
    except asyncio.TimeoutError:
        logger.warning(f"Node {node_id} registration timeout")
    except WebSocketDisconnect:
        manager.disconnect(node_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(node_id)


# ============== HTTP API Endpoints ==============

@app.get("/health")
def health():
    """
    健康检查
    
    返回节点状态和 MT5 库可用性
    """
    return {
        "status": "ok",
        "service": service_name,
        "trading_mode": TRADING_MODE,
        "mt5_available": MT5_AVAILABLE,
        "nodes_connected": len(manager.get_connected_nodes()),
        "endpoints": [
            "GET /health",
            "POST /api/node/execute",
            "POST /api/node/balance",
            "POST /api/node/mock/reset",
            "GET /api/node/mock/balance",
            "WS /ws/node/{node_id}",
            "GET /api/node/list",
            "POST /api/node/send/{node_id}",
        ],
    }


@app.get("/api/node/list")
def list_nodes():
    """
    获取已注册的节点列表
    """
    nodes = [
        {
            "node_id": info.node_id,
            "broker": info.broker,
            "account": info.account,
            "platform": info.platform,
            "version": info.version,
            "capabilities": info.capabilities,
            "status": info.status,
            "connected_at": info.connected_at,
            "last_heartbeat": info.last_heartbeat,
        }
        for info in manager.get_connected_nodes()
    ]
    
    return {
        "total": len(nodes),
        "nodes": nodes,
    }


@app.post("/api/node/send/{node_id}")
async def send_command(node_id: str, command: CommandRequest, request: Request):
    """
    向指定节点发送命令
    
    路径参数：
    - node_id: 目标节点 ID
    
    请求体：
    {
        "command": {
            "type": "TRADE",
            "task_id": "xxx",
            "order": {...}
        }
    }
    """
    request_id = request.state.request_id
    
    if not manager.is_connected(node_id):
        raise HTTPException(status_code=404, detail=f"Node not connected: {node_id}")
    
    # 包装命令消息
    message = {
        "type": command.command.get("type", "TRADE"),
        "node_id": node_id,
        "timestamp": int(time.time()),
        **command.command,
    }
    
    # 发送命令
    success = await manager.send_message(node_id, message)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send command")
    
    return {
        "status": "sent",
        "node_id": node_id,
        "request_id": request_id,
    }


@app.post("/api/node/execute", response_model=NodeResultResponse)
async def execute(task: NodeTaskModel, request: Request):
    """
    执行 MT5 交易任务
    
    支持三种模式：
    1. mock: 模拟交易（默认，不需要真实 MT5 账户）
    2. local: 本地 MT5 连接（Linux 直接连接，需要 MT5 环境）
    3. remote: 远程节点执行（通过 WebSocket 发送到 Windows 节点）
    
    请求体：
    {
        "task_id": "xxx",
        "symbol": "EURUSD",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 0.01,
        "price": null,
        "stop_loss": null,
        "take_profit": null,
        "mt5_login": 123456,
        "mt5_password": "your_password",
        "mt5_server": "your_server",
        "node_id": "node_001"  // 可选，指定执行节点
    }
    """
    task_data = task.dict()
    task_id = task.task_id
    request_id = request.state.request_id
    
    logger.info(
        "mt5-node executing",
        request_id=request_id,
        task_id=task.task_id,
        symbol=task.symbol,
        side=task.side,
        order_type=task.order_type,
        quantity=task.quantity,
        node_id=task.node_id,
    )
    
    start_time = time.time()
    
    # 获取凭证
    login, password, server = _get_credentials(task)
    
    # 确定执行模式
    use_remote = task.node_id and manager.is_connected(task.node_id)
    use_local = TRADING_MODE == "live" and login and password and server
    use_mock = not use_remote and not use_local
    
    try:
        if use_remote:
            # ========== 远程节点执行 ==========
            logger.info(
                "Executing via remote node",
                request_id=request_id,
                node_id=task.node_id,
            )
            
            # 创建任务 Future
            future = asyncio.Future()
            manager.pending_tasks[task_id] = future
            manager.task_routing[task_id] = task.node_id
            
            # 发送交易命令到节点
            trade_command = {
                "type": "TRADE",
                "task_id": task_id,
                "order": {
                    "symbol": task.symbol,
                    "side": task.side,
                    "order_type": task.order_type,
                    "quantity": task.quantity,
                    "price": task.price,
                    "stop_loss": task.stop_loss,
                    "take_profit": task.take_profit,
                    "comment": f"ironbull:{task_id}",
                },
            }
            
            success = await manager.send_message(task.node_id, trade_command)
            
            if not success:
                raise Exception(f"Failed to send command to node {task.node_id}")
            
            # 等待结果 (超时 30 秒)
            try:
                result_data = await asyncio.wait_for(future, timeout=30)
                result_dict = result_data.get("result", {})
                
                result = NodeResult(
                    task_id=task_id,
                    success=result_dict.get("success", False),
                    exchange_order_id=result_dict.get("order_id", ""),
                    filled_price=result_dict.get("filled_price", 0),
                    filled_quantity=result_dict.get("filled_quantity", 0),
                    executed_at=time_now(),
                    execution_ms=0,
                    error_code=result_dict.get("error_code"),
                    error_message=result_dict.get("error_message"),
                )
                
            except asyncio.TimeoutError:
                raise Exception("Trade execution timeout")
            
            finally:
                # 清理
                if task_id in manager.pending_tasks:
                    del manager.pending_tasks[task_id]
                if task_id in manager.task_routing:
                    del manager.task_routing[task_id]
        
        elif use_local:
            # ========== 本地 MT5 执行 ==========
            client = _get_mt5_client(login, password, server)
            if client is None:
                raise Exception("MT5 connection failed")
            
            try:
                # 下单
                order_result = client.place_order(
                    symbol=task.symbol,
                    side=task.side,
                    order_type=task.order_type,
                    volume=task.quantity,
                    price=task.price,
                    stop_loss=task.stop_loss,
                    take_profit=task.take_profit,
                    comment=f"ironbull:{task_id}",
                )
                
                if not order_result.is_success:
                    raise Exception(order_result.error_message or "MT5 order failed")
                
                # 构建结果
                result = NodeResult(
                    task_id=task_id,
                    success=True,
                    exchange_order_id=order_result.order_id or "",
                    filled_price=order_result.filled_price or task.price,
                    filled_quantity=order_result.filled_quantity or task.quantity,
                    executed_at=time_now(),
                    execution_ms=0,
                    error_code=order_result.error_code,
                    error_message=order_result.error_message,
                )
                
            finally:
                # 保持连接活跃
                pass
        
        else:
            # ========== 模拟交易 ==========
            if not MT5_AVAILABLE:
                logger.warning("MT5 library not installed, using mock mode")
            
            result = _create_mock_result(task, request_id)
            
            logger.info(
                "mock order executed",
                request_id=request_id,
                task_id=task_id,
                symbol=task.symbol,
                side=task.side,
                quantity=task.quantity,
            )
        
        end_time = time.time()
        result.execution_ms = int((end_time - start_time) * 1000)
        
        logger.info(
            "node executed",
            request_id=request_id,
            task_id=task_id,
            exchange=task.exchange or "mt5",
            mode="remote" if use_remote else ("local" if use_local else "mock"),
            success=result.success,
            order_id=result.exchange_order_id,
            filled_price=result.filled_price,
            execution_ms=result.execution_ms,
        )
        
        return {"result": asdict(result)}
        
    except Exception as e:
        logger.error(
            "node execution failed",
            request_id=request_id,
            task_id=task_id,
            error=str(e),
        )
        
        result = NodeResult(
            task_id=task_id,
            success=False,
            exchange_order_id="",
            filled_price=0,
            filled_quantity=0,
            executed_at=time_now(),
            execution_ms=0,
            error_code="EXECUTION_ERROR",
            error_message=str(e),
        )
        
        return {"result": asdict(result)}


@app.post("/api/node/balance", response_model=BalanceResponse)
def get_balance(req: BalanceRequest, request: Request):
    """
    查询 MT5 账户余额
    
    请求体：
    {
        "mt5_login": 123456,
        "mt5_password": "your_password",
        "mt5_server": "your_server"
    }
    
    响应：
    {
        "mode": "live",
        "available": true,
        "balance": {
            "balance": 10000.0,
            "equity": 10050.0,
            "margin": 500.0,
            "free_margin": 9550.0,
            "profit": 50.0,
            "leverage": 100
        }
    }
    """
    request_id = request.state.request_id
    
    # 获取凭证
    login = req.mt5_login
    password = req.mt5_password or ""
    server = req.mt5_server or ""
    
    use_live = TRADING_MODE == "live" and login and password and server
    
    if use_live:
        # 真实余额查询
        client = _get_mt5_client(login, password, server)
        if client is None:
            return BalanceResponse(
                mode="live",
                available=False,
                error="MT5 connection failed",
            )
        
        try:
            balance = client.get_balance()
            if balance is None:
                return BalanceResponse(
                    mode="live",
                    available=False,
                    error="Failed to get balance",
                )
            
            return BalanceResponse(
                mode="live",
                available=True,
                balance={
                    "balance": balance.balance,
                    "equity": balance.equity,
                    "margin": balance.margin,
                    "free_margin": balance.free_margin,
                    "profit": balance.profit,
                    "leverage": balance.leverage,
                },
            )
        except Exception as e:
            logger.error("get balance failed", error=str(e))
            return BalanceResponse(
                mode="live",
                available=False,
                error=str(e),
            )
    else:
        # 模拟余额
        return BalanceResponse(
            mode="mock",
            available=True,
            balance=_mock_balance.copy(),
        )


@app.post("/api/node/mock/reset")
def reset_mock_balance():
    """
    重置模拟账户余额
    
    请求体（可选）：
    {
        "balance": 10000.0
    }
    
    响应：
    {
        "status": "ok",
        "message": "Mock balance reset",
        "balance": {
            "balance": 10000.0,
            ...
        }
    }
    """
    global _mock_balance, _mock_positions
    _mock_balance = {
        "balance": 10000.0,
        "equity": 10000.0,
        "margin": 0.0,
        "free_margin": 10000.0,
        "profit": 0.0,
    }
    _mock_positions = {}
    
    logger.info("Mock balance reset")
    
    return {
        "status": "ok",
        "message": "Mock balance reset",
        "balance": _mock_balance.copy(),
    }


@app.get("/api/node/mock/balance")
def get_mock_balance():
    """
    查询模拟账户余额和持仓
    
    响应：
    {
        "mode": "mock",
        "balance": {...},
        "positions": [...]
    }
    """
    positions = list(_mock_positions.values())
    
    return {
        "mode": "mock",
        "balance": _mock_balance.copy(),
        "positions": positions,
    }
