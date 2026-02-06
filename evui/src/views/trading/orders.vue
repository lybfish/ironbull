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
          <el-form-item label="状态">
            <el-select v-model="where.status" placeholder="全部" clearable style="width:120px">
              <el-option label="PENDING" value="PENDING"/>
              <el-option label="FILLED" value="FILLED"/>
              <el-option label="CANCELLED" value="CANCELLED"/>
              <el-option label="REJECTED" value="REJECTED"/>
              <el-option label="PARTIAL" value="PARTIAL"/>
            </el-select>
          </el-form-item>
          <el-form-item label="方向">
            <el-select v-model="where.side" placeholder="全部" clearable style="width:100px">
              <el-option label="买入" value="buy"/>
              <el-option label="卖出" value="sell"/>
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
        :data="list"
        stripe
        border
        style="width:100%; margin-top:12px"
        size="small"
        :header-cell-style="{background:'#fafafa'}">
        <el-table-column prop="order_id" label="订单ID" width="160">
          <template slot-scope="{row}">
            <span :title="row.order_id">{{ truncateId(row.order_id) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="symbol" label="标的" width="110"/>
        <el-table-column prop="exchange" label="交易所" width="100" align="center">
          <template slot-scope="{row}">
            <el-tag size="mini">{{ row.exchange }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="side" label="方向" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.side === 'buy' || row.side === 'BUY' ? 'success' : 'danger'" size="mini">
              {{ row.side === 'buy' || row.side === 'BUY' ? '买入' : '卖出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="order_type" label="类型" width="80"/>
        <el-table-column prop="quantity" label="数量" width="100" align="right"/>
        <el-table-column prop="filled_quantity" label="已成交" width="100" align="right"/>
        <el-table-column prop="price" label="价格" width="100" align="right"/>
        <el-table-column prop="avg_price" label="均价" width="100" align="right"/>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template slot-scope="{row}">
            <el-tag :type="statusType(row.status)" size="mini">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="170">
          <template slot-scope="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && list.length === 0" description="暂无订单"/>

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

export default {
  name: 'OrderList',
  data() {
    return {
      loading: false,
      list: [],
      total: 0,
      currentPage: 1,
      pageSize: 20,
      where: { symbol: '', status: '', side: '', dateRange: null }
    }
  },
  computed: {
    stats() {
      const s = { filled: 0, cancelled: 0, pending: 0 }
      this.list.forEach(row => {
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
  },
  methods: {
    formatTime(t) {
      return t ? String(t).replace('T', ' ').substring(0, 19) : '-'
    },
    truncateId(id) {
      if (!id) return '-'
      const str = String(id)
      return str.length <= 12 ? str : str.slice(0, 8) + '...' + str.slice(-4)
    },
    statusType(s) {
      const m = { PENDING: 'warning', FILLED: 'success', CANCELLED: 'info', REJECTED: 'danger', PARTIAL: 'warning' }
      return m[(s || '').toUpperCase()] || 'info'
    },
    onSearch() {
      this.currentPage = 1
      this.fetchData()
    },
    reset() {
      this.where = { symbol: '', status: '', side: '', dateRange: null }
      this.currentPage = 1
      this.fetchData()
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
</style>
