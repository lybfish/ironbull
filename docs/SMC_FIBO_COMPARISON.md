# SMC 斐波那契策略对比分析：old1 vs 当前实现

## 📋 概述

本文档对比分析 old1 中的 SMC 斐波那契回测实现与当前系统的实现差异。

## 🏗️ 架构差异

### old1 架构
- **完整的回测引擎**：`backtest_engine.py` 包含完整的订单管理、成交、持仓、权益计算
- **数据库存储**：回测结果存储在 MySQL 表中（`backtest_runs`, `backtest_orders`, `backtest_fills`, `backtest_trades`, `backtest_equity`）
- **信号快照**：支持将K线数据快照存储在 `trade_signals.params_json.snapshot` 中
- **独立脚本**：`test_smc_backtest.py` 作为独立的回测脚本

### 当前架构
- **策略分析器**：`libs/strategies/smc_fibo.py` 只负责生成交易信号
- **独立回测引擎**：`services/backtest/app/backtest_engine.py` 负责执行回测
- **信号驱动**：策略返回 `StrategyOutput`，由回测引擎处理

## 🔍 核心逻辑差异

### 1. 斐波那契回撤计算

#### old1 实现
```python
# 从摆动高低点计算斐波那契回撤位
swing_range = swing_high["price"] - swing_low["price"]
if side == "BUY":
    entry = swing_high["price"] - swing_range * level  # 从高点回撤
    base_stop = swing_low["price"] * (1 - stop_buffer_pct)
    tp = swing_high["price"]  # 止盈回到高点
else:
    entry = swing_low["price"] + swing_range * level  # 从低点反弹
    base_stop = swing_high["price"] * (1 + stop_buffer_pct)
    tp = swing_low["price"]  # 止盈回到低点
```

#### 当前实现
```python
# 做多：从高点回撤到低点
fibo_dict = fibo_levels(recent_high, recent_low, self.fibo_entry_levels)
# 做空：从低点反弹到高点
fibo_dict = {}
for level in self.fibo_entry_levels:
    fibo_dict[level] = recent_low + swing_range * level
```

**差异**：
- old1 的止盈目标更明确（回到摆动高点/低点）
- 当前实现使用斐波那契扩展位作为止盈（1.272, 1.618）

### 2. 斐波那契 Fallback 机制

#### old1 实现
```python
fibo_side_fallback = False
if fibo_mode and fibo_fallback and not side:
    trend_base = htf_trend or trend
    if trend_base == "bull":
        side = "BUY"
        fibo_side_fallback = True
    elif trend_base == "bear":
        side = "SELL"
        fibo_side_fallback = True

# 使用 fallback 时，额外检查价格位置
if fibo_side_fallback:
    if side == "BUY" and bar["l"] > mid_price:
        continue  # 价格太高，跳过
    if side == "SELL" and bar["h"] < mid_price:
        continue  # 价格太低，跳过
```

#### 当前实现
**❌ 缺失**：当前实现没有 `fibo_fallback` 机制

**影响**：当无法通过订单块/结构确定方向时，old1 可以根据趋势自动确定方向，当前实现会直接跳过。

### 3. 回踩拒绝确认（Retest）

#### old1 实现
```python
def detect_rejection(
    bar, prev, prev2, side, zone_low, zone_high,
    include_stars, allow_engulf, pinbar_ratio
) -> dict:
    # 检测多种拒绝形态：
    # 1. close_reject: 收盘价拒绝（价格触达区间后收盘在区间外）
    # 2. pinbar: Pin Bar 形态（影线/实体比 >= pinbar_ratio）
    # 3. engulf: 吞没形态
    # 4. morning_star: 晨星（做多）
    # 5. evening_star: 暮星（做空）
```

#### 当前实现
```python
def _detect_rejection(self, current, prev, prev2, side, zone_low, zone_high):
    # 实现了相同的拒绝形态检测逻辑
    # 包括：close_reject, pinbar, engulf, morning_star, evening_star
```

**差异**：
- ✅ 逻辑基本一致
- ⚠️ old1 的 `pinbar_ratio` 默认值是 2.0，当前实现默认是 1.5

### 4. 订单管理

#### old1 实现
```python
# 完整的订单生命周期管理
pending_orders: list[dict] = []  # 待成交订单
orders: list[dict] = []          # 所有订单记录
fills: list[dict] = []           # 成交记录
trades: list[dict] = []          # 完整交易记录

# 支持限价单和市价单
# 支持订单有效期（TIF - Time In Force）
tif_bars = max(1, int(params.get("tif_bars", 20) or 20))
```

