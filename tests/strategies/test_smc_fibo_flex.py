"""
SMC Fibo Flex 策略测试

单元测试和集成测试
"""

import unittest
from typing import List, Dict
from libs.strategies import get_strategy
from libs.contracts import StrategyOutput


class TestSMCFiboFlex(unittest.TestCase):
    """SMC Fibo Flex 策略测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.strategy = get_strategy("smc_fibo_flex", {})
    
    def test_strategy_load(self):
        """测试策略加载"""
        self.assertEqual(self.strategy.code, "smc_fibo_flex")
        self.assertEqual(self.strategy.name, "SMC斐波那契灵活策略")
    
    def test_preset_configs(self):
        """测试预设配置"""
        presets = ["conservative", "balanced", "aggressive", "forex_specific"]
        for preset in presets:
            strategy = get_strategy("smc_fibo_flex", {"preset_profile": preset})
            self.assertIsNotNone(strategy)
            self.assertEqual(strategy.code, "smc_fibo_flex")
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = {
            "max_loss": 100,
            "min_rr": 2.0,
            "fibo_levels": [0.5, 0.618, 0.705],
            "structure": "both",
            "bias": "with_trend",
        }
        strategy = get_strategy("smc_fibo_flex", config)
        self.assertIsNotNone(strategy)
        self.assertEqual(strategy.config["max_loss"], 100)
        self.assertEqual(strategy.config["min_rr"], 2.0)
    
    def test_analyze_with_insufficient_data(self):
        """测试数据不足的情况"""
        candles = [
            {"open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000, "timestamp": 1000 + i}
            for i in range(30)  # 少于50根K线
        ]
        result = self.strategy.analyze("BTCUSDT", "1h", candles)
        self.assertIsNone(result)
    
    def test_analyze_with_sufficient_data(self):
        """测试数据充足的情况（可能无信号）"""
        candles = [
            {
                "open": 100 + i * 0.1,
                "high": 105 + i * 0.1,
                "low": 95 + i * 0.1,
                "close": 102 + i * 0.1,
                "volume": 1000,
                "timestamp": 1000 + i * 3600
            }
            for i in range(100)
        ]
        result = self.strategy.analyze("BTCUSDT", "1h", candles)
        # 可能返回信号或None（取决于市场条件）
        if result:
            self.assertIsInstance(result, StrategyOutput)
            self.assertIn(result.side, ["BUY", "SELL"])
            self.assertIsNotNone(result.entry_price)
            self.assertIsNotNone(result.stop_loss)
            self.assertIsNotNone(result.take_profit)


if __name__ == "__main__":
    unittest.main()
