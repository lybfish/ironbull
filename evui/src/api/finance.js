/**
 * 财务 API — 配额套餐、提现、点卡流水、奖励记录
 */
import axios from 'axios'

// ---- 配额套餐 ----
export function getQuotaPlans(params = {}) {
  return axios.get('/quota-plans', {params})
}
export function createQuotaPlan(data) {
  return axios.post('/quota-plans', data)
}
export function updateQuotaPlan(id, data) {
  return axios.put(`/quota-plans/${id}`, data)
}
export function toggleQuotaPlan(id) {
  return axios.patch(`/quota-plans/${id}/toggle`)
}
export function getQuotaUsage(tenantId, days = 30) {
  return axios.get(`/quota-usage/${tenantId}`, {params: {days}})
}

// ---- 提现 ----
export function getWithdrawals(params = {}) {
  return axios.get('/withdrawals', {params})
}
export function approveWithdrawal(id) {
  return axios.post(`/withdrawals/${id}/approve`)
}
export function rejectWithdrawal(id, reason = '') {
  return axios.post(`/withdrawals/${id}/reject`, {reason})
}
export function completeWithdrawal(id, txHash = '') {
  return axios.post(`/withdrawals/${id}/complete`, {tx_hash: txHash})
}

// ---- 点卡流水 ----
export function getPointcardLogs(params = {}) {
  return axios.get('/pointcard-logs', {params})
}

// ---- 奖励记录 ----
export function getRewards(params = {}) {
  return axios.get('/rewards', {params})
}

// ---- 利润池 ----
export function getProfitPools(params = {}) {
  return axios.get('/profit-pools', {params})
}
export function getProfitPoolStats() {
  return axios.get('/profit-pools/stats')
}
export function retryProfitPool(id) {
  return axios.post(`/profit-pools/${id}/retry`)
}
