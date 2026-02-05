# IronBull 管理后台（Vue 3）

Vue 3 + Vite + Element Plus，对接 data-api（8026）做订单、持仓、资金、绩效查询与展示。

## 安装与运行

```bash
cd services/admin-web
npm install
npm run dev
```

浏览器访问：http://localhost:5174

## 构建

```bash
npm run build
```

产物在 `dist/`，可部署到 nginx 等；需配置 API 代理或环境变量 `VITE_API_BASE_URL` 指向 data-api（如 `http://your-host:8026`）。

## 依赖服务（必先启动）

**先启动 data-api**，否则接口会报错、页面数据为空：

```bash
cd services/data-api
PYTHONPATH=../.. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8026
```

前端默认直连 `http://127.0.0.1:8026`（`.env.development`），data-api 已开 CORS 允许 localhost:5174/5175。  
若想用 Vite 代理代替直连，可删掉或注释 `.env.development` 里的 `VITE_API_BASE_URL`，并在 vite.config.js 中把 proxy target 设为 8026。

## 页面

- **概览**：订单/成交/持仓数量、绩效摘要
- **订单 / 成交 / 持仓 / 资金账户 / 流水**：表格列表
- **绩效分析**：绩效汇总、净值曲线（ECharts）、风险指标

顶部可切换租户 ID、账户 ID（默认 1/1），切换后刷新页面以重新拉取数据。未登录访问任意页会跳转登录页；登录后请求自动带 `Authorization: Bearer <token>`。
