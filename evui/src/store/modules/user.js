/**
 * 登录状态管理 — IronBull 静态菜单模式
 */
import setting from '@/config/setting'
import {menuRoutes} from '@/router'
import {formatMenus} from 'ele-admin'

export default {
  namespaced: true,
  state: {
    user: setting.takeUser(),
    authorities: [],
    roles: [],
    menus: null,
    permission: []
  },
  mutations: {
    SET(state, obj) {
      state[obj.key] = obj.value
    },
    SET_TOKEN(state, obj) {
      setting.cacheToken(obj.token, obj.remember)
      state.token = obj.token
      if (!obj.token) {
        state.user = {}
        state.menus = null
        setting.cacheUser()
      }
    },
    SET_PERMISSION(state, data) {
      state.permission = data
    }
  },
  actions: {
    setPermission({commit}, data) {
      commit('SET_PERMISSION', data)
    },
    /**
     * 缓存token
     */
    setToken({commit}, token) {
      let remember = true
      if (typeof token === 'object') {
        remember = token.remember
        token = token.token
      }
      commit('SET_TOKEN', {token: token, remember: remember})
    },
    /**
     * 移除token
     */
    removeToken({commit}) {
      commit('SET_TOKEN', {})
    },
    /**
     * 设置用户信息
     */
    setUser({commit}, user) {
      setting.cacheUser(user)
      commit('SET', {key: 'user', value: user})
    },
    /**
     * 设置用户权限
     */
    setAuthorities({commit}, authorities) {
      commit('SET', {key: 'authorities', value: authorities})
    },
    /**
     * 设置用户角色
     */
    setRoles({commit}, roles) {
      commit('SET', {key: 'roles', value: roles})
    },
    /**
     * 设置用户菜单
     */
    setMenus({commit}, menus) {
      commit('SET', {key: 'menus', value: menus})
    },
    /**
     * 获取菜单 — IronBull 使用静态菜单
     */
    getMenus({commit}) {
      return new Promise((resolve) => {
        // 将 menuRoutes 转换为 ele-admin 格式的菜单数据
        const menuData = menuRoutes.map(r => {
          const item = {
            path: r.path,
            title: r.meta ? r.meta.title : '',
            icon: r.meta ? r.meta.icon : '',
            component: r.component ? r.path : null
          }
          if (r.children) {
            item.children = r.children.map(c => ({
              path: c.path,
              title: c.meta ? c.meta.title : '',
              icon: c.meta ? c.meta.icon : '',
              component: c.path
            }))
          }
          return item
        })

        const {menus, homePath} = formatMenus(menuData)
        commit('SET', {key: 'menus', value: menus})
        commit('SET', {key: 'roles', value: ['admin']})
        commit('SET', {key: 'authorities', value: ['*']})

        // 加载用户信息
        if (setting.userUrl) {
          import('axios').then(({default: axios}) => {
            axios.get(setting.userUrl).then(res => {
              const result = setting.parseUser(res)
              if (result.code === 0 && result.data) {
                setting.cacheUser(result.data)
                commit('SET', {key: 'user', value: result.data})
              }
            }).catch(() => {})
          })
        }

        resolve({menus: menus, home: homePath || '/dashboard'})
      })
    }
  }
}
