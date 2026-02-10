# SMC 斐波那契策略：胜率差异分析

## 🔍 问题描述

当前实现的回测结果（胜率26.22%）与old1的回测结果（胜率很高）差距很大，需要找出关键差异。

---

## ⚠️ 关键差异发现

### 1. **止盈模式（tp_mode）** - 🔴 **最重要**

| 项目 | old1 | 当前实现 | 影响 |
|------|------|---------|------|
| 默认值 | `"swing"` | `"fibo"` | **极大** |
| 逻辑 | 回到摆动点（更容易达到） | 斐波那契扩展位（更难达到） | 胜率差异的主要原因 |

**old1 逻辑：**
```python
if side == "BUY":
    tp = swing_high["price"]  # 回到高点
else:
    tp = swing_low["price"]   # 回到低点
```

**当前实现逻辑：**
```python
# fibo模式（默认）
extension = fibo_extension(recent_high, recent_low, [1.272, 1.618])
take_profit = extension.get(1.272, entry + sl_distance * min_rr)
```

**影响分析：**
- old1：止盈目标是回到摆动点，通常距离更近，更容易触发
- 当前：止盈目标是斐波那契扩展位（1.272倍），通常距离更远，更难触发
- **结果：当前实现更容易被止损，胜率更低**

---

### 2. **止损缓冲（stop_buffer_pct）** - 🔴 **非常重要**

| 项目 | old1 | 当前实现 | 影响 |
|------|------|---------|------|
| 默认值 | `0.05` (5%) | `0.002` (0.2%) | **极大** |
| 逻辑 | 止损距离摆动点5% | 止损距离摆动点0.2% | 止损触发频率差异很大 |

**old1 逻辑：**
```python
stop_buffer_pct = 0.05  # 5%
if side == "BUY":
    base_stop = swing_low["price"] * (1 - stop_buffer_pct)  # 低点下方5%
else:
    base_stop = swing_high["price"] * (1 + stop_buffer_pct)  # 高点上方5%
```

**当前实现逻辑：**
```python
sl_buffer_pct = 0.002  # 0.2%
if side == "BUY":
    stop_loss = recent_low * (1 - self.sl_buffer_pct)  # 低点下方0.2%
else:
    stop_loss = recent_high * (1 + self.sl_buffer_pct)  # 高点上方0.2%
```

**影响分析：**
- old1：止损距离摆动点5%，给价格波动留出很大空间，不容易被扫止损
- 当前：止损距离摆动点0.2%，非常接近摆动点，容易被正常波动扫止损
- **结果：当前实现止损触发更频繁，胜率更低**

---

### 3. **入场模式（confirm_mode/entry_mode）** - 🟡 **重要**

| 项目 | old1 | 当前实现 | 影响 |
|------|------|---------|------|
| 支持模式 | `limit` / `market` / `retest` | 仅 `retest`（可选） | **中等** |
| 限价单 | ✅ 支持挂单等待价格触达 | ❌ 不支持 | 入场价格可能更差 |

**old1 逻辑：**
```python
confirm_mode = "limit"  # 默认限价单
if confirm_mode == "limit":
    # 创建限价单，等待价格触达
    open_order = {
        "price": entry,
        "expireI": i + 1 + tif_bars,  # 订单有效期
    }
```

**当前实现逻辑：**
```python
# 直接使用当前价格作为入场价
entry_price = current_price  # 立即入场
```

**影响分析：**
- old1：可以挂限价单，等待更好的价格，入场价格可能更优
- 当前：直接使用当前价格，可能不是最优入场点
- **结果：当前实现入场价格可能更差，影响盈亏比**

---

### 4. **回踩确认逻辑** - 🟡 **重要**

| 项目 | old1 | 当前实现 | 影响 |
|------|------|---------|------|
| 确认方式 | 价格触达区间 + 拒绝形态 | 价格已在区间 + 拒绝形态 | **中等** |
| 触达检测 | ✅ 严格检测价格是否触达区间 | ⚠️ 可能已假设价格在区间 | 确认质量差异 |

