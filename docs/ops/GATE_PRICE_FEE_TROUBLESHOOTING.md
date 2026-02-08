# Gate 价格和手续费不显示问题排查指南

## 问题描述

线上 Gate 交易所出现两个问题：
1. **价格不显示**：订单或成交记录中 `filled_price` 为 0 或 null
2. **手续费不显示**：`commission` 字段为 0 或 null

## 问题原因分析

### 1. 价格不显示的可能原因

#### 原因 A：Gate API 响应格式特殊
Gate 交易所的订单响应可能不包含 `average` 字段，或者字段名不同：
- Binance: `average` 字段包含成交均价
- Gate: 可能使用 `avgPrice`、`fill_price` 或在 `info` 中

#### 原因 B：合约张数转换问题
Gate 永续合约以"张"为单位，1 张 BTC/USDT = 0.0001 BTC。如果转换逻辑有问题，可能导致价格计算错误。

#### 原因 C：市价单异步成交
市价单提交后，Gate 可能异步返回（status=open, filled=0），需要重新查询才能获取成交价。

### 2. 手续费不显示的可能原因

#### 原因 A：Gate 响应中无 fee 字段
Gate 的订单响应可能不包含 `fee` 对象，手续费信息在 `info` 原始响应中。

#### 原因 B：需要单独查询成交记录
某些交易所（包括 Gate）的订单响应不含手续费，需要通过 `fetch_order_trades` 或 `fetch_my_trades` 获取。

#### 原因 C：手续费字段名不同
Gate 可能使用：
- `info.fee`
- `info.commission`
- `info.fill_fee`
- `info.taker_fee` / `info.maker_fee`

## 排查步骤

### 步骤 1：运行诊断脚本

```bash
# 测试 Gate API 连接和价格获取
PYTHONPATH=. python3 scripts/debug_gate_price_fee.py

# 测试响应解析逻辑
PYTHONPATH=. python3 scripts/debug_gate_price_fee.py --test-parsing

# 检查数据库中的订单
PYTHONPATH=. python3 scripts/debug_gate_price_fee.py --check-db
```

### 步骤 2：检查日志

查看 signal-monitor 或 execution-node 的日志：

```bash
# 查看最近的订单日志
tail -f tmp/logs/signal-monitor.log | grep "order created"

# 查看手续费补偿日志
tail -f tmp/logs/signal-monitor.log | grep "fee fetched"

# 查看 Gate 特定日志
tail -f tmp/logs/signal-monitor.log | grep -i gate
```

关键日志字段：
- `filled_price`: 成交价格
- `commission`: 手续费
- `commission_asset`: 手续费币种
- `raw_response`: 交易所原始响应

### 步骤 3：检查数据库

```sql
-- 检查最近的订单价格和手续费
SELECT 
    order_id,
    symbol,
    side,
    status,
    filled_quantity,
    filled_price,
    commission,
    commission_asset,
    created_at
FROM fact_order
WHERE tenant_id = 1  -- 你的租户 ID
ORDER BY created_at DESC
LIMIT 20;

-- 检查成交记录
SELECT 
    fill_id,
    order_id,
    symbol,
    side,
    price,
    quantity,
    commission,
    commission_asset,
    created_at
FROM fact_fill
WHERE tenant_id = 1
ORDER BY created_at DESC
LIMIT 20;

-- 统计价格为 0 的订单数量
SELECT 
    COUNT(*) as zero_price_count,
    COUNT(CASE WHEN filled_price > 0 THEN 1 END) as has_price_count
FROM fact_order
WHERE tenant_id = 1
AND created_at > DATE_SUB(NOW(), INTERVAL 7 DAY);

-- 统计手续费为 0 的订单数量
SELECT 
    COUNT(*) as zero_commission_count,
    COUNT(CASE WHEN commission > 0 THEN 1 END) as has_commission_count
FROM fact_order
WHERE tenant_id = 1
AND status IN (2, 3)  -- FILLED 或 PARTIAL
AND created_at > DATE_SUB(NOW(), INTERVAL 7 DAY);
```

### 步骤 4：测试真实下单

在测试环境或小额测试：

```bash
# 使用 Gate 测试网（如果有）
PYTHONPATH=. python3 scripts/test_isolated_open_close.py \
    --exchange gate \
    --symbol BTC/USDT \
    --amount 5 \
    --yes

# 查看返回的价格和手续费
```

## 修复方案

### 方案 1：增强 Gate 价格解析（推荐）

在 `libs/trading/live_trader.py` 的 `_parse_order_response` 方法中增强 Gate 价格提取：

```python
def _parse_order_response(self, ...):
    # ... 现有代码 ...
    
    # ★ 增强价格提取（Gate 特殊处理）
    filled_price = response.get("average") or response.get("price") or 0
    
    # Gate 可能在 info 中
    if filled_price == 0:
        info = response.get("info", {})
        if isinstance(info, dict):
            filled_price = (
                info.get("avgPrice") or 
                info.get("fill_price") or 
                info.get("avg_price") or 
                0
            )
            if filled_price:
                try:
                    filled_price = float(filled_price)
                except (ValueError, TypeError):
                    filled_price = 0
    
    return OrderResult(
        # ...
        filled_price=filled_price,
        # ...
    )
```

### 方案 2：增强手续费获取（已实现）

