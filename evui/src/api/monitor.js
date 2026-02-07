/**
 * 系统监控 API
 */
import axios from 'axios'

export function getMonitorStatus() {
  return axios.get('/monitor/status')
}

export function getMonitorMetrics(days = 7) {
  return axios.get('/monitor/metrics', {params: {days}})
}

export function getAuditLogs(params = {}) {
  return axios.get('/audit-logs', {params})
}

export function exportAuditLogs(params = {}) {
  return axios.get('/audit-logs/export', {params, responseType: 'blob'})
}

export function getAuditLogStats(days = 30) {
  return axios.get('/audit-logs/stats', {params: {days}})
}

// ---- 用户分析 ----
export function getUserAnalyticsOverview(days = 30) {
  return axios.get('/user-analytics/overview', {params: {days}})
}

export function getUserRanking(params = {}) {
  return axios.get('/user-analytics/ranking', {params})
}

export function getUserGrowth(days = 30) {
  return axios.get('/user-analytics/growth', {params: {days}})
}

// ---- 批量操作 ----
export function batchToggleUsers(data) {
  return axios.post('/batch/toggle-users', data)
}

export function batchRechargeUsers(data) {
  return axios.post('/batch/recharge-users', data)
}

export function batchBindStrategy(data) {
  return axios.post('/batch/bind-strategy', data)
}

// ---- 风控 ----
export function getRiskRules() {
  return axios.get('/risk/rules')
}

export function updateRiskRules(data) {
  return axios.put('/risk/rules', data)
}

export function getRiskViolations(days = 7) {
  return axios.get('/risk/violations', {params: {days}})
}
