<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px">
      <el-col :span="6">
        <stat-card title="流水条数" :value="total" icon="el-icon-s-order" color="primary" :loading="loading" help-text="当前筛选结果"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="收入合计" :value="stats.income" icon="el-icon-top" color="success" :loading="loading">
          <template slot="value">{{ formatCurrency(stats.income) }}</template>
        </stat-card>
      </el-col>
      <el-col :span="6">
        <stat-card title="支出合计" :value="stats.expense" icon="el-icon-bottom" color="danger" :loading="loading">
          <template slot="value">{{ formatCurrency(stats.expense) }}</template>
        </stat-card>
      </el-col>
      <el-col :span="6">
        <stat-card title="净额" :value="stats.net" icon="el-icon-data-analysis" :color="stats.net >= 0 ? 'success' : 'danger'" :loading="loading">
          <template slot="value">
            <span :style="{ color: stats.net >= 0 ? '#67C23A' : '#F56C6C' }">{{ formatCurrency(stats.net) }}</span>
          </template>
        </stat-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <div class="toolbar">
        <span class="toolbar-title">资金流水</span>
        <el-button size="small" icon="el-icon-refresh" :loading="loading" @click="fetchData">刷新</el-button>
      </div>

      <div class="search-bar">
        <el-form :inline="true" size="small">
          <el-form-item label="类型">
            <el-select v-model="filters.tx_type" placeholder="全部" clearable style="width:140px">
              <el-option label="充值" value="DEPOSIT"/>
              <el-option label="提现" value="WITHDRAW"/>
              <el-option label="手续费" value="FEE"/>
              <el-option label="盈亏" value="PNL"/>
              <el-option label="转账" value="TRANSFER"/>
              <el-option label="资金费" value="FUNDING"/>
            </el-select>
          </el-form-item>
          <el-form-item label="币种">
            <el-input v-model="filters.currency" placeholder="币种" clearable style="width:100px" @keyup.enter.native="onSearch"/>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" icon="el-icon-search" @click="onSearch">查询</el-button>
            <el-button icon="el-icon-refresh-left" @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table
        v-loading="loading"
        :data="list"
        stripe
        border
        style="width:100%; margin-top:12px"
        size="small"
        :header-cell-style="{background:'#fafafa'}">
        <el-table-column prop="tx_id" label="流水ID" width="120"/>
        <el-table-column prop="account_id" label="账户ID" width="100"/>
        <el-table-column prop="tx_type" label="类型" width="100">
          <template slot-scope="{row}">
            <el-tag :type="getTxTypeTagType(row.tx_type)" size="small">{{ getTxTypeLabel(row.tx_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="currency" label="币种" width="80"/>
        <el-table-column prop="amount" label="金额" width="120" align="right">
          <template slot-scope="{row}">
            <span :style="{ color: parseFloat(row.amount) >= 0 ? '#67C23A' : '#F56C6C' }">{{ formatCurrency(row.amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="balance_after" label="变动后余额" width="120" align="right">
          <template slot-scope="{row}">{{ formatCurrency(row.balance_after) }}</template>
        </el-table-column>
        <el-table-column prop="description" label="备注" min-width="150" show-overflow-tooltip>
          <template slot-scope="{row}">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column prop="reference_id" label="参考ID" width="120" show-overflow-tooltip/>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template slot-scope="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && list.length === 0" description="暂无流水记录"/>

      <div v-if="total > 0" class="pagination-wrap">
        <span class="total-tip">共 {{ total }} 条</span>
        <el-pagination
          background
          layout="prev, pager, next, sizes"
          :total="total"
          :page-sizes="[20, 50, 100, 200]"
          :page-size.sync="pagination.limit"
          :current-page.sync="pagination.page"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"/>
      </div>
    </el-card>
  </div>
</template>

<script>
import { getTransactions } from '@/api/trading'

export default {
  name: 'TransactionList',
  data() {
    return {
      loading: false,
      list: [],
      total: 0,
      filters: { tx_type: '', currency: '' },
      pagination: { page: 1, limit: 50 }
    }
  },
  computed: {
    stats() {
      let income = 0
      let expense = 0
      this.list.forEach(row => {
        const amt = parseFloat(row.amount) || 0
        if (amt >= 0) income += amt
        else expense += Math.abs(amt)
      })
      return { income, expense, net: income - expense }
    }
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    formatTime(t) {
      return t ? String(t).replace('T', ' ').substring(0, 19) : '-'
    },
    formatCurrency(value) {
      if (value == null || value === '') return '0.00'
      const num = parseFloat(value)
      return isNaN(num) ? '0.00' : num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    },
    onSearch() {
      this.pagination.page = 1
      this.fetchData()
    },
    handleReset() {
      this.filters = { tx_type: '', currency: '' }
      this.pagination.page = 1
      this.fetchData()
    },
    handleSizeChange(val) {
      this.pagination.limit = val
      this.pagination.page = 1
      this.fetchData()
    },
    handlePageChange(val) {
      this.pagination.page = val
      this.fetchData()
    },
    getTxTypeLabel(type) {
      const labels = { DEPOSIT: '充值', WITHDRAW: '提现', FEE: '手续费', PNL: '盈亏', TRANSFER: '转账', FUNDING: '资金费' }
      return labels[type] || type
    },
    getTxTypeTagType(type) {
      const types = { DEPOSIT: 'success', WITHDRAW: 'warning', FEE: 'info', PNL: 'success', TRANSFER: '', FUNDING: 'info' }
      return types[type] || ''
    },
    async fetchData() {
      this.loading = true
      try {
        const params = {
          offset: (this.pagination.page - 1) * this.pagination.limit,
          limit: this.pagination.limit
        }
        if (this.filters.tx_type) params.transaction_type = this.filters.tx_type
        if (this.filters.currency) params.currency = this.filters.currency
        const res = await getTransactions(params)
        const data = res.data
        this.list = data.data || []
        this.total = data.total != null ? data.total : this.list.length
      } catch (e) {
        this.$message.error(e.response?.data?.detail || '获取流水失败')
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
</style>
