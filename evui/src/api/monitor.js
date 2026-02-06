/**
 * 系统监控 API
 */
import axios from 'axios'

export function getMonitorStatus() {
  return axios.get('/monitor/status')
}

export function getAuditLogs(params = {}) {
  return axios.get('/audit-logs', {params})
}
