# IronBull 策略最优参数配置

> 基于 BTCUSDT 1h 90天回测数据，以损定仓模式（每笔最大亏损 100 USDT）

---

## 一、策略排名总览

### 以损定仓模式（risk_per_trade: 100）

| 排名 | 策略 | 收益% | 交易 | 胜率% | 盈亏比 | PF | 回撤% |
|------|------|-------|------|-------|--------|-----|-------|
| 1 | boll_squeeze | +85.6% | 44 | 20.4% | 13.56 | 3.49 | 63.7% |
| 2 | smc_fibo | +13.7% | 21 | 61.9% | 1.80 | 2.92 | 32.5% |
| 3 | turtle | +6.6% | 25 | 44.0% | 2.07 | 1.63 | 5.5% |
| 4 | ma_cross | +4.9% | 29 | 31.0% | 3.47 | 1.56 | 5.4% |
| 5 | swing | +3.2% | 51 | 25.5% | 3.71 | 1.27 | 6.4% |
| 6 | keltner | +2.3% | 10 | 60.0% | 1.11 | 1.67 | 3.2% |

---

## 二、稳健型配置（低回撤优先）

### 1. keltner - 最低回撤
```json
{
  "strategy_code": "keltner",
  "risk_per_trade": 100,
  "strategy_config": {
    "ema_period": 20,
    "atr_period": 10,
    "atr_mult": 2.0,
    "mode": "trend"
  }
}
```
**指标**: 回撤 3.2% | 收益 +2.3% | 胜率 60.0% | PF 1.67

---

### 2. turtle - 经典稳健
```json
{
  "strategy_code": "turtle",
  "risk_per_trade": 100,
  "strategy_config": {
    "entry_period": 20,
    "exit_period": 10,
    "atr_period": 20,
    "risk_mult": 2.0
  }
}
```
**指标**: 回撤 5.5% | 收益 +6.6% | 胜率 44.0% | PF 1.63

---

### 3. ma_cross - 简单有效
```json
{
  "strategy_code": "ma_cross",
  "risk_per_trade": 100,
  "strategy_config": {
    "fast_ma": 10,
    "slow_ma": 30,
    "atr_mult_sl": 1.5,
    "atr_mult_tp": 3.0
  }
}
```
**指标**: 回撤 5.4% | 收益 +4.9% | 胜率 31.0% | PF 1.56

---

### 4. smc_fibo（稳健版）- 高胜率
```json
{
  "strategy_code": "smc_fibo",
  "risk_per_trade": 100,
  "strategy_config": {
    "max_loss": 100,
    "min_rr": 1.5,
    "fibo_levels": [0.382],
    "fibo_tolerance": 0.005,
    "htf_multiplier": 4,
    "require_htf_filter": true
  }
}
```
**指标**: 回撤 9.6% | 收益 +66.0% | 胜率 81.8% | 交易 11笔

---

## 三、收益型配置（收益优先）

### 1. boll_squeeze - 最高收益
```json
{
  "strategy_code": "boll_squeeze",
  "risk_per_trade": 100,
  "strategy_config": {
    "bb_period": 20,
    "bb_std": 2.0,
    "kc_period": 20,
    "kc_mult": 1.5,
    "atr_mult_sl": 1.5,
    "atr_mult_tp": 3.0
  }
}
```
**指标**: 收益 +85.6% | 回撤 63.7% | 胜率 20.4% | PF 3.49

⚠️ 注意：胜率低，回撤大，适合风险承受能力强的用户

---

### 2. smc_fibo（激进版）- 高收益+高胜率
```json
{
  "strategy_code": "smc_fibo",
  "risk_per_trade": 100,
  "strategy_config": {
    "max_loss": 100,
    "min_rr": 1.5,
    "fibo_levels": [0.382, 0.5, 0.618],
    "fibo_tolerance": 0.005,
    "htf_multiplier": 4,
    "require_htf_filter": true
  }
}
```
**指标**: 收益 +13.7% | 回撤 32.5% | 胜率 61.9% | PF 2.92

