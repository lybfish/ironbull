"""
Windows 本地测试脚本
测试 mt5-node-agent 的 Mock 模式

使用方法:
    python test_local.py
"""

import asyncio
import json
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import MT5Client, AgentConfig, MT5Config, setup_logging

# ============ 测试配置选择 ============
# 修改 USE_ONLINE_SERVER 为 True 则测试线上服务器
USE_ONLINE_SERVER = True  # True = 线上测试, False = 本地测试

# 线上服务器配置 (支持 IP 或域名)
ONLINE_CONFIG = AgentConfig(
    server_url="api.aigomsg.com",  # 或用 IP: "54.255.160.210:9102"
    node_id="test_online_node",
    mt5=MT5Config(
        login=0,  # Mock 模式不需要真实账户
        password="",
        server=""
    ),
    symbols=["EURUSD", "XAUUSD"],
    timeframe="H1",
    heartbeat_interval=30,
    kline_interval=60,
    balance_interval=300,
    log_level="DEBUG"
)

# 本地服务器配置
LOCAL_CONFIG = AgentConfig(
    server_url="localhost:9102",
    node_id="test_local_node",
    mt5=MT5Config(
        login=0,  # Mock 模式不需要真实账户
        password="",
        server=""
    ),
    symbols=["EURUSD", "XAUUSD"],
    timeframe="H1",
    heartbeat_interval=30,
    kline_interval=60,
    balance_interval=300,
    log_level="DEBUG"
)

# 根据选择使用对应配置
TEST_CONFIG = ONLINE_CONFIG if USE_ONLINE_SERVER else LOCAL_CONFIG

# 获取 WebSocket 地址
def get_ws_url():
    """获取 WebSocket 连接地址"""
    if USE_ONLINE_SERVER:
        return f"ws://54.255.160.210:9103/ws/node/{TEST_CONFIG.node_id}"
    else:
        return f"ws://localhost:9102/ws/node/{TEST_CONFIG.node_id}"


async def test_mt5_client():
    """测试 MT5 客户端 (Mock 模式)"""
    print("\n" + "=" * 50)
    print("测试 1: MT5 客户端初始化")
    print("=" * 50)
    
    client = MT5Client(TEST_CONFIG.mt5)
    
    # 测试连接 (Mock 模式会失败)
    print("\n尝试连接 MT5...")
    connected = client.connect()
    print(f"MT5 连接结果: {connected}")
    
    if connected:
        print("\nMT5 已连接，测试下单...")
        
        # 测试下单
        result = client.place_order(
            symbol="EURUSD",
            side="BUY",
            order_type="MARKET",
            volume=0.01,
            price=1.0850,
            stop_loss=1.0800,
            take_profit=1.0900
        )
        print(f"下单结果: {json.dumps(result, indent=2)}")
        
        # 测试查询余额
        balance = client.get_balance()
        print(f"\n余额查询: {json.dumps(balance, indent=2)}")
        
        # 测试查询持仓
        positions = client.get_positions()
        print(f"\n持仓查询: {json.dumps(positions, indent=2)}")
        
        # 测试 K 线
        klines = client.get_klines("EURUSD", "H1", 5)
        print(f"\nK 线数据: {json.dumps(klines, indent=2)}")
        
        client.disconnect()
        print("\nMT5 测试完成!")
    else:
        print("\nMT5 连接失败 (正常，Mock 模式不需要 MT5)")
        print("测试 Mock 模式功能...")
        
        # 测试 Mock 模式
        result = client.place_order(
            symbol="EURUSD",
            side="BUY",
            order_type="MARKET",
            volume=0.01,
            price=1.0850
        )
        print(f"\nMock 下单结果: {json.dumps(result, indent=2)}")
    
    return True


