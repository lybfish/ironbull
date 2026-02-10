# Old1 信号默认参数对比

## 📋 Old1 默认参数（从代码中提取）

### 来源1：`scripts/core/settings.py`

```python
FIBO_LEVELS = "0.5,0.618,0.705"
FIBO_RETEST_BARS = 20
FIBO_MIN_RR = 2
FIBO_PINBAR_RATIO = 1.5          # ⚠️ 注意：代码中是1.5
FIBO_ALLOW_ENGULF = True
FIBO_STOP_BUFFER_PCT = 0.05      # ✅ 5%
FIBO_STOP_SOURCE = "auto"
FIBO_TP_MODE = "swing"            # ✅ 默认swing
FIBO_TIF_BARS = 20
FIBO_BIAS = "with_trend"
FIBO_STRUCTURE = "both"
FIBO_ENTRY_SOURCE = "auto"
FIBO_ENTRY_MODE = "retest"
FIBO_ORDER_TYPE = "limit"
FIBO_SESSION = "all"
FIBO_HTF_TIMEFRAME = "1h"
FIBO_FALLBACK = True
FIBO_RETEST_IGNORE_STOP_TOUCH = False
```

### 来源2：`scripts/test_smc_backtest.py`（回测默认参数）

```python
"smc": {
    "fiboLevels": [0.5, 0.618, 0.705],
    "retestBars": 20,
    "minRr": 2,
    "pinbarRatio": 1.5,           # ⚠️ 回测脚本中是1.5
    "allowEngulf": True,
    "stopBufferPct": 0.05,        # ✅ 5%
    "stopSource": "auto",
    "tpMode": "swing",            # ✅ 默认swing
    "bias": "with_trend",
    "structure": "both",
    "entry": "auto",
    "session": "all",
    "htfTimeframe": "1h",
    "fiboFallback": True,
    "retestIgnoreStopTouch": False,
}
```

### 来源3：`prototype/app.js`（前端默认值）

```javascript
smc: {
    stopBufferPct: 0.05,          // ✅ 5%
    pinbarRatio: 2,               // ⚠️ 前端显示是2（可能被覆盖）
    minRr: 2,
    // ...
}
```

---

## 🔍 关键参数对比

| 参数 | Old1 默认值 | 当前实现默认值 | 状态 |
|------|------------|--------------|------|
| **stopBufferPct** | **0.05 (5%)** | ~~0.002 (0.2%)~~ → **0.05 (5%)** | ✅ **已修复** |
| **tpMode** | **"swing"** | ~~"fibo"~~ → **"swing"** | ✅ **已修复** |
| **pinbarRatio** | 1.5 (代码) / 2 (前端) | 2.0 | ⚠️ 需确认 |
| **minRr** | 2 | 2.0 | ✅ 一致 |
| **fiboLevels** | [0.5, 0.618, 0.705] | [0.382, 0.5, 0.618] | ⚠️ 有差异 |
| **retestBars** | 20 | 20 | ✅ 一致 |
| **allowEngulf** | True | True | ✅ 一致 |
| **fiboFallback** | True | True | ✅ 一致 |
| **stopSource** | "auto" | "auto" | ✅ 一致 |

---

## ⚠️ 需要注意的差异

### 1. Pin Bar 比例

- **Old1代码默认**：`1.5`
- **Old1前端默认**：`2`
- **当前实现**：`2.0`

**分析**：
- 代码中默认是1.5，但前端显示是2
- 可能前端有覆盖，或者不同版本
- 当前实现使用2.0，与前端一致
- **建议**：保持2.0（与前端一致，且更严格）

### 2. 斐波那契回撤位

- **Old1默认**：`[0.5, 0.618, 0.705]`
- **当前实现**：`[0.382, 0.5, 0.618]`

**分析**：
- Old1包含0.705（更深回撤）
- 当前实现包含0.382（更浅回撤）
- **影响**：可能影响信号数量和入场时机
- **建议**：可以调整为与old1一致，或保持当前设置（0.382是经典斐波那契位）

---

## ✅ 已修复的关键问题

### 1. 止损缓冲（stopBufferPct）

**修复前：**
```python
self.sl_buffer_pct = 0.002  # 0.2% - 太小，容易被扫止损
```

**修复后：**
```python
self.sl_buffer_pct = 0.05   # 5% - 与old1一致
```

**影响**：止损距离摆动点5%，给价格波动留出足够空间，不容易被正常波动扫止损。

### 2. 止盈模式（tpMode）

**修复前：**
```python
self.tp_mode = "fibo"  # 斐波那契扩展 - 难达到
```

**修复后：**
```python
self.tp_mode = "swing"  # 回到摆动点 - 容易达到，与old1一致
```

**影响**：止盈目标更容易达到，胜率会显著提升。

---

## 📊 总结

**核心修复（已完成）：**
1. ✅ `stopBufferPct`: 0.002 → 0.05 (5%)
2. ✅ `tpMode`: "fibo" → "swing"

**可选调整：**
1. ⚠️ `fiboLevels`: 考虑添加0.705，或保持当前设置
2. ⚠️ `pinbarRatio`: 当前2.0与前端一致，可以保持

**预期效果：**
修复这两个关键参数后，胜率应该会显著提升，接近old1的水平。