代码中已有手续费补偿逻辑（第 870-925 行），但可能需要增强 Gate 特定字段：

```python
# 在 _parse_order_response 中增加 Gate 手续费字段
if commission == 0:
    info = response.get("info", {})
    if isinstance(info, dict):
        # Gate 特定字段
        raw_comm = (
            info.get("commission") or 
            info.get("totalFee") or 
            info.get("fee") or
            info.get("fill_fee") or  # Gate 特有
            info.get("taker_fee") or  # Gate 特有
            info.get("maker_fee")     # Gate 特有
        )
        if raw_comm is not None:
            try:
                commission = abs(float(raw_comm))
            except (ValueError, TypeError):
                pass
```

### 方案 3：强制查询成交记录

如果上述方案仍无效，可以在订单成交后强制查询成交记录：

```python
# 在 create_order 方法中，市价单成交后
if order_type == OrderType.MARKET and result.status == OrderStatus.FILLED:
    # 强制查询成交记录获取真实价格和手续费
    try:
        await asyncio.sleep(0.5)  # 等待成交记录生成
        trades = await self.exchange.fetch_order_trades(
            result.exchange_order_id, 
            ccxt_sym
        )
        if trades:
            # 计算加权平均价格
            total_cost = sum(float(t.get("cost", 0)) for t in trades)
            total_qty = sum(float(t.get("amount", 0)) for t in trades)
            if total_qty > 0:
                avg_price = total_cost / total_qty
                result.filled_price = avg_price
            
            # 累加手续费
            total_fee = 0.0
            for t in trades:
                fee = t.get("fee", {})
                if fee and fee.get("cost"):
                    total_fee += abs(float(fee["cost"]))
            if total_fee > 0:
                result.commission = total_fee
    except Exception as e:
        logger.warning("fetch trades for price/fee failed", error=str(e))
```

## 临时解决方案

如果无法立即修复代码，可以：

### 1. 手动补充价格

```sql
-- 根据市场价格补充缺失的成交价
UPDATE fact_order o
SET filled_price = (
    SELECT AVG(price) 
    FROM fact_fill f 
    WHERE f.order_id = o.order_id
)
WHERE o.filled_price = 0 
AND o.status IN (2, 3)
AND EXISTS (
    SELECT 1 FROM fact_fill f WHERE f.order_id = o.order_id
);
```

### 2. 估算手续费

```sql
-- 按 0.05% taker 费率估算（Gate 默认费率）
UPDATE fact_order
SET 
    commission = filled_price * filled_quantity * 0.0005,
    commission_asset = 'USDT'
WHERE commission = 0
AND status IN (2, 3)
AND filled_price > 0
AND filled_quantity > 0
AND created_at > DATE_SUB(NOW(), INTERVAL 7 DAY);
```

## 验证修复

修复后，验证以下几点：

1. **新订单有价格**：
```bash
# 下一个测试单
PYTHONPATH=. python3 scripts/test_isolated_open_close.py --exchange gate --amount 5 --yes

# 检查数据库
mysql> SELECT filled_price, commission FROM fact_order ORDER BY created_at DESC LIMIT 1;
```

2. **日志中有价格和手续费**：
```bash
tail -f tmp/logs/signal-monitor.log | grep "order created"
# 应该看到 filled_price=xxx commission=xxx
```

3. **前端显示正常**：
- 登录管理后台
- 查看订单列表 → 成交价列应有数值
- 查看成交列表 → 成交价和手续费列应有数值

## 预防措施

1. **添加监控告警**：
```python
# 在 libs/monitor/health_checker.py 中添加
def check_zero_price_orders():
    """检查最近是否有价格为 0 的已成交订单"""
    with get_db() as session:
        count = session.query(Order).filter(
            Order.status.in_([2, 3]),
            Order.filled_price == 0,
            Order.created_at > datetime.now() - timedelta(hours=1)
        ).count()
        if count > 0:
            alerter.send_alert(
                level="warning",
                title="订单价格缺失",
                message=f"最近 1 小时有 {count} 个已成交订单价格为 0"
            )
```

2. **添加单元测试**：
```python
# tests/test_gate_price_fee.py
def test_gate_price_parsing():
    """测试 Gate 价格解析"""
    trader = LiveTrader(exchange="gate", ...)
    
    # 模拟 Gate 响应
    response = {
        "id": "123",
        "status": "closed",
        "filled": 0.001,
        "info": {
            "avgPrice": "50000.5",
            "fill_fee": "0.025"
        }
    }
    
    result = trader._parse_order_response(...)
    assert result.filled_price > 0
    assert result.commission > 0
```

3. **配置日志级别**：
```yaml
# config/default.yaml
log_level: DEBUG  # 开发/测试环境
# log_level: INFO  # 生产环境
```

## 相关文件

- `libs/trading/live_trader.py` - 订单执行和响应解析
- `services/execution-node/app/main.py` - 执行节点订单处理
- `services/signal-monitor/app/main.py` - 信号监控和订单创建
- `scripts/debug_gate_price_fee.py` - 诊断脚本
- `docs/ops/LIVE_SMALL_TEST.md` - 实盘测试文档

## 联系支持

如果问题仍未解决，请提供：
1. 诊断脚本输出
2. 最近的日志文件（signal-monitor.log）
3. 数据库查询结果
4. Gate 交易所的原始 API 响应（如有）
