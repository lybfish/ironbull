# 线上部署注意事项

部署到生产环境时按本清单逐项确认，避免漏配或安全风险。

---

## 一、部署前必做

### 1. 环境变量（禁止用默认值）

- 在 `deploy/` 下复制 `env.production.example` 为 **`.env.production`**，并**全部改为实际值**。
- **必须修改的项**：
  - `IRONBULL_JWT_SECRET`：用 `openssl rand -hex 32` 生成，不要用示例或空。
  - `IRONBULL_DB_*`：生产 MySQL 地址、账号、密码、库名。
  - `IRONBULL_REDIS_*`：生产 Redis；有密码务必填 `IRONBULL_REDIS_PASSWORD`。
  - `IRONBULL_CORS_ORIGINS`：填管理后台实际域名（如 `https://admin.ironbull.example.com`），逗号分隔多域名。
  - `IRONBULL_NODE_AUTH_SECRET`：中心与执行节点鉴权用，用 `openssl rand -hex 16` 生成。
- 若未创建 `.env.production`，`start.sh` 会提示 “using defaults (NOT recommended for production)”，**线上禁止**依赖默认。

### 2. 数据库

- 确认 MySQL 已安装、已建库（如 `ironbull`），字符集建议 `utf8mb4`。
- **先跑完迁移再启动服务**：按顺序执行 `migrations/` 下 SQL（001 → 013），或使用项目提供的迁移脚本（若有）。未迁移会导致 data-api / merchant-api 启动报错或接口 500。
- 生产库不要用 `config/default.yaml` 里的默认密码（如 `root123456`），应通过 `.env.production` 覆盖。

### 3. Redis

- 确认 Redis 已安装并启动；若设了密码，必须在 `.env.production` 中配置 `IRONBULL_REDIS_PASSWORD`。
- data-api 的 Dashboard 等会用到 Redis 缓存，未配置或连不上会影响接口或性能。

### 4. 安全与密钥

- **不要**把 `.env.production` 提交到 Git；应加入 `.gitignore`，仅在服务器上保留。
- 若使用交易所 API（实盘），勿在 default.yaml 里写死密钥；用环境变量（如 `IRONBULL_EXCHANGE_API_KEY` 等）并在 `.env.production` 中配置。
- default.yaml 中的 `telegram_bot_token`、`exchange_*` 等为示例/开发用，生产一律用环境变量覆盖，避免泄露。

---

## 二、启动方式

- 使用 **`deploy/start.sh`** 或 **Makefile** 管理进程（不要直接前台跑 uvicorn 做生产）：
  - `make start` / `./deploy/start.sh start`   — 启动 data-api、merchant-api、signal-monitor、monitor-daemon
  - `make stop` / `./deploy/start.sh stop`      — 停止
  - `make restart` / `./deploy/start.sh restart` — 重启
  - `make status` — 查看状态
- 启动前在项目根目录执行，且保证已 `chmod +x deploy/start.sh deploy/deploy.sh`。
- 日志与 PID：`tmp/logs/*.log`、`tmp/pids/*.pid`，便于排错与重启。

---

## 三、发布方式概览

- **方式 A（推荐）**：本地一键 `make push-deploy` — 本地 push 后自动 SSH 到线上拉代码并执行发布（需先做一次 `make deploy-setup`）。
- **方式 B**：手动 SSH 登录服务器后，在项目根目录执行 `make deploy` 或 `deploy/deploy.sh`。

---

### 方式 A：本地一键 push + 线上发布（参考 old3）

在**本地**执行，一次配置后即可一键完成：push → SSH 连线上 → 线上拉代码并重启。

#### 1. 首次配置（只需一次）

```bash
make deploy-setup
# 或多环境: make deploy-setup NAME=prod
```

按提示输入：**服务器地址、SSH 端口、用户名、项目在服务器上的路径、Git 远程与分支、线上执行是否使用 sudo**。会生成 `deploy/.deploy.<name>.env`（已加入 .gitignore，勿提交）。建议配置 SSH 免密登录。若部署路径需要 root 权限（如 `/opt/ironbull`），可选择「线上执行使用 sudo」。

#### 2. 线上首次无代码时（创建目录并 clone）

若服务器上还没有项目目录或未 clone 过仓库，可任选其一：

- **方式一**：先单独执行一次初始化（在服务器上创建 `DEPLOY_PATH` 并 clone）：
  ```bash
  make deploy-init
  # 或 make deploy-init NAME=prod
  ```
- **方式二**：直接执行 `make push-deploy`，脚本会检测到线上无仓库并自动执行上述初始化，再继续拉代码与发布。

