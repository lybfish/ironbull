# SMC Fibonacci 策略完整参数文档

## 目录
1. 概述  
2. Old1 对齐参数  
3. 回踩确认形态参数  
4. 流动性参数  
5. Order Block / FVG 参数  
6. 外汇交易理论参数  
7. 风险管理参数  
8. 实盘交易优化参数  
9. 信号质量参数  
10. 自适应与优化参数  
11. 参数配置示例  
12. 参数验证规则  
13. 实施计划  

---

## 一、概述

- **参数分类说明**
  - **Old1 对齐参数**：直接来自旧版 `smc_backtest / smc_fibo_old1` 引擎，必须一一对齐，保证回测/实盘结果一致性。
  - **回踩确认形态参数**：控制金K、Pin Bar、吞没等 K 线拒绝形态，用于“回踩确认入场”逻辑。
  - **流动性参数**：控制内外流动性、高低点、假突破（Liquidity Sweep）等 SMC 关键概念。
  - **Order Block / FVG 参数**：订单块、FVG（公平价差）及供需反转相关设置。
  - **外汇交易理论参数**：时区、新闻过滤、AMD 理论、出场层级、大周期方向判断等。
  - **风险管理参数**：以损定仓、RR、最大风险约束等。
  - **实盘优化参数**：滑点、点差、价格保护、成交方式等。
  - **信号质量参数**：信号强度评分、过滤条件、综合评分。
  - **自适应与优化参数**：Auto Profile、环境识别、预设模板等。

- **参数优先级说明**
  - **高优先级 (High)**：与 Old1 行为强相关，会显著影响回测曲线或下单逻辑，必须优先实现和验证。
  - **中优先级 (Medium)**：对信号质量和实盘体验有明显影响，但不改变核心逻辑。
  - **低优先级 (Low)**：更多是优化体验、调参与研究用途，可逐步实现。

- **参数使用建议**
  - 初期：优先只开放 **Old1 对齐参数 + 基础风险参数**，确保结果和旧引擎一致。
  - 进阶：逐步开启 **回踩确认形态 + 流动性 + OB/FVG** 等过滤类参数。
  - 高级：最后再开放 **自适应、复杂形态权重、外汇专用过滤**，供专业用户微调。

---

## 二、Old1 对齐参数（必须实现）

> 说明：本节主要来自 `_legacy_readonly/old2/TradeCore/scripts/ops/smc_backtest_params_doc.md`、`smc_fibo_old1.py`、`OLD1_DEFAULT_PARAMS.md` 等文档，是对齐 Old1 行为的“硬约束参数”。

### 2.1 基础回测 / 交易参数

| 参数名 | 类型 | 默认值 | 说明 | 优先级 | 来源 |
|-------|------|--------|------|--------|------|
| `fee_bps` | float | `0` | 手续费（基点），如 10 = 0.1% | Medium | old1 |
| `spread_points` | float | `0` | 点差（点），用来模拟买卖价差 | Medium | old1 |
| `price_digits` | int | `5` | 价格小数位精度 | Medium | old1 |
| `order_type` | str | `"limit"` | 下单类型：`limit` / `market` | High | old1 |
| `tif_bars` | int | `20` | 订单有效期（K 线根数） | High | old1 |
| `direction` | str | `"both"` | 交易方向：`both/buy/sell` | High | old1 |
| `cooldown_bars` | int | `0` | 开仓后的冷却期，避免过度交易 | Medium | old1 |

### 2.2 资金管理 / RR 参数

| 参数名 | 类型 | 默认值 | 说明 | 优先级 | 来源 |
|-------|------|--------|------|--------|------|
| `rr` | float | `2` | 目标风险回报比（仅在 `tp_mode="rr"` 时使用） | Medium | old1 |
| `risk_pct` | float | `1` | 每单占用账户资金百分比（%） | Medium | old1 |
| `risk_cash` / `max_loss` | float | `100` | 以损定仓：固定亏损金额（USDT） | High | old1 + 现实现 |
| `max_leverage` | float | `10` | 最大杠杆倍数，用于约束仓位大小 | Medium | old1 |
| `minRr` / `min_rr` | float | `2` | **最小 RR 过滤，低于该值不开仓** | High | old1 + 现实现 |

