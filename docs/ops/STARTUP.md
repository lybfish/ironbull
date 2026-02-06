# IronBull v0 — Startup Guide

本指南用于本地一键复现实验链路（v0）。

- **端口与流程总览**（含生产 vs 实验、端口冲突说明）：`docs/ops/PORTS_AND_FLOW.md`
- 相关规范：`docs/ops/ERRORS_AND_LOGGING.md`

## 端口一览
- `strategy-engine`: 8000
- `signal-hub`: 8001
- `risk-control`: 8002
- `execution-dispatcher`: 8003
- `follow-service`: 8004
- `data-provider`: 8005
- `strategy-runner`: 8006
- `backtest`: 8030
- `crypto-node`: 9101
- `mt5-node`: 9102

## 启动顺序（建议）
1. `signal-hub`
2. `risk-control`
3. `execution-dispatcher`
4. `crypto-node`
5. `mt5-node`
6. `strategy-engine`
7. `data-provider`
8. `follow-service`
9. `strategy-runner`
10. `backtest`

## 启动命令
> 统一方式：使用 `python3 -m uvicorn`（避免 `uvicorn` 不在 PATH）

```bash
# signal-hub
cd services/signal-hub
PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

```bash
# risk-control
cd services/risk-control
PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```

```bash
# execution-dispatcher
cd services/execution-dispatcher
PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8003
```

```bash
# crypto-node
cd nodes/crypto-node
PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 9101
```

```bash
# mt5-node
cd nodes/mt5-node
PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 9102
```

```bash
# strategy-engine
cd services/strategy-engine
PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```bash
# data-provider
cd services/data-provider
PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8005
```

```bash
# follow-service
cd services/follow-service
PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8004
```

```bash
# strategy-runner
cd services/strategy-runner
PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8006
```

```bash
# backtest (Flask)
cd services/backtest
PYTHONPATH=../.. python3 app/main.py
```

## Demo 脚本
```bash
# 最小链路：Signal → Risk → Dispatcher → Node
./scripts/demo_flow.sh

# 策略引擎：K 线分析 → Signal → Risk → Dispatcher → Node
./scripts/demo_strategy_engine.sh

# Data Provider：candles / mtf / macro
./scripts/demo_data_provider.sh

# Follow Service：关系创建 + 广播
./scripts/demo_follow_service.sh

# Strategy Runner：任务管理与触发
./scripts/demo_strategy_runner.sh

# Backtest：策略回测（历史数据验证）
./scripts/demo_backtest.sh
```

## 常见问题
- `uvicorn: command not found`
  - 使用 `python3 -m uvicorn` 启动。
- `ModuleNotFoundError: No module named 'libs'`
  - 启动命令前加 `PYTHONPATH=../..`。