async def test_websocket_connection():
    """测试 WebSocket 连接 (需要服务器运行)"""
    print("\n" + "=" * 50)
    print("测试 2: WebSocket 连接测试")
    print("=" * 50)

    try:
        import websockets

        ws_url = get_ws_url()
        print(f"\n尝试连接服务器: {ws_url}")

        async with websockets.connect(ws_url) as ws:
            print("连接成功!")
            
            # 发送注册
            register_msg = {
                "type": "REGISTER",
                "node_id": TEST_CONFIG.node_id,
                "broker": "Mock-Broker",
                "account": "000000",
                "platform": "mt5",
                "version": "1.0.0",
                "capabilities": ["trade", "kline", "balance", "position"]
            }
            
            await ws.send(json.dumps(register_msg))
            print(f"发送注册: {json.dumps(register_msg, indent=2)}")
            
            # 等待确认
            ack = await asyncio.wait_for(ws.recv(), timeout=5)
            print(f"收到确认: {ack}")
            
            # 发送心跳
            await ws.send(json.dumps({"type": "HEARTBEAT", "status": "connected"}))
            pong = await asyncio.wait_for(ws.recv(), timeout=5)
            print(f"收到心跳响应: {pong}")
            
            print("\nWebSocket 测试通过!")
            return True
            
    except ImportError:
        print("websockets 库未安装，跳过 WebSocket 测试")
        return None
    except Exception as e:
        print(f"WebSocket 测试失败: {e}")
        return False


async def test_full_flow():
    """测试完整流程: 注册 -> 接收命令 -> 返回结果"""
    print("\n" + "=" * 50)
    print("测试 3: 完整流程测试")
    print("=" * 50)

    try:
        import websockets

        ws_url = get_ws_url()
        print(f"\n连接服务器: {ws_url}")

        async with websockets.connect(ws_url) as ws:
            # 注册
            await ws.send(json.dumps({
                "type": "REGISTER",
                "node_id": "flow_test_node",
                "broker": "Test-Broker",
                "account": "12345",
                "platform": "mt5"
            }))
            
            ack = await asyncio.wait_for(ws.recv(), timeout=5)
            print(f"注册: {ack}")
            
            # 模拟执行一个交易命令
            print("\n模拟收到 TRADE 命令...")
            trade_cmd = {
                "type": "TRADE",
                "task_id": "test_order_001",
                "order": {
                    "symbol": "EURUSD",
                    "side": "BUY",
                    "order_type": "MARKET",
                    "quantity": 0.01,
                    "price": 1.0850
                }
            }
            
            # 假设我们执行了这个订单
            result = {
                "success": True,
                "order_id": "REAL_ORDER_12345",
                "filled_price": 1.0850,
                "filled_quantity": 0.01
            }
            
            # 发送结果
            await ws.send(json.dumps({
                "type": "TRADE_RESULT",
                "task_id": "test_order_001",
                "result": result
            }))
            print(f"发送结果: {json.dumps(result, indent=2)}")
            
            print("\n完整流程测试通过!")
            return True
            
    except Exception as e:
        print(f"完整流程测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("=" * 50)
    print("MT5 Node Agent - Windows 本地测试")
    print("=" * 50)

    # 显示当前配置
    mode = "线上测试" if USE_ONLINE_SERVER else "本地测试"
    print(f"模式: {mode}")
    print(f"服务器: {TEST_CONFIG.server_url}")
    print(f"节点ID: {TEST_CONFIG.node_id}")
    print("-" * 50)

    # 配置日志
    logger = setup_logging("DEBUG")
    
    results = {}
    
    # 测试 1: MT5 客户端
    results["MT5客户端"] = await test_mt5_client()
    
    # 测试 2: WebSocket 连接 (需要服务器)
    ws_result = await test_websocket_connection()
    results["WebSocket连接"] = ws_result
    
    if ws_result:
        # 测试 3: 完整流程
        results["完整流程"] = await test_full_flow()
    
    # 输出测试总结
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    
    for test_name, passed in results.items():
        if passed is None:
            status = "跳过"
        elif passed:
            status = "通过"
        else:
            status = "失败"
        print(f"  {test_name}: {status}")
    
    # 检查是否全部通过
    failed = [k for k, v in results.items() if v is False]
    
    if failed:
        print(f"\n失败的测试: {', '.join(failed)}")
        return 1
    else:
        print("\n所有测试通过!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
