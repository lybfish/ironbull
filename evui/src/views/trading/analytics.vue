<template>
  <div class="ele-body">
    <!-- 账户选择器 -->
    <el-card shadow="never" style="margin-bottom: 15px;">
      <el-form :inline="true" size="small">
        <el-form-item label="选择账户">
          <el-select v-model="accountId" placeholder="请选择交易账户" @change="handleAccountChange" style="width:280px"
            :loading="accountsLoading">
            <el-option v-for="acc in accounts" :key="acc.id" :label="`#${acc.id} - ${acc.exchange} (${acc.account_type})`" :value="acc.id"/>
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
import {getPerformance, getRisk, getStatistics} from '@/api/analytics'
import {getAccounts} from '@/api/trading'

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
      performanceData: {},
      riskData: {},
      statsList: []
    }
  },
  mounted() {
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
        const res = await getAccounts()
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
        console.error('获取统计数据失败:', e)
      } finally {
        this.statsLoading = false
      }
    }
  }
}
</script>

<style scoped>
.metric-item { padding: 12px 0; text-align: center; }
.metric-label { color: #909399; font-size: 13px; margin-bottom: 8px; }
.metric-value { font-size: 20px; font-weight: 600; color: #303133; }
</style>
