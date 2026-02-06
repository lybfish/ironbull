/**
 * 认证相关 API
 */
import axios from 'axios'

export function login(data) {
  return axios.post('/auth/login', data)
}

export function getUserInfo() {
  return axios.get('/auth/me')
}

export function changePassword(data) {
  return axios.post('/auth/change-password', data)
}
