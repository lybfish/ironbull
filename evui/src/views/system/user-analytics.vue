<template>
  <div class="ele-body ele-body-card">
    <!-- 概览卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="4" :md="8" :sm="12">
        <stat-card title="总用户" :value="overview.total_users" icon="el-icon-user" color="primary" :loading="loading"/>
      </el-col>
      <el-col :lg="4" :md="8" :sm="12">
        <stat-card title="活跃用户" :value="overview.active_users" icon="el-icon-user-solid" color="success" :loading="loading"/>
      </el-col>
      <el-col :lg="4" :md="8" :sm="12">
        <stat-card :title="periodDays + '天新增'" :value="overview.new_users_period" icon="el-icon-plus" color="warning" :loading="loading"/>
      </el-col>
      <el-col :lg="4" :md="8" :sm="12">
        <stat-card title="交易用户" :value="overview.trading_users" icon="el-icon-s-data" color="danger" help-text="有活跃策略绑定" :loading="loading"/>
      </el-col>
      <el-col :lg="4" :md="8" :sm="12">
        <stat-card title="已充值" :value="overview.funded_users" icon="el-icon-bank-card" color="info" help-text="有点卡余额" :loading="loading"/>
      </el-col>
      <el-col :lg="4" :md="8" :sm="12">
        <stat-card title="市场节点" :value="overview.market_nodes" icon="el-icon-star-on" color="warning" :loading="loading"/>
      </el-col>
    </el-row>

    <el-row :gutter="15" style="margin-bottom: 15px;">
      <!-- 增长趋势 -->
      <el-col :lg="16" :md="24">
        <el-card shadow="never">
          <div slot="header" class="hdr">
            <span>用户增长趋势</span>
            <el-radio-group v-model="periodDays" size="mini" @change="fetchAll">
              <el-radio-button :label="7">7天</el-radio-button>
              <el-radio-button :label="30">30天</el-radio-button>
              <el-radio-button :label="60">60天</el-radio-button>
            </el-radio-group>
          </div>
          <div ref="chartGrowth" style="height: 300px;" v-loading="loading"></div>
        </el-card>
      </el-col>
      <!-- 用户分层 -->
      <el-col :lg="8" :md="24">
        <el-card shadow="never">
          <div slot="header">用户分层（按点卡余额）</div>
          <div ref="chartTiers" style="height: 300px;" v-loading="loading"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 排行榜 -->
    <el-row :gutter="15">
      <el-col :lg="8" :md="24">
        <el-card shadow="never">
          <div slot="header" class="hdr">
            <span>点卡余额排行</span>
            <el-tag type="warning" size="mini">Top {{ rankLimit }}</el-tag>
          </div>
          <el-table :data="rankPointCard" size="mini" stripe :show-header="false" max-height="320">
            <el-table-column width="40" align="center">
              <template slot-scope="{row}"><span class="rank-num">{{ row.rank }}</span></template>
            </el-table-column>
            <el-table-column prop="email" show-overflow-tooltip/>
            <el-table-column width="100" align="right">
              <template slot-scope="{row}"><span style="font-weight:600;">{{ row.value.toFixed(2) }}</span></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :lg="8" :md="24">
        <el-card shadow="never">
          <div slot="header" class="hdr">
            <span>累计奖励排行</span>
            <el-tag type="success" size="mini">Top {{ rankLimit }}</el-tag>
          </div>
          <el-table :data="rankReward" size="mini" stripe :show-header="false" max-height="320">
            <el-table-column width="40" align="center">
              <template slot-scope="{row}"><span class="rank-num">{{ row.rank }}</span></template>
            </el-table-column>
            <el-table-column prop="email" show-overflow-tooltip/>
            <el-table-column width="100" align="right">
              <template slot-scope="{row}"><span style="font-weight:600;">{{ row.value.toFixed(2) }}</span></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :lg="8" :md="24">
        <el-card shadow="never">
          <div slot="header" class="hdr">
            <span>成交笔数排行</span>
            <el-tag type="primary" size="mini">Top {{ rankLimit }}</el-tag>
          </div>
          <el-table :data="rankTrade" size="mini" stripe :show-header="false" max-height="320">
            <el-table-column width="40" align="center">
              <template slot-scope="{row}"><span class="rank-num">{{ row.rank }}</span></template>
            </el-table-column>
            <el-table-column prop="email" show-overflow-tooltip/>
            <el-table-column width="80" align="right">
              <template slot-scope="{row}"><span style="font-weight:600;">{{ row.value }}</span></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import {getUserAnalyticsOverview, getUserRanking, getUserGrowth} from '@/api/monitor'
