# 端口与流程说明

本文档统一说明各服务端口分配及两条主流程，避免端口冲突与启动顺序混乱。

## 一、端口分配表

| 端口 | 服务 | 说明 | 由谁启动 |
|------|------|------|----------|
| **8000** | strategy-engine | 策略引擎（K 线分析 → 信号） | 实验/本地 |
| **8001** | signal-hub | 信号中心 | 实验/本地 |
| **8002** | risk-control | 风控 | 实验/本地 |
| **8003** | execution-dispatcher | 执行调度 | 实验/本地 |
| **8004** | follow-service | 跟单服务 | 实验/本地 |
| **8005** | data-provider | 行情/数据提供 | 实验/本地 |
| **8006** | strategy-runner | 策略定时运行 | 实验/本地 |
| **8010** | merchant-api | 商户/用户 API（点卡、流水等） | `deploy/start.sh` |
| **8020** | signal-monitor | 信号监控（管理后台用） | `deploy/start.sh` |
| **8026** | data-api | 数据与监控 API（订单、成交、Dashboard） | `deploy/start.sh` |
| **8030** | backtest | 回测服务（Flask） | 实验/本地 |
| **9101** | crypto-node / execution-node | 加密节点 / 执行节点默认端口 | 实验/本地 或 节点 |
| **9102** | mt5-node | MT5 节点 | 实验/本地 |
| — | monitor-daemon | 监控守护进程（无 HTTP 端口） | `deploy/start.sh` |

**重要**：`data-provider` 固定为 **8005**，不要与 `merchant-api`（8010）混用。配置里 `data_provider_url` 应对应 8005。

---

## 二、两条主流程

### 1. 生产核心链路（当前 deploy/start.sh 管理的）

```
用户/商户请求
    → merchant-api (8010)   # 点卡、流水、用户信息等
    → data-api (8026)      # 订单、成交、Dashboard、监控状态
    → signal-monitor (8020) # 管理后台看信号状态（代理到 signal-hub 等）
    → monitor-daemon       # 健康检查、告警（无端口）
```

- **前端**：admin-web 通常通过 Nginx 反向代理到 8010 / 8026 / 8020，不直接记端口。
- **依赖**：data-api / merchant-api 依赖 MySQL、Redis 等，不依赖 8000–8006 的实验链路即可运行。

### 2. 实验/策略链路（v0 本地复现用）

```
策略/回测
    → strategy-engine (8000)   # 策略计算
    → signal-hub (8001)        # 信号汇聚
    → risk-control (8002)      # 风控
    → execution-dispatcher (8003)  # 分发
    → crypto-node (9101) / mt5-node (9102)  # 执行

数据与定时
    → data-provider (8005)     # K 线等数据
    → strategy-runner (8006)  # 定时跑策略，调 data-provider
    → follow-service (8004)   # 跟单
    → backtest (8030)         # 回测
```

- 启动顺序建议见 `docs/ops/STARTUP.md`。
- 与生产核心链路**端口完全分离**：生产用 8010/8020/8026，实验用 8000–8006、8030、9101/9102。

---

## 三、配置与文档对应关系

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| `data_provider_url` | `http://127.0.0.1:8005` | data-provider 地址，勿用 8010（与 merchant-api 冲突） |
| `signal_monitor_url` | `http://127.0.0.1:8020` | signal-monitor 地址（管理后台） |
| `signal_hub` / `risk` / `execution_dispatcher` 等 | 见 `config/default.yaml` | 与 STARTUP.md 端口一致 |

---

## 四、常见问题

- **Q：为什么 config 里曾经是 data_provider_url: 8010？**  
  A：历史笔误，8010 已固定为 merchant-api。data-provider 应为 8005，已在 `config/default.yaml` 中修正。

- **Q：只跑生产环境，需要开 8000–8006 吗？**  
  A：不需要。只启动 `deploy/start.sh` 的四个进程即可（data-api、merchant-api、signal-monitor、monitor-daemon）。

- **Q：admin-web 访问的 API 端口？**  
  A：由 Nginx 或前端环境变量决定，通常代理到 8010（merchant-api）、8026（data-api）、8020（signal-monitor），见部署侧配置。