### 2.3 Fibo / 入场核心参数

| 参数名 | 类型 | 默认值 | 说明 | 优先级 | 来源 |
|-------|------|--------|------|--------|------|
| `fiboLevels` / `fibo_levels` | list[float] | `[0.5, 0.618, 0.705]` | 斐波那契回撤入场位 | High | old1 |
| `fibo_tolerance` | float | `0.005` | 回撤位容差（0.5%） | Medium | 现实现 |
| `entry` / `entry_source` | str | `"auto"` | 入场参考来源：`auto/ob/swing/fvg` | High | old1 |
| `entry_mode` / `confirm_mode` | str | `"limit"` | 最终下单模式：`limit/market`（fibo 模式下会强制 limit） | High | old1 |
| `session` | str | `"all"` | 交易时段过滤：`all/london/ny/asia/custom` | Medium | old1 |
| `htfTimeframe` | str | `"1h"` | HTF 时间框架（如 `1h/4h`） | Medium | old1 |
| `fiboFallback` / `fibo_fallback` | bool | `True` | 斐波那契 Fallback 机制：主结构失败时是否尝试次级结构 | Medium | old1 + 现实现 |

### 2.4 结构 / 趋势偏好参数

| 参数名 | 类型 | 默认值 | 说明 | 优先级 | 来源 |
|-------|------|--------|------|--------|------|
| `structure` | str | `"both"` | 结构过滤：`bos/choch/both` | High | old1 + 现实现 |
| `bias` | str | `"with_trend"` | 趋势偏好：`with_trend/counter/both` | High | old1 + 现实现 |
| `swing` | int/str | `3` / `"auto"` | HTF/LTF 摆动点灵敏度，支持 `"auto"` | Medium | old1 |
| `htfSwing` / `htf_swing` | int/str | `3` / `"auto"` | HTF 结构识别灵敏度 | Medium | old1 |
| `autoProfile` / `auto_profile` | str | `"medium"` | 自动档位：`conservative/medium/aggressive` | Medium | old1 |

### 2.5 止损 / 止盈 / 回踩确认参数

| 参数名 | 类型 | 默认值 | 说明 | 优先级 | 来源 |
|-------|------|--------|------|--------|------|
| `stopBufferPct` / `stop_buffer_pct` | float | `0.05` | 止损缓冲（相对 swing/OB 的百分比），Old1 关键参数 | High | old1 + 现实现 |
| `stopSource` / `stop_source` | str | `"auto"` | 止损来源：`auto/ob/swing/structure` | High | old1 + 现实现 |
| `tpMode` / `tp_mode` | str | `"swing"` | 止盈模式：`swing/rr/fibo` | High | old1 + 现实现 |
| `retestBars` / `retest_bars` | int | `20` | 回踩确认最长等待 K 线数 | High | old1 + 现实现 |
| `retestCancelOrder` / `retest_cancel_order` | bool | `False` | 回踩超时是否自动取消订单 | Medium | old1 |
| `retestIgnoreStopTouch` / `retest_ignore_stop_touch` | bool | `False` | 回踩期间若提前触及止损，是否忽略停止继续等待 | Medium | old1 + 现实现 |
| `pinbarRatio` / `pinbar_ratio` | float | `1.5`（代码）/`2.0`（前端 & 建议） | Pin Bar 影线/实体最小比值 | High | old1 + 现实现 |
| `allowEngulf` / `allow_engulf` | bool | `True` | 是否允许吞没形态作为回踩确认 | High | old1 + 现实现 |
| `marketReject` / `market_reject` | bool | `True` | 是否允许“市价拒绝”模式（价格偏离 Fibo 但出现强拒绝形态） | Medium | old1 |
| `marketMaxDevAtr` / `market_max_dev_atr` | float | `0.3` | 市价拒绝时，允许偏离 Fibo 位的最大 ATR 倍数 | Medium | old1 |

