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

// ---- 账户分配 ----
export function getExchangeAccounts(params = {}) {
  return axios.get('/exchange-accounts', {params})
}
export function assignNode(accountId, data) {
  return axios.put(`/exchange-accounts/${accountId}/assign-node`, data)
}
export function batchAssignNode(data) {
  return axios.post('/exchange-accounts/batch-assign-node', data)
}

// ---- 同步 ----
export function syncBalance(data = {}) {
  return axios.post('/sync/balance', data)
}
export function syncPositions(data = {}) {
  return axios.post('/sync/positions', data)
}
