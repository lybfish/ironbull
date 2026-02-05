/**
 * Data API 请求封装
 * 登录后 token 存 localStorage，请求头自动带 Authorization: Bearer <token>
 */
import axios from 'axios'

const TOKEN_KEY = 'ironbull_admin_token'

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

const LOGIN_EMAIL_KEY = 'ironbull_admin_email'

export function setToken(token, email) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
    if (email) localStorage.setItem(LOGIN_EMAIL_KEY, email)
  } else {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(LOGIN_EMAIL_KEY)
  }
}

export function getLoginEmail() {
  return localStorage.getItem(LOGIN_EMAIL_KEY) || ''
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(LOGIN_EMAIL_KEY)
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

export async function login(tenantId, email, password) {
  const { data } = await api.post('/api/auth/login', {
    tenant_id: tenantId,
    email: email.trim(),
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

export default api