### 2.6 SMC 扩展参数（OB/FVG/流动性）

| 参数名 | 类型 | 默认值 | 说明 | 优先级 | 来源 |
|-------|------|--------|------|--------|------|
| `liquidity` | str | `"external"` | 流动性优先类型：`external/internal/both` | High | old1 |
| `obType` / `ob_type` | str | `"reversal"` | 订单块类型：`reversal/continuation` | Medium | old1 |
| `wickOb` / `wick_ob` | bool | `True` | 是否允许“影线订单块” | Medium | old1 |
| `useOb` / `use_ob` | bool/str | `True`/`"auto"` | 是否启用订单块过滤 | High | old1 |
| `obLookback` / `ob_lookback` | int | `20` | 寻找订单块的回看范围 | Medium | old1 |
| `useFvg` / `use_fvg` | bool/str | `True`/`"auto"` | 是否启用 FVG 过滤 | Medium | old1 |
| `fvgMinPct` / `fvg_min_pct` | float | `0.15` | FVG 最小缺口（%） | Medium | old1 |
| `useSweep` / `use_sweep` | bool/str | `True`/`"auto"` | 是否启用流动性扫除条件 | High | old1 |
| `sweepLen` / `sweep_len` | int | `5` | 扫流动性时考虑的 swing 根数 | Medium | old1 |
| `limitOffsetPct` / `limit_offset_pct` | float | `0.2` | limit 挂单偏移（% of range） | Medium | old1 |
| `limitTolAtr` / `limit_tol_atr` | float | `0.2` | limit 成交允许偏离（ATR 倍数） | Medium | old1 |
| `atrPeriod` / `atr_period` | int | `14` | ATR 周期 | Medium | old1 |

---

## 三、回踩确认形态参数（金K / 拒绝形态）

> 说明：本节参数控制“价格回踩 Fibo/OB 区域后是否需要 K 线拒绝确认”，现实现中已有 `pinbar`, `engulfing`, `morning/evening star`, `close reject` 等形态，可扩展到更多形态（含金K）。

### 3.1 已实现形态（现有 5 种）

| 参数名 | 类型 | 默认值 | 说明 | 优先级 | 来源 |
|-------|------|--------|------|--------|------|
| `enable_pinbar` | bool | `True` | 是否启用 Pin Bar 拒绝形态 | High | 现实现 |
| `pinbar_ratio` | float | `1.5~2.0` | 影线长度 / 实体长度最小比 | High | old1 + 现实现 |
| `enable_engulfing` / `allow_engulf` | bool | `True` | 是否启用吞没形态 | High | old1 + 现实现 |
| `enable_morning_star` | bool | `True` | 是否启用晨星（看多反转） | Medium | 现实现 |
| `enable_evening_star` | bool | `True` | 是否启用暮星（看空反转） | Medium | 现实现 |
| `enable_close_reject` | bool | `True` | 收盘价强烈拒绝 Fibo/OB 边界（Close Reject） | Medium | 现实现 |

### 3.2 建议新增形态（金K + 其它 13+ 种）

> 下表是建议补充的形态集合，最终可通过统一的 `rejection_patterns` 模块实现，并支持权重与开关控制。

