import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../api'
import Layout from '../components/Layout.vue'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { title: '登录', public: true } },
  {
    path: '/',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '概览' } },
      { path: 'orders', name: 'Orders', component: () => import('../views/Orders.vue'), meta: { title: '订单' } },
      { path: 'fills', name: 'Fills', component: () => import('../views/Fills.vue'), meta: { title: '成交' } },
      { path: 'positions', name: 'Positions', component: () => import('../views/Positions.vue'), meta: { title: '持仓' } },
      { path: 'accounts', name: 'Accounts', component: () => import('../views/Accounts.vue'), meta: { title: '资金账户' } },
      { path: 'transactions', name: 'Transactions', component: () => import('../views/Transactions.vue'), meta: { title: '流水' } },
      { path: 'analytics', name: 'Analytics', component: () => import('../views/Analytics.vue'), meta: { title: '绩效分析' } },
      { path: 'strategies', name: 'Strategies', component: () => import('../views/Strategies.vue'), meta: { title: '策略管理' } },
      { path: 'signal-monitor', name: 'SignalMonitor', component: () => import('../views/SignalMonitor.vue'), meta: { title: '信号监控' } },
      { path: 'tenants', name: 'Tenants', component: () => import('../views/Tenants.vue'), meta: { title: '租户管理' } },
      { path: 'users', name: 'Users', component: () => import('../views/Users.vue'), meta: { title: '用户管理' } },
      { path: 'admins', name: 'Admins', component: () => import('../views/Admins.vue'), meta: { title: '管理员' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const token = getToken()
  if (to.meta.public) {
    if (token && to.path === '/login') return next('/')
    return next()
  }
  if (!token && to.meta.requiresAuth) return next('/login')
  next()
})

export default router
