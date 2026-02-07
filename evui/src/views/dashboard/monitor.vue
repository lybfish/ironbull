<template>
  <div class="ele-body">
    <el-card shadow="never" v-loading="loading">
      <div slot="header" class="card-header">
        <span>系统监控</span>
        <div>
          <el-tag :type="overallType" size="small" style="margin-right:12px">{{ overallLabel }}</el-tag>
          <el-switch v-model="autoRefresh" active-text="自动刷新" inactive-text="手动刷新" @change="handleAutoRefreshChange"/>
          <el-button type="primary" size="mini" icon="el-icon-refresh" style="margin-left:12px" @click="fetchData">刷新</el-button>
        </div>
      </div>

      <!-- 服务状态卡片 -->
      <el-row :gutter="15" style="margin-bottom: 20px;">
        <el-col :span="6" v-for="svc in services" :key="svc.name">
          <stat-card :title="svc.name" :value="svc.healthy ? '在线' : '离线'" icon="el-icon-connection"
            :color="svc.healthy ? 'success' : 'danger'"
            :help-text="svc.latency_ms ? `响应 ${svc.latency_ms}ms` : (svc.error || '未知')" :loading="loading"/>
        </el-col>
        <el-col :span="6">
          <stat-card title="数据库" :value="dbStatus.mysql_ok ? '正常' : '异常'" icon="el-icon-coin"
            :color="dbStatus.mysql_ok ? 'success' : 'danger'" help-text="MySQL 连接状态" :loading="loading"/>
        </el-col>
        <el-col :span="6">
          <stat-card title="Redis" :value="dbStatus.redis_ok ? '正常' : '异常'" icon="el-icon-box"
            :color="dbStatus.redis_ok ? 'success' : 'danger'" help-text="Redis 连接状态" :loading="loading"/>
        </el-col>
      </el-row>

      <!-- API 指标概览 -->
      <el-row :gutter="15" style="margin-bottom: 15px;" v-if="metrics.summary">
        <el-col :lg="6" :md="12">
          <el-card shadow="never" class="metric-card">
            <div class="metric-label">API 调用量 ({{ metricDays }}天)</div>
            <div class="metric-val">{{ metrics.summary.total_calls }}</div>
          </el-card>
        </el-col>
        <el-col :lg="6" :md="12">
          <el-card shadow="never" class="metric-card">
            <div class="metric-label">错误数</div>
            <div class="metric-val text-danger">{{ metrics.summary.total_errors }}</div>
          </el-card>
        </el-col>
        <el-col :lg="6" :md="12">
          <el-card shadow="never" class="metric-card">
            <div class="metric-label">错误率</div>
            <div class="metric-val" :class="metrics.summary.error_rate > 5 ? 'text-danger' : 'text-success'">
              {{ metrics.summary.error_rate }}%
            </div>
          </el-card>
        </el-col>
        <el-col :lg="6" :md="12">
          <el-card shadow="never" class="metric-card">
            <div class="metric-label">平均延迟</div>
            <div class="metric-val" :class="metrics.summary.avg_latency_ms > 500 ? 'text-warning' : ''">
              {{ metrics.summary.avg_latency_ms }}ms
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- API 趋势图 -->
      <el-row :gutter="15" style="margin-bottom: 15px;">
        <el-col :lg="12" :md="24">
          <el-card shadow="never">
            <div slot="header" class="card-header">
              <span>API 调用量 & 错误数</span>
              <el-radio-group v-model="metricDays" size="mini" @change="fetchMetrics">
                <el-radio-button :label="7">7天</el-radio-button>
                <el-radio-button :label="14">14天</el-radio-button>
                <el-radio-button :label="30">30天</el-radio-button>
              </el-radio-group>
            </div>
            <div ref="chartCalls" style="height: 240px;" v-loading="metricsLoading"></div>
          </el-card>
        </el-col>
        <el-col :lg="12" :md="24">
          <el-card shadow="never">
            <div slot="header"><span>API 延迟 (ms)</span></div>
            <div ref="chartLatency" style="height: 240px;" v-loading="metricsLoading"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 错误分布 -->
      <el-row :gutter="15" style="margin-bottom: 15px;" v-if="metrics.error_by_service && metrics.error_by_service.length">
        <el-col :span="24">
          <el-card shadow="never">
            <div slot="header">错误按服务分布</div>
            <el-table :data="metrics.error_by_service" size="mini" stripe border>
              <el-table-column prop="service" label="服务"/>
              <el-table-column prop="count" label="错误数" width="120" align="center">
                <template slot-scope="{row}">
                  <el-tag type="danger" size="mini">{{ row.count }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <!-- 服务健康详情 -->
      <el-card shadow="never" style="margin-bottom: 16px;">
        <div slot="header">服务健康详情</div>
        <el-table :data="services" stripe border size="small">
          <el-table-column prop="name" label="服务名" width="180"/>
          <el-table-column prop="url" label="健康检查地址" min-width="250" show-overflow-tooltip/>
          <el-table-column label="状态" width="100" align="center">
            <template slot-scope="{row}">
              <el-tag :type="row.healthy ? 'success' : 'danger'" size="mini">{{ row.healthy ? '健康' : '异常' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="延迟" width="100" align="center">
            <template slot-scope="{row}">
              <span v-if="row.latency_ms">{{ row.latency_ms }}ms</span>
              <span v-else style="color:#909399">-</span>
            </template>
          </el-table-column>
          <el-table-column label="错误" min-width="200" show-overflow-tooltip>
            <template slot-scope="{row}">
              <span v-if="row.error" style="color:#F56C6C">{{ row.error }}</span>
              <span v-else style="color:#67C23A">无</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 基础设施 -->
      <el-card shadow="never" style="margin-bottom: 16px;">
        <div slot="header">基础设施</div>
        <el-descriptions :column="4" border size="small">
          <el-descriptions-item label="MySQL">
            <el-tag :type="dbStatus.mysql_ok ? 'success' : 'danger'" size="mini">{{ dbStatus.mysql_ok ? '正常' : '异常' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Redis">
            <el-tag :type="dbStatus.redis_ok ? 'success' : 'danger'" size="mini">{{ dbStatus.redis_ok ? '正常' : '异常' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="MySQL 延迟" v-if="dbStatus.mysql_latency_ms">{{ dbStatus.mysql_latency_ms }}ms</el-descriptions-item>
          <el-descriptions-item label="Redis 延迟" v-if="dbStatus.redis_latency_ms">{{ dbStatus.redis_latency_ms }}ms</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </el-card>

    <!-- 节点心跳 -->
    <el-card shadow="never" style="margin-top:16px" v-if="nodes.length > 0">
      <div slot="header">
        <span>执行节点心跳</span>
        <el-tag size="mini" style="margin-left:8px">{{ nodes.length }} 个节点</el-tag>
      </div>
      <el-table :data="nodes" stripe border size="small">
        <el-table-column prop="code" label="节点编码" width="150"/>
        <el-table-column prop="name" label="节点名称" width="150"/>
        <el-table-column label="状态" width="100" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.online ? 'success' : 'danger'" size="mini">{{ row.online ? '在线' : '离线' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后心跳" width="170">
          <template slot-scope="{row}">{{ formatTime(row.last_heartbeat) }}</template>
        </el-table-column>
        <el-table-column label="延迟/超时" width="120" align="center">
          <template slot-scope="{row}">
            <span v-if="row.seconds_since_heartbeat != null">{{ row.seconds_since_heartbeat }}s</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script>
import {getMonitorStatus, getMonitorMetrics} from '@/api/monitor'
import * as echarts from 'echarts/core'
import {LineChart, BarChart} from 'echarts/charts'
import {GridComponent, TooltipComponent, LegendComponent} from 'echarts/components'
import {CanvasRenderer} from 'echarts/renderers'

echarts.use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

export default {
  name: 'SystemMonitor',
  data() {
    return {
      loading: false, metricsLoading: false,
      overall: '', services: [], nodes: [],
      dbStatus: {mysql_ok: false, redis_ok: false},
      autoRefresh: false, refreshTimer: null,
      metricDays: 7,
      metrics: {},
      chartInst: {}
    }
  },
  computed: {
    overallType() { return this.overall === 'healthy' ? 'success' : (this.overall === 'degraded' ? 'warning' : 'info') },
    overallLabel() { return this.overall === 'healthy' ? '系统正常' : (this.overall === 'degraded' ? '系统降级' : '加载中...') }
  },
  mounted() {
    this.fetchData()
    this.fetchMetrics()
    this.resizeFn = () => { Object.values(this.chartInst).forEach(c => c && c.resize()) }
    window.addEventListener('resize', this.resizeFn)
  },
  beforeDestroy() {
    this.clearRefreshTimer()
    window.removeEventListener('resize', this.resizeFn)
    Object.values(this.chartInst).forEach(c => c && c.dispose())
  },
  methods: {
    formatTime(t) { return t ? t.replace('T', ' ').substring(0, 19) : '-' },
    getChart(ref) {
      if (this.chartInst[ref]) { return this.chartInst[ref] }
      const el = this.$refs[ref]
      if (!el) { return null }
      const c = echarts.init(el)
      this.chartInst[ref] = c
      return c
    },
    async fetchData() {
      this.loading = true
      try {
        const res = await getMonitorStatus()
        const d = res.data.data || res.data || {}
        this.overall = d.overall || ''
        this.services = d.services || []
        this.nodes = d.nodes || []
        this.dbStatus = d.db || {mysql_ok: false, redis_ok: false}
      } catch (e) {
        this.$message.error('获取监控状态失败')
      } finally {
        this.loading = false
      }
    },
    async fetchMetrics() {
      this.metricsLoading = true
      try {
        const res = await getMonitorMetrics(this.metricDays)
        this.metrics = (res.data && res.data.data) || {}
        this.$nextTick(() => {
          this.renderCallsChart()
          this.renderLatencyChart()
        })
      } catch (e) {
        console.error('metrics error', e)
      } finally {
        this.metricsLoading = false
      }
    },
    renderCallsChart() {
      const chart = this.getChart('chartCalls')
      if (!chart || !this.metrics.daily) { return }
      const d = this.metrics.daily
      chart.setOption({
        tooltip: {trigger: 'axis'},
        legend: {data: ['调用量', '错误数'], bottom: 0},
        grid: {left: 50, right: 20, top: 10, bottom: 35},
        xAxis: {type: 'category', data: (d.dates || []).map(x => x.slice(5)), axisLabel: {fontSize: 11}},
        yAxis: {type: 'value', splitLine: {lineStyle: {color: '#F2F6FC'}}},
        series: [
          {name: '调用量', type: 'bar', data: d.api_calls || [], itemStyle: {color: '#409EFF', borderRadius: [3, 3, 0, 0]}, barMaxWidth: 20},
          {name: '错误数', type: 'bar', data: d.errors || [], itemStyle: {color: '#F56C6C', borderRadius: [3, 3, 0, 0]}, barMaxWidth: 20}
        ]
      }, true)
    },
    renderLatencyChart() {
      const chart = this.getChart('chartLatency')
      if (!chart || !this.metrics.daily) { return }
      const d = this.metrics.daily
      chart.setOption({
        tooltip: {trigger: 'axis'},
        legend: {data: ['平均延迟', '最大延迟'], bottom: 0},
        grid: {left: 50, right: 20, top: 10, bottom: 35},
        xAxis: {type: 'category', data: (d.dates || []).map(x => x.slice(5)), axisLabel: {fontSize: 11}},
        yAxis: {type: 'value', name: 'ms', splitLine: {lineStyle: {color: '#F2F6FC'}}},
        series: [
          {name: '平均延迟', type: 'line', data: d.avg_latency || [], smooth: true, lineStyle: {color: '#E6A23C'}, itemStyle: {color: '#E6A23C'}, symbol: 'circle', symbolSize: 4},
          {name: '最大延迟', type: 'line', data: d.max_latency || [], smooth: true, lineStyle: {color: '#F56C6C', type: 'dashed'}, itemStyle: {color: '#F56C6C'}, symbol: 'none'}
        ]
      }, true)
    },
    handleAutoRefreshChange(val) {
      if (val) { this.startAutoRefresh() } else { this.clearRefreshTimer() }
    },
    startAutoRefresh() { this.clearRefreshTimer(); this.refreshTimer = setInterval(() => { this.fetchData() }, 30000) },
    clearRefreshTimer() { if (this.refreshTimer) { clearInterval(this.refreshTimer); this.refreshTimer = null } }
  }
}
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.metric-card { text-align: center; }
.metric-label { font-size: 12px; color: #909399; margin-bottom: 4px; }
.metric-val { font-size: 22px; font-weight: 700; color: #303133; }
.text-success { color: #67C23A !important; }
.text-warning { color: #E6A23C !important; }
.text-danger { color: #F56C6C !important; }
</style>