| 形态名称 | 参数示例 | 说明 | 优先级 | 来源 |
|----------|----------|------|--------|------|
| 金K（Golden K） | `enable_golden_k: bool` | 关键支撑位上出现长下影金K，实体收在区间上半部分 | High | 外汇实战 |
| Inside Bar | `enable_inside_bar: bool` | 内包线形态，可作为回踩后的继续信号 | Medium | K 线形态 |
| Wick Rejection | `enable_wick_reject: bool`, `wick_min_ratio: float` | 单根或多根连续长影线拒绝某价位 | High | 实战经验 |
| Fakey / False Break | `enable_fakey: bool` | 先假突破再快速反向收回区间 | High | 流动性逻辑 |
| Tweezer Top/Bottom | `enable_tweezer: bool` | 顶底双针形态 | Medium | K 线形态 |
| Three Inside Up/Down | `enable_three_inside: bool` | 三根组合反转形态 | Low | K 线形态 |
| Belt Hold | `enable_belt_hold: bool` | 强势单根光头光脚K，趋势延续或快速反转 | Medium | K 线形态 |
| Hammer / Hanging Man | `enable_hammer: bool` | 锤子线/上吊线 | Medium | K 线形态 |
| Shooting Star | `enable_shooting_star: bool` | 长上影拒绝高位 | Medium | K 线形态 |
| Harami | `enable_harami: bool` | 孕线形态 | Low | K 线形态 |
| Multi-Bar Rejection | `multi_bar_reject_bars: int` | 连续 N 根 K 线在区间边界附近收盘失败 | Medium | 实战经验 |
| Gap Rejection | `enable_gap_reject: bool` | 向下/上跳空后迅速收回缺口 | Low | 指数/股票场景 |
| Volume Spike Rejection | `enable_volume_reject: bool` | 成交量放大 + K 线拒绝 | Low | 外汇/合约 |
| Pattern Min Score | `pattern_min_score: float` | 当启用多形态时的最小综合得分 | High | 本项目扩展 |

### 3.3 形态权重与综合评分

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `pattern_weights` | dict[str,float] | `{}` | 为每种形态配置权重，例如：`{"pinbar": 1.0, "golden_k": 1.2}` | Medium |
| `pattern_min_score` | float | `1.0` | 多形态叠加后的最小总得分，低于该值不入场 | High |
| `pattern_side_filter` | str | `"both"` | 是否区分多空方向：`both/buy_only/sell_only` | Low |

---

## 四、流动性参数（内外流动性 / 时区高低点 / 假突破）

> 说明：围绕 External / Internal Liquidity、Session 高低点和 Sweep 逻辑设计，用于捕捉“扫流动性 + 反转”的 SMC 核心。

### 4.1 内外流动性配置

| 参数名 | 类型 | 默认值 | 说明 | 优先级 | 来源 |
|-------|------|--------|------|--------|------|
| `liquidity` | str | `"external"` | 流动性模式：`external/internal/both` | High | old1 |
| `allow_external` | bool | `True` | 是否允许使用外部高低点（如日/周/月高低） | High | 外汇理论 |
| `allow_internal` | bool | `True` | 是否允许使用内部 swing 高低点 | High | 外汇理论 |
| `liquidity_lookback` | int | `20` | 统计内部流动性高低点的回看范围 | Medium | SMC 现实现 |
| `htf_liquidity_timeframe` | str | `"4h"` | 外部流动性参考时间框架 | Medium | 外汇理论 |

### 4.2 时区高低点与假突破

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `session_mode` | str | `"forex"` | 时区模式：`none/forex/custom` | Medium |
| `asia_session` | str | `"00:00-06:00"` | 亚盘时间段（服务器时间） | Medium |
| `london_session` | str | `"08:00-16:00"` | 欧盘时间段 | Medium |
| `ny_session` | str | `"13:00-21:00"` | 美盘时间段 | Medium |
| `session_hl_lookback` | int | `1` | 统计最近 N 日的 Session 高低点 | Medium |
| `fake_break_min_ratio` | float | `0.3` | 假突破最小超出比例（相对高低点 range） | Medium |
| `fake_break_max_bars` | int | `5` | 假突破后允许在多少根 K 线内迅速收回 | Medium |

### 4.3 Sweep / Liquidity Grab 相关

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `use_sweep` | bool/str | `"auto"` | 是否启用扫流动性条件 | High |
| `sweep_len` | int | `5` | 扫流动性时参考的 swing 长度 | Medium |
| `sweep_confirm_pattern` | str | `"rejection"` | 扫流动性后确认方式：`rejection/structure_only/both` | Medium |
| `sweep_min_rr` | float | `1.5` | 仅当扫流动性后的 RR ≥ 该值才有效 | Medium |
| `sweep_mtf_confirm` | bool | `False` | 是否要求 HTF 结构也完成扫流动性 | Low |

