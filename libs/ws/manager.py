"""
WebSocket Connection Manager

管理 WebSocket 连接和消息广播
"""

import asyncio
import json
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

from libs.core import get_logger, gen_id

logger = get_logger("ws-manager")


@dataclass
class Client:
    """WebSocket 客户端"""
    client_id: str
    websocket: WebSocket
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.now)
    last_ping: datetime = field(default_factory=datetime.now)


class ConnectionManager:
    """
    WebSocket 连接管理器
    
    功能：
    - 管理客户端连接
    - 订阅/取消订阅频道
    - 广播消息到频道
    
    使用示例：
        manager = ConnectionManager()
        
        # 接受连接
        await manager.connect(websocket)
        
        # 订阅
        manager.subscribe(client_id, "ticker:BTC/USDT")
        
        # 广播
        await manager.broadcast("ticker:BTC/USDT", {"price": 98000})
    """
    
    def __init__(self):
        # client_id -> Client
        self.clients: Dict[str, Client] = {}
        # channel -> set of client_ids
        self.channels: Dict[str, Set[str]] = {}
        # websocket -> client_id (反向映射)
        self._ws_to_client: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket) -> str:
        """
        接受 WebSocket 连接
        
        Returns:
            client_id
        """
        await websocket.accept()
        
        client_id = gen_id("ws_")
        client = Client(
            client_id=client_id,
            websocket=websocket,
        )
        
        self.clients[client_id] = client
        self._ws_to_client[websocket] = client_id
        
        logger.info("client connected", client_id=client_id)
        
        # 发送欢迎消息
        await self.send_to_client(client_id, {
            "type": "connected",
            "client_id": client_id,
            "message": "Welcome to IronBull WebSocket",
        })
        
        return client_id
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        client_id = self._ws_to_client.get(websocket)
        if not client_id:
            return
        
        client = self.clients.get(client_id)
        if client:
            # 从所有频道移除
            for channel in list(client.subscriptions):
                self.unsubscribe(client_id, channel)
            
            del self.clients[client_id]
        
        del self._ws_to_client[websocket]
        
        logger.info("client disconnected", client_id=client_id)
    
    def subscribe(self, client_id: str, channel: str) -> bool:
        """
        订阅频道
        
        Args:
            client_id: 客户端 ID
            channel: 频道名称 (如 ticker:BTC/USDT)
        """
        client = self.clients.get(client_id)
        if not client:
            return False
        
        # 添加到客户端订阅列表
        client.subscriptions.add(channel)
        
        # 添加到频道
        if channel not in self.channels:
            self.channels[channel] = set()
        self.channels[channel].add(client_id)
        
        logger.debug("client subscribed", client_id=client_id, channel=channel)
        return True
    
    def unsubscribe(self, client_id: str, channel: str) -> bool:
        """取消订阅"""
        client = self.clients.get(client_id)
        if not client:
            return False
        
        client.subscriptions.discard(channel)
        
        if channel in self.channels:
            self.channels[channel].discard(client_id)
            if not self.channels[channel]:
                del self.channels[channel]
        
        logger.debug("client unsubscribed", client_id=client_id, channel=channel)
        return True
    
    async def send_to_client(self, client_id: str, data: dict):
        """发送消息到指定客户端"""
        client = self.clients.get(client_id)
        if not client:
            return
        
        try:
            await client.websocket.send_json(data)
        except Exception as e:
            logger.warning("send failed", client_id=client_id, error=str(e))
    
    async def broadcast(self, channel: str, data: dict):
        """
        广播消息到频道
        
        Args:
            channel: 频道名称
            data: 消息数据
        """
        client_ids = self.channels.get(channel, set())
        if not client_ids:
            return
        
        # 添加频道信息
        message = {"channel": channel, **data}
        
        # 并发发送
        tasks = []
        for client_id in list(client_ids):
            client = self.clients.get(client_id)
            if client:
                tasks.append(self._safe_send(client, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_all(self, data: dict):
        """广播到所有客户端"""
        tasks = []
        for client in self.clients.values():
            tasks.append(self._safe_send(client, data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_send(self, client: Client, data: dict):
        """安全发送（捕获异常）"""
        try:
            await client.websocket.send_json(data)
        except Exception:
            pass
    
    def get_client_id(self, websocket: WebSocket) -> Optional[str]:
        """获取 WebSocket 对应的 client_id"""
        return self._ws_to_client.get(websocket)
    
    def get_subscribed_channels(self, client_id: str) -> Set[str]:
        """获取客户端订阅的频道"""
        client = self.clients.get(client_id)
        return client.subscriptions.copy() if client else set()
    
    def get_channel_subscribers(self, channel: str) -> int:
        """获取频道订阅者数量"""
        return len(self.channels.get(channel, set()))
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_clients": len(self.clients),
            "total_channels": len(self.channels),
            "channels": {
                ch: len(subs) for ch, subs in self.channels.items()
            },
        }


# 单例
_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """获取连接管理器实例"""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
