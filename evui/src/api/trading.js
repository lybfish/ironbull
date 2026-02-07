/**
 * 交易相关 API — 订单、成交、持仓、资金、流水
 */
import axios from 'axios'

// 默认租户（从 localStorage 获取，fallback 为 1）
let defaultParams = {tenant_id: parseInt(localStorage.getItem('ironbull_tenant_id')) || 1}

export function setDefaultTenant(tenantId, accountId) {
  defaultParams = {tenant_id: tenantId}
  if (accountId) {defaultParams.account_id = accountId}
}

function withDefaults(params) {
  return {...defaultParams, ...params}
}

export function getOrders(params = {}) {
  return axios.get('/orders', {params: withDefaults({limit: 50, ...params})})
}

export function getFills(params = {}) {
  return axios.get('/fills', {params: withDefaults({limit: 50, ...params})})
}

export function getPositions(params = {}) {
  return axios.get('/positions', {params: withDefaults({limit: 100, ...params})})
}

export function getAccounts(params = {}) {
  return axios.get('/accounts', {params: withDefaults({limit: 50, ...params})})
}

export function getTransactions(params = {}) {
  return axios.get('/transactions', {params: withDefaults({limit: 50, ...params})})
}

export function submitManualOrder(data) {
  return axios.post('/manual-order', data)
}

export function closePosition(data) {
  return axios.post('/close-position', data)
}