---

## 五、Order Block / FVG 参数

### 5.1 订单块（Order Block）参数

| 参数名 | 类型 | 默认值 | 说明 | 优先级 | 来源 |
|-------|------|--------|------|--------|------|
| `use_ob` | bool/str | `"auto"` | 是否启用订单块过滤 | High | old1 |
| `ob_type` | str | `"reversal"` | 订单块类型：`reversal/continuation` | Medium | old1 |
| `ob_lookback` | int | `20` | 寻找订单块的历史回看范围 | Medium | old1 |
| `ob_min_body_ratio` | float | `0.5` | 订单块实体长度 / 总 K 线长度最小比值 | Medium | 现实现 |
| `wick_ob` | bool | `True` | 是否允许影线订单块（只用影线区域） | Low | old1 |
| `ob_max_tests` | int | `3` | 订单块允许被测试的次数，超过则失效 | Medium | SMC 理论 |
| `ob_valid_bars` | int | `100` | 订单块最大有效 K 线数 | Medium | SMC 理论 |

### 5.2 FVG（Fair Value Gap）参数

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `use_fvg` | bool/str | `"auto"` | 是否启用 FVG 过滤 | Medium |
| `fvg_min_pct` | float | `0.15` | FVG 最小缺口百分比 | Medium |
| `fvg_valid_bars` | int | `50` | FVG 最大有效 K 线数 | Medium |
| `fvg_fill_mode` | str | `"touch"` | 认为“回填完成”的模式：`touch/full/partial` | Medium |
| `fvg_direction_filter` | str | `"with_trend"` | 是否只交易与趋势同向的 FVG | Low |

### 5.3 供需反转 / OB+FVG 联动

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `sd_reversal_required` | bool | `False` | 是否要求供需区（OB/FVG）发生反转才允许进场 | Medium |
| `ob_fvg_confluence` | bool | `True` | 是否要求 OB 与 FVG 重叠 | Medium |
| `ob_fvg_min_overlap_pct` | float | `0.3` | OB/FVG 重叠区域最小占比 | Medium |

---

## 六、外汇交易理论参数

> 来自你提供的“外汇与交易策略系统整理”等文档，聚焦于时区、新闻、AMD 理论、出场层级与方向判断。

### 6.1 时区与新闻过滤

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `enable_session_filter` | bool | `False` | 是否启用时区过滤（亚/欧/美盘） | Medium |
| `allowed_sessions` | list[str] | `["london","ny"]` | 允许开仓的交易时段 | Medium |
| `session_risk_factor` | dict | `{}` | 不同时段风险系数（调整仓位或 RR） | Low |
| `enable_news_filter` | bool | `False` | 是否启用新闻事件过滤 | Medium |
| `news_impact_levels` | list[str] | `["high"]` | 过滤的新闻级别：`low/medium/high` | Medium |
| `news_blackout_minutes` | int | `30` | 新闻前后禁止开仓的分钟数 | Medium |

### 6.2 AMD 入场理论（Accumulation / Manipulation / Distribution）

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `amd_entry_mode` | str | `"off"` | AMD 入场模式：`off/basic/advanced` | Medium |
| `amd_phase_filter` | list[str] | `[]` | 仅在特定阶段入场：`["accumulation","manipulation","distribution"]` | Medium |
| `amd_timebox_minutes` | int | `60` | AMD 时间框窗口 | Low |

### 6.3 出场层级与方向判断

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `exit_level` | str | `"basic"` | 出场层级：`basic/intermediate/advanced` | Medium |
| `direction_htf_timeframe` | str | `"4h"` | 大周期方向判断时间框架 | Medium |
| `direction_mtf_confirm` | bool | `True` | 是否要求多周期方向共振 | Medium |
| `direction_kline_combo` | bool | `True` | 是否使用 K 线组合（如金K、吞没）辅助方向判断 | Medium |