#### 当前实现
**❌ 缺失**：策略层不管理订单，只生成信号
- 回测引擎直接根据信号开仓
- 不支持限价单、订单有效期等概念

### 5. 止损止盈计算

#### old1 实现
```python
# 支持多种止损来源
stop_source = (smc.get("stopSource") or "auto").lower()

def pick_stop(side, base_stop, entry):
    if stop_source == "auto":
        # 自动选择：订单块外侧 vs 摆动点外侧
        ...
    elif stop_source == "ob":
        # 仅使用订单块
        ...
    elif stop_source == "swing":
        # 仅使用摆动点
        ...

# 支持多种止盈模式
tp_mode = (smc.get("tpMode") or "swing").lower()
# "swing": 回到摆动点
# "rr": 固定盈亏比
# "fibo": 斐波那契扩展位
```

#### 当前实现
```python
# 止损：优先使用订单块，fallback 到摆动点
if supporting_ob:
    stop_loss = supporting_ob.low * (1 - self.sl_buffer_pct)
else:
    stop_loss = recent_low * (1 - self.sl_buffer_pct)

# 止盈：使用斐波那契扩展位
extension = fibo_extension(recent_high, recent_low, [1.272, 1.618])
take_profit = extension.get(1.272, recent_high + sl_distance * self.min_rr)
```

**差异**：
- old1 支持更灵活的止损止盈配置
- 当前实现逻辑更简单，但灵活性较低

### 6. 多时间框架（HTF）

#### old1 实现
```python
# 使用独立的 HTF K线数据
htf_candles: list[dict] = None  # 从外部传入

# HTF 摆动点识别
htf_swing = max(1, int(htf_swing_raw or 3))
htf_swing_highs, htf_swing_lows = find_swing_points(htf_candles, htf_swing)

# HTF 趋势判断
htf_trend = determine_trend(htf_candles, htf_swing_highs, htf_swing_lows)
```

#### 当前实现
```python
# 通过聚合小周期K线模拟大周期
def _aggregate_to_htf(self, candles: List[Dict]) -> List[Dict]:
    # 将 n 根小周期K线聚合成1根大周期K线
    ...

# 使用 EMA 判断大周期趋势
def _get_htf_trend(self, candles: List[Dict]) -> str:
    # 计算大周期 EMA，判断趋势方向
    ...
```

**差异**：
- old1 使用真实的 HTF K线数据（更准确）
- 当前实现通过聚合模拟（可能不够精确）

### 7. 参数配置

#### old1 参数（更丰富）
```python
smc = {
    "fiboLevels": [0.5, 0.618, 0.705],      # 斐波那契回撤位
    "retestBars": 20,                        # 回踩等待K线数
    "minRr": 2,                             # 最小盈亏比
    "pinbarRatio": 1.5,                      # Pin Bar 比例
    "allowEngulf": True,                     # 允许吞没形态
    "stopBufferPct": 0.05,                  # 止损缓冲百分比
    "stopSource": "auto",                    # 止损来源：auto/ob/swing
    "tpMode": "swing",                       # 止盈模式：swing/rr/fibo
    "bias": "with_trend",                    # 交易偏向：with_trend/counter
    "structure": "both",                     # 结构类型：both/bull/bear
    "entry": "auto",                         # 入场来源：auto/ob/fvg
    "session": "all",                        # 交易时段：all/london/ny/asian
    "htfTimeframe": "1h",                    # 大周期时间框架
    "fiboFallback": True,                    # 斐波那契 fallback
    "retestIgnoreStopTouch": False,          # 回踩期间忽略止损触及
}
```

#### 当前实现参数
```python
config = {
    "max_loss": 100,                         # 每单最大亏损
    "min_rr": 1.5,                           # 最小盈亏比
    "fibo_levels": [0.382, 0.5, 0.618],     # 斐波那契回撤位
    "fibo_tolerance": 0.005,                 # 回撤位容差
    "lookback": 50,                          # 回看周期
    "swing_left": 5,                         # 摆动点左侧K线数
    "swing_right": 3,                        # 摆动点右侧K线数
    "ob_min_body_ratio": 0.5,               # 订单块最小实体比例
    "sl_buffer_pct": 0.002,                  # 止损缓冲
    "htf_multiplier": 4,                     # 大周期倍数
    "htf_ema_fast": 20,                      # 大周期快EMA
    "htf_ema_slow": 50,                      # 大周期慢EMA
    "require_htf_filter": True,              # 是否强制大周期过滤
    "require_retest": True,                   # 是否要求回踩确认
    "retest_bars": 20,                       # 回踩等待K线数
    "pinbar_ratio": 1.5,                     # Pin Bar 比例
    "allow_engulf": True,                    # 允许吞没形态
    "retest_ignore_stop_touch": False,       # 回踩期间忽略止损触及
}
```

