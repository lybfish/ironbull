# SMC Fibo Flex 策略使用文档

## 概述

SMC Fibo Flex 是一个全新的、独立的 SMC Fibonacci 策略，实现了完整参数文档中的所有功能，适用于外汇和加密货币市场。

## 策略特点

- **完全独立**：不依赖任何旧版策略代码
- **参数灵活**：所有参数都有默认值，可以完全省略或部分配置
- **模块化设计**：功能模块独立，便于维护和扩展
- **完整功能**：实现文档中所有参数（Old1对齐、回踩确认、流动性、OB/FVG、外汇理论、风险管理等）

## 快速开始

### 基本使用

```python
from libs.strategies import get_strategy

# 使用默认配置
strategy = get_strategy("smc_fibo_flex", {})

# 使用自定义配置
config = {
    "max_loss": 100,
    "min_rr": 2.0,
    "fibo_levels": [0.5, 0.618, 0.705],
}
strategy = get_strategy("smc_fibo_flex", config)
```

### 使用预设模板

```python
# 使用保守预设
config = {
    "preset_profile": "conservative"
}
strategy = get_strategy("smc_fibo_flex", config)

# 使用外汇专用预设
config = {
    "preset_profile": "forex_specific"
}
strategy = get_strategy("smc_fibo_flex", config)
```

## 参数说明

完整参数列表请参考：[SMC_FIBO_COMPLETE_PARAMS.md](../SMC_FIBO_COMPLETE_PARAMS.md)

### 核心参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_loss` | float | 100 | 每单最大亏损（USDT） |
| `min_rr` | float | 2.0 | 最小盈亏比 |
| `fibo_levels` | list | [0.5, 0.618, 0.705] | 斐波那契回撤位 |
| `structure` | str | "both" | 结构过滤：bos/choch/both |
| `bias` | str | "with_trend" | 趋势偏好：with_trend/counter/both |
| `require_retest` | bool | True | 是否要求回踩确认 |
| `preset_profile` | str | "none" | 预设模板：none/conservative/balanced/aggressive/forex_specific |

## 预设配置

策略提供四套预设配置：

1. **conservative**（保守）：低风险，高RR要求，严格过滤
2. **balanced**（中等）：平衡风险和收益
3. **aggressive**（激进）：高风险高收益，宽松过滤
4. **forex_specific**（外汇专用）：针对外汇市场优化，包含时区/新闻过滤

预设配置示例文件位于：`libs/strategies/smc_fibo_flex/examples/`

## 回测使用

```python
from services.backtest.app.backtest_engine import BacktestEngine

engine = BacktestEngine(
    initial_balance=10000,
    commission_rate=0.001,
    risk_per_trade=100,
)

strategy = get_strategy("smc_fibo_flex", {
    "max_loss": 100,
    "min_rr": 2.0,
})

result = engine.run(
    strategy=strategy,
    symbol="BTCUSDT",
    timeframe="1h",
    candles=candles,
    lookback=50,
)
```

## 信号监控使用

策略已自动注册到信号监控系统，可以在数据库中配置使用：

```sql
INSERT INTO dim_strategy (code, name, config) VALUES (
    'smc_fibo_flex',
    'SMC斐波那契灵活策略',
    '{"max_loss": 100, "min_rr": 2.0, "preset_profile": "balanced"}'::jsonb
);
```

## 参数验证

所有参数都会自动验证和标准化：

- 类型验证（float/int/bool/str/list）
- 范围验证（参考文档第12章）
- 枚举值验证（structure/bias/tp_mode等）
- camelCase / snake_case 兼容转换
- 默认值回退（优先Old1默认值）

## 注意事项

1. 策略需要至少50根K线才能开始分析
2. 回踩确认模式下，信号会延迟产生（等待确认）
3. 所有价格精度保留5位小数
4. 参数验证失败时会使用安全默认值

## 参考文档

- [完整参数文档](../SMC_FIBO_COMPLETE_PARAMS.md)
- [策略基类接口](../../libs/strategies/base.py)
- [策略输出格式](../../libs/contracts/strategy_output.py)
