<template>
  <div class="ele-body ele-body-card">
    <!-- 顶部用户卡片 -->
    <el-card shadow="never" body-style="padding: 20px;">
      <div class="ele-cell workplace-user-card">
        <div class="ele-cell-content ele-cell">
          <el-avatar :size="68" :src="loginUser.avatar || defaultAvatar"/>
          <div class="ele-cell-content">
            <h4 class="ele-elip">你好，【{{ loginUser.nickname || 'Admin' }}】，欢迎使用 Aigo 管理后台！</h4>
            <div class="ele-text-secondary ele-elip" style="margin-top: 8px;">
              <i class="el-icon-sunny"></i>
              <span>祝您交易顺利，收益满满!</span>
            </div>
          </div>
        </div>
        <div class="workplace-count-group">
          <div class="workplace-count-item">
            <div class="workplace-count-header">
              <el-tag type="primary" size="small" class="ele-tag-round">
                <i class="el-icon-wallet"></i>
              </el-tag>
              <span class="workplace-count-name">总余额</span>
            </div>
            <div class="workplace-count-num">${{ formatMoney(tenant.equity) }}</div>
          </div>
          <div class="workplace-count-item">
            <div class="workplace-count-header">
              <el-tag :type="tenant.dailyPnl >= 0 ? 'success' : 'danger'" size="small" class="ele-tag-round">
                <i class="el-icon-s-data"></i>
              </el-tag>
              <span class="workplace-count-name">日收益</span>
            </div>
            <div class="workplace-count-num" :class="tenant.dailyPnl >= 0 ? 'text-success' : 'text-danger'">
              ${{ formatMoney(tenant.dailyPnl) }}
            </div>
          </div>
          <div class="workplace-count-item">
            <div class="workplace-count-header">
              <el-tag type="warning" size="small" class="ele-tag-round">
                <i class="el-icon-s-order"></i>
              </el-tag>
              <span class="workplace-count-name">持仓数</span>
            </div>
            <div class="workplace-count-num">{{ tenant.positions || 0 }}</div>
          </div>
          <div class="workplace-count-item">
            <div class="workplace-count-header">
              <el-tag size="small" class="ele-tag-round">
                <i class="el-icon-s-operation"></i>
              </el-tag>
              <span class="workplace-count-name">活跃策略</span>
            </div>
            <div class="workplace-count-num">{{ platform.active_bindings || 0 }}</div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 实时数据卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="6" :md="12" :sm="12">
        <stat-card
          title="租户总数"
          :value="platform.total_tenants"
          icon="el-icon-s-custom"
          color="primary"
          help-text="平台注册租户数量"
          :loading="loading">
          <template v-slot:footer>
            <span class="ele-text-secondary">活跃 {{ platform.active_tenants }}</span>
          </template>
        </stat-card>
      </el-col>
      <el-col :lg="6" :md="12" :sm="12">
        <stat-card
          title="用户总数"
          :value="platform.total_users"
          icon="el-icon-user"
          color="success"
          help-text="平台注册用户总数"
          :loading="loading"/>
      </el-col>
      <el-col :lg="6" :md="12" :sm="12">
        <stat-card
          title="订单总数"
          :value="platform.total_orders"
          icon="el-icon-document"
          color="warning"
          help-text="平台累计订单数量"
          :loading="loading"/>
      </el-col>
      <el-col :lg="6" :md="12" :sm="12">
        <stat-card
          title="执行节点"
          :value="platform.total_nodes"
          icon="el-icon-s-platform"
          color="info"
          help-text="已注册的执行节点"
          :loading="loading">
          <template v-slot:footer>
            <span class="ele-text-secondary">在线 {{ platform.online_nodes }}</span>
          </template>
        </stat-card>
      </el-col>
    </el-row>

    <!-- 绩效和系统状态 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="16" :md="24">
        <el-card shadow="never">
          <div slot="header" class="card-header-flex">
            <span>绩效摘要</span>
            <el-button size="mini" icon="el-icon-refresh" @click="fetchData" :loading="loading">刷新</el-button>
          </div>
          <el-row :gutter="20">
            <el-col :span="4" class="perf-item" v-for="item in perfItems" :key="item.label">
              <div class="perf-label">{{ item.label }}</div>
              <div class="perf-value" :class="item.cls || ''">{{ item.value }}</div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
      <el-col :lg="8" :md="24">
        <el-card shadow="never">
          <div slot="header" class="card-header-flex">
            <span>系统状态</span>
            <el-tag :type="systemHealthy ? 'success' : 'danger'" size="small">
              {{ systemHealthy ? '正常' : '异常' }}
            </el-tag>
          </div>
          <div class="system-status-grid">
            <div class="status-item">
              <div class="status-label">data-api</div>
              <div class="status-value">
                <el-tag :type="services.data_api ? 'success' : 'danger'" size="mini">
                  {{ services.data_api ? '在线' : '离线' }}
                </el-tag>
              </div>
            </div>
            <div class="status-item">
              <div class="status-label">signal-monitor</div>
              <div class="status-value">
                <el-tag :type="services.signal_monitor ? 'success' : 'danger'" size="mini">
                  {{ services.signal_monitor ? '在线' : '离线' }}
                </el-tag>
              </div>
            </div>
            <div class="status-item">
              <div class="status-label">数据库</div>
              <div class="status-value">
                <el-tag :type="services.database ? 'success' : 'danger'" size="mini">
                  {{ services.database ? '正常' : '异常' }}
                </el-tag>
              </div>
            </div>
          </div>
          <div style="text-align: center; margin-top: 15px;">
            <el-button size="mini" icon="el-icon-refresh" @click="fetchData" :loading="loading">
              刷新数据
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图表 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="12" :md="24">
        <el-card shadow="never">
          <div slot="header" class="card-header-flex">
            <span>每日订单量</span>
            <el-radio-group v-model="trendDays" size="mini" @change="fetchTrends">
              <el-radio-button :label="7">7天</el-radio-button>
              <el-radio-button :label="30">30天</el-radio-button>
              <el-radio-button :label="60">60天</el-radio-button>
            </el-radio-group>
          </div>
          <div ref="chartOrders" style="height: 260px;" v-loading="trendLoading"></div>
        </el-card>
      </el-col>
      <el-col :lg="12" :md="24">
        <el-card shadow="never">
          <div slot="header" class="card-header-flex">
            <span>每日新增用户</span>
          </div>
          <div ref="chartUsers" style="height: 260px;" v-loading="trendLoading"></div>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="12" :md="24">
        <el-card shadow="never">
          <div slot="header" class="card-header-flex">
            <span>每日成交额 (USDT)</span>
          </div>
          <div ref="chartVolume" style="height: 260px;" v-loading="trendLoading"></div>
        </el-card>
      </el-col>
      <el-col :lg="12" :md="24">
        <el-card shadow="never">
          <div slot="header" class="card-header-flex">
            <span>每日利润池入池 (USDT)</span>
          </div>
          <div ref="chartPool" style="height: 260px;" v-loading="trendLoading"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷方式 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="3" :md="6" :sm="6" :xs="12">
        <el-card shadow="hover" body-style="padding: 0;">
          <router-link to="/trading/orders" class="app-link-block">
            <i class="app-link-icon el-icon-s-order"></i>
            <div class="app-link-title">订单管理</div>
          </router-link>
        </el-card>
      </el-col>
      <el-col :lg="3" :md="6" :sm="6" :xs="12">
        <el-card shadow="hover" body-style="padding: 0;">
          <router-link to="/trading/positions" class="app-link-block">
            <i class="app-link-icon el-icon-s-data" style="color: #95de64;"></i>
            <div class="app-link-title">当前持仓</div>
          </router-link>
        </el-card>
      </el-col>
      <el-col :lg="3" :md="6" :sm="6" :xs="12">
        <el-card shadow="hover" body-style="padding: 0;">
          <router-link to="/strategy/list" class="app-link-block">
            <i class="app-link-icon el-icon-s-opportunity" style="color: #ff9c6e;"></i>
            <div class="app-link-title">策略目录</div>
          </router-link>
        </el-card>
      </el-col>
      <el-col :lg="3" :md="6" :sm="6" :xs="12">
        <el-card shadow="hover" body-style="padding: 0;">
          <router-link to="/monitor/signal-control" class="app-link-block">
            <i class="app-link-icon el-icon-connection" style="color: #b37feb;"></i>
            <div class="app-link-title">信号监控</div>
          </router-link>
        </el-card>
      </el-col>
      <el-col :lg="3" :md="6" :sm="6" :xs="12">
        <el-card shadow="hover" body-style="padding: 0;">
          <router-link to="/system/tenants" class="app-link-block">
            <i class="app-link-icon el-icon-s-custom" style="color: #ffd666;"></i>
            <div class="app-link-title">租户管理</div>
          </router-link>
        </el-card>
      </el-col>
      <el-col :lg="3" :md="6" :sm="6" :xs="12">
        <el-card shadow="hover" body-style="padding: 0;">
          <router-link to="/user/exchange-accounts" class="app-link-block">
            <i class="app-link-icon el-icon-wallet" style="color: #5cdbd3;"></i>
            <div class="app-link-title">交易账户</div>
          </router-link>
        </el-card>
      </el-col>
      <el-col :lg="3" :md="6" :sm="6" :xs="12">
        <el-card shadow="hover" body-style="padding: 0;">
          <router-link to="/monitor/nodes" class="app-link-block">
            <i class="app-link-icon el-icon-s-platform" style="color: #ff85c0;"></i>
            <div class="app-link-title">执行节点</div>
          </router-link>
        </el-card>
      </el-col>
      <el-col :lg="3" :md="6" :sm="6" :xs="12">
        <el-card shadow="hover" body-style="padding: 0;">
          <router-link to="/trading/analytics" class="app-link-block">
            <i class="app-link-icon el-icon-data-analysis" style="color: #ffc069;"></i>
            <div class="app-link-title">绩效分析</div>
          </router-link>
        </el-card>
      </el-col>
    </el-row>

    <!-- 近期信号 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :span="24">
        <el-card shadow="never">
          <div slot="header" class="card-header-flex">
            <span>近期信号</span>
            <router-link to="/strategy/signal-history"><el-button type="text" size="mini">查看全部</el-button></router-link>
          </div>
          <el-table :data="recentSignals" stripe size="mini" style="width: 100%" :header-cell-style="{background:'#fafafa'}" v-loading="loading">
            <el-table-column prop="signal_id" label="信号ID" width="160">
              <template slot-scope="{row}">
                <span style="font-family: monospace; font-size: 12px">{{ (row.signal_id || '').slice(0, 16) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="event_type" label="事件" width="100" align="center">
              <template slot-scope="{row}">
                <el-tag :type="signalTagType(row.event_type)" size="mini">{{ row.event_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90" align="center">
              <template slot-scope="{row}">
                <el-tag :type="row.status === 'SUCCESS' ? 'success' : row.status === 'FAILED' ? 'danger' : 'warning'" size="mini">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="详情" min-width="200">
              <template slot-scope="{row}">
                <span style="font-size: 12px; color: #606266">{{ signalDetail(row) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="170">
              <template slot-scope="{row}">
                <span style="font-size: 12px">{{ row.created_at || '-' }}</span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!loading && recentSignals.length === 0" description="暂无信号记录" :image-size="60"/>
        </el-card>
      </el-col>
    </el-row>

    <!-- 交易概览 -->
    <el-row :gutter="15">
      <el-col :lg="8" :md="12">
        <el-card shadow="never">
          <div slot="header" class="card-header-flex">
            <span>账户资产</span>
            <router-link to="/trading/accounts"><el-button type="text" size="mini">详情</el-button></router-link>
          </div>
          <div class="trade-overview-item">
            <div class="trade-overview-label">当前权益</div>
            <div class="trade-overview-value">{{ formatMoney(tenant.equity) }} USDT</div>
          </div>
          <div class="trade-overview-item">
            <div class="trade-overview-label">累计收益率</div>
            <div class="trade-overview-value" :class="tenant.totalReturn >= 0 ? 'text-success' : 'text-danger'">
              {{ fmtPct(tenant.totalReturn) }}
            </div>
          </div>
          <div class="trade-overview-item">
            <div class="trade-overview-label">最大回撤</div>
            <div class="trade-overview-value text-danger">{{ fmtPct(tenant.maxDrawdown) }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :lg="8" :md="12">
        <el-card shadow="never">
          <div slot="header" class="card-header-flex">
            <span>持仓概览</span>
            <router-link to="/trading/positions"><el-button type="text" size="mini">管理</el-button></router-link>
          </div>
          <div class="trade-overview-item">
            <div class="trade-overview-label">活跃持仓</div>
            <div class="trade-overview-value">{{ tenant.positions || 0 }} 个</div>
          </div>
          <div class="trade-overview-item">
            <div class="trade-overview-label">总订单数</div>
            <div class="trade-overview-value">{{ tenant.orders || 0 }}</div>
          </div>
          <div class="trade-overview-item">
            <div class="trade-overview-label">胜率</div>
            <div class="trade-overview-value">{{ fmtPct(tenant.winRate, 1) }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :lg="8" :md="12">
        <el-card shadow="never">
          <div slot="header" class="card-header-flex">
            <span>风险指标</span>
            <router-link to="/trading/analytics"><el-button type="text" size="mini">查看</el-button></router-link>
          </div>
          <div class="trade-overview-item">
            <div class="trade-overview-label">夏普比率</div>
            <div class="trade-overview-value">{{ tenant.sharpeRatio !== null && tenant.sharpeRatio !== undefined ? tenant.sharpeRatio.toFixed(2) : '-' }}</div>
          </div>
          <div class="trade-overview-item">
            <div class="trade-overview-label">总交易次数</div>
            <div class="trade-overview-value">{{ tenant.totalTrades || '-' }}</div>
          </div>
          <div class="trade-overview-item">
            <div class="trade-overview-label">日收益</div>
            <div class="trade-overview-value" :class="tenant.dailyPnl >= 0 ? 'text-success' : 'text-danger'">
              {{ tenant.dailyPnl !== null && tenant.dailyPnl !== undefined ? tenant.dailyPnl.toFixed(2) : '-' }}
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import {getDashboardSummary, getPerformance, getDashboardTrends} from '@/api/analytics'
import {getOrders, getPositions} from '@/api/trading'
import {getMonitorStatus} from '@/api/monitor'
import {getSignalEvents} from '@/api/admin'
import * as echarts from 'echarts/core'
import {LineChart, BarChart} from 'echarts/charts'
import {GridComponent, TooltipComponent, LegendComponent} from 'echarts/components'
import {CanvasRenderer} from 'echarts/renderers'

echarts.use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

export default {
  name: 'Workplace',
  data() {
    return {
      loading: true,
      trendLoading: false,
      trendDays: 30,
      defaultAvatar: require('@/assets/logo.png'),
      platform: {
        total_tenants: 0,
        active_tenants: 0,
        total_users: 0,
        total_orders: 0,
        total_nodes: 0,
        online_nodes: 0,
        active_bindings: 0
      },
      tenant: {
        orders: 0,
        positions: 0,
        equity: null,
        totalReturn: null,
        dailyPnl: null,
        maxDrawdown: null,
        sharpeRatio: null,
        totalTrades: null,
        winRate: null
      },
      services: {
        data_api: false,
        signal_monitor: false,
        database: false
      },
      recentSignals: [],
      chartInstances: {}
    }
  },
  computed: {
    loginUser() {
      return this.$store.state.user.user || {}
    },
    systemHealthy() {
      return this.services.data_api && this.services.database && this.services.signal_monitor
    },
    perfItems() {
      return [
        {label: '累计收益率', value: this.fmtPct(this.tenant.totalReturn), cls: this.tenant.totalReturn >= 0 ? 'text-success' : 'text-danger'},
        {label: '日收益', value: this.tenant.dailyPnl !== null && this.tenant.dailyPnl !== undefined ? this.tenant.dailyPnl.toFixed(2) : '-', cls: this.tenant.dailyPnl >= 0 ? 'text-success' : 'text-danger'},
        {label: '最大回撤', value: this.fmtPct(this.tenant.maxDrawdown), cls: 'text-danger'},
        {label: '夏普比率', value: this.tenant.sharpeRatio !== null && this.tenant.sharpeRatio !== undefined ? this.tenant.sharpeRatio.toFixed(2) : '-'},
        {label: '总交易', value: this.tenant.totalTrades || '-'},
        {label: '胜率', value: this.fmtPct(this.tenant.winRate, 1)}
      ]
    }
  },
  mounted() {
    this.fetchData()
    this.fetchTrends()
    this.resizeHandler = () => {
      Object.values(this.chartInstances).forEach(c => c && c.resize())
    }
    window.addEventListener('resize', this.resizeHandler)
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.resizeHandler)
    Object.values(this.chartInstances).forEach(c => c && c.dispose())
  },
  methods: {
    formatMoney(val) {
      if (val === null || val === undefined) {return '0.00'}
      return parseFloat(val || 0).toFixed(2)
    },
    fmtPct(val, decimals) {
      if (val === null || val === undefined) {return '-'}
      return (val * 100).toFixed(decimals || 2) + '%'
    },
    signalTagType(t) {
      const m = { CREATED: '', DISPATCHED: 'warning', EXECUTED: 'success', FAILED: 'danger' }
      return m[(t || '').toUpperCase()] || 'info'
    },
    signalDetail(row) {
      try {
        const d = typeof row.detail === 'string' ? JSON.parse(row.detail) : (row.detail || {})
        const parts = []
        if (d.strategy) parts.push(d.strategy)
        if (d.symbol) parts.push(d.symbol)
        if (d.side) parts.push(d.side)
        if (row.source) parts.push(row.source)
        return parts.join(' · ') || row.detail || '-'
      } catch (e) { return row.detail || '-' }
    },
    async fetchData() {
      this.loading = true
      try {
        const [summaryRes, ordersRes, positionsRes, perfRes, monitorRes, signalRes] = await Promise.allSettled([
          getDashboardSummary(),
          getOrders({limit: 1}),
          getPositions({limit: 1}),
          getPerformance().catch(() => null),
          getMonitorStatus().catch(() => null),
          getSignalEvents({page_size: 8}).catch(() => null)
        ])

        if (summaryRes.status === 'fulfilled' && summaryRes.value && summaryRes.value.data) {
          const d = summaryRes.value.data.data || summaryRes.value.data
          Object.assign(this.platform, d)
        }
        if (ordersRes.status === 'fulfilled' && ordersRes.value) {
          this.tenant.orders = ordersRes.value.data.total || 0
        }
        if (positionsRes.status === 'fulfilled' && positionsRes.value) {
          this.tenant.positions = positionsRes.value.data.total || 0
        }
        if (perfRes.status === 'fulfilled' && perfRes.value && perfRes.value.data) {
          const s = perfRes.value.data.data ? perfRes.value.data.data.summary : null
          if (s) {
            this.tenant.equity = s.current_equity
            this.tenant.totalReturn = s.total_return
            this.tenant.dailyPnl = s.daily_pnl
            this.tenant.maxDrawdown = s.max_drawdown
            this.tenant.sharpeRatio = s.sharpe_ratio
            this.tenant.totalTrades = s.total_trades
            this.tenant.winRate = s.win_rate
          }
        }
        if (monitorRes.status === 'fulfilled' && monitorRes.value && monitorRes.value.data) {
          const m = monitorRes.value.data.data || monitorRes.value.data
          // services 是数组 [{name, healthy, ...}]，按 name 查找
          const svcList = m.services || []
          const findSvc = (name) => {
            const s = svcList.find(x => x.name === name)
            return s ? !!s.healthy : false
          }
          this.services = {
            data_api: findSvc('data-api'),
            signal_monitor: findSvc('signal-monitor'),
            database: !!(m.db && m.db.mysql_ok)
          }
        }
        if (signalRes.status === 'fulfilled' && signalRes.value && signalRes.value.data) {
          const sd = signalRes.value.data
          this.recentSignals = (sd.data || sd.events || []).slice(0, 8)
        }
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error(e)
      } finally {
        this.loading = false
      }
    },
    async fetchTrends() {
      this.trendLoading = true
      try {
        const res = await getDashboardTrends(this.trendDays)
        const d = (res.data && res.data.data) || res.data || {}
        this.$nextTick(() => {
          this.renderBarChart('chartOrders', d.dates || [], d.orders || [], '订单量', '#409EFF')
          this.renderLineChart('chartUsers', d.dates || [], d.new_users || [], '新增用户', '#67C23A')
          this.renderAreaChart('chartVolume', d.dates || [], d.trade_volume || [], '成交额', '#E6A23C')
          this.renderAreaChart('chartPool', d.dates || [], d.pool_amount || [], '入池金额', '#F56C6C')
        })
      } catch (e) {
        console.error('trends error', e)
      } finally {
        this.trendLoading = false
      }
    },
    getChartInstance(refName) {
      if (this.chartInstances[refName]) {
        return this.chartInstances[refName]
      }
      const el = this.$refs[refName]
      if (!el) { return null }
      const chart = echarts.init(el)
      this.chartInstances[refName] = chart
      return chart
    },
    buildBaseOption(dates) {
      return {
        tooltip: {trigger: 'axis'},
        grid: {left: 50, right: 20, top: 20, bottom: 30},
        xAxis: {
          type: 'category',
          data: dates.map(d => d.slice(5)),
          axisLabel: {fontSize: 11, color: '#909399'},
          axisLine: {lineStyle: {color: '#E4E7ED'}}
        },
        yAxis: {
          type: 'value',
          splitLine: {lineStyle: {color: '#F2F6FC'}},
          axisLabel: {fontSize: 11, color: '#909399'}
        }
      }
    },
    renderBarChart(refName, dates, data, name, color) {
      const chart = this.getChartInstance(refName)
      if (!chart) { return }
      const opt = this.buildBaseOption(dates)
      opt.series = [{
        name: name, type: 'bar', data: data,
        itemStyle: {color: color, borderRadius: [3, 3, 0, 0]},
        barMaxWidth: 20
      }]
      chart.setOption(opt, true)
    },
    renderLineChart(refName, dates, data, name, color) {
      const chart = this.getChartInstance(refName)
      if (!chart) { return }
      const opt = this.buildBaseOption(dates)
      opt.series = [{
        name: name, type: 'line', data: data,
        smooth: true,
        symbol: 'circle', symbolSize: 5,
        lineStyle: {color: color, width: 2},
        itemStyle: {color: color}
      }]
      chart.setOption(opt, true)
    },
    renderAreaChart(refName, dates, data, name, color) {
      const chart = this.getChartInstance(refName)
      if (!chart) { return }
      const opt = this.buildBaseOption(dates)
      opt.series = [{
        name: name, type: 'line', data: data,
        smooth: true,
        symbol: 'none',
        lineStyle: {color: color, width: 2},
        areaStyle: {color: {type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{offset: 0, color: color + '40'}, {offset: 1, color: color + '05'}]
        }}
      }]
      chart.setOption(opt, true)
    }
  }
}
</script>

<style scoped>
.card-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.workplace-user-card .ele-cell-content { overflow: hidden; }
.workplace-count-group { white-space: nowrap; }
.workplace-count-item {
  padding: 0 5px 0 25px;
  box-sizing: border-box;
  display: inline-block;
  text-align: right;
}
.workplace-count-name { padding-left: 8px; }
.workplace-count-num { font-size: 24px; margin-top: 6px; }

.system-status-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
}
.status-item { text-align: center; }
.status-label { font-size: 12px; color: #909399; margin-bottom: 5px; }
.status-value { font-size: 13px; }

.perf-item { text-align: center; padding: 12px 0; }
.perf-label { color: #909399; font-size: 12px; margin-bottom: 6px; }
.perf-value { font-size: 18px; font-weight: 600; color: #303133; }

.trade-overview-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}
.trade-overview-item:last-child { border-bottom: none; }
.trade-overview-label { font-size: 13px; color: #909399; }
.trade-overview-value { font-size: 14px; font-weight: 500; color: #303133; }

.app-link-block {
  display: block;
  color: inherit;
  padding: 15px 0;
  text-align: center;
  text-decoration: none;
  cursor: pointer;
}
.app-link-block .app-link-icon { color: #69c0ff; font-size: 30px; margin-top: 5px; }
.app-link-block .app-link-title { margin-top: 8px; }

.text-success { color: #67C23A !important; }
.text-warning { color: #E6A23C !important; }
.text-danger { color: #F56C6C !important; }

@media screen and (max-width: 992px) {
  .workplace-count-item { padding: 0 5px 0 10px; }
}

@media screen and (max-width: 768px) {
  .workplace-user-card, .workplace-count-group { display: block; }
  .workplace-count-group { margin-top: 15px; text-align: right; }
  .workplace-user-card ::v-deep .el-avatar { width: 45px !important; height: 45px !important; }
  .workplace-user-card h4 { font-size: 16px; }
  .workplace-user-card h4 + .ele-text-secondary { font-size: 12px; }
  .workplace-user-card { margin: -10px; }
  .system-status-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
