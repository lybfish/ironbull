/**
 * 路由配置 — IronBull 管理后台（静态路由模式）
 */
import Vue from 'vue'
import VueRouter from 'vue-router'
import store from '@/store'
import setting from '@/config/setting'
import EleLayout from '@/layout'
import NProgress from 'nprogress'

Vue.use(VueRouter)

/**
 * 业务路由（作为 Layout 的 children）
 * meta.title  — 显示在标签页和面包屑
 * meta.icon   — 侧边栏图标 (Element UI icon class)
 * meta.hide   — true 则不在侧边栏显示
 */
const menuRoutes = [
  // ──────────── 仪表盘 ────────────
  {
    path: '/dashboard',
    component: () => import('@/views/dashboard/workplace'),
    meta: {title: '仪表盘', icon: 'el-icon-s-home'}
  },

  // ──────────── 交易数据（纯数据查看）────────────
  {
    path: '/trading',
    meta: {title: '交易数据', icon: 'el-icon-s-order'},
    children: [
      {path: '/trading/orders', component: () => import('@/views/trading/orders'), meta: {title: '订单列表'}},
      {path: '/trading/fills', component: () => import('@/views/trading/fills'), meta: {title: '成交记录'}},
      {path: '/trading/positions', component: () => import('@/views/trading/positions'), meta: {title: '持仓管理'}},
      {path: '/trading/accounts', component: () => import('@/views/trading/accounts'), meta: {title: '资金账户'}},
      {path: '/trading/transactions', component: () => import('@/views/trading/transactions'), meta: {title: '资金流水'}},
      {path: '/trading/analytics', component: () => import('@/views/trading/analytics'), meta: {title: '绩效分析'}}
    ]
  },

  // ──────────── 策略管理（策略相关配置集中）────────────
  {
    path: '/strategy',
    meta: {title: '策略管理', icon: 'el-icon-s-opportunity'},
    children: [
      {path: '/strategy/list', component: () => import('@/views/strategy/index'), meta: {title: '策略目录'}},
      {path: '/strategy/tenant-strategies', component: () => import('@/views/tenant/tenant-strategies'), meta: {title: '租户策略'}},
      {path: '/strategy/bindings', component: () => import('@/views/strategy/bindings'), meta: {title: '策略绑定'}}
    ]
  },

  // ──────────── 监控中心（信号 + 持仓监控 + 节点）────────────
  {
    path: '/monitor',
    meta: {title: '监控中心', icon: 'el-icon-data-board'},
    children: [
      {path: '/monitor/signal-control', component: () => import('@/views/strategy/signal-control'), meta: {title: '信号监控'}},
      {path: '/monitor/signal-history', component: () => import('@/views/strategy/signal-history'), meta: {title: '信号历史'}},
      {path: '/monitor/trading-control', component: () => import('@/views/trading/control'), meta: {title: '交易控制台'}},
      {path: '/monitor/sync', component: () => import('@/views/node/sync'), meta: {title: '同步与持仓监控'}},
      {path: '/monitor/nodes', component: () => import('@/views/node/index'), meta: {title: '执行节点'}}
    ]
  },

  // ──────────── 用户与账户 ────────────
  {
    path: '/user',
    meta: {title: '用户与账户', icon: 'el-icon-s-custom'},
    children: [
      {path: '/user/manage', component: () => import('@/views/user-manage/index'), meta: {title: '用户管理'}},
      {path: '/user/exchange-accounts', component: () => import('@/views/exchange/accounts'), meta: {title: '交易所账户'}}
    ]
  },

  // ──────────── 财务管理 ────────────
  {
    path: '/finance',
    meta: {title: '财务管理', icon: 'el-icon-s-finance'},
    children: [
      {path: '/finance/withdrawals', component: () => import('@/views/finance/withdrawals'), meta: {title: '提现管理'}},
      {path: '/finance/pointcard-logs', component: () => import('@/views/finance/pointcard-logs'), meta: {title: '点卡流水'}},
      {path: '/finance/rewards', component: () => import('@/views/finance/rewards'), meta: {title: '奖励记录'}}
    ]
  },

  // ──────────── 系统设置（平台级配置）────────────
  {
    path: '/system',
    meta: {title: '系统设置', icon: 'el-icon-s-tools'},
    children: [
      {path: '/system/tenants', component: () => import('@/views/tenant/index'), meta: {title: '租户管理'}},
      {path: '/system/quota-plans', component: () => import('@/views/quota/index'), meta: {title: '配额套餐'}},
      {path: '/system/admins', component: () => import('@/views/system/admins'), meta: {title: '管理员'}},
      {path: '/system/monitor', component: () => import('@/views/dashboard/monitor'), meta: {title: '系统监控'}},
      {path: '/system/audit-log', component: () => import('@/views/system/audit-log'), meta: {title: '审计日志'}}
    ]
  }
]

// 静态路由
const routes = [
  {
    path: '/login',
    component: () => import('@/views/login/login'),
    meta: {title: '登录'}
  },
  {
    path: '*',
    component: () => import('@/views/exception/404')
  }
]

const router = new VueRouter({
  routes,
  mode: 'hash'
})

// 路由守卫
router.beforeEach((to, from, next) => {
  NProgress.start()
  updateTitle(to)
  if (setting.takeToken()) {
    // 已登录 — 判断是否已注册路由
    if (!store.state.user.menus) {
      store.dispatch('user/getMenus').then(({home}) => {
        // 将静态菜单路由注册到 Layout 下
        const flatChildren = []
        menuRoutes.forEach(r => {
          if (r.children) {
            r.children.forEach(c => flatChildren.push(c))
          } else {
            flatChildren.push(r)
          }
        })
        router.addRoute({
          path: '/',
          component: EleLayout,
          redirect: setting.homePath || home || '/dashboard',
          children: flatChildren
        })
        next({...to, replace: true})
      }).catch(() => {
        next()
      })
    } else {
      next()
    }
  } else if (setting.whiteList.includes(to.path)) {
    next()
  } else {
    next({path: '/login', query: to.path === '/' ? {} : {from: to.path}})
  }
})

router.afterEach(() => {
  setTimeout(() => {
    NProgress.done(true)
  }, 300)
})

export default router

/**
 * 导出菜单路由供 Vuex store 使用
 */
export {menuRoutes}

/**
 * 更新浏览器标题
 */
function updateTitle(route) {
  if (!route.path.startsWith('/redirect/')) {
    const names = []
    if (route && route.meta && route.meta.title) {
      names.push(route.meta.title)
    }
    const appName = process.env.VUE_APP_NAME
    if (appName) {
      names.push(appName)
    }
    document.title = names.join(' - ')
  }
}
