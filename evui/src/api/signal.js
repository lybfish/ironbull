/**
 * 信号监控 API（对接 signal-monitor 的 /signal-api 代理）
 * 使用绝对 URL（origin + /signal-api）避免被全局 baseURL /api 拼成 /api/signal-api/xxx 导致 404
 */
import axios from 'axios'
import setting from '@/config/setting'

function signalApiUrl(path) {
  const base = typeof window !== 'undefined' ? window.location.origin + '/signal-api' : '/signal-api'
  return base + path
}

const signalAxios = axios.create({ timeout: 15000 })

signalAxios.interceptors.request.use((config) => {
  const token = setting.takeToken()
  if (token) {
    config.headers[setting.tokenHeaderName] = 'Bearer ' + token
  }
  return config
}, err => Promise.reject(err))

export function getSignalStatus() {
  return signalAxios.get(signalApiUrl('/status'))
}

export function getSignalConfig() {
  return signalAxios.get(signalApiUrl('/config'))
}

export function updateSignalConfig(data) {
  return signalAxios.post(signalApiUrl('/config'), data)
}

export function getSignalStrategies() {
  return signalAxios.get(signalApiUrl('/strategies'))
}

export function startSignalMonitor() {
  return signalAxios.post(signalApiUrl('/start'))
}

export function stopSignalMonitor() {
  return signalAxios.post(signalApiUrl('/stop'))
}

export function testSignalNotify() {
  return signalAxios.post(signalApiUrl('/test-notify'))
}