#### 3. 日常发布

```bash
make push-deploy                    # 推送当前分支 → 线上 pull + 迁移 + 重启
make push-deploy BUILD=1            # 含线上构建 admin-web
make push-deploy NO_MIGRATE=1       # 不跑迁移
make push-deploy DRY_RUN=1          # 试跑，不实际执行
make push-deploy NAME=prod          # 使用名为 prod 的配置
```

**说明**：若线上尚未初始化（无代码），`push-deploy` 会自动在服务器上创建配置中的路径并执行 `git clone`，再继续发布。

---

### 方式 B：在服务器上拉代码并发布

SSH 登录服务器后，在**项目根目录**执行：

#### 1. 仅拉取代码（不迁移、不重启）

```bash
cd /path/to/ironbull
make deploy-pull
# 或: git pull
```

#### 2. 拉代码 + 迁移 + 重启（常用）

```bash
make deploy
```

等价于：`git pull` → `make migrate-013` → `make restart`。  
若本次没有数据库变更：`make deploy NO_MIGRATE=1`。

#### 3. 含前端构建

```bash
make deploy-build
```

#### 4. 试跑

```bash
make deploy DRY_RUN=1
```

#### 5. 直接调脚本

- `./deploy/deploy.sh` — 拉代码 + 迁移 + 重启
- `./deploy/deploy.sh --no-migrate` — 不跑迁移
- `./deploy/deploy.sh --build` — 含 admin-web 构建
- `./deploy/deploy.sh --dry-run` — 仅打印步骤

---

## 四、Nginx 与前端

- 使用 `deploy/nginx.conf` 作参考（可复制到 `/etc/nginx/sites-enabled/` 并软链）。
- **必须修改**：
  - `server_name` 改为实际域名（如 `admin.ironbull.example.com`、`api.ironbull.example.com`）。
  - `root` 改为 admin-web 构建产物的实际路径（如 `/opt/ironbull/services/admin-web/dist`）。
- **生产强烈建议开启 HTTPS**：在 nginx 中配置 `listen 443 ssl`、证书路径，并做 http→https 跳转。
- 当前配置约定：
  - 管理后台域名下 `/api/`、`/health` 反向代理到 **data-api (8026)**。
  - 商户 API 独立域名或端口代理到 **merchant-api (8010)**。
- admin-web 构建：在 `services/admin-web` 下执行 `npm run build`。若管理后台与 API 同域（通过 Nginx 代理 `/api/`），一般**不需**设置 `VITE_API_BASE_URL`（相对路径即可）；若前后端不同域，需在构建时指定 `VITE_API_BASE_URL` 为 data-api 的完整地址。

---

## 五、端口与进程

- 生产只需暴露/使用以下端口（详见 `docs/ops/PORTS_AND_FLOW.md`）：
  - **8026** data-api  
  - **8010** merchant-api  
  - **8020** signal-monitor  
- 确保 8000–8006、8030、9101/9102 等实验链路端口未占用本机关键服务即可；若不跑策略/回测，可不启动对应进程。
- 防火墙/安全组：只开放 80/443 给 Nginx，8026/8010/8020 仅本机或内网访问，不对外。

---

## 六、上线后建议

- 定期查看 `tmp/logs/*.log` 与 Nginx 的 `access_log`/`error_log`，排查 5xx 与异常请求。
- 管理后台「系统监控」依赖 monitor-daemon 与 data-api 的 `/api/monitor/status`，确认 monitor-daemon 已随 `start.sh` 启动。
- 若启用 Telegram 告警，在 `.env.production` 中配置 `IRONBULL_TELEGRAM_BOT_TOKEN` 与 `IRONBULL_TELEGRAM_CHAT_ID`。
- 数据库与 Redis 建议做备份与高可用；生产环境勿使用 `trading_mode: live` 与实盘密钥除非已充分验证。

---

## 七、快速自检

| 项 | 命令/方式 |
|----|-----------|
| 环境变量是否加载 | `./deploy/start.sh start` 看是否输出 “Loaded env from .../.env.production” |
| 服务是否起来 | `./deploy/start.sh status` 四个均为 running |
| data-api 健康 | `curl -s http://127.0.0.1:8026/health` |
| merchant-api 健康 | `curl -s http://127.0.0.1:8010/health` |
| 管理后台能否登录 | 浏览器访问配置的 admin 域名，用 009 迁移中的 admin 账号（或自建）登录 |

完成以上各项后，线上部署即可按流程稳定运行；有变更（如改域名、加 HTTPS、换 DB）时再对应更新 `.env.production` 与 Nginx 配置。
