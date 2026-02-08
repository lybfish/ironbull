#!/usr/bin/env python3
"""
Gate 价格和手续费排查脚本

用法:
    PYTHONPATH=. python3 scripts/debug_gate_price_fee.py --symbol BTC/USDT
    PYTHONPATH=. python3 scripts/debug_gate_price_fee.py --symbol ETH/USDT --check-db
"""
import asyncio
import argparse
from libs.core.config import config
from libs.core.logger import get_logger
from libs.trading.live_trader import LiveTrader
from libs.core.database import get_db

log = get_logger("debug_gate")


async def test_gate_price_fetch():
    """测试 Gate 价格获取"""
    log.info("=== 测试 Gate 价格获取 ===")
    
    # 从配置读取 API 密钥
    api_key = config.get("exchange_api_key")
    api_secret = config.get("exchange_api_secret")
    
    if not api_key or not api_secret:
        log.error("未配置 exchange_api_key 或 exchange_api_secret")
        return
    
    trader = LiveTrader(
        exchange="gate",  # 会自动转为 gateio
        api_key=api_key,
        api_secret=api_secret,
        market_type="future",
        sandbox=False,
    )
    
    try:
        # 1. 测试加载市场
        log.info("1. 加载市场信息...")
        await trader.exchange.load_markets()
        log.info(f"市场加载成功，共 {len(trader.exchange.markets)} 个交易对")
        
        # 2. 测试获取 ticker
        symbol = "BTC/USDT:USDT"
        log.info(f"2. 获取 {symbol} ticker...")
        ticker = await trader.exchange.fetch_ticker(symbol)
        log.info(f"Ticker 数据: {ticker}")
        log.info(f"  - last: {ticker.get('last')}")
        log.info(f"  - bid: {ticker.get('bid')}")
        log.info(f"  - ask: {ticker.get('ask')}")
        log.info(f"  - average: {ticker.get('average')}")
        
        # 3. 测试获取余额
        log.info("3. 获取账户余额...")
        balance = await trader.get_balance()
        log.info(f"余额: {balance}")
        
        # 4. 测试获取持仓
        log.info("4. 获取持仓...")
        positions = await trader.get_positions()
        log.info(f"持仓数量: {len(positions)}")
        for pos in positions[:3]:  # 只显示前3个
            log.info(f"  - {pos}")
        
        # 5. 测试小额下单（如果有余额）
        if balance.get("USDT", {}).get("free", 0) > 10:
            log.info("5. 测试小额市价单...")
            log.info("  (跳过实际下单，避免真实交易)")
            # 可以取消注释测试真实下单
            # result = await trader.create_order(
            #     symbol="BTC/USDT",
            #     side=OrderSide.BUY,
            #     order_type=OrderType.MARKET,
            #     quantity=0.001,
            #     amount_usdt=10,
            # )
            # log.info(f"订单结果: {result}")
        
    except Exception as e:
        log.error(f"测试失败: {e}", exc_info=True)
    finally:
        await trader.close()


async def check_db_orders():
    """检查数据库中的订单价格和手续费"""
    log.info("=== 检查数据库订单 ===")
    
    with get_db() as session:
        from libs.order_trade.models import Order, Fill
        
        # 检查最近 10 个订单
        orders = session.query(Order).order_by(Order.created_at.desc()).limit(10).all()
        log.info(f"最近 10 个订单:")
        for order in orders:
            log.info(f"  订单 {order.order_id}:")
            log.info(f"    - symbol: {order.symbol}")
            log.info(f"    - side: {order.side}")
            log.info(f"    - status: {order.status}")
            log.info(f"    - filled_quantity: {order.filled_quantity}")
            log.info(f"    - filled_price: {order.filled_price}")
            log.info(f"    - commission: {order.commission}")
            log.info(f"    - commission_asset: {order.commission_asset}")
        
        # 检查最近 10 个成交
        fills = session.query(Fill).order_by(Fill.created_at.desc()).limit(10).all()
        log.info(f"\n最近 10 个成交:")
        for fill in fills:
            log.info(f"  成交 {fill.fill_id}:")
            log.info(f"    - symbol: {fill.symbol}")
            log.info(f"    - side: {fill.side}")
            log.info(f"    - price: {fill.price}")
            log.info(f"    - quantity: {fill.quantity}")
            log.info(f"    - commission: {fill.commission}")
            log.info(f"    - commission_asset: {fill.commission_asset}")


async def test_gate_order_response_parsing():
    """测试 Gate 订单响应解析"""
    log.info("=== 测试 Gate 订单响应解析 ===")
    
    # 模拟 Gate 返回的订单响应
    mock_responses = [
        {
            "name": "完整手续费",
            "response": {
                "id": "123456",
                "status": "closed",
                "filled": 0.001,
                "average": 50000.0,
                "price": 50000.0,
                "fee": {
                    "cost": 0.025,
                    "currency": "USDT"
                }
            }
        },
        {
            "name": "info 中的手续费",
            "response": {
                "id": "123457",
                "status": "closed",
                "filled": 0.001,
                "average": 50000.0,
                "info": {
                    "commission": "0.025",
                    "commissionAsset": "USDT"
                }
            }
        },
        {
            "name": "无手续费",
            "response": {
                "id": "123458",
                "status": "closed",
                "filled": 0.001,
                "average": 50000.0,
            }
        },
        {
            "name": "fees 数组",
            "response": {
                "id": "123459",
                "status": "closed",
                "filled": 0.001,
                "average": 50000.0,
                "fees": [
                    {"cost": 0.01, "currency": "USDT"},
                    {"cost": 0.015, "currency": "USDT"}
                ]
            }
        }
    ]
    
    from libs.trading.live_trader import LiveTrader
    from libs.contracts import OrderSide, OrderType
    
    trader = LiveTrader(
        exchange="gate",
        api_key="dummy",
        api_secret="dummy",
        market_type="future",
        sandbox=True,
    )
    
    for test_case in mock_responses:
        log.info(f"\n测试用例: {test_case['name']}")
        result = trader._parse_order_response(
            order_id="test_order",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.001,
            price=50000.0,
            response=test_case["response"]
        )
        log.info(f"  解析结果:")
        log.info(f"    - filled_price: {result.filled_price}")
        log.info(f"    - commission: {result.commission}")
        log.info(f"    - commission_asset: {result.commission_asset}")


def main():
    parser = argparse.ArgumentParser(description="Gate 价格和手续费排查")
    parser.add_argument("--symbol", type=str, default="BTC/USDT", help="交易对")
    parser.add_argument("--check-db", action="store_true", help="检查数据库")
    parser.add_argument("--test-parsing", action="store_true", help="测试响应解析")
    args = parser.parse_args()
    
    if args.test_parsing:
        asyncio.run(test_gate_order_response_parsing())
    elif args.check_db:
        asyncio.run(check_db_orders())
    else:
        asyncio.run(test_gate_price_fetch())


if __name__ == "__main__":
    main()
