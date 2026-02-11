# MT5 Node Agent

Windows 端节点代理，用于连接 Linux 服务器的 mt5-node 中控服务。

## 功能特性

- **WebSocket 通信**: 主动连接服务器，支持反向连接（无需公网 IP）
- **MT5 集成**: 连接本地 MT5 终端执行真实交易
- **心跳保活**: 30 秒心跳，维持连接稳定
- **数据采集**: 自动采集 K 线、余额、持仓数据上报服务器
- **Mock 模式**: 无 MT5 环境时可运行 Mock 模式测试

## 系统要求

- **操作系统**: Windows 10/11
- **Python**: 3.8+ (打包后无需安装 Python)
- **MT5**: MetaTrader 5 终端 (可选，Mock 模式不需要)

## 快速开始

### 方式一：直接运行 Python 脚本

```powershell
# 1. 安装依赖
pip install -r requirements.txt

# 2. 创建配置文件
copy config.yaml.sample config.yaml
# 编辑 config.yaml，填写服务器地址和 MT5 账户信息

# 3. 运行
python main.py
```

### 方式二：使用打包后的 EXE

```powershell
# 1. 从 GitHub Releases 下载 mt5-node-agent.exe

# 2. 创建配置文件
copy config.yaml.sample config.yaml
# 编辑 config.yaml，填写服务器地址和 MT5 账户信息

# 3. 双击运行 mt5-node-agent.exe
```

## 配置说明

### config.yaml 配置项

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `server_url` | Linux 服务器地址 | `your-server.com:9102` |
| `node_id` | 节点唯一标识 | `node_001` |
| `mt5.login` | MT5 账户登录名 | `123456` |
| `mt5.password` | MT5 账户密码 | `your_password` |
| `mt5.server` | MT5 服务器名称 | `ICMarkets-Demo` |
| `mt5.path` | MT5 终端路径 (可选) | `C:/Program Files/...` |
| `symbols` | 监控品种列表 | `["EURUSD", "XAUUSD"]` |
| `timeframe` | K 线时间周期 | `H1` |
| `heartbeat_interval` | 心跳间隔 (秒) | `30` |
| `kline_interval` | K 线上报间隔 (秒) | `60` |
| `balance_interval` | 余额上报间隔 (秒) | `300` |
| `log_level` | 日志级别 | `INFO` |

### 时间周期可选值

- `M1`: 1 分钟
- `M5`: 5 分钟
- `M15`: 15 分钟
- `M30`: 30 分钟
- `H1`: 1 小时
- `H4`: 4 小时
- `D1`: 日线
- `W1`: 周线
- `MN1`: 月线

## 打包 EXE

```powershell
# 1. 安装打包工具
pip install pyinstaller

# 2. 打包
pyinstaller pyinstaller.spec

# 3. 输出位置
# dist/mt5-node-agent/mt5-node-agent.exe
```

## 运行日志

程序运行时会输出日志，日志级别由 `log_level` 配置：

```
2024-01-01 12:00:00 | INFO     | Starting MT5 Node Agent v1.0.0
2024-01-01 12:00:00 | INFO     | Node ID: node_001
2024-01-01 12:00:00 | INFO     | Connecting to server: ws://your-server.com:9102/ws/node/node_001
2024-01-01 12:00:01 | INFO     | Connected to server
2024-01-01 12:00:01 | INFO     | Registered successfully: 2024-01-01T12:00:01
2024-01-01 12:00:01 | INFO     | Agent started successfully
```

## 常见问题

### Q: 连接服务器失败

A: 检查以下几点：
1. 服务器地址是否正确
2. 服务器的 mt5-node 服务是否启动
3. 防火墙是否允许出站连接

### Q: MT5 连接失败

A: 检查以下几点：
1. MT5 终端是否已启动
2. 账户登录名、密码、服务器是否正确
3. MT5 终端路径是否正确（如果配置了 path）

### Q: 如何开机自启

A: 将 mt5-node-agent.exe 或快捷方式添加到启动文件夹：
1. 按 `Win + R`
2. 输入 `shell:startup`
3. 将 exe 文件或快捷方式复制到该文件夹

## 协议

MIT License
