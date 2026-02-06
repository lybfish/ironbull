/**
 * Data API 请求封装
 * 登录后 token 存 localStorage，请求头自动带 Authorization: Bearer <token>
 */
import axios from 'axios'

const TOKEN_KEY = 'ironbull_admin_token'
const ADMIN_NAME_KEY = 'ironbull_admin_name'

const devBase = import.meta.env.VITE_API_BASE_URL != null && import.meta.env.VITE_API_BASE_URL !== ''
  ? import.meta.env.VITE_API_BASE_URL
  : ''
const prodBase = import.meta.env.VITE_API_BASE_URL || ''
const baseURL = import.meta.env.DEV ? devBase : prodBase

const api = axios.create({
  baseURL,
  timeout: 15000,
})

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token, nickname) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
    if (nickname) localStorage.setItem(ADMIN_NAME_KEY, nickname)
  } else {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(ADMIN_NAME_KEY)
  }
}

export function getAdminName() {
  return localStorage.getItem(ADMIN_NAME_KEY) || ''
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ADMIN_NAME_KEY)
}

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      clearToken()
      if (window.location.pathname !== '/login') window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export function setTenantAccount(tenantId, accountId) {
  api.defaults.params = api.defaults.params || {}
  api.defaults.params.tenant_id = tenantId
  if (accountId != null) api.defaults.params.account_id = accountId
}

export async function login(username, password) {
  const { data } = await api.post('/api/auth/login', {
    username: username.trim(),
    password,
  })
  return data
}

// 未登录时仍带默认租户/账户（便于开发）
setTenantAccount(1, 1)

export async function getOrders(params = {}) {
  const { data } = await api.get('/api/orders', { params: { limit: 50, ...params } })
  return data
}

export async function getFills(params = {}) {
  const { data } = await api.get('/api/fills', { params: { limit: 50, ...params } })
  return data
}

export async function getPositions(params = {}) {
  const { data } = await api.get('/api/positions', { params: { limit: 100, ...params } })
  return data
}

export async function getAccounts(params = {}) {
  const { data } = await api.get('/api/accounts', { params: { limit: 50, ...params } })
  return data
}

export async function getTransactions(params = {}) {
  const { data } = await api.get('/api/transactions', { params: { limit: 50, ...params } })
  return data
}

export async function getPerformance(params = {}) {
  const { data } = await api.get('/api/analytics/performance', { params })
  return data
}

export async function getRisk(params = {}) {
  const { data } = await api.get('/api/analytics/risk', { params })
  return data
}

export async function getStatistics(params = {}) {
  const { data } = await api.get('/api/analytics/statistics', { params: { limit: 20, ...params } })
  return data
}

export async function getStrategies(params = {}) {
  const { data } = await api.get('/api/strategies', { params })
  return data
}

export async function getStrategyBindings(params = {}) {
  const { data } = await api.get('/api/strategy-bindings', { params })
  return data
}

export async function getSignalMonitorStatus() {
  const { data } = await api.get('/api/signal-monitor/status')
  return data
}

// ---- Dashboard ----
export async function getDashboardSummary() {
  const { data } = await api.get('/api/dashboard/summary')
  return data
}

// ---- 用户管理 ----
export async function getUsers(params = {}) {
  const { data } = await api.get('/api/users', { params })
  return data
}

// ---- 租户管理 ----
export async function getTenants(params = {}) {
  const { data } = await api.get('/api/tenants', { params })
  return data
}
export async function createTenant(body) {
  const { data } = await api.post('/api/tenants', body)
  return data
}
export async function updateTenant(id, body) {
  const { data } = await api.put(`/api/tenants/${id}`, body)
  return data
}
export async function toggleTenant(id) {
  const { data } = await api.patch(`/api/tenants/${id}/toggle`)
  return data
}
export async function rechargeTenant(id, amount, cardType = 'self') {
  const { data } = await api.post(`/api/tenants/${id}/recharge`, { amount, card_type: cardType })
  return data
}

// ---- 策略绑定 ----
export async function getBindingsAdmin(params = {}) {
  const { data } = await api.get('/api/strategy-bindings-admin', { params })
  return data
}

// ---- 交易所账户 ----
export async function getExchangeAccounts(params = {}) {
  const { data } = await api.get('/api/exchange-accounts', { params })
  return data
}

// ---- 管理员管理 ----
export async function getAdmins(params = {}) {
  const { data } = await api.get('/api/admins', { params })
  return data
}
export async function createAdmin(body) {
  const { data } = await api.post('/api/admins', body)
  return data
}
export async function updateAdmin(id, body) {
  const { data } = await api.put(`/api/admins/${id}`, body)
  return data
}
export async function toggleAdmin(id) {
  const { data } = await api.patch(`/api/admins/${id}/toggle`)
  return data
}
export async function resetAdminPassword(id, newPassword) {
  const { data } = await api.post(`/api/admins/${id}/reset-password`, { new_password: newPassword })
  return data
}

// ---- 配额套餐管理 ----
export async function getQuotaPlans() {
  const { data } = await api.get('/api/quota-plans')
  return data
}
export async function createQuotaPlan(body) {
  const { data } = await api.post('/api/quota-plans', body)
  return data
}
export async function updateQuotaPlan(id, body) {
  const { data } = await api.put(`/api/quota-plans/${id}`, body)
  return data
}
export async function toggleQuotaPlan(id) {
  const { data } = await api.patch(`/api/quota-plans/${id}/toggle`)
  return data
}
export async function assignTenantPlan(tenantId, planId) {
  const { data } = await api.post(`/api/tenants/${tenantId}/assign-plan`, { plan_id: planId })
  return data
}
export async function getQuotaUsage(tenantId, days = 30) {
  const { data } = await api.get(`/api/quota-usage/${tenantId}`, { params: { days } })
  return data
}

export default api
