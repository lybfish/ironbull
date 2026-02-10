# Old1 斐波那契逻辑修复说明

## 🔍 关键差异

### Old1 的逻辑（1606-1643行）

```python
# 1. 检测到BOS/CHoCH后，确定方向
side = bos or choch

# 2. 计算所有斐波那契回撤位的候选入场点
fib_candidates = []
for level in fibo_levels:
    if side == "BUY":
        entry = swing_high["price"] - swing_range * level  # 计算回撤位价格
        if entry > mid_price:
            continue
        # 计算止损止盈
        base_stop = swing_low["price"] * (1 - stop_buffer_pct)
        tp = swing_high["price"]
    else:
        entry = swing_low["price"] + swing_range * level
        if entry < mid_price:
            continue
        base_stop = swing_high["price"] * (1 + stop_buffer_pct)
        tp = swing_low["price"]
    
    stop, stop_used_swing = pick_stop(side, base_stop, entry)
    if entry == stop:
        continue
    tp, rr_value = ensure_min_rr(side, entry, stop, tp)
    if rr_value < min_rr:
        continue
    # 添加到候选列表（不管当前价格是否在回撤位）
    fib_candidates.append((rr_value, entry, stop, tp, level, stop_used_swing))

# 3. 如果没有候选，使用mid_price作为入场点
if not fib_candidates:
    entry = mid_price
    # ... 计算止损止盈
    if rr_value >= min_rr:
        fib_candidates.append((rr_value, entry, stop, tp, 0.5, stop_used_swing))

# 4. 选择最优候选（按盈亏比排序）
if not fib_candidates:
    continue
fib_candidates.sort(key=lambda x: x[0], reverse=True)
rr_value, entry, stop, tp, level, stop_used_swing = fib_candidates[0]

# 5. 创建信号（限价单，等待价格触达entry）
```

**关键点：**
- ✅ 计算所有斐波那契回撤位的入场点（不管当前价格在哪里）
- ✅ 选择最优的入场点（按盈亏比排序）
- ✅ 如果没有合适的回撤位，使用mid_price
- ✅ 创建限价单，等待价格触达entry价格

### 当前实现的逻辑

```python
# 1. 检测BOS/CHoCH确定方向
side = bos or choch

# 2. 只检查当前价格是否在斐波那契回撤位
fibo_zone = price_in_fibo_zone(current_price, fibo_dict, self.fibo_tolerance)

if fibo_zone:  # ❌ 只有当前价格在回撤位时才生成信号
    fibo_level, fibo_price = fibo_zone
    # ... 生成信号
```

**问题：**
- ❌ 只检查当前价格是否在回撤位
- ❌ 如果当前价格不在回撤位，就不生成信号
- ❌ 不会计算所有可能的回撤位入场点

## 🔧 修复方案

需要修改逻辑，使其与old1一致：

1. **计算所有斐波那契回撤位候选**
2. **选择最优的入场点**（按盈亏比）
3. **如果没有合适的回撤位，使用mid_price**
4. **创建限价单信号**（等待价格触达）