---

## 七、风险管理参数

### 7.1 仓位与风险限制

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `max_loss` / `risk_cash` | float | `100` | 每单最大亏损金额 | High |
| `risk_pct` | float | `1` | 每单风险占比（%） | Medium |
| `daily_max_loss` | float | `300` | 每日最大亏损金额 | High |
| `daily_max_loss_pct` | float | `5` | 每日最大亏损占比（%） | High |
| `max_consecutive_loss` | int | `3` | 最大允许连亏笔数 | Medium |
| `account_risk_mode` | str | `"fixed_cash"` | 风险模式：`fixed_cash/fixed_pct/hybrid` | Medium |

### 7.2 止损止盈增强

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `sl_trailing_mode` | str | `"off"` | 跟踪止损：`off/fixed_atr/structure` | Medium |
| `sl_trailing_atr_mult` | float | `1.5` | ATR 跟踪止损倍数 | Medium |
| `partial_take_profit_levels` | list[float] | `[1.0, 2.0]` | 分批止盈 RR 倍数 | Medium |
| `partial_tp_ratios` | list[float] | `[0.5, 0.5]` | 分批止盈对应平仓比例 | Medium |
| `hard_tp_rr` | float | `3.0` | 最终强制止盈 RR | Low |

---

## 八、实盘交易优化参数

### 8.1 滑点与点差

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `spread_points` | float | `0` | 点差（点） | Medium |
| `slippage_mode` | str | `"fixed"` | 滑点模式：`fixed/percentage/volatility_based` | Medium |
| `slippage_value` | float | `0.5` | 固定滑点（点）或百分比 | Medium |

### 8.2 订单执行与价格保护

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `order_type` | str | `"limit"` | 订单类型：`limit/market/post_only` | High |
| `post_only` | bool | `False` | 是否只挂 Maker 单 | Medium |
| `price_protection_pct` | float | `0.3` | 市价价差保护，超过则拒绝成交 | Medium |
| `cancel_on_disconnect` | bool | `True` | 断线时是否取消所有挂单 | Low |

---

## 九、信号质量参数

> 用于量化每个信号的“质量”，进一步作为过滤条件或打分展示。

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `enable_signal_score` | bool | `True` | 是否启用信号打分 | Medium |
| `score_components` | dict | `{}` | 子评分开关：`{"structure":1,"ob":1,"fvg":1,"liquidity":1,"pattern":1}` | Medium |
| `min_signal_score` | float | `0.0` | 最小信号得分，低于该值不交易 | High |
| `score_decay_bars` | int | `10` | 信号随时间衰减的 K 线数 | Medium |
| `duplicate_signal_filter_bars` | int | `3` | 在多少根 K 线内过滤相同方向的重复信号 | Medium |

---

## 十、自适应与优化参数

### 10.1 Auto Profile / 市场环境自适应

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `auto_profile` | str | `"medium"` | 自动档位：`conservative/medium/aggressive` | Medium |
| `volatility_thresholds` | dict | `{}` | 各档位对应的波动率阈值 | Low |
| `rr_auto_adjust` | bool | `False` | 是否根据波动率自动调整 `min_rr` | Medium |
| `sl_buffer_auto_adjust` | bool | `False` | 是否根据波动率自动调整 `stop_buffer_pct` | Medium |

### 10.2 参数预设模板

| 参数名 | 类型 | 默认值 | 说明 | 优先级 |
|-------|------|--------|------|--------|
| `preset_profile` | str | `"none"` | 参数预设：`none/conservative/balanced/aggressive/forex_specific` | Medium |
| `preset_overrides_allowed` | bool | `True` | 是否允许用户在预设基础上再覆盖细节参数 | Medium |

---

## 十一、参数配置示例

### 11.1 保守配置（低风险）

