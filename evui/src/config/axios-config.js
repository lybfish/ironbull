/**
 * axios配置 — 适配 IronBull data-api
 */
import Vue from 'vue'
import VueAxios from 'vue-axios'
import axios from 'axios'
import store from '../store'
import router from '../router'
import setting from './setting'
import {MessageBox} from 'element-ui'

Vue.use(VueAxios, axios)

// 设置统一的url
axios.defaults.baseURL = process.env.VUE_APP_API_BASE_URL

/* 请求拦截器 */
axios.interceptors.request.use((config) => {
  // 添加token到header
  const token = setting.takeToken()
  if (token) {
    config.headers[setting.tokenHeaderName] = 'Bearer ' + token
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

/* 响应拦截器 — 适配 IronBull data-api 格式 */
axios.interceptors.response.use((res) => {
  // IronBull data-api 使用 HTTP 状态码，成功时直接返回
  return res
}, (error) => {
  if (error.response) {
    const status = error.response.status
    if (status === 401) {
      // 登录过期
      const url = error.response.config ? error.response.config.url : ''
      if (url === setting.menuUrl) {
        goLogin()
      } else {
        MessageBox.alert('登录状态已过期, 请退出重新登录!', '系统提示', {
          confirmButtonText: '重新登录',
          callback: (action) => {
            if (action === 'confirm') {
              goLogin(true)
            }
          },
          beforeClose: () => {
            MessageBox.close()
          }
        })
      }
    } else if (status === 403) {
      // 无权限
      Vue.prototype.$message.error('没有权限访问')
    }
  }
  return Promise.reject(error)
})

/**
 * 跳转到登录页面
 */
function goLogin(reload) {
  store.dispatch('user/removeToken').then(() => {
    if (reload) {
      location.replace('/login')
    } else {
      const path = router.currentRoute.path
      return router.push({
        path: '/login',
        query: path && path !== '/' ? {from: path} : null
      })
    }
  })
}
