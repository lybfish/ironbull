<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px">
      <el-col :span="6">
        <stat-card title="信号总数" :value="serverStats.total" icon="el-icon-s-opportunity" color="primary" :loading="loading"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="已执行" :value="serverStats.executed" icon="el-icon-circle-check" color="success" :loading="loading"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="失败/拒绝" :value="serverStats.failed" icon="el-icon-circle-close" color="danger" :loading="loading"/>
      </el-col>
      <el-col :span="6">
        <stat-card title="待处理/其他" :value="serverStats.pending" icon="el-icon-time" color="warning" :loading="loading"/>
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
              <el-option label="position-monitor" value="position-monitor"/>
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
        :header-cell-style="{background:'#fafafa'}"
        :row-class-name="tableRowClassName"
        @row-click="onRowClick">

        <el-table-column prop="signal_id" label="信号ID" width="165" show-overflow-tooltip>
          <template slot-scope="{row}">
            <span class="id-text">{{ row.signal_id }}</span>
          </template>
        </el-table-column>

        <el-table-column label="策略" width="150" show-overflow-tooltip>
          <template slot-scope="{row}">
            <span v-if="getDetail(row, 'strategy')" style="font-weight:500">{{ getDetail(row, 'strategy') }}</span>
            <span v-else-if="getDetail(row, 'strategy_code')" style="font-weight:500">{{ getDetail(row, 'strategy_code') }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="币对" width="110" align="center">
          <template slot-scope="{row}">
            <span v-if="getDetail(row, 'symbol')" style="font-weight:600;color:#303133">{{ getDetail(row, 'symbol') }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="方向" width="70" align="center">
          <template slot-scope="{row}">
            <el-tag v-if="getDetail(row, 'side')" :type="getDetail(row, 'side') === 'BUY' ? 'success' : 'danger'" size="mini" effect="dark">{{ getDetail(row, 'side') }}</el-tag>
            <el-tag v-else-if="getDetail(row, 'action')" :type="getDetail(row, 'action') === 'BUY' ? 'success' : 'danger'" size="mini" effect="dark">{{ getDetail(row, 'action') }}</el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column prop="event_type" label="事件" width="90" align="center">
          <template slot-scope="{row}">
            <el-tag :type="eventTypeTag(row.event_type)" size="mini">{{ eventTypeLabel(row.event_type) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag :type="statusTag(row.status)" size="mini" effect="dark">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="价格信息" width="200">
          <template slot-scope="{row}">
            <div v-if="row.event_type === 'CREATED'" class="price-info">
              <span v-if="getDetail(row, 'entry_price')">入场: <b>{{ formatNum(getDetail(row, 'entry_price')) }}</b></span>
              <span v-if="getDetail(row, 'stop_loss')" style="color:#F56C6C;margin-left:6px">SL: {{ formatNum(getDetail(row, 'stop_loss')) }}</span>
              <span v-if="getDetail(row, 'take_profit')" style="color:#67C23A;margin-left:6px">TP: {{ formatNum(getDetail(row, 'take_profit')) }}</span>
            </div>
            <div v-else-if="row.event_type === 'EXECUTED'" class="price-info">
              <span v-if="getDetail(row, 'filled_price')">成交: <b>{{ formatNum(getDetail(row, 'filled_price')) }}</b></span>
              <span v-if="getDetail(row, 'filled_quantity')" style="margin-left:6px;color:#909399">数量: {{ formatNum(getDetail(row, 'filled_quantity')) }}</span>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="目标/成功" width="90" align="center">
          <template slot-scope="{row}">
            <span v-if="getDetail(row, 'targets') != null">
              <span :style="getDetail(row, 'success_count') > 0 ? 'color:#67C23A;font-weight:600' : 'color:#F56C6C;font-weight:600'">{{ getDetail(row, 'success_count') || 0 }}</span>
              <span style="color:#C0C4CC"> / </span>
              <span>{{ getDetail(row, 'targets') }}</span>
            </span>
            <span v-else-if="row.account_id">#{{ row.account_id }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column label="附加信息" min-width="180" show-overflow-tooltip>
          <template slot-scope="{row}">
            <!-- CREATED: 信号类型 + 置信度 + 周期 -->
            <div v-if="row.event_type === 'CREATED'">
              <el-tag v-if="getDetail(row, 'signal_type')" type="info" size="mini" style="margin-right:4px">{{ signalTypeLabel(getDetail(row, 'signal_type')) }}</el-tag>
              <span v-if="getDetail(row, 'confidence')" style="color:#909399">置信度: {{ getDetail(row, 'confidence') }}%</span>
              <span v-if="getDetail(row, 'timeframe')" style="color:#909399;margin-left:6px">{{ getDetail(row, 'timeframe') }}</span>
            </div>
            <!-- DISPATCHED: 动作描述 -->
            <div v-else-if="row.event_type === 'DISPATCHED' || (row.event_type === 'FAILED' && getDetail(row, 'action'))">
              <el-tag v-if="getDetail(row, 'action')" :type="actionTagType(getDetail(row, 'action'))" size="mini">{{ actionLabel(getDetail(row, 'action')) }}</el-tag>
            </div>
            <!-- EXECUTED: 订单号 -->
            <div v-else-if="row.event_type === 'EXECUTED'">
              <span v-if="getDetail(row, 'order_id')" class="id-text">订单: {{ getDetail(row, 'order_id') }}</span>
            </div>
            <!-- 错误信息 -->
            <span v-if="row.error_message" style="color:#F56C6C;margin-left:4px">[{{ row.error_message }}]</span>
            <span v-else-if="!row.event_type" class="text-muted">-</span>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="时间" width="160">
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

    <!-- 详情弹窗 -->
    <el-dialog :title="'信号详情 - ' + (detailRow.signal_id || '')" :visible.sync="detailVisible" width="680px" append-to-body>
      <div v-if="detailRow.signal_id">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="信号ID" :span="2">
            <span class="id-text">{{ detailRow.signal_id }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="事件类型">
            <el-tag :type="eventTypeTag(detailRow.event_type)" size="mini">{{ eventTypeLabel(detailRow.event_type) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detailRow.status)" size="mini" effect="dark">{{ statusLabel(detailRow.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="来源服务">{{ detailRow.source_service }}</el-descriptions-item>
          <el-descriptions-item label="账户ID">{{ detailRow.account_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="时间" :span="2">{{ formatTime(detailRow.created_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="detailRow.error_message" label="错误信息" :span="2">
            <span style="color:#F56C6C">{{ detailRow.error_message }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <div v-if="detailRow.detail && typeof detailRow.detail === 'object'" style="margin-top:16px">
          <h4 style="margin-bottom:8px;color:#303133">事件详情</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item v-for="(val, key) in detailRow.detail" :key="key" :label="detailKeyLabel(key)">
              <span v-if="key === 'side' || key === 'action'">
                <el-tag :type="val === 'BUY' ? 'success' : 'danger'" size="mini" effect="dark">{{ val }}</el-tag>
              </span>
              <span v-else-if="key === 'signal_type'">{{ signalTypeLabel(val) }}</span>
              <span v-else-if="typeof val === 'number'">{{ formatNum(val) }}</span>
              <span v-else>{{ val }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <!-- 同信号的事件时间线 -->
        <div v-if="signalTimeline.length > 1" style="margin-top:16px">
          <h4 style="margin-bottom:8px;color:#303133">信号生命周期</h4>
          <el-timeline>
            <el-timeline-item
              v-for="(ev, idx) in signalTimeline" :key="idx"
              :type="timelineType(ev.status)"
              :timestamp="formatTime(ev.created_at)"
              placement="top">
              <span style="font-weight:500">{{ eventTypeLabel(ev.event_type) }}</span>
              <span style="margin-left:6px;color:#909399">{{ statusLabel(ev.status) }}</span>
              <span v-if="ev.account_id" style="margin-left:6px;color:#606266">#{{ ev.account_id }}</span>
              <span v-if="ev.error_message" style="margin-left:6px;color:#F56C6C">{{ ev.error_message }}</span>
            </el-timeline-item>
          </el-timeline>
        </div>
      </div>
    </el-dialog>
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
      },
      serverStats: {
        total: 0,
        executed: 0,
        failed: 0,
        pending: 0
      },
      detailVisible: false,
      detailRow: {},
      signalTimeline: []
    }
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    // ── 标签/映射 ──
    eventTypeLabel(t) {
      const m = { CREATED: '信号创建', RISK_CHECK: '风控检查', RISK_PASSED: '风控通过', RISK_REJECTED: '风控拒绝', DISPATCHED: '已分发', EXECUTED: '已执行', FAILED: '失败' }
      return m[t] || t
    },
    eventTypeTag(t) {
      const m = { CREATED: 'info', RISK_CHECK: 'info', RISK_PASSED: 'success', RISK_REJECTED: 'danger', DISPATCHED: 'warning', EXECUTED: 'success', FAILED: 'danger' }
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
    signalTypeLabel(t) {
      const m = { OPEN: '开仓', CLOSE: '平仓', HEDGE: '对冲', REVERSE: '反转' }
      return m[t] || t
    },
    actionLabel(a) {
      const m = { no_bindings: '无绑定', no_strategy: '无策略', executed: '已执行', error: '执行错误' }
      return m[a] || a
    },
    actionTagType(a) {
      const m = { no_bindings: 'warning', no_strategy: 'danger', executed: 'success', error: 'danger' }
      return m[a] || 'info'
    },
    timelineType(s) {
      const m = { pending: 'warning', passed: 'success', rejected: 'danger', executing: 'warning', executed: 'success', failed: 'danger' }
      return m[s] || 'info'
    },
    detailKeyLabel(key) {
      const m = {
        strategy: '策略', strategy_code: '策略代码', symbol: '币对', side: '方向', action: '动作',
        signal_type: '信号类型', entry_price: '入场价格', stop_loss: '止损价', take_profit: '止盈价',
        confidence: '置信度', timeframe: '时间周期', targets: '目标账户数', success_count: '成功数',
        order_id: '订单号', filled_quantity: '成交数量', filled_price: '成交价格',
      }
      return m[key] || key
    },

    // ── 工具方法 ──
    getDetail(row, key) {
      if (!row.detail || typeof row.detail !== 'object') return null
      return row.detail[key]
    },
    formatNum(v) {
      if (v == null) return '-'
      const n = Number(v)
      if (isNaN(n)) return String(v)
      if (n > 100) return n.toFixed(2)
      if (n > 1) return n.toFixed(4)
      return n.toFixed(6)
    },
    formatTime(t) {
      if (!t) return '-'
      const d = new Date(t)
      if (isNaN(d.getTime())) return String(t).replace('T', ' ').substring(0, 19)
      const pad = n => String(n).padStart(2, '0')
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
    },
    tableRowClassName({ row }) {
      if (row.status === 'failed') return 'row-failed'
      if (row.event_type === 'CREATED') return 'row-created'
      return ''
    },

    // ── 行点击 → 显示详情 ──
    async onRowClick(row) {
      this.detailRow = row
      this.signalTimeline = []
      this.detailVisible = true
      // 获取同 signal_id 的所有事件，展示生命周期
      if (row.signal_id) {
        try {
          const res = await getSignalEvents({ signal_id: row.signal_id, page_size: 50 })
          this.signalTimeline = (res.data.data || []).sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
        } catch (e) {
          // ignore
        }
      }
    },

    // ── 搜索/重置 ──
    onSearch() {
      this.currentPage = 1
      this.fetchData()
    },
    reset() {
      this.where = { signal_id: '', event_type: '', status: '', source_service: '', dateRange: null }
      this.currentPage = 1
      this.fetchData()
    },

    // ── 数据获取 ──
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

        // 服务端统计
        if (data.stats) {
          this.serverStats = data.stats
        } else {
          // 降级：从当前页数据计算
          let executed = 0, failed = 0, pending = 0
          this.list.forEach(row => {
            const st = (row.status || '').toLowerCase()
            if (st === 'executed') executed++
            else if (st === 'rejected' || st === 'failed') failed++
            else pending++
          })
          this.serverStats = { total: this.total, executed, failed, pending }
        }
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
.price-info { font-size: 12px; line-height: 1.6; }
.price-info b { color: #303133; }
</style>
<style>
.el-table .row-failed { background-color: #FEF0F0 !important; }
.el-table .row-created { background-color: #F0F9EB !important; }
</style>
