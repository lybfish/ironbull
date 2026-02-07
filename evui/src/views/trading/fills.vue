<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px">
      <el-col :span="6">
        <stat-card title="成交笔数" :value="total" icon="el-icon-s-data" color="primary" :loading="loading" help-text="当前筛选结果"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="成交总额" icon="el-icon-coin" color="warning" :loading="loading">
          <template slot="value">{{ formatMoney(stats.totalValue) }}</template>
        </stat-card>
      </el-col>
      <el-col :span="6">
        <stat-card title="总手续费" icon="el-icon-money" color="info" :loading="loading">
          <template slot="value">{{ formatMoney(stats.totalFee) }}</template>
        </stat-card>
      </el-col>
      <el-col :span="6">
        <stat-card title="买入/卖出" :value="stats.buyCount + ' / ' + stats.sellCount" icon="el-icon-s-operation" color="info" :loading="loading"/>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <div class="toolbar">
        <span class="toolbar-title">成交记录</span>
        <el-button size="small" icon="el-icon-refresh" :loading="loading" @click="fetchData">刷新</el-button>
      </div>

      <div class="search-bar">
        <el-form :inline="true" :model="where" size="small">
          <el-form-item label="标的">
            <el-input v-model="where.symbol" placeholder="如 BTC/USDT" clearable style="width:140px" @keyup.enter.native="onSearch"/>
          </el-form-item>
          <el-form-item label="方向">
            <el-select v-model="where.side" placeholder="全部" clearable style="width:100px">
              <el-option label="买入" value="BUY"/>
              <el-option label="卖出" value="SELL"/>
            </el-select>
          </el-form-item>
          <el-form-item label="开/平仓">
            <el-select v-model="where.trade_type" placeholder="全部" clearable style="width:100px">
              <el-option label="开仓" value="OPEN"/>
              <el-option label="平仓" value="CLOSE"/>
              <el-option label="加仓" value="ADD"/>
              <el-option label="减仓" value="REDUCE"/>
            </el-select>
          </el-form-item>
          <el-form-item label="交易所">
            <el-select v-model="where.exchange" placeholder="全部" clearable style="width:120px">
              <el-option
                v-for="ex in exchangeOptions"
                :key="ex"
                :label="ex.toUpperCase()"
                :value="ex"/>
            </el-select>
          </el-form-item>
          <el-form-item label="日期范围">
            <el-date-picker
              v-model="where.dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始"
              end-placeholder="结束"
              value-format="yyyy-MM-dd"
              style="width:240px"/>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" icon="el-icon-search" @click="onSearch">查询</el-button>
            <el-button icon="el-icon-refresh-left" @click="reset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredList"
        stripe
        border
        style="width:100%; margin-top:12px"
        size="small"
        :header-cell-style="{background:'#fafafa'}">
        <el-table-column prop="fill_id" label="成交ID" width="160">
          <template slot-scope="{row}">
            <span :title="row.fill_id" class="id-text">{{ truncateId(row.fill_id) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="order_id" label="订单ID" width="160">
          <template slot-scope="{row}">
            <span :title="row.order_id" class="id-text">{{ truncateId(row.order_id) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="symbol" label="标的" width="110">
          <template slot-scope="{row}">
            <span style="font-weight: 600;">{{ row.symbol }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="exchange" label="交易所" width="100" align="center">
          <template slot-scope="{row}">
            <el-tag size="mini" effect="plain" v-if="row.exchange">{{ (row.exchange || '').toUpperCase() }}</el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="side" label="方向" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag :type="isBuy(row) ? 'success' : 'danger'" size="mini" effect="dark">
              {{ isBuy(row) ? '买入' : '卖出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trade_type" label="开/平仓" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag :type="tradeTypeTag(row.trade_type)" size="mini" effect="plain">
              {{ tradeTypeLabel(row.trade_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="成交价" width="120" align="right">
          <template slot-scope="{row}">{{ formatPrice(row.price) }}</template>
        </el-table-column>
        <el-table-column prop="quantity" label="成交量" width="110" align="right">
          <template slot-scope="{row}">{{ formatNum(row.quantity) }}</template>
        </el-table-column>
        <el-table-column label="成交金额" width="130" align="right">
          <template slot-scope="{row}">
            <span style="font-weight: 500;">{{ formatMoney(row.value || (row.quantity * row.price)) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="fee" label="手续费" width="100" align="right">
          <template slot-scope="{row}">{{ formatNum(row.fee) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="成交时间" min-width="170">
          <template slot-scope="{row}">{{ formatTime(row.filled_at || row.created_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && filteredList.length === 0" description="暂无成交记录"/>

      <div v-if="total > 0" class="pagination-wrap">
        <span class="total-tip">共 {{ total }} 条</span>
        <el-pagination
          background
          layout="prev, pager, next, sizes"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          :page-size.sync="pageSize"
          :current-page.sync="currentPage"
          @size-change="fetchData"
          @current-change="fetchData"/>
      </div>
    </el-card>
  </div>
</template>

<script>
import { getFills } from '@/api/trading'
import { getExchangeAccounts } from '@/api/admin'

export default {
  name: 'FillList',
  data() {
    return {
      loading: false,
      list: [],
      total: 0,
      currentPage: 1,
      pageSize: 20,
      where: { symbol: '', side: '', trade_type: '', exchange: '', dateRange: null },
      accountOptions: []
    }
  },
  computed: {
    exchangeOptions() {
      const set = new Set()
      this.list.forEach(r => { if (r.exchange) set.add(r.exchange) })
      this.accountOptions.forEach(a => { if (a.exchange) set.add(a.exchange) })
      return Array.from(set).sort()
    },
    filteredList() {
      return this.list.filter(r => {
        if (this.where.exchange) {
          if ((r.exchange || '').toLowerCase() !== this.where.exchange.toLowerCase()) return false
        }
        return true
      })
    },
    stats() {
      let totalFee = 0
      let totalValue = 0
      let buyCount = 0
      let sellCount = 0
      this.filteredList.forEach(row => {
        totalFee += parseFloat(row.fee || 0)
        totalValue += parseFloat(row.value || (row.quantity * row.price) || 0)
        if (this.isBuy(row)) buyCount++
        else sellCount++
      })
      return { totalFee, totalValue, buyCount, sellCount }
    }
  },
  mounted() {
    this.fetchData()
    this.fetchAccounts()
  },
  methods: {
    isBuy(row) {
      return (row.side || '').toUpperCase() === 'BUY'
    },
    tradeTypeLabel(t) {
      return { OPEN: '开仓', CLOSE: '平仓', ADD: '加仓', REDUCE: '减仓' }[t] || t || '开仓'
    },
    tradeTypeTag(t) {
      return { OPEN: '', CLOSE: 'danger', ADD: 'warning', REDUCE: 'info' }[t] || ''
    },
    formatPrice(val) {
      if (val == null || val === '') return '-'
      const n = Number(val)
      if (isNaN(n)) return val
      if (n >= 1000) return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      if (n >= 1) return n.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
      return n.toLocaleString('en-US', { minimumFractionDigits: 6, maximumFractionDigits: 8 })
    },
    formatNum(v) {
      if (v == null || v === '') return '0'
      const n = parseFloat(v)
      return isNaN(n) ? '0' : n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 6 })
    },
    formatMoney(val) {
      if (val == null || val === '') return '0.00'
      const n = Number(val)
      return isNaN(n) ? '0.00' : n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    },
    formatTime(t) {
      if (!t) return '-'
      const d = new Date(t)
      if (isNaN(d.getTime())) return String(t).replace('T', ' ').substring(0, 19)
      const pad = n => String(n).padStart(2, '0')
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
    },
    truncateId(id) {
      if (!id) return '-'
      const str = String(id)
      return str.length <= 12 ? str : str.slice(0, 8) + '...' + str.slice(-4)
    },
    onSearch() {
      this.currentPage = 1
      this.fetchData()
    },
    reset() {
      this.where = { symbol: '', side: '', trade_type: '', exchange: '', dateRange: null }
      this.currentPage = 1
      this.fetchData()
    },
    async fetchAccounts() {
      try {
        const res = await getExchangeAccounts({ status: 1 })
        this.accountOptions = (res.data.data || res.data || [])
      } catch (e) { /* 静默 */ }
    },
    async fetchData() {
      this.loading = true
      try {
        const params = {
          limit: this.pageSize,
          offset: (this.currentPage - 1) * this.pageSize
        }
        if (this.where.symbol) params.symbol = this.where.symbol
        if (this.where.side) params.side = this.where.side
        if (this.where.trade_type) params.trade_type = this.where.trade_type
        if (this.where.dateRange && this.where.dateRange.length === 2) {
          params.start_time = this.where.dateRange[0] + 'T00:00:00'
          params.end_time = this.where.dateRange[1] + 'T23:59:59'
        }
        const res = await getFills(params)
        const data = res.data
        this.list = data.data || []
        this.total = data.total != null ? data.total : this.list.length
      } catch (e) {
        this.$message.error(e.response?.data?.detail || '获取成交记录失败')
        this.list = []
        this.total = 0
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.toolbar-title { font-size: 16px; font-weight: 500; color: #303133; }
.search-bar { margin-bottom: 12px; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.total-tip { color: #909399; font-size: 12px; }
.id-text { font-family: 'Courier New', monospace; font-size: 12px; color: #606266; cursor: default; }
.text-muted { color: #C0C4CC; }
</style>
