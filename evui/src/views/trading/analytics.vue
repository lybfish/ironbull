<template>
  <div class="ele-body">
    <!-- 账户选择器 -->
    <el-card shadow="never" style="margin-bottom: 15px;">
      <el-form :inline="true" size="small">
        <el-form-item label="选择账户">
          <el-select v-model="accountId" placeholder="请选择交易账户" @change="handleAccountChange" style="width:280px"
            :loading="accountsLoading">
            <el-option v-for="acc in accounts" :key="acc.id" :label="`#${acc.id} ${acc.user_email ? acc.user_email + ' - ' : ''}${acc.exchange} (${acc.account_type})`" :value="acc.id"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="el-icon-refresh" @click="fetchAll" :disabled="!accountId">刷新数据</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div v-if="!accountId && !accountsLoading">
      <el-empty description="请先选择一个交易账户以查看分析数据"/>
    </div>

    <div v-if="accountId">
      <!-- 统计卡片行 -->
      <el-row :gutter="15" style="margin-bottom: 15px;">
        <el-col :lg="4" :md="8" :sm="12" :xs="24">
          <stat-card title="当前权益" :value="performanceData.current_equity || 0" icon="el-icon-wallet"
            color="primary" format="money" :precision="2" help-text="账户当前总权益" :loading="loading"/>
        </el-col>
        <el-col :lg="4" :md="8" :sm="12" :xs="24">
          <stat-card title="累计收益率" :value="(performanceData.total_return || 0) * 100" icon="el-icon-trophy"
            color="success" format="percent" :precision="2" help-text="累计总收益率" :loading="loading">
            <template slot="value">
              <span :style="{color: (performanceData.total_return || 0) >= 0 ? '#67C23A' : '#F56C6C'}">
                {{ formatPercent(performanceData.total_return) }}
              </span>
            </template>
          </stat-card>
        </el-col>
        <el-col :lg="4" :md="8" :sm="12" :xs="24">
          <stat-card title="日盈亏" :value="performanceData.daily_pnl || 0" icon="el-icon-coin"
            color="warning" format="money" :precision="2" help-text="当日盈亏金额" :loading="loading">
            <template slot="value">
              <span :style="{color: (performanceData.daily_pnl || 0) >= 0 ? '#67C23A' : '#F56C6C'}">
                {{ formatMoney(performanceData.daily_pnl) }}
              </span>
            </template>
          </stat-card>
        </el-col>
        <el-col :lg="4" :md="8" :sm="12" :xs="24">
          <stat-card title="夏普比率" :value="performanceData.sharpe_ratio || 0" icon="el-icon-data-line"
            color="info" format="number" :precision="2" help-text="风险调整后收益指标" :loading="loading"/>
        </el-col>
        <el-col :lg="4" :md="8" :sm="12" :xs="24">
          <stat-card title="最大回撤" :value="(riskData.max_drawdown || 0) * 100" icon="el-icon-bottom"
            color="danger" format="percent" :precision="2" help-text="历史最大回撤幅度" :loading="riskLoading"/>
        </el-col>
        <el-col :lg="4" :md="8" :sm="12" :xs="24">
          <stat-card title="胜率" :value="(performanceData.win_rate || 0) * 100" icon="el-icon-success"
            color="success" format="percent" :precision="1" help-text="盈利交易占比" :loading="loading"/>
        </el-col>
      </el-row>

      <!-- 权益曲线图表 -->
      <el-card shadow="never" style="margin-top: 16px" v-loading="curveLoading">
        <div slot="header">
          <span>权益曲线</span>
          <el-date-picker
            v-model="curveDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始"
            end-placeholder="结束"
            value-format="yyyy-MM-dd"
            size="mini"
            style="margin-left: 16px; width: 260px"
            @change="fetchEquityCurve"/>
        </div>
        <div ref="equityChart" style="width: 100%; height: 320px"></div>
        <el-empty v-if="!curveLoading && equityCurve.length === 0" description="暂无净值数据，请确认日期范围"/>
      </el-card>

      <!-- 绩效汇总卡片 -->
      <el-card shadow="never" style="margin-top: 16px" v-loading="loading">
        <div slot="header">绩效汇总</div>
        <el-row :gutter="20">
          <el-col :span="8">
            <div class="metric-item">
              <div class="metric-label">盈利因子</div>
              <div class="metric-value">{{ formatNumber(performanceData.profit_factor) }}</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="metric-item">
              <div class="metric-label">平均交易盈亏</div>
              <div class="metric-value">{{ formatMoney(performanceData.avg_trade_pnl) }}</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="metric-item">
              <div class="metric-label">总交易次数</div>
              <div class="metric-value">{{ performanceData.total_trades || 0 }}</div>
            </div>
          </el-col>
        </el-row>
      </el-card>

      <!-- 风险指标卡片 -->
      <el-card shadow="never" style="margin-top: 16px" v-loading="riskLoading">
        <div slot="header">风险指标</div>
        <el-row :gutter="20">
          <el-col :span="6">
            <div class="metric-item">
              <div class="metric-label">最大回撤</div>
              <div class="metric-value">{{ formatPercent(riskData.max_drawdown) }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric-item">
              <div class="metric-label">VaR (95%)</div>
              <div class="metric-value">{{ formatMoney(riskData.var_95) }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric-item">
              <div class="metric-label">波动率</div>
              <div class="metric-value">{{ formatPercent(riskData.volatility) }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric-item">
              <div class="metric-label">风险等级</div>
              <div class="metric-value">
                <el-tag :type="getRiskTagType(riskData.risk_level)" size="small">{{ riskData.risk_level || '-' }}</el-tag>
              </div>
            </div>
          </el-col>
          <el-col :span="6" style="margin-top: 16px">
            <div class="metric-item">
              <div class="metric-label">当前回撤</div>
              <div class="metric-value">{{ formatPercent(riskData.current_drawdown) }}</div>
            </div>
          </el-col>
        </el-row>
      </el-card>

      <!-- 统计数据表格 -->
      <el-card shadow="never" style="margin-top: 16px" v-loading="statsLoading">
        <div slot="header">交易统计</div>
        <el-table :data="statsList" stripe border size="small" :header-cell-style="{background:'#fafafa'}">
          <el-table-column prop="date" label="日期" width="120"/>
          <el-table-column prop="symbol" label="交易对" width="150"/>
          <el-table-column prop="trades" label="交易次数" width="100" align="right"/>
          <el-table-column prop="pnl" label="盈亏" width="120" align="right">
            <template slot-scope="{row}">
              <span :style="{color: (row.pnl || 0) >= 0 ? '#67C23A' : '#F56C6C'}">{{ formatMoney(row.pnl) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="win_rate" label="胜率" width="100" align="right">
            <template slot-scope="{row}">{{ formatPercent(row.win_rate) }}</template>
          </el-table-column>
          <el-table-column prop="volume" label="成交量" width="120" align="right">
            <template slot-scope="{row}">{{ formatMoney(row.volume) }}</template>
          </el-table-column>
          <el-table-column prop="fees" label="手续费" width="120" align="right">
            <template slot-scope="{row}">{{ formatMoney(row.fees) }}</template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!statsLoading && statsList.length === 0" description="暂无统计数据"/>
      </el-card>
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts/lib/echarts'
import 'echarts/lib/chart/line'
import 'echarts/lib/component/tooltip'
import 'echarts/lib/component/grid'
import 'echarts/lib/component/dataZoom'

import {getPerformance, getRisk, getStatistics} from '@/api/analytics'
import {getExchangeAccounts} from '@/api/admin'

export default {
  name: 'Analytics',
  data() {
    return {
      accountsLoading: false,
      accounts: [],
      accountId: null,
      loading: false,
      riskLoading: false,
      statsLoading: false,
      curveLoading: false,
      performanceData: {},
      riskData: {},
      statsList: [],
      equityCurve: [],
      curveDateRange: null,
      chartInstance: null
    }
  },
  beforeDestroy() {
    // 移除窗口 resize 监听
    window.removeEventListener('resize', this._handleResize)
    if (this.chartInstance) {
      this.chartInstance.dispose()
      this.chartInstance = null
    }
  },
  mounted() {
    // 监听窗口 resize，自动调整图表尺寸
    this._handleResize = () => {
      if (this.chartInstance) this.chartInstance.resize()
    }
    window.addEventListener('resize', this._handleResize)
    this.fetchAccounts()
  },
  methods: {
    formatMoney(val) {
      if (val === null || val === undefined) return '-'
      return Number(val).toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})
    },
    formatPercent(val) {
      if (val === null || val === undefined) return '-'
      return (Number(val) * 100).toFixed(2) + '%'
    },
    formatNumber(val, decimals = 2) {
      if (val === null || val === undefined) return '-'
      return Number(val).toFixed(decimals)
    },
    getRiskTagType(riskLevel) {
      if (!riskLevel) return 'info'
      const level = riskLevel.toString().toLowerCase()
      if (level.includes('低') || level.includes('low')) return 'success'
      if (level.includes('中') || level.includes('medium')) return 'warning'
      if (level.includes('高') || level.includes('high')) return 'danger'
      return 'info'
    },
    async fetchAccounts() {
      this.accountsLoading = true
      try {
        const res = await getExchangeAccounts({page_size: 100})
        const data = res.data.data || res.data || []
        this.accounts = Array.isArray(data) ? data : []
        if (this.accounts.length > 0 && !this.accountId) {
          this.accountId = this.accounts[0].id
          this.fetchAll()
        }
      } catch (e) {
        console.error('获取账户列表失败:', e)
      } finally {
        this.accountsLoading = false
      }
    },
    handleAccountChange() {
      if (this.accountId) this.fetchAll()
    },
    fetchAll() {
      this.fetchPerformance()
      this.fetchRisk()
      this.fetchStatistics()
      this.fetchEquityCurve()
    },
    async fetchPerformance() {
      if (!this.accountId) return
      this.loading = true
      try {
        const res = await getPerformance({account_id: this.accountId})
        if (res.data.success && res.data.data) {
          this.performanceData = res.data.data.summary || {}
        }
      } catch (e) {
        this.$message.error('获取绩效数据失败')
        console.error('获取绩效数据失败:', e)
      } finally {
        this.loading = false
      }
    },
    async fetchRisk() {
      if (!this.accountId) return
      this.riskLoading = true
      try {
        const res = await getRisk({account_id: this.accountId})
        if (res.data.success && res.data.data) {
          this.riskData = res.data.data || {}
        }
      } catch (e) {
        this.$message.error('获取风险数据失败')
        console.error('获取风险数据失败:', e)
      } finally {
        this.riskLoading = false
      }
    },
    async fetchStatistics() {
      if (!this.accountId) return
      this.statsLoading = true
      try {
        const res = await getStatistics({account_id: this.accountId})
        if (res.data.success && res.data.data) {
          this.statsList = res.data.data || []
        }
      } catch (e) {
        this.$message.error('获取统计数据失败')
        console.error('获取统计数据失败:', e)
      } finally {
        this.statsLoading = false
      }
    },
    async fetchEquityCurve() {
      if (!this.accountId) return
      this.curveLoading = true
      try {
        const params = {account_id: this.accountId}
        if (this.curveDateRange && this.curveDateRange.length === 2) {
          params.start_date = this.curveDateRange[0]
          params.end_date = this.curveDateRange[1]
        } else {
          // 默认最近30天
          const end = new Date()
          const start = new Date(end.getTime() - 30 * 86400000)
          const fmt = d => d.toISOString().slice(0, 10)
          params.start_date = fmt(start)
          params.end_date = fmt(end)
        }
        const res = await getPerformance(params)
        if (res.data.success && res.data.data && res.data.data.equity_curve) {
          const raw = res.data.data.equity_curve
          const curve = Array.isArray(raw) ? raw : []
          // 过滤无效点：日期非空且权益为有效数字（避免 NaN/空导致图表异常）
          this.equityCurve = curve.filter(p => {
            const date = p.date || p.snapshot_date || ''
            const val = Number(p.equity ?? p.nav ?? p.value ?? 0)
            return date && !Number.isNaN(val) && val >= 0
          })
        } else {
          this.equityCurve = []
        }
        this.$nextTick(() => this.renderChart())
      } catch (e) {
        this.equityCurve = []
      } finally {
        this.curveLoading = false
      }
    },
    renderChart() {
      if (!this.$refs.equityChart) return
      if (this.equityCurve.length === 0) {
        if (this.chartInstance) { this.chartInstance.clear() }
        return
      }
      if (!this.chartInstance) {
        this.chartInstance = echarts.init(this.$refs.equityChart)
      }
      const dates = this.equityCurve.map(p => p.date || p.snapshot_date || '')
      const equities = this.equityCurve.map(p => {
        const v = Number(p.equity ?? p.nav ?? p.value ?? 0)
        return Number.isNaN(v) ? 0 : v
      })
      this.chartInstance.setOption({
        tooltip: { trigger: 'axis', formatter: params => {
          const p = params[0]
          return `${p.axisValue}<br/>权益: <b>${Number(p.value).toFixed(2)}</b> USDT`
        }},
        grid: { left: 60, right: 20, top: 20, bottom: 60 },
        xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11 } },
        yAxis: { type: 'value', axisLabel: { formatter: v => v.toFixed(0) } },
        dataZoom: [{ type: 'inside', start: 0, end: 100 }, { type: 'slider', start: 0, end: 100, height: 20, bottom: 5 }],
        series: [{
          type: 'line', data: equities, smooth: true, symbol: 'none',
          lineStyle: { width: 2, color: '#409EFF' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64,158,255,0.3)' },
            { offset: 1, color: 'rgba(64,158,255,0.02)' }
          ])}
        }]
      })
    }
  }
}
</script>

<style scoped>
.metric-item { padding: 12px 0; text-align: center; }
.metric-label { color: #909399; font-size: 13px; margin-bottom: 8px; }
.metric-value { font-size: 20px; font-weight: 600; color: #303133; }
</style>
