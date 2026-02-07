<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px">
      <el-col :span="6">
        <stat-card title="信号总数" :value="total" icon="el-icon-s-opportunity" color="primary" :loading="loading"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="已执行" :value="stats.executed" icon="el-icon-circle-check" color="success" :loading="loading"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="已拒绝" :value="stats.rejected" icon="el-icon-circle-close" color="danger" :loading="loading"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="待处理/其他" :value="stats.pending" icon="el-icon-time" color="warning" :loading="loading"/>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <div class="toolbar">
        <span class="toolbar-title">信号事件历史</span>
        <el-button size="small" icon="el-icon-refresh" :loading="loading" @click="fetchData">刷新</el-button>
      </div>

      <div class="search-bar">
        <el-form :inline="true" size="small">
          <el-form-item label="信号ID">
            <el-input v-model="where.signal_id" placeholder="信号ID" clearable style="width:160px" @keyup.enter.native="onSearch"/>
          </el-form-item>
          <el-form-item label="事件类型">
            <el-select v-model="where.event_type" placeholder="全部" clearable style="width:140px">
              <el-option label="创建" value="CREATED"/>
              <el-option label="风控通过" value="RISK_PASSED"/>
              <el-option label="风控拒绝" value="RISK_REJECTED"/>
              <el-option label="已分发" value="DISPATCHED"/>
              <el-option label="已执行" value="EXECUTED"/>
              <el-option label="失败" value="FAILED"/>
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="where.status" placeholder="全部" clearable style="width:110px">
              <el-option label="待处理" value="pending"/>
              <el-option label="通过" value="passed"/>
              <el-option label="拒绝" value="rejected"/>
              <el-option label="执行中" value="executing"/>
              <el-option label="已执行" value="executed"/>
              <el-option label="失败" value="failed"/>
            </el-select>
          </el-form-item>
          <el-form-item label="来源服务">
            <el-select v-model="where.source_service" placeholder="全部" clearable style="width:150px">
              <el-option label="signal-hub" value="signal-hub"/>
              <el-option label="signal-monitor" value="signal-monitor"/>
              <el-option label="risk-control" value="risk-control"/>
              <el-option label="execution-dispatcher" value="execution-dispatcher"/>
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
        <el-table-column prop="signal_id" label="信号ID" width="150" show-overflow-tooltip>
          <template slot-scope="{row}">
            <span class="id-text">{{ row.signal_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="event_type" label="事件类型" width="130" align="center">
          <template slot-scope="{row}">
            <el-tag :type="eventTypeTag(row.event_type)" size="mini">{{ eventTypeLabel(row.event_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template slot-scope="{row}">
            <el-tag :type="statusTag(row.status)" size="mini" effect="dark">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source_service" label="来源服务" width="140" align="center">
          <template slot-scope="{row}">
            <span class="text-muted">{{ row.source_service }}</span>
          </template>
        </el-table-column>
        <el-table-column label="账户" width="70" align="center">
          <template slot-scope="{row}">
            <span v-if="row.account_id">#{{ row.account_id }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="详情" min-width="200" show-overflow-tooltip>
          <template slot-scope="{row}">
            <div v-if="row.detail && typeof row.detail === 'object'">
              <span v-if="row.detail.symbol" style="font-weight:600;margin-right:6px">{{ row.detail.symbol }}</span>
              <span v-if="row.detail.action">
                <el-tag :type="row.detail.action === 'BUY' ? 'success' : 'danger'" size="mini">{{ row.detail.action }}</el-tag>
              </span>
              <span v-if="row.detail.price" style="margin-left:6px">@ {{ row.detail.price }}</span>
              <span v-if="row.detail.strategy_code" style="margin-left:6px;color:#909399">[{{ row.detail.strategy_code }}]</span>
            </div>
            <span v-else-if="row.detail" class="text-muted">{{ typeof row.detail === 'string' ? row.detail : JSON.stringify(row.detail) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="错误信息" width="150" show-overflow-tooltip>
          <template slot-scope="{row}">
            <span v-if="row.error_message" style="color:#F56C6C">{{ row.error_message }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170">
          <template slot-scope="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && list.length === 0" description="暂无信号事件记录"/>

      <div v-if="total > 0" class="pagination-wrap">
        <span class="total-tip">共 {{ total }} 条</span>
        <el-pagination
          background
          layout="prev, pager, next, sizes"
          :total="total"
          :page-sizes="[20, 50, 100]"
          :page-size.sync="pageSize"
          :current-page.sync="currentPage"
          @size-change="fetchData"
          @current-change="fetchData"/>
      </div>
    </el-card>
  </div>
</template>

<script>
import { getSignalEvents } from '@/api/admin'

export default {
  name: 'SignalHistory',
  data() {
    return {
      loading: false,
      list: [],
      total: 0,
      currentPage: 1,
      pageSize: 20,
      where: {
        signal_id: '',
        event_type: '',
        status: '',
        source_service: '',
        dateRange: null
      }
    }
  },
  computed: {
    stats() {
      const s = { executed: 0, rejected: 0, pending: 0 }
      this.list.forEach(row => {
        const st = (row.status || '').toLowerCase()
        if (st === 'executed') s.executed++
        else if (st === 'rejected' || st === 'failed') s.rejected++
        else s.pending++
      })
      return s
    }
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    eventTypeLabel(t) {
      const m = { CREATED: '创建', RISK_CHECK: '风控检查', RISK_PASSED: '风控通过', RISK_REJECTED: '风控拒绝', DISPATCHED: '已分发', EXECUTED: '已执行', FAILED: '失败' }
      return m[t] || t
    },
    eventTypeTag(t) {
      const m = { CREATED: '', RISK_CHECK: 'info', RISK_PASSED: 'success', RISK_REJECTED: 'danger', DISPATCHED: 'warning', EXECUTED: 'success', FAILED: 'danger' }
      return m[t] || 'info'
    },
    statusLabel(s) {
      const m = { pending: '待处理', passed: '通过', rejected: '拒绝', executing: '执行中', executed: '已执行', failed: '失败' }
      return m[s] || s
    },
    statusTag(s) {
      const m = { pending: 'warning', passed: 'success', rejected: 'danger', executing: 'warning', executed: 'success', failed: 'danger' }
      return m[s] || 'info'
    },
    formatTime(t) {
      if (!t) return '-'
      const d = new Date(t)
      if (isNaN(d.getTime())) return String(t).replace('T', ' ').substring(0, 19)
      const pad = n => String(n).padStart(2, '0')
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
    },
    onSearch() {
      this.currentPage = 1
      this.fetchData()
    },
    reset() {
      this.where = { signal_id: '', event_type: '', status: '', source_service: '', dateRange: null }
      this.currentPage = 1
      this.fetchData()
    },
    async fetchData() {
      this.loading = true
      try {
        const params = {
          page: this.currentPage,
          page_size: this.pageSize
        }
        if (this.where.signal_id) params.signal_id = this.where.signal_id
        if (this.where.event_type) params.event_type = this.where.event_type
        if (this.where.status) params.status = this.where.status
        if (this.where.source_service) params.source_service = this.where.source_service
        if (this.where.dateRange && this.where.dateRange.length === 2) {
          params.start_date = this.where.dateRange[0]
          params.end_date = this.where.dateRange[1]
        }
        const res = await getSignalEvents(params)
        const data = res.data
        this.list = data.data || []
        this.total = data.total != null ? data.total : this.list.length
      } catch (e) {
        this.$message.error(e.response?.data?.detail || '获取信号事件失败')
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
.text-muted { color: #C0C4CC; }
</style>