**old1 逻辑：**
```python
if confirm_mode == "retest":
    # 1. 创建待确认信号
    pending = {
        "zone_low": min(entry, stop),
        "zone_high": max(entry, stop),
    }
    # 2. 等待价格触达区间
    touched = bar["l"] <= zone_high and bar["h"] >= zone_low
    if touched:
        pending["touched"] = True
    # 3. 触达后检测拒绝形态
    if pending.get("touched"):
        rej = detect_rejection(...)
        if rej:
            # 确认入场
```

**当前实现逻辑：**
```python
if self.require_retest:
    # 检测时价格已在Fibo区间
    self._pending = {
        "touched": True,  # 直接设为True
        "zone_low": ...,
        "zone_high": ...,
    }
    return None  # 等待下一根K线确认
```

**影响分析：**
- old1：严格等待价格触达区间，然后检测拒绝形态，确认质量更高
- 当前：假设价格已在区间，可能错过最佳确认时机
- **结果：当前实现确认质量可能较低**

---

### 5. **盈亏比计算** - 🟢 **次要**

| 项目 | old1 | 当前实现 | 影响 |
|------|------|---------|------|
| 止盈调整 | ✅ `ensure_min_rr()` 自动调整 | ❌ 固定计算 | **小** |

**old1 逻辑：**
```python
def ensure_min_rr(side, entry, stop, tp):
    rr_value = rr_net_calc(side, entry, stop, tp)
    if rr_value >= min_rr:
        return tp, rr_value
    # 如果不够，自动调整止盈
    target_rr = max(min_rr * 1.2, min_rr + 0.3)
    tp = entry + target_rr * (entry - stop)  # 调整止盈
    return tp, rr_value
```

**当前实现逻辑：**
```python
# 固定计算，不调整
take_profit = self._calc_take_profit(...)
rr_ratio = self._calc_rr_ratio(entry, stop_loss, take_profit)
if rr_ratio < self.min_rr:
    return None  # 直接跳过
```

**影响分析：**
- old1：如果盈亏比不够，会自动调整止盈，增加交易机会
- 当前：如果盈亏比不够，直接跳过，可能错过一些交易
- **结果：当前实现交易机会可能更少**

---

## 📊 影响评估

### 胜率差异的主要原因（按重要性排序）

1. **🔴 止盈模式差异（tp_mode）** - **影响最大**
   - old1：回到摆动点（容易达到）
   - 当前：斐波那契扩展（难达到）
   - **估计影响：胜率差异 10-20%**

2. **🔴 止损缓冲差异（stop_buffer_pct）** - **影响很大**
   - old1：5%缓冲（不容易被扫）
   - 当前：0.2%缓冲（容易被扫）
   - **估计影响：胜率差异 5-15%**

3. **🟡 入场模式差异** - **影响中等**
   - old1：限价单（更好的入场价）
   - 当前：市价单（可能不是最优价）
   - **估计影响：胜率差异 2-5%**

4. **🟡 回踩确认差异** - **影响中等**
   - old1：严格等待触达后确认
   - 当前：假设已在区间
   - **估计影响：胜率差异 2-5%**

5. **🟢 盈亏比调整差异** - **影响较小**
   - old1：自动调整止盈
   - 当前：固定计算
   - **估计影响：胜率差异 1-3%**

---

## 🔧 修复建议

### 优先级1：修复止盈模式

```python
# 修改默认 tp_mode 为 "swing"
self.tp_mode = self.config.get("tp_mode", "swing")  # 从 "fibo" 改为 "swing"
```

### 优先级2：修复止损缓冲

```python
# 修改默认 sl_buffer_pct 为 0.05
self.sl_buffer_pct = self.config.get("sl_buffer_pct", 0.05)  # 从 0.002 改为 0.05
```

### 优先级3：实现限价单支持（可选）

在回测引擎中支持限价单挂单，等待价格触达。

### 优先级4：优化回踩确认逻辑

确保严格等待价格触达区间后再检测拒绝形态。

---

## 📝 总结

**核心问题：**
1. ✅ 止盈模式应该是 `"swing"`（回到摆动点），而不是 `"fibo"`（斐波那契扩展）
2. ✅ 止损缓冲应该是 `0.05`（5%），而不是 `0.002`（0.2%）

**这两个差异是导致胜率差异的主要原因！**

修复这两个问题后，胜率应该会显著提升，接近old1的水平。