**差异**：
- old1 参数更丰富，支持更多配置选项
- 当前实现参数更简洁，但缺少一些高级功能

## 📊 数据库表结构差异

### old1 表结构
```sql
-- 回测运行记录
backtest_runs (run_id, strategy_name, params_json, symbol, timeframe, ...)

-- 回测指标
backtest_metrics (run_id, total_return, mdd, trades, win_rate)

-- 订单记录
backtest_orders (run_id, i, ts, side, price, tif, status)

-- 成交记录
backtest_fills (run_id, i, ts, side, price, fee, spread)

-- 交易记录
backtest_trades (run_id, i, ts, side, entry, stop, tp, qty, pnl, reason)

-- 权益曲线
backtest_equity (run_id, i, equity)

-- 信号记录（带快照）
trade_signals (id, symbol, timeframe, params_json, snapshot, ...)
```

### 当前系统表结构
```sql
-- 策略配置
dim_strategy (code, name, config_json, ...)

-- 订单记录（实盘）
fact_order (order_id, symbol, side, quantity, price, status, ...)

-- 成交记录（实盘）
fact_fill (fill_id, order_id, quantity, price, fee, ...)

-- 持仓记录（实盘）
fact_position (position_id, symbol, quantity, entry_price, ...)

-- 资金记录（实盘）
fact_ledger (ledger_id, account_id, balance, ...)
```

**差异**：
- old1 有专门的回测结果存储表
- 当前系统只有实盘交易表，回测结果不持久化

## 🎯 关键功能缺失对比

### old1 有，当前实现缺失的功能

1. **斐波那契 Fallback 机制** ⚠️
   - 当无法确定方向时，根据趋势自动确定方向

2. **灵活的止损止盈配置** ⚠️
   - `stopSource`: auto/ob/swing
   - `tpMode`: swing/rr/fibo

3. **订单有效期（TIF）** ❌
   - 支持限价单在 N 根K线后自动取消

4. **交易时段过滤** ❌
   - 支持按交易时段（伦敦/纽约/亚洲）过滤信号

5. **回测结果持久化** ❌
   - 回测结果不存储到数据库

6. **信号快照机制** ❌
   - 无法保存信号生成时的K线快照

### 当前实现有，old1 没有的功能

1. **以损定仓** ✅
   - 根据固定亏损金额计算仓位

2. **多时间框架聚合** ✅
   - 通过聚合小周期K线模拟大周期（无需额外数据）

3. **策略基类统一接口** ✅
   - 所有策略继承 `StrategyBase`，接口统一

## 🔧 建议改进

### 高优先级

1. **实现斐波那契 Fallback 机制**
   ```python
   # 在 smc_fibo.py 中添加
   fibo_fallback = self.config.get("fibo_fallback", True)
   if fibo_fallback and not side:
       htf_trend = self._get_htf_trend(candles)
       if htf_trend == "bullish":
           side = "BUY"
       elif htf_trend == "bearish":
           side = "SELL"
   ```

2. **增强止损止盈配置**
   ```python
   stop_source = self.config.get("stop_source", "auto")  # auto/ob/swing
   tp_mode = self.config.get("tp_mode", "fibo")          # swing/rr/fibo
   ```

3. **调整 Pin Bar 默认比例**
   ```python
   # 与 old1 保持一致
   self.pinbar_ratio = self.config.get("pinbar_ratio", 2.0)  # 从 1.5 改为 2.0
   ```

### 中优先级

4. **支持订单有效期（TIF）**
   - 在回测引擎中实现限价单超时取消

5. **回测结果持久化**
   - 创建回测结果存储表
   - 支持回测历史查询和对比

### 低优先级

6. **交易时段过滤**
   - 添加时段检测逻辑

7. **信号快照机制**
   - 在信号生成时保存K线快照

## 📝 总结

old1 的实现更加**完整和灵活**，特别是在：
- 订单管理（限价单、有效期）
- 止损止盈配置（多种模式）
- 斐波那契 Fallback 机制
- 回测结果持久化

当前实现更加**简洁和统一**，优势在于：
- 策略接口统一
- 以损定仓机制
- 多时间框架聚合（无需额外数据）

**建议**：优先实现斐波那契 Fallback 机制和增强止损止盈配置，这两个功能对策略表现影响较大。
