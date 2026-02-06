# ============================================================
# IronBull Makefile（参考 old3 quanttrade 用法）
# 用法: make [target] [VAR=value]
# 默认: make / make help
# ============================================================

SHELL    := /bin/bash
ROOT     := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
DEPLOY   := $(ROOT)deploy
SCRIPTS  := $(ROOT)scripts
SERVICES := $(ROOT)services

# 可选：只操作指定服务，多个用空格分隔。例: make start SVC="data-api merchant-api"
SVC      ?=

.PHONY: help start stop restart status health test admin-install admin-build admin-dev node-bundle migrate migrate-013 clean deploy deploy-pull deploy-build deploy-setup deploy-init push-deploy deploy-child-setup deploy-child deploy-child-restart deploy-child-batch-setup deploy-child-batch deploy-child-batch-restart

# ---------------------------------------------------------------------------
# 默认目标
# ---------------------------------------------------------------------------
help:
	@echo ""
	@echo "  IronBull 常用命令"
	@echo "  =================="
	@echo "  服务（生产，deploy/start.sh）："
	@echo "    make start [SVC=data-api]       启动全部或指定服务"
	@echo "    make stop [SVC=signal-monitor]  停止全部或指定服务"
	@echo "    make restart [SVC=...]          重启"
	@echo "    make status [SVC=...]           查看状态"
	@echo "  健康检查："
	@echo "    make health [SVC=data-api|merchant-api|signal-monitor|all]"
	@echo "  测试："
	@echo "    make test                       运行 pytest"
	@echo "  管理后台 (admin-web)："
	@echo "    make admin-install              安装依赖"
	@echo "    make admin-build                构建 dist"
	@echo "    make admin-dev                  开发模式 (vite)"
	@echo "  打包/部署子服务器（执行节点）："
	@echo "    make node-bundle                仅打出 dist/execution-node/"
	@echo "    make deploy-child-setup [NAME=] 首次配置子机（主机、路径、端口、免密）"
	@echo "    make deploy-child [NAME=]       一键：构建→同步到子机→重启（目录无则创建）"
	@echo "    make deploy-child SKIP_BUILD=1  仅同步+重启，不重新 build"
	@echo "    make deploy-child-restart [NAME=] 仅重启子机节点"
	@echo "  批量部署多台子机（Linux，同一路径/端口）："
	@echo "    make deploy-child-batch-setup   首次配置多台子机地址与免密"
	@echo "    make deploy-child-batch         构建→同步到所有子机→逐台重启"
	@echo "    make deploy-child-batch SKIP_BUILD=1  仅同步+逐台重启"
	@echo "    make deploy-child-batch-restart 仅批量重启所有子机节点"
	@echo "  数据库："
	@echo "    make migrate-013                执行迁移 013（幂等）"
	@echo "  线上发布："
	@echo "    make deploy-setup [NAME=prod]   首次配置（服务器、路径、分支）"
	@echo "    make deploy-init [NAME=xxx]     线上首次：创建目录并 clone 仓库"
	@echo "    make push-deploy [NAME=xxx]      本地 push + 连线上拉代码并发布（一键）"
	@echo "    make push-deploy BUILD=1         含线上构建 admin-web"
	@echo "    make push-deploy NO_MIGRATE=1    不跑迁移"
	@echo "  线上发布（仅 SSH 到服务器后执行）："
	@echo "    make deploy-pull                仅拉取代码"
	@echo "    make deploy                     拉代码 + 迁移 + 重启"
	@echo "    make deploy-build               拉代码 + 迁移 + 构建 admin + 重启"
	@echo "  清理："
	@echo "    make clean                      清理 tmp/pids、tmp/logs"
	@echo ""
	@echo "  服务名: data-api merchant-api signal-monitor monitor-daemon"
	@echo ""

# ---------------------------------------------------------------------------
# 服务：启动 / 停止 / 重启 / 状态（委托 deploy/start.sh）
# ---------------------------------------------------------------------------
start:
	@$(DEPLOY)/start.sh start $(SVC)

stop:
	@$(DEPLOY)/start.sh stop $(SVC)

restart:
	@$(DEPLOY)/start.sh restart $(SVC)

status:
	@$(DEPLOY)/start.sh status $(SVC)