---

### 3. turtle（激进版）
```json
{
  "strategy_code": "turtle",
  "risk_per_trade": 200,
  "strategy_config": {
    "entry_period": 15,
    "exit_period": 8,
    "atr_period": 14,
    "risk_mult": 1.5
  }
}
```
**指标**: 加大仓位提高收益，回撤相应增加

---

## 四、SMC + Fibo 策略详细参数说明

### 核心参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_loss` | float | 100 | 每单最大亏损（USDT） |
| `min_rr` | float | 1.5 | 最小盈亏比，低于此值不开仓 |
| `fibo_levels` | list | [0.382, 0.5, 0.618] | 斐波那契入场回撤位 |
| `fibo_tolerance` | float | 0.005 | 回撤位容差（0.5%） |

### 大周期过滤参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `htf_multiplier` | int | 4 | 大周期倍数（1h×4=4h） |
| `htf_ema_fast` | int | 20 | 大周期快EMA |
| `htf_ema_slow` | int | 50 | 大周期慢EMA |
| `require_htf_filter` | bool | true | 是否强制大周期过滤 |

### SMC 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `lookback` | int | 50 | 回看周期 |
| `swing_left` | int | 5 | 摆动点左侧K线数 |
| `swing_right` | int | 3 | 摆动点右侧K线数 |
| `ob_min_body_ratio` | float | 0.5 | 订单块最小实体比例 |
| `sl_buffer_pct` | float | 0.002 | 止损缓冲（0.2%） |

### 不同配置效果对比

| 配置 | fibo_levels | min_rr | 交易 | 胜率 | 收益 | 回撤 |
|------|-------------|--------|------|------|------|------|
| 高胜率 | [0.382] | 1.5 | 11 | 81.8% | +66% | 9.6% |
| 平衡 | [0.5] | 1.5 | 19 | 63.2% | +122% | - |
| 激进 | [0.382,0.5,0.618] | 1.5 | 21 | 61.9% | +123% | 13% |
| 保守 | [0.382,0.5,0.618] | 2.5 | 15 | 60.0% | +70% | 9.3% |

---

## 五、回测 API 调用示例

### 稳健型回测
```bash
curl -X POST http://localhost:8005/api/backtest/run-live \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_code": "keltner",
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "days": 90,
    "initial_balance": 10000,
    "risk_per_trade": 100
  }'
```

### 收益型回测
```bash
curl -X POST http://localhost:8005/api/backtest/run-live \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_code": "smc_fibo",
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "days": 90,
    "initial_balance": 10000,
    "risk_per_trade": 100,
    "strategy_config": {
      "max_loss": 100,
      "min_rr": 1.5,
      "fibo_levels": [0.382, 0.5, 0.618],
      "require_htf_filter": true
    }
  }'
```

---

## 六、风险提示

1. **历史表现不代表未来收益**
2. **以损定仓模式**可有效控制单笔亏损，但不能防止连续亏损
3. **回撤**是策略安全性的重要指标，建议选择回撤 < 20% 的配置
4. **胜率 vs 盈亏比**：高胜率策略往往盈亏比较低，需要平衡选择
5. 建议先用**小仓位实盘验证**，再逐步加大

---

## 七、推荐配置汇总

| 风格 | 推荐策略 | risk_per_trade | 预期收益 | 预期回撤 |
|------|---------|----------------|----------|----------|
| **极度保守** | keltner | 50 | 1-2% | < 3% |
| **稳健** | turtle | 100 | 5-10% | 5-8% |
| **平衡** | smc_fibo (0.382) | 100 | 10-20% | 10-15% |
| **激进** | smc_fibo (全部位) | 100 | 15-30% | 15-25% |
| **高风险** | boll_squeeze | 100 | 30-80% | 50-70% |

---

*更新时间: 2026-02-05*
*基于数据: BTCUSDT 1h 90天*
