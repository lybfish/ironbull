#!/usr/bin/env python3
"""
测试 Gate 价格和手续费修复

用法:
    PYTHONPATH=. python3 scripts/test_gate_price_fee_fix.py
"""
from libs.trading.live_trader import LiveTrader
from libs.trading.order_result import OrderSide, OrderType


def test_parse_order_response():
    """测试订单响应解析（包含 Gate 特殊格式）"""
    print("=== 测试订单响应解析 ===\n")
    
    trader = LiveTrader(
        exchange="gate",
        api_key="dummy",
        api_secret="dummy",
        market_type="future",
        sandbox=True,
    )
    
    test_cases = [
        {
            "name": "标准格式（Binance 风格）",
            "response": {
                "id": "123456",
                "status": "closed",
                "filled": 0.001,
                "average": 50000.0,
                "fee": {
                    "cost": 0.025,
                    "currency": "USDT"
                }
            },
            "expected": {
                "filled_price": 50000.0,
                "commission": 0.025,
                "commission_asset": "USDT"
            }
        },
        {
            "name": "Gate 格式（info 中的价格和手续费）",
            "response": {
                "id": "123457",
                "status": "closed",
                "filled": 0.001,
                "info": {
                    "avgPrice": "50123.5",
                    "fill_fee": "0.025",
                    "fee_currency": "USDT"
                }
            },
            "expected": {
                "filled_price": 50123.5,
                "commission": 0.025,
                "commission_asset": "USDT"
            }
        },
        {
            "name": "Gate 格式 2（taker_fee）",
            "response": {
                "id": "123458",
                "status": "closed",
                "filled": 0.001,
                "price": 50000.0,
                "info": {
                    "taker_fee": "0.03",
                    "fee_currency": "USDT"
                }
            },
            "expected": {
                "filled_price": 50000.0,
                "commission": 0.03,
                "commission_asset": "USDT"
            }
        },
        {
            "name": "Gate 格式 3（avg_price + maker_fee）",
            "response": {
                "id": "123459",
                "status": "closed",
                "filled": 0.001,
                "info": {
                    "avg_price": "49999.5",
                    "maker_fee": "0.02"
                }
            },
            "expected": {
                "filled_price": 49999.5,
                "commission": 0.02,
                "commission_asset": ""
            }
        },
        {
            "name": "fees 数组格式",
            "response": {
                "id": "123460",
                "status": "closed",
                "filled": 0.001,
                "average": 50000.0,
                "fees": [
                    {"cost": 0.01, "currency": "USDT"},
                    {"cost": 0.015, "currency": "USDT"}
                ]
            },
            "expected": {
                "filled_price": 50000.0,
                "commission": 0.025,
                "commission_asset": "USDT"
            }
        },
        {
            "name": "无价格无手续费（应该为 0）",
            "response": {
                "id": "123461",
                "status": "closed",
                "filled": 0.001,
            },
            "expected": {
                "filled_price": 0,
                "commission": 0,
                "commission_asset": ""
            }
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"测试 {i}: {test_case['name']}")
        
        result = trader._parse_order_response(
            order_id="test_order",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.001,
            price=50000.0,
            response=test_case["response"]
        )
        
        expected = test_case["expected"]
        
        # 验证结果
        checks = []
        
        # 检查价格
        price_ok = abs(result.filled_price - expected["filled_price"]) < 0.01
        checks.append(("价格", price_ok, result.filled_price, expected["filled_price"]))
        
        # 检查手续费
        commission_ok = abs(result.commission - expected["commission"]) < 0.001
        checks.append(("手续费", commission_ok, result.commission, expected["commission"]))
        
        # 检查手续费币种
        asset_ok = result.commission_asset == expected["commission_asset"]
        checks.append(("手续费币种", asset_ok, result.commission_asset, expected["commission_asset"]))
        
        # 打印结果
        all_ok = all(c[1] for c in checks)
        status = "✅ 通过" if all_ok else "❌ 失败"
        print(f"  {status}")
        
        for name, ok, actual, expected_val in checks:
            if not ok:
                print(f"    {name}: 期望 {expected_val}, 实际 {actual}")
        
        if all_ok:
            passed += 1
        else:
            failed += 1
        
        print()
    
    print(f"=== 测试结果 ===")
    print(f"通过: {passed}/{len(test_cases)}")
    print(f"失败: {failed}/{len(test_cases)}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！Gate 价格和手续费解析已修复。")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查代码。")
        return False


if __name__ == "__main__":
    success = test_parse_order_response()
    exit(0 if success else 1)
