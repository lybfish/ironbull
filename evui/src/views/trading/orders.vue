<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px">
      <el-col :span="6">
        <stat-card title="订单总数" :value="total" icon="el-icon-s-order" color="primary" :loading="loading" help-text="当前筛选结果"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="已成交" :value="stats.filled" icon="el-icon-circle-check" color="success" :loading="loading"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="已取消/拒绝" :value="stats.cancelled" icon="el-icon-remove-outline" color="info" :loading="loading"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="待处理/部分" :value="stats.pending" icon="el-icon-time" color="warning" :loading="loading"/>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <div class="toolbar">
        <span class="toolbar-title">订单列表</span>
        <el-button size="small" icon="el-icon-refresh" :loading="loading" @click="fetchData">刷新</el-button>
      </div>

      <div class="search-bar">
        <el-form :inline="true" :model="where" size="small">
          <el-form-item label="标的">
            <el-input v-model="where.symbol" placeholder="如 BTC/USDT" clearable style="width:140px" @keyup.enter.native="onSearch"/>
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
          <el-form-item label="状态">
            <el-select v-model="where.status" placeholder="全部" clearable style="width:120px">
              <el-option label="待处理" value="PENDING"/>
              <el-option label="已成交" value="FILLED"/>
              <el-option label="已取消" value="CANCELLED"/>
              <el-option label="已拒绝" value="REJECTED"/>
              <el-option label="部分成交" value="PARTIAL"/>
            </el-select>
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
        <el-table-column prop="order_id" label="订单ID" width="140">
          <template slot-scope="{row}">
            <el-tooltip content="点击查看关联成交" placement="top">
              <span class="id-text copyable" @click="goToFills(row.order_id)">{{ truncateId(row.order_id) }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="symbol" label="标的" width="110">
          <template slot-scope="{row}">
            <span style="font-weight: 600;">{{ row.symbol }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="exchange" label="交易所" width="90" align="center">
          <template slot-scope="{row}">
            <el-tag size="mini" effect="plain">{{ (row.exchange || '').toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="账户" width="60" align="center">
          <template slot-scope="{row}">
            <span class="text-muted">#{{ row.account_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="side" label="方向" width="90" align="center">
          <template slot-scope="{row}">
            <el-tag :type="isBuy(row) ? 'success' : 'danger'" size="mini" effect="dark">
              {{ isBuy(row) ? '买入' : '卖出' }}
            </el-tag>
            <div v-if="row.position_side" style="font-size:11px;color:#909399;margin-top:2px">{{ row.position_side }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="order_type" label="类型" width="80" align="center">
          <template slot-scope="{row}">
            <span>{{ row.order_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="开/平仓" width="100" align="center">
          <template slot-scope="{row}">
            <el-tag :type="tradeTypeTag(row.trade_type)" size="mini" effect="dark">
              {{ tradeTypeLabel(row.trade_type) }}
            </el-tag>
            <div v-if="row.close_reason" style="font-size:11px;margin-top:2px">
              <el-tag :type="row.close_reason === 'TP' ? 'success' : 'danger'" size="mini" effect="plain">
                {{ closeReasonLabel(row.close_reason) }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="杠杆" width="60" align="center">
          <template slot-scope="{row}">
            <span v-if="row.leverage">{{ row.leverage }}x</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="成交进度" width="130" align="center">
          <template slot-scope="{row}">
            <div class="progress-cell">
              <el-progress
                :percentage="fillPercent(row)"
                :stroke-width="14"
                :text-inside="true"
                :color="fillPercent(row) >= 100 ? '#67c23a' : '#409eff'"
                style="width: 100%;"/>
              <span class="progress-text">{{ formatNum(row.filled_quantity) }} / {{ formatNum(row.quantity) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="委托价" width="100" align="right">
          <template slot-scope="{row}">{{ formatPrice(row.price) }}</template>
        </el-table-column>
        <el-table-column prop="avg_price" label="成交均价" width="100" align="right">
          <template slot-scope="{row}">{{ formatPrice(row.avg_price) }}</template>
        </el-table-column>
        <el-table-column label="止损/止盈" width="110" align="right">
          <template slot-scope="{row}">
            <div v-if="row.stop_loss || row.take_profit" style="line-height:1.4">
              <div v-if="row.stop_loss" style="color:#F56C6C;font-size:12px">SL {{ formatPrice(row.stop_loss) }}</div>
              <div v-if="row.take_profit" style="color:#67C23A;font-size:12px">TP {{ formatPrice(row.take_profit) }}</div>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="手续费" width="80" align="right">
          <template slot-scope="{row}">
            <span v-if="row.total_fee">{{ formatNum(row.total_fee) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template slot-scope="{row}">
            <el-tag :type="statusType(row.status)" size="mini">{{ statusLabel(row.status) }}</el-tag>
            <el-tooltip v-if="row.error_message" :content="row.error_message" placement="top">
              <i class="el-icon-warning" style="color:#F56C6C;margin-left:4px;cursor:pointer"></i>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="160">
          <template slot-scope="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && filteredList.length === 0" description="暂无订单"/>

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
import { getOrders } from '@/api/trading'
import { getExchangeAccounts } from '@/api/admin'

export default {
  name: 'OrderList',
  data() {
    return {
      loading: false,
      list: [],
      total: 0,
      currentPage: 1,
      pageSize: 20,
      where: { symbol: '', status: '', side: '', exchange: '', trade_type: '', dateRange: null },
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
      return this.list
    },
    stats() {
      const s = { filled: 0, cancelled: 0, pending: 0 }
      this.filteredList.forEach(row => {
        const st = (row.status || '').toUpperCase()
        if (st === 'FILLED') s.filled++
        else if (st === 'CANCELLED' || st === 'REJECTED') s.cancelled++
        else s.pending++
      })
      return s
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
    formatTime(t) {
      if (!t) return '-'
      const d = new Date(t)
      if (isNaN(d.getTime())) return String(t).replace('T', ' ').substring(0, 19)
      const pad = n => String(n).padStart(2, '0')
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
    },
    formatPrice(val) {
      if (val == null || val === '' || val === 0) return '-'
      const n = Number(val)
      if (isNaN(n)) return val
      if (n >= 1000) return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      if (n >= 1) return n.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
      return n.toLocaleString('en-US', { minimumFractionDigits: 6, maximumFractionDigits: 8 })
    },
    formatNum(v) {
      if (v == null || v === '') return '0'
      const n = parseFloat(v)
      return isNaN(n) ? '0' : n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 6 })
    },
    truncateId(id) {
      if (!id) return '-'
      const str = String(id)
      return str.length <= 12 ? str : str.slice(0, 8) + '...' + str.slice(-4)
    },
    copyId(id) {
      if (!id) return
      if (navigator.clipboard) {
        navigator.clipboard.writeText(id).then(() => {
          this.$message.success('已复制: ' + id)
        })
      }
    },
    fillPercent(row) {
      const qty = parseFloat(row.quantity) || 0
      const filled = parseFloat(row.filled_quantity) || 0
      if (qty <= 0) return 0
      return Math.min(100, Math.round((filled / qty) * 100))
    },
    statusType(s) {
      const m = { PENDING: 'warning', FILLED: 'success', CANCELLED: 'info', REJECTED: 'danger', PARTIAL: 'warning' }
      return m[(s || '').toUpperCase()] || 'info'
    },
    statusLabel(s) {
      const m = { PENDING: '待处理', FILLED: '已成交', CANCELLED: '已取消', REJECTED: '已拒绝', PARTIAL: '部分成交' }
      return m[(s || '').toUpperCase()] || s
    },
    tradeTypeLabel(t) {
      const m = { OPEN: '开仓', CLOSE: '平仓', ADD: '加仓', REDUCE: '减仓' }
      return m[(t || '').toUpperCase()] || '开仓'
    },
    tradeTypeTag(t) {
      const m = { OPEN: '', CLOSE: 'warning', ADD: 'info', REDUCE: 'info' }
      return m[(t || '').toUpperCase()] || ''
    },
    closeReasonLabel(r) {
      const m = { SL: '止损', TP: '止盈', SIGNAL: '信号平仓', MANUAL: '手动平仓', LIQUIDATION: '强平' }
      return m[(r || '').toUpperCase()] || r
    },
    goToFills(orderId) {
      this.$router.push({ path: '/trading/fills', query: { order_id: orderId } })
    },
    onSearch() {
      this.currentPage = 1
      this.fetchData()
    },
    reset() {
      this.where = { symbol: '', status: '', side: '', exchange: '', trade_type: '', dateRange: null }
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
        if (this.where.status) params.status = this.where.status
        if (this.where.side) params.side = this.where.side
        if (this.where.trade_type) params.trade_type = this.where.trade_type
        if (this.where.exchange) params.exchange = this.where.exchange
        if (this.where.dateRange && this.where.dateRange.length === 2) {
          params.start_time = this.where.dateRange[0] + 'T00:00:00'
          params.end_time = this.where.dateRange[1] + 'T23:59:59'
        }
        const res = await getOrders(params)
        const data = res.data
        this.list = data.data || []
        this.total = data.total != null ? data.total : this.list.length
      } catch (e) {
        this.$message.error(e.response?.data?.detail || '获取订单失败')
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
.id-text { font-family: 'Courier New', monospace; font-size: 12px; color: #606266; }
.copyable { cursor: pointer; }
.copyable:hover { color: #409eff; text-decoration: underline; }
.progress-cell { display: flex; flex-direction: column; gap: 2px; }
.progress-text { font-size: 11px; color: #909399; text-align: center; }
.text-muted { color: #C0C4CC; }
</style>
