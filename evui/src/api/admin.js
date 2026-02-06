/**
 * 管理 API — 租户、用户、管理员、策略、绑定、交易所账户
 */
import axios from 'axios'

// ---- 租户 ----
export function getTenants(params = {}) {
  return axios.get('/tenants', {params})
}
export function createTenant(data) {
  return axios.post('/tenants', data)
}
export function updateTenant(id, data) {
  return axios.put(`/tenants/${id}`, data)
}
export function toggleTenant(id) {
  return axios.patch(`/tenants/${id}/toggle`)
}
export function rechargeTenant(id, data) {
  return axios.post(`/tenants/${id}/recharge`, data)
}
export function assignTenantPlan(tenantId, planId) {
  return axios.post(`/tenants/${tenantId}/assign-plan`, {plan_id: planId})
}

// ---- 租户策略实例（按租户管理对用户展示的策略） ----
export function getTenantStrategies(tenantId, params = {}) {
  return axios.get(`/tenants/${tenantId}/tenant-strategies`, {params})
}
export function createTenantStrategy(tenantId, data) {
  return axios.post(`/tenants/${tenantId}/tenant-strategies`, data)
}
export function updateTenantStrategy(tenantId, instanceId, data) {
  return axios.put(`/tenants/${tenantId}/tenant-strategies/${instanceId}`, data)
}
export function copyTenantStrategyFromMaster(tenantId, instanceId) {
  return axios.post(`/tenants/${tenantId}/tenant-strategies/${instanceId}/copy-from-master`)
}
export function deleteTenantStrategy(tenantId, instanceId) {
  return axios.delete(`/tenants/${tenantId}/tenant-strategies/${instanceId}`)
}

// ---- 用户 ----
export function getUsers(params = {}) {
  return axios.get('/users', {params})
}
export function getUserDetail(id) {
  return axios.get(`/users/${id}`)
}
export function rechargeUser(id, data) {
  return axios.post(`/users/${id}/recharge`, data)
}
export function getUserTeam(id, params = {}) {
  return axios.get(`/users/${id}/team`, {params})
}
export function setMarketNode(id, data) {
  return axios.post(`/users/${id}/set-market-node`, data)
}

// ---- 管理员 ----
export function getAdmins(params = {}) {
  return axios.get('/admins', {params})
}
export function createAdmin(data) {
  return axios.post('/admins', data)
}
export function updateAdmin(id, data) {
  return axios.put(`/admins/${id}`, data)
}
export function toggleAdmin(id) {
  return axios.patch(`/admins/${id}/toggle`)
}
export function resetAdminPassword(id, data) {
  return axios.post(`/admins/${id}/reset-password`, data)
}

// ---- 策略 ----
export function getStrategies(params = {}) {
  return axios.get('/strategies', {params})
}
export function getStrategyDetail(id) {
  return axios.get(`/strategies/${id}`)
}
export function updateStrategy(id, data) {
  return axios.post(`/strategies/${id}`, data)
}
export function toggleStrategy(id) {
  return axios.patch(`/strategies/${id}/toggle`)
}
export function getStrategyBindings(params = {}) {
  return axios.get('/strategy-bindings', {params})
}
export function getBindingsAdmin(params = {}) {
  return axios.get('/strategy-bindings-admin', {params})
}

// ---- 交易所账户 ----
export function getExchangeAccounts(params = {}) {
  return axios.get('/exchange-accounts', {params})
}
export function assignNode(accountId, data) {
  return axios.put(`/exchange-accounts/${accountId}/assign-node`, data)
}
export function batchAssignNode(data) {
  return axios.post('/exchange-accounts/batch-assign-node', data)
}