import * as echarts from 'echarts/core'
import {LineChart, BarChart, PieChart} from 'echarts/charts'
import {GridComponent, TooltipComponent, LegendComponent} from 'echarts/components'
import {CanvasRenderer} from 'echarts/renderers'

echarts.use([LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

export default {
  name: 'UserAnalytics',
  data() {
    return {
      loading: false,
      periodDays: 30,
      rankLimit: 15,
      overview: {},
      rankPointCard: [],
      rankReward: [],
      rankTrade: [],
      chartInst: {}
    }
  },
  mounted() {
    this.fetchAll()
    this.resizeFn = () => { Object.values(this.chartInst).forEach(c => c && c.resize()) }
    window.addEventListener('resize', this.resizeFn)
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.resizeFn)
    Object.values(this.chartInst).forEach(c => c && c.dispose())
  },
  methods: {
    async fetchAll() {
      this.loading = true
      try {
        const [ovRes, growRes, r1, r2, r3] = await Promise.allSettled([
          getUserAnalyticsOverview(this.periodDays),
          getUserGrowth(this.periodDays),
          getUserRanking({rank_by: 'point_card', limit: this.rankLimit}),
          getUserRanking({rank_by: 'reward', limit: this.rankLimit}),
          getUserRanking({rank_by: 'trade_count', limit: this.rankLimit}),
        ])
        if (ovRes.status === 'fulfilled') {
          this.overview = (ovRes.value.data && ovRes.value.data.data) || {}
          this.$nextTick(() => { this.renderTiers() })
        }
        if (growRes.status === 'fulfilled') {
          const g = (growRes.value.data && growRes.value.data.data) || {}
          this.$nextTick(() => { this.renderGrowth(g) })
        }
        if (r1.status === 'fulfilled') { this.rankPointCard = (r1.value.data && r1.value.data.data) || [] }
        if (r2.status === 'fulfilled') { this.rankReward = (r2.value.data && r2.value.data.data) || [] }
        if (r3.status === 'fulfilled') { this.rankTrade = (r3.value.data && r3.value.data.data) || [] }
      } catch (e) {
        console.error(e)
      } finally {
        this.loading = false
      }
    },
    getChart(ref) {
      if (this.chartInst[ref]) { return this.chartInst[ref] }
      const el = this.$refs[ref]
      if (!el) { return null }
      const c = echarts.init(el)
      this.chartInst[ref] = c
      return c
    },
    renderGrowth(g) {
      const chart = this.getChart('chartGrowth')
      if (!chart) { return }
      chart.setOption({
        tooltip: {trigger: 'axis'},
        legend: {data: ['每日新增', '累计用户'], bottom: 0},
        grid: {left: 50, right: 50, top: 20, bottom: 40},
        xAxis: {type: 'category', data: (g.dates || []).map(d => d.slice(5)), axisLabel: {fontSize: 11}},
        yAxis: [
          {type: 'value', name: '新增', splitLine: {lineStyle: {color: '#F2F6FC'}}},
          {type: 'value', name: '累计'}
        ],
        series: [
          {name: '每日新增', type: 'bar', data: g.daily_new || [], itemStyle: {color: '#409EFF', borderRadius: [3, 3, 0, 0]}, barMaxWidth: 16},
          {name: '累计用户', type: 'line', yAxisIndex: 1, data: g.cumulative || [], smooth: true, lineStyle: {color: '#67C23A'}, itemStyle: {color: '#67C23A'}, symbol: 'none'}
        ]
      }, true)
    },
    renderTiers() {
      const chart = this.getChart('chartTiers')
      if (!chart) { return }
      const tiers = this.overview.user_tiers || []
      chart.setOption({
        tooltip: {trigger: 'item', formatter: '{b}: {c} ({d}%)'},
        series: [{
          type: 'pie', radius: ['40%', '70%'],
          label: {fontSize: 11},
          data: tiers.map(t => ({name: t.label, value: t.count})),
          itemStyle: {borderRadius: 4, borderColor: '#fff', borderWidth: 2}
        }]
      }, true)
    }
  }
}
</script>

<style scoped>
.hdr { display: flex; justify-content: space-between; align-items: center; }
.rank-num { display: inline-block; width: 22px; height: 22px; line-height: 22px; text-align: center; border-radius: 50%; background: #f0f2f5; font-size: 12px; font-weight: 600; color: #606266; }
</style>
