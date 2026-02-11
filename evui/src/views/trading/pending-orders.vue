<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px">
      <el-col :span="6">
        <stat-card title="总挂单" :value="stats.total" icon="el-icon-tickets" color="primary" :loading="statsLoading"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="等待中" :value="stats.pending" icon="el-icon-time" color="warning" :loading="statsLoading"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="已成交" :value="stats.filled" icon="el-icon-circle-check" color="success" :loading="statsLoading"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="已撤/过期" :value="stats.cancelled + stats.expired" icon="el-icon-remove-outline" color="info" :loading="statsLoading"/>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <div class="toolbar">
        <span class="toolbar-title">限价挂单记录</span>
        <el-button size="small" icon="el-icon-refresh" :loading="loading" @click="fetchData">刷新</el-button>
      </div>

      <!-- 筛选 -->
      <div class="search-bar">
        <el-form :inline="true" size="small">
          <el-form-item label="交易对">
            <el-input v-model="where.symbol" placeholder="如 ETHUSDT" clearable style="width:130px" @keyup.enter.native="onSearch"/>
          </el-form-item>
          <el-form-item label="策略">
            <el-input v-model="where.strategy_code" placeholder="策略编码" clearable style="width:140px" @keyup.enter.native="onSearch"/>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="where.status" placeholder="全部" clearable style="width:120px">
              <el-option label="等待中" value="PENDING"/>
              <el-option label="已成交" value="FILLED"/>
              <el-option label="确认中" value="CONFIRMING"/>
              <el-option label="已过期" value="EXPIRED"/>
              <el-option label="已撤单" value="CANCELLED"/>
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" icon="el-icon-search" @click="onSearch">查询</el-button>
            <el-button icon="el-icon-refresh-left" @click="resetSearch">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table v-loading="loading" :data="list" stripe border size="small" style="width:100%;margin-top:12px"
        :header-cell-style="{background:'#fafafa'}">
        <el-table-column prop="id" label="ID" width="60" align="center"/>
        <el-table-column prop="symbol" label="交易对" width="110">
          <template slot-scope="{row}"><span style="font-weight:600">{{ row.symbol }}</span></template>
        </el-table-column>
        <el-table-column prop="side" label="方向" width="70" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.side === 'BUY' ? 'success' : 'danger'" size="mini" effect="dark">{{ row.side === 'BUY' ? '买入' : '卖出' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="entry_price" label="挂单价" width="110" align="right">
          <template slot-scope="{row}">{{ formatPrice(row.entry_price) }}</template>
        </el-table-column>
        <el-table-column label="止损/止盈" width="120" align="right">
          <template slot-scope="{row}">
            <div v-if="row.stop_loss" style="color:#F56C6C;font-size:12px">SL {{ formatPrice(row.stop_loss) }}</div>
            <div v-if="row.take_profit" style="color:#67C23A;font-size:12px">TP {{ formatPrice(row.take_profit) }}</div>
            <span v-if="!row.stop_loss && !row.take_profit" style="color:#C0C4CC">-</span>
          </template>
        </el-table-column>
        <el-table-column label="成交信息" width="130" align="right">
          <template slot-scope="{row}">
            <div v-if="row.filled_price">
              <div style="font-size:12px">价 {{ formatPrice(row.filled_price) }}</div>
              <div style="font-size:11px;color:#909399">量 {{ row.filled_qty }}</div>
            </div>
            <span v-else style="color:#C0C4CC">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="strategy_code" label="策略" width="140" show-overflow-tooltip/>
        <el-table-column label="金额/杠杆" width="100" align="center">
          <template slot-scope="{row}">
            <div v-if="row.amount_usdt" style="font-size:12px">{{ row.amount_usdt }}U</div>
            <div v-if="row.leverage" style="font-size:11px;color:#909399">{{ row.leverage }}x</div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template slot-scope="{row}">
            <el-tag :type="statusType(row.status)" size="mini">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="placed_at" label="挂单时间" width="160">
          <template slot-scope="{row}">{{ formatTime(row.placed_at) }}</template>
        </el-table-column>
        <el-table-column prop="closed_at" label="结束时间" width="160">
          <template slot-scope="{row}">{{ formatTime(row.closed_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template slot-scope="{row}">
            <el-button
              v-if="row.status === 'PENDING' || row.status === 'CONFIRMING'"
              type="text" size="mini" style="color:#F56C6C"
              @click="handleCancel(row)">
              撤单
            </el-button>
            <span v-else style="color:#C0C4CC">-</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && list.length === 0" description="暂无限价挂单记录"/>

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
import { getPendingLimitOrders, getPendingLimitOrderStats, cancelPendingLimitOrder } from '@/api/trading'

export default {
  name: 'PendingOrders',
  data() {
    return {
      loading: false,
      statsLoading: false,
      list: [],
      total: 0,
      currentPage: 1,
      pageSize: 20,
      where: { symbol: '', strategy_code: '', status: '' },
      stats: { total: 0, pending: 0, filled: 0, confirming: 0, expired: 0, cancelled: 0 }
    }
  },
  mounted() {
    this.fetchData()
    this.fetchStats()
  },
  methods: {
    formatTime(t) {
      if (!t) return '-'
      return String(t).replace('T', ' ').substring(0, 19)
    },
    formatPrice(val) {
      if (val == null || val === '' || val === 0) return '-'
      const n = Number(val)
      if (isNaN(n)) return val
      if (n >= 1000) return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      if (n >= 1) return n.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
      return n.toLocaleString('en-US', { minimumFractionDigits: 6, maximumFractionDigits: 8 })
    },
    statusType(s) {
      const m = { PENDING: 'warning', FILLED: 'success', CONFIRMING: '', EXPIRED: 'info', CANCELLED: 'info' }
      return m[s] || 'info'
    },
    statusLabel(s) {
      const m = { PENDING: '等待中', FILLED: '已成交', CONFIRMING: '确认中', EXPIRED: '已过期', CANCELLED: '已撤单' }
      return m[s] || s
    },
    onSearch() {
      this.currentPage = 1
      this.fetchData()
    },
    resetSearch() {
      this.where = { symbol: '', strategy_code: '', status: '' }
      this.currentPage = 1
      this.fetchData()
      this.fetchStats()
    },
    async handleCancel(row) {
      const action = row.status === 'CONFIRMING' ? '撤销确认并市价平仓' : '撤销挂单'
      try {
        await this.$confirm(`确定要${action}（${row.symbol} ${row.side}）吗？`, '撤单确认', {
          confirmButtonText: '确认', cancelButtonText: '取消', type: 'warning'
        })
      } catch { return }
      try {
        await cancelPendingLimitOrder(row.id)
        this.$message.success(action + '成功')
        this.fetchData()
        this.fetchStats()
      } catch (e) {
        this.$message.error(e.response?.data?.detail || action + '失败')
      }
    },
    async fetchStats() {
      this.statsLoading = true
      try {
        const res = await getPendingLimitOrderStats()
        this.stats = res.data.stats || this.stats
      } catch (e) { /* silent */ }
      finally { this.statsLoading = false }
    },
    async fetchData() {
      this.loading = true
      try {
        const params = {
          page: this.currentPage,
          page_size: this.pageSize
        }
        if (this.where.symbol) params.symbol = this.where.symbol
        if (this.where.strategy_code) params.strategy_code = this.where.strategy_code
        if (this.where.status) params.status = this.where.status
        const res = await getPendingLimitOrders(params)
        const data = res.data
        this.list = data.data || []
        this.total = data.total != null ? data.total : this.list.length
      } catch (e) {
        this.$message.error(e.response?.data?.detail || '获取挂单列表失败')
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