```json
{
  "strategy_code": "smc_fibo",
  "risk_per_trade": 50,
  "strategy_config": {
    "max_loss": 50,
    "min_rr": 2.0,
    "fibo_levels": [0.5, 0.618, 0.705],
    "fibo_tolerance": 0.003,
    "structure": "both",
    "bias": "with_trend",
    "stop_buffer_pct": 0.05,
    "tp_mode": "swing",
    "require_retest": true,
    "retest_bars": 20,
    "pinbar_ratio": 2.0,
    "allow_engulf": true,
    "use_ob": "auto",
    "use_fvg": "auto",
    "use_sweep": "auto",
    "auto_profile": "conservative",
    "preset_profile": "conservative"
  }
}
```

### 11.2 中等配置（平衡）

```json
{
  "strategy_code": "smc_fibo",
  "risk_per_trade": 100,
  "strategy_config": {
    "max_loss": 100,
    "min_rr": 1.8,
    "fibo_levels": [0.382, 0.5, 0.618, 0.705],
    "fibo_tolerance": 0.005,
    "structure": "both",
    "bias": "with_trend",
    "stop_buffer_pct": 0.05,
    "tp_mode": "swing",
    "require_retest": true,
    "retest_bars": 20,
    "pinbar_ratio": 2.0,
    "allow_engulf": true,
    "use_ob": true,
    "use_fvg": true,
    "use_sweep": "auto",
    "htf_multiplier": 4,
    "require_htf_filter": true,
    "auto_profile": "medium",
    "preset_profile": "balanced"
  }
}
```

### 11.3 激进配置（高风险高收益）

```json
{
  "strategy_code": "smc_fibo",
  "risk_per_trade": 150,
  "strategy_config": {
    "max_loss": 150,
    "min_rr": 1.5,
    "fibo_levels": [0.382, 0.5, 0.618],
    "fibo_tolerance": 0.008,
    "structure": "both",
    "bias": "both",
    "stop_buffer_pct": 0.04,
    "tp_mode": "rr",
    "rr": 3.0,
    "require_retest": false,
    "use_ob": true,
    "use_fvg": true,
    "use_sweep": true,
    "liquidity": "both",
    "htf_multiplier": 3,
    "require_htf_filter": false,
    "auto_profile": "aggressive",
    "preset_profile": "aggressive"
  }
}
```

### 11.4 外汇市场专用配置

```json
{
  "strategy_code": "smc_fibo",
  "risk_per_trade": 100,
  "strategy_config": {
    "max_loss": 100,
    "min_rr": 2.0,
    "fibo_levels": [0.5, 0.618, 0.705],
    "structure": "both",
    "bias": "with_trend",

    "stop_buffer_pct": 0.05,
    "tp_mode": "swing",
    "use_ob": "auto",
    "use_fvg": "auto",
    "use_sweep": "auto",
    "liquidity": "external",
    "htf_multiplier": 4,
    "require_htf_filter": true,

    "enable_session_filter": true,
    "allowed_sessions": ["london", "ny"],
    "enable_news_filter": true,
    "news_impact_levels": ["high"],
    "news_blackout_minutes": 30,

    "amd_entry_mode": "basic",
    "direction_htf_timeframe": "4h",
    "direction_mtf_confirm": true,

    "auto_profile": "medium",
    "preset_profile": "forex_specific"
  }
}
```

---

## 十二、参数验证规则

### 12.1 类型验证

- **浮点型**：`min_rr`, `stop_buffer_pct`, `fibo_tolerance`, `rr`, `market_max_dev_atr` 等必须为 `float` 或可安全转换为 `float`。
- **整型**：`retest_bars`, `tif_bars`, `cooldown_bars`, `htf_multiplier`, `atr_period` 等必须为 `int` 且 ≥ 1。
- **布尔型**：`allow_engulf`, `require_retest`, `use_ob`, `use_fvg`, `use_sweep` 等接受 `bool` 或 `"true"/"false"` 字符串。
- **枚举型字符串**：`structure`, `bias`, `tp_mode`, `order_type`, `liquidity` 等必须在预定义枚举集合内。

### 12.2 范围验证

