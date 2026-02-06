#!/usr/bin/env bash
# 遍历 data-api 所有接口并记录 HTTP 状态码（需本地 data-api 运行在 8026，且存在 admin/admin123）
set -e
BASE="http://127.0.0.1:8026"
TOKEN=""

login() {
  local res
  res=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/auth/login" -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}')
  local code=$(echo "$res" | tail -n1)
  if [ "$code" = "200" ]; then
    TOKEN=$(echo "$res" | head -n-1 | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))")
  fi
  echo "$code"
}

req() {
  local method=$1
  local path=$2
  local extra=${3:-}
  local url="$BASE$path"
  local curl_cmd="curl -s -o /dev/null -w %{http_code} -X $method $url"
  [ -n "$TOKEN" ] && curl_cmd="$curl_cmd -H \"Authorization: Bearer $TOKEN\""
  [ -n "$extra" ] && curl_cmd="$curl_cmd $extra"
  eval "$curl_cmd"
}

echo "=== Data-API 接口测试 ==="
echo "1. 登录 (admin/admin123)..."
login_code=$(login)
if [ "$login_code" != "200" ]; then
  echo "登录失败 HTTP $login_code，无法继续（请确认 dim_admin 存在用户 admin 密码 admin123）"
  exit 1
fi
echo "登录成功，token 已获取"
echo ""

echo "2. 逐个请求（仅记录状态码）"
echo "METHOD PATH -> CODE"
echo "----------------------------------------"

# GET 类（需 tenant_id 的加 ?tenant_id=1）
get_routes=(
  "/health"
  "/api/strategies"
  "/api/strategies?tenant_id=1"
  "/api/strategies/1"
  "/api/strategy-bindings?tenant_id=1"
  "/api/strategy-bindings-admin?page=1&page_size=5"
  "/api/tenants/1/tenant-strategies"
  "/api/tenants?page=1&page_size=5"
  "/api/users?tenant_id=1&page=1&page_size=5"
  "/api/accounts?tenant_id=1"
  "/api/orders?tenant_id=1&limit=2"
  "/api/fills?tenant_id=1&limit=2"
  "/api/positions?tenant_id=1&limit=2"
  "/api/transactions?tenant_id=1&limit=2"
  "/api/analytics/performance?tenant_id=1"
  "/api/analytics/risk?tenant_id=1"
  "/api/analytics/statistics?tenant_id=1"
  "/api/dashboard/summary"
  "/api/admins"
  "/api/nodes"
  "/api/exchange-accounts"
  "/api/quota-plans"
  "/api/quota-usage/1"
  "/api/withdrawals?page=1&page_size=5"
  "/api/audit-logs?page=1&page_size=5"
  "/api/monitor/status"
  "/api/auth/me"
  "/api/pointcard-logs?page=1&page_size=5"
  "/api/rewards?page=1&page_size=5"
)
for path in "${get_routes[@]}"; do
  code=$(req GET "$path")
  echo "GET  $path -> $code"
done

# POST 租户策略实例（会 200 或 400/404）
code=$(req POST "/api/tenants/1/tenant-strategies" "-H \"Content-Type: application/json\" -d '{\"strategy_id\":1,\"copy_from_master\":true,\"status\":1,\"sort_order\":0}'")
echo "POST /api/tenants/1/tenant-strategies -> $code"

# GET 列表 again（若有实例）
code=$(req GET "/api/tenants/1/tenant-strategies")
echo "GET  /api/tenants/1/tenant-strategies (again) -> $code"

# PUT 更新租户策略实例（instance_id 可能不存在，预期 200/404）
code=$(req PUT "/api/tenants/1/tenant-strategies/1" "-H \"Content-Type: application/json\" -d '{\"sort_order\":1}'")
echo "PUT  /api/tenants/1/tenant-strategies/1 -> $code"

# POST copy-from-master（可能 404 若实例不存在）
code=$(req POST "/api/tenants/1/tenant-strategies/1/copy-from-master")
echo "POST /api/tenants/1/tenant-strategies/1/copy-from-master -> $code"

# DELETE 租户策略实例（可能 404）
code=$(req DELETE "/api/tenants/1/tenant-strategies/99999")
echo "DELETE /api/tenants/1/tenant-strategies/99999 -> $code"

echo "----------------------------------------"
echo "完成（5xx 需排查，401=未带 token 或过期）"
