# SMC 斐波那契策略：大小周期分析逻辑

## 📊 概述

策略使用**多时间框架（MTF）分析**，通过小周期和大周期结合判断趋势和入场时机。

---

## 🔍 小周期（LTF - Lower Timeframe）

### 判断方法：**摆动点结构（Swing Points）**

**代码位置：** `_get_trend()` 方法

### 识别逻辑

1. **摆动点识别**
   - 摆动高点：左侧5根K线 + 右侧3根K线中，当前K线最高
   - 摆动低点：左侧5根K线 + 右侧3根K线中，当前K线最低
   - 参数：`swing_left=5`, `swing_right=3`

2. **趋势判断规则**
   ```
   上升趋势（bullish）：
   - Higher High (HH): 最近高点 > 前一个高点
   - Higher Low (HL): 最近低点 > 前一个低点
   - 同时满足 HH 和 HL
   
   下降趋势（bearish）：
   - Lower High (LH): 最近高点 < 前一个高点
   - Lower Low (LL): 最近低点 < 前一个低点
   - 同时满足 LH 和 LL
   
   中性（neutral）：
   - 不满足上述条件（如：HH+LL 或 LH+HL）
   ```

### 示例

```
价格走势：
  H2 ──┐
       │
  H1 ──┘──┐
          │
  L2 ─────┘
  
  L1 ─────┐
          │
          └──
          
判断：
- H2 > H1 → Higher High ✅
- L2 > L1 → Higher Low ✅
→ 小周期趋势：bullish（上升）
```

---

## 🌐 大周期（HTF - Higher Timeframe）

### 判断方法：**EMA 交叉**

**代码位置：** `_get_htf_trend()` 方法

### 识别逻辑

1. **K线聚合**
   - 将小周期K线聚合成大周期
   - 参数：`htf_multiplier=4`
   - 例如：4根1h K线 → 1根4h K线
   - 聚合规则：
     - Open: 第一根K线的开盘价
     - High: 4根K线的最高价
     - Low: 4根K线的最低价
     - Close: 最后一根K线的收盘价
     - Volume: 4根K线的成交量之和

2. **EMA 计算**
   - 快EMA：`htf_ema_fast=20`（默认20）
   - 慢EMA：`htf_ema_slow=50`（默认50）
   - 在大周期K线上计算EMA

3. **趋势判断规则**
   ```
   上升趋势（bullish）：
   - 快EMA > 慢EMA
   - EMA差距 > 0.5%
   
   下降趋势（bearish）：
   - 快EMA < 慢EMA
   - EMA差距 < -0.5%
   
   中性（neutral）：
   - EMA差距在 -0.5% ~ +0.5% 之间
   ```

### 示例

```
大周期K线（4h）：
价格: 3000 → 3100 → 3050 → 3200

EMA计算：
- EMA(20) = 3150
- EMA(50) = 3100
- 差距 = (3150 - 3100) / 3100 * 100 = 1.61%

判断：
- 快EMA > 慢EMA ✅
- 差距 > 0.5% ✅
→ 大周期趋势：bullish（上升）
```

---

## 🔄 大小周期结合使用

### 1. 趋势过滤（`require_htf_filter=True`）

**规则：**
- 做多时：大周期不能看跌（允许 bullish 和 neutral）
- 做空时：大周期不能看涨（允许 bearish 和 neutral）

**代码逻辑：**
```python
if self.require_htf_filter:
    # 做多时：大周期不能看跌
    if trend == "bullish" and htf_trend == "bearish":
        return None  # 过滤掉逆势交易
    
    # 做空时：大周期不能看涨
    if trend == "bearish" and htf_trend == "bullish":
        return None  # 过滤掉逆势交易
```

### 2. 斐波那契 Fallback（`fibo_fallback=True`）

**规则：**
- 当小周期趋势为 `neutral` 时
- 根据大周期趋势自动确定方向
- 大周期看涨 → 自动做多
- 大周期看跌 → 自动做空

**代码逻辑：**
```python
if trend == "neutral" and self.fibo_fallback:
    if htf_trend == "bullish":
        side = "BUY"
        fibo_side_fallback = True
    elif htf_trend == "bearish":
        side = "SELL"
        fibo_side_fallback = True
```

---

## 📈 实际应用示例

### 场景1：顺势交易

```
小周期（1h）：
- 摆动点：HH + HL → bullish ✅
- 趋势：bullish

大周期（4h）：
- EMA(20) = 3150, EMA(50) = 3100
- 差距 = +1.61% → bullish ✅

结果：
- 大小周期同向 → 允许做多 ✅
- 信号强度高
```

### 场景2：逆势过滤

```
小周期（1h）：
- 摆动点：HH + HL → bullish ✅
- 趋势：bullish

大周期（4h）：
- EMA(20) = 3100, EMA(50) = 3150
- 差距 = -1.58% → bearish ❌

结果：
- 小周期看涨，大周期看跌 → 过滤掉 ❌
- 避免逆势交易
```

### 场景3：Fallback 机制

```
小周期（1h）：
- 摆动点：HH + LL（混合结构）
- 趋势：neutral ❌

大周期（4h）：
- EMA(20) = 3150, EMA(50) = 3100
- 差距 = +1.61% → bullish ✅

结果：
- 小周期中性，大周期看涨 → Fallback 做多 ✅
- 根据大周期方向确定交易方向
```

---

## ⚙️ 配置参数

### 小周期参数

```python
swing_left = 5        # 摆动点左侧K线数
swing_right = 3       # 摆动点右侧K线数
```

### 大周期参数

```python
htf_multiplier = 4    # 大周期倍数（4根1h = 1根4h）
htf_ema_fast = 20     # 快EMA周期
htf_ema_slow = 50     # 慢EMA周期
require_htf_filter = True  # 是否启用大周期过滤
```

### Fallback 参数

```python
fibo_fallback = True  # 是否启用斐波那契 Fallback
```

---

## 🎯 总结

| 周期 | 判断方法 | 指标 | 用途 |
|------|---------|------|------|
| **小周期（LTF）** | 摆动点结构 | Higher High/Low, Lower High/Low | 确定入场时机和方向 |
| **大周期（HTF）** | EMA 交叉 | EMA(20) vs EMA(50) | 趋势过滤和方向确认 |

**优势：**
- ✅ 小周期捕捉精确入场点
- ✅ 大周期过滤逆势交易
- ✅ Fallback 机制增加交易机会
- ✅ 多时间框架提高胜率

**注意事项：**
- ⚠️ 大周期聚合可能不够精确（建议使用真实HTF数据）
- ⚠️ EMA差距阈值（0.5%）可能需要根据市场调整
- ⚠️ 摆动点参数（5/3）可能需要优化
