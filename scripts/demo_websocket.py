#!/usr/bin/env python3
"""
v1 Phase 7: WebSocket 实时行情演示脚本

演示如何连接 WebSocket 并订阅实时行情
"""

import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("请先安装 websockets: pip3 install websockets")
    sys.exit(1)


WS_URL = "ws://127.0.0.1:8010/ws"


async def demo():
    print("=" * 50)
    print("v1 Phase 7: WebSocket 实时行情 Demo")
    print("=" * 50)
    print()
    
    print(f"连接到: {WS_URL}")
    print()
    
    try:
        async with websockets.connect(WS_URL) as ws:
            # 接收欢迎消息
            welcome = await ws.recv()
            welcome_data = json.loads(welcome)
            print(f"✅ 已连接: {welcome_data}")
            print()
            
            # 订阅 BTC/USDT
            print(">>> 订阅 BTC/USDT")
            await ws.send(json.dumps({
                "action": "subscribe",
                "symbol": "BTC/USDT"
            }))
            
            # 等待订阅确认
            sub_response = await ws.recv()
            print(f"<<< {json.loads(sub_response)}")
            print()
            
            # 订阅 ETH/USDT
            print(">>> 订阅 ETH/USDT")
            await ws.send(json.dumps({
                "action": "subscribe",
                "symbol": "ETH/USDT"
            }))
            
            sub_response2 = await ws.recv()
            print(f"<<< {json.loads(sub_response2)}")
            print()
            
            # 查询订阅列表
            print(">>> 查询订阅列表")
            await ws.send(json.dumps({"action": "list"}))
            
            list_response = await ws.recv()
            print(f"<<< {json.loads(list_response)}")
            print()
            
            # 接收实时行情
            print("等待实时行情推送 (按 Ctrl+C 退出)...")
            print("-" * 50)
            
            count = 0
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    data = json.loads(msg)
                    
                    if data.get("type") == "ticker":
                        count += 1
                        symbol = data.get("symbol", "")
                        last = data.get("last", 0)
                        change_pct = data.get("change_pct_24h", 0)
                        
                        # 格式化显示
                        arrow = "↑" if change_pct > 0 else "↓" if change_pct < 0 else "→"
                        print(f"[{count:4d}] {symbol:12s} 价格: {last:12.2f}  变化: {arrow} {change_pct:+.4f}%")
                    else:
                        print(f"<<< {data}")
                        
                except asyncio.TimeoutError:
                    print("... 等待数据中 ...")
                    
    except websockets.exceptions.ConnectionClosed as e:
        print(f"连接关闭: {e}")
    except ConnectionRefusedError:
        print("❌ 连接失败: data-provider 服务未运行")
        print("请先启动: cd ironbull && python3 -m uvicorn services.data-provider.app.main:app --port 8010")
    except KeyboardInterrupt:
        print("\n\n已停止")


if __name__ == "__main__":
    print()
    asyncio.run(demo())
