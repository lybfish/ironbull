<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px">
      <el-col :span="6">
        <stat-card title="成交笔数" :value="total" icon="el-icon-s-data" color="primary" :loading="loading" help-text="当前筛选结果"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="总手续费" :value="stats.totalFee" icon="el-icon-coin" color="warning" :loading="loading">
          <template slot="value">{{ formatNum(stats.totalFee) }}</template>
        </stat-card>
      </el-col>
      <el-col :span="6">
        <stat-card title="已实现盈亏" :value="stats.totalPnl" icon="el-icon-data-analysis" :color="stats.totalPnl >= 0 ? 'success' : 'danger'" :loading="loading">
          <template slot="value">
            <span :style="{ color: stats.totalPnl >= 0 ? '#67c23a' : '#f56c6c' }">{{ formatNum(stats.totalPnl) }}</span>
          </template>
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
              <el-option label="买入" value="buy"/>
              <el-option label="卖出" value="sell"/>
            </el-select>
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
        <el-table-column prop="fill_id" label="成交ID" width="160">
          <template slot-scope="{row}">
            <span :title="row.fill_id">{{ truncateId(row.fill_id) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="order_id" label="订单ID" width="160">
          <template slot-scope="{row}">
            <span :title="row.order_id">{{ truncateId(row.order_id) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="symbol" label="标的" width="100"/>
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
        <el-table-column prop="price" label="成交价" width="100" align="right">
          <template slot-scope="{row}">{{ formatNum(row.price) }}</template>
        </el-table-column>
        <el-table-column prop="quantity" label="成交量" width="100" align="right">
          <template slot-scope="{row}">{{ formatNum(row.quantity) }}</template>
        </el-table-column>
        <el-table-column prop="fee" label="手续费" width="100" align="right">
          <template slot-scope="{row}">{{ formatNum(row.fee) }}</template>
        </el-table-column>
        <el-table-column prop="fee_currency" label="币种" width="80" align="center"/>
        <el-table-column prop="realized_pnl" label="已实现盈亏" width="120" align="right">
          <template slot-scope="{row}">
            <span :style="{ color: parseFloat(row.realized_pnl || 0) >= 0 ? '#67c23a' : '#f56c6c', fontWeight: 600 }">
              {{ (parseFloat(row.realized_pnl || 0) >= 0 ? '+' : '') }}{{ formatNum(row.realized_pnl) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="成交时间" min-width="170">
          <template slot-scope="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && list.length === 0" description="暂无成交记录"/>

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

export default {
  name: 'FillList',
  data() {
    return {
      loading: false,
      list: [],
      total: 0,
      currentPage: 1,
      pageSize: 20,
      where: { symbol: '', side: '' }
    }
  },
  computed: {
    stats() {
      let totalFee = 0
      let totalPnl = 0
      let buyCount = 0
      let sellCount = 0
      this.list.forEach(row => {
        totalFee += parseFloat(row.fee || 0)
        totalPnl += parseFloat(row.realized_pnl || 0)
        if ((row.side || '').toLowerCase() === 'buy') buyCount++
        else sellCount++
      })
      return { totalFee, totalPnl, buyCount, sellCount }
    }
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    formatNum(v) {
      if (v == null || v === '') return '0'
      const n = parseFloat(v)
      return isNaN(n) ? '0' : n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 6 })
    },
    formatTime(t) {
      return t ? String(t).replace('T', ' ').substring(0, 19) : '-'
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
      this.where = { symbol: '', side: '' }
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
        if (this.where.side) params.side = this.where.side
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
</style>