# ---------------------------------------------------------------------------
# 健康检查（curl 各服务 /health）
# ---------------------------------------------------------------------------
health:
	@echo "=== Health check ==="
	@if [ -z "$(SVC)" ] || [ "$(SVC)" = "all" ]; then \
		echo -n "data-api (8026):    "; curl -sf http://127.0.0.1:8026/health && echo " OK" || echo " FAIL"; \
		echo -n "merchant-api (8010): "; curl -sf http://127.0.0.1:8010/health && echo " OK" || echo " FAIL"; \
		echo -n "signal-monitor(8020): "; curl -sf http://127.0.0.1:8020/health && echo " OK" || echo " FAIL"; \
	elif [ "$(SVC)" = "data-api" ]; then \
		curl -sf http://127.0.0.1:8026/health && echo " OK" || (echo " FAIL"; exit 1); \
	elif [ "$(SVC)" = "merchant-api" ]; then \
		curl -sf http://127.0.0.1:8010/health && echo " OK" || (echo " FAIL"; exit 1); \
	elif [ "$(SVC)" = "signal-monitor" ]; then \
		curl -sf http://127.0.0.1:8020/health && echo " OK" || (echo " FAIL"; exit 1); \
	else \
		echo "SVC 可选: data-api | merchant-api | signal-monitor | all"; exit 1; \
	fi

# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------
test:
	cd $(ROOT) && PYTHONPATH=$(ROOT) python3 -m pytest tests -v --tb=short

# ---------------------------------------------------------------------------
# 管理后台 admin-web
# ---------------------------------------------------------------------------
admin-install:
	cd $(SERVICES)/admin-web && npm install

admin-build:
	cd $(SERVICES)/admin-web && npm run build

admin-dev:
	cd $(SERVICES)/admin-web && npm run dev

# ---------------------------------------------------------------------------
# 打包子服务器（执行节点独立部署包 → dist/execution-node/）
# ---------------------------------------------------------------------------
node-bundle:
	cd $(ROOT) && PYTHONPATH=$(ROOT) python3 $(SCRIPTS)/build_node_bundle.py
	@echo "已生成 dist/execution-node/，可拷贝到子服务器后 pip install -r requirements.txt && uvicorn 运行"

# ---------------------------------------------------------------------------
# 数据库迁移
# ---------------------------------------------------------------------------
migrate-013:
	cd $(ROOT) && PYTHONPATH=$(ROOT) python3 scripts/run_migration_013.py

# ---------------------------------------------------------------------------
# 线上发布
# ---------------------------------------------------------------------------
# 首次：在本地执行一次，生成 deploy/.deploy.<name>.env（勿提交）
deploy-setup:
	@$(DEPLOY)/deploy-setup.sh $(NAME)

# 线上首次：在服务器上创建目录并 clone 仓库（需先 make deploy-setup）
deploy-init:
	@NAME="$(NAME)" DRY_RUN="$(DRY_RUN)" $(DEPLOY)/deploy-init.sh $(NAME)

# 本地一键：push 后 SSH 到线上拉代码并执行 deploy（若线上无代码会先执行 deploy-init）
push-deploy:
	@NO_MIGRATE="$(NO_MIGRATE)" BUILD="$(BUILD)" DRY_RUN="$(DRY_RUN)" NAME="$(NAME)" $(DEPLOY)/push-and-deploy.sh $(NAME)

# 以下在服务器上执行（SSH 登录后 cd 到项目根目录）
deploy-pull:
	@git pull

deploy:
	@$(DEPLOY)/deploy.sh

deploy-build:
	@BUILD=1 $(DEPLOY)/deploy.sh

# ---------------------------------------------------------------------------
# 子服务器（执行节点）一键部署
# ---------------------------------------------------------------------------
deploy-child-setup:
	@NAME="$(NAME)" $(DEPLOY)/deploy-child-setup.sh $(NAME)

deploy-child:
	@NAME="$(NAME)" SKIP_BUILD="$(SKIP_BUILD)" $(DEPLOY)/deploy-child.sh $(NAME)

deploy-child-restart:
	@NAME="$(NAME)" $(DEPLOY)/deploy-child-restart.sh $(NAME)

# 批量部署多台 Linux 子机（同一路径/用户/端口）
deploy-child-batch-setup:
	@$(DEPLOY)/deploy-child-batch-setup.sh

deploy-child-batch:
	@SKIP_BUILD="$(SKIP_BUILD)" $(DEPLOY)/deploy-child-batch.sh

deploy-child-batch-restart:
	@$(DEPLOY)/deploy-child-batch-restart.sh

# ---------------------------------------------------------------------------
# 清理
# ---------------------------------------------------------------------------
clean:
	rm -rf $(ROOT)tmp/pids $(ROOT)tmp/logs
	@echo "Cleaned tmp/pids and tmp/logs"
