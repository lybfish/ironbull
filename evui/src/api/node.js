/**
 * 节点 API — 执行节点 CRUD、账户分配、同步
 */
import axios from 'axios'

// ---- 节点 CRUD ----
export function getNodes(params = {}) {
  return axios.get('/nodes', {params})
}
export function createNode(data) {
  return axios.post('/nodes', data)
}
export function updateNode(id, data) {
  return axios.put(`/nodes/${id}`, data)
}
export function deleteNode(id) {
  return axios.delete(`/nodes/${id}`)
}
export function getNodeAccounts(id) {
  return axios.get(`/nodes/${id}/accounts`)
}

// ---- 同步 ----
export function syncBalance(data = {}) {
  return axios.post('/sync/balance', data)
}
export function syncPositions(data = {}) {
  return axios.post('/sync/positions', data)
}
export function syncTrades(data = {}) {
  return axios.post('/sync/trades', data)
}
export function syncMarkets(data = {}) {
  return axios.post('/sync/markets', data)
}
export function getMarkets(params = {}) {
  return axios.get('/sync/markets', { params })
}

// ---- 持仓监控(SL/TP) ----
export function getPositionMonitorStatus() {
  return axios.get('/signal-monitor/status')
}
export function getMonitoredPositions() {
  return axios.get('/sync/monitored-positions')
}
export function triggerPositionMonitorScan() {
  return axios.post('/signal-monitor/trigger-scan')
}
export function getRealtimePrices(symbols, exchangeSymbols) {
  const params = { symbols }
  if (exchangeSymbols) params.exchange_symbols = exchangeSymbols
  return axios.get('/signal-monitor/realtime-prices', { params })
}
