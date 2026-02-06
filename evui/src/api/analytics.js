/**
 * 分析 API — Dashboard、绩效、风险、统计
 */
import axios from 'axios'

let defaultParams = {tenant_id: 1}

export function setDefaultTenant(tenantId) {
  defaultParams = {tenant_id: tenantId}
}

export function getDashboardSummary() {
  return axios.get('/dashboard/summary')
}

export function getPerformance(params = {}) {
  return axios.get('/analytics/performance', {params: {...defaultParams, ...params}})
}

export function getRisk(params = {}) {
  return axios.get('/analytics/risk', {params: {...defaultParams, ...params}})
}

export function getStatistics(params = {}) {
  return axios.get('/analytics/statistics', {params: {...defaultParams, limit: 20, ...params}})
}