- `min_rr`：推荐范围 \[0.5, 5\]，默认 ≥ 1.5。
- `stop_buffer_pct`：推荐范围 \[0.005, 0.1\]（0.5% ~ 10%）。
- `fibo_tolerance`：推荐范围 \[0.001, 0.02\]。
- `pinbar_ratio`：推荐范围 \[1.0, 4.0\]。
- `risk_pct`：推荐范围 \[0.1, 5.0\]。
- `daily_max_loss_pct`：推荐范围 \[1, 20\]。

### 12.3 枚举值验证

- `structure` ∈ `{ "bos", "choch", "both" }`
- `bias` ∈ `{ "with_trend", "counter", "both" }`
- `tp_mode` ∈ `{ "swing", "rr", "fibo" }`
- `order_type` ∈ `{ "limit", "market", "post_only" }`
- `liquidity` ∈ `{ "external", "internal", "both" }`
- `amd_entry_mode` ∈ `{ "off", "basic", "advanced" }`
- `exit_level` ∈ `{ "basic", "intermediate", "advanced" }`
- `preset_profile` ∈ `{ "none", "conservative", "balanced", "aggressive", "forex_specific" }`

### 12.4 默认值与回退逻辑

- 若用户未提供某参数，则：
  - 有 Old1 默认值的，优先采用 **Old1 默认**；
  - 仅在本项目中新增的参数，采用安全的 **保守默认**（如风控相关偏紧）。
- 对于兼容旧配置的场景：
  - 同时支持 `camelCase` 与 `snake_case`（如 `pinbarRatio` / `pinbar_ratio`）。
  - 若两者同时出现，以策略最新标准字段为主，并记录告警日志。

---

## 十三、实施计划（按优先级分阶段）

> 目标：在不破坏现有线上行为的前提下，逐步落地本参数文档中的所有高/中优先级参数。

### 阶段一：Old1 完全对齐（高优先级）

- **范围**
  - 确认所有 **2.x 小节中的 Old1 参数** 均已在 `smc_fibo.py` / `smc_fibo_old1.py` 中映射。
  - 对齐 `stop_buffer_pct`, `tp_mode`, `fibo_levels`, `pinbar_ratio`, `min_rr`, `retest_bars`, `allow_engulf`, `fibo_fallback`, `liquidity`, `use_ob`, `use_fvg`, `use_sweep` 等关键字段。
- **输出**
  - 更新后的策略代码 + 回测对比文档（新旧引擎曲线对比）。

### 阶段二：回踩确认形态与流动性增强（中高优先级）

- **范围**
  - 落地本文件 **第 3、4 章** 的关键参数：
    - 金K / Wick Rejection / Fakey / 多形态权重。
    - 内外流动性、时区高低点、假突破检测、Sweep 逻辑扩展。
- **输出**
  - `rejection_patterns` 模块化实现。
  - 流动性识别与 Sweep 检测模块。

### 阶段三：OB / FVG / 外汇理论与风险增强（中优先级）

- **范围**
  - 完善 OB / FVG 参数，实现 OB/FVG 联动与供需反转逻辑。
  - 加入时区 / 新闻 / AMD 等过滤，完善风险管理参数（每日风险、连亏限制等）。
- **输出**
  - 策略配置预设（保守/平衡/激进/外汇专用）。
  - 更新 `docs/STRATEGY_PARAMS.md` 或新增专用参数说明链接到本文件。

### 阶段四：信号质量评分与自适应（中低优先级）

- **范围**
  - 实现信号评分体系（结构、OB、FVG、流动性、形态等子评分）。
  - 实现 Auto Profile、自适应 RR 与止损缓冲调整。
- **输出**
  - 前端可视化信号评分。
  - 回测报告中展示不同评分阈值下的收益/胜率变化。

### 阶段五：细节完善与回归测试（收尾）

- **范围**
  - 根据实盘反馈细调参数范围和默认值。
  - 完成参数验证（类型/范围/枚举）单元测试。
- **输出**
  - 全量回归回测结果归档。
  - 最终版本的 SMC Fibonacci 策略参数说明书（即本文件）。

