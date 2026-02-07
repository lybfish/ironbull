<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="6" :md="12">
        <el-card shadow="never" class="stat-mini">
          <div class="stat-mini-label">总操作数</div>
          <div class="stat-mini-val">{{ stats.success_count + stats.fail_count }}</div>
        </el-card>
      </el-col>
      <el-col :lg="6" :md="12">
        <el-card shadow="never" class="stat-mini">
          <div class="stat-mini-label">成功</div>
          <div class="stat-mini-val text-success">{{ stats.success_count }}</div>
        </el-card>
      </el-col>
      <el-col :lg="6" :md="12">
        <el-card shadow="never" class="stat-mini">
          <div class="stat-mini-label">失败</div>
          <div class="stat-mini-val text-danger">{{ stats.fail_count }}</div>
        </el-card>
      </el-col>
      <el-col :lg="6" :md="12">
        <el-card shadow="never" class="stat-mini">
          <div class="stat-mini-label">操作趋势</div>
          <div ref="chartMini" style="height: 50px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="filters.admin_name" placeholder="操作人" clearable size="small" style="width:130px" @keyup.enter.native="fetchData"/>
        <el-input v-model="filters.action" placeholder="操作类型" clearable size="small" style="width:130px; margin-left:8px" @keyup.enter.native="fetchData"/>
        <el-select v-model="filters.success" placeholder="结果" clearable size="small" style="width:100px; margin-left:8px">
          <el-option label="成功" :value="true"/>
          <el-option label="失败" :value="false"/>
        </el-select>
        <el-input v-model="filters.source_service" placeholder="来源服务" clearable size="small" style="width:130px; margin-left:8px" @keyup.enter.native="fetchData"/>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          size="small"
          style="width:240px; margin-left:8px"
          value-format="yyyy-MM-dd"
          @change="handleDateChange"/>
        <el-button type="primary" size="small" icon="el-icon-search" style="margin-left:8px" @click="fetchData">查询</el-button>
        <el-button size="small" icon="el-icon-refresh" @click="handleReset">重置</el-button>
        <el-button size="small" type="success" icon="el-icon-download" style="margin-left:auto" @click="handleExport" :loading="exporting">导出CSV</el-button>
      </div>

      <el-table v-loading="loading" :data="list" stripe border style="width:100%; margin-top:12px" size="small">
        <el-table-column prop="id" label="ID" width="60"/>
        <el-table-column prop="admin_name" label="操作人" width="110"/>
        <el-table-column prop="action" label="操作类型" width="130">
          <template slot-scope="{row}">
            <el-tag size="mini" :type="getActionTagType(row.action)">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="70" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.success !== false ? 'success' : 'danger'" size="mini">
              {{ row.success !== false ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="变更" width="180">
          <template slot-scope="{row}">
            <template v-if="row.status_before || row.status_after">
              <span class="change-before">{{ row.status_before || '-' }}</span>
              <i class="el-icon-right" style="margin: 0 4px; color: #409EFF;"></i>
              <span class="change-after">{{ row.status_after || '-' }}</span>
            </template>
            <span v-else style="color: #C0C4CC;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="source_service" label="来源" width="100"/>
        <el-table-column label="耗时" width="70" align="center">
          <template slot-scope="{row}">
            <span v-if="row.duration_ms" :style="{color: row.duration_ms > 1000 ? '#F56C6C' : '#909399'}">
              {{ row.duration_ms }}ms
            </span>
            <span v-else style="color:#C0C4CC">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip>
          <template slot-scope="{row}">
            <el-tooltip :content="row.detail || '-'" placement="top" effect="dark">
              <span>{{ row.detail || '-' }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP" width="120"/>
        <el-table-column prop="created_at" label="时间" width="170"/>
      </el-table>

      <el-pagination
        v-if="total > 0"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        :current-page="pagination.page"
        :page-sizes="[10, 20, 50, 100]"
        :page-size="pagination.size"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        style="margin-top:16px; text-align:right"/>
      <el-empty v-if="!loading && list.length === 0" description="暂无审计日志"/>
    </el-card>
  </div>
</template>

<script>
import {getAuditLogs, exportAuditLogs, getAuditLogStats} from '@/api/monitor'
import * as echarts from 'echarts/core'
import {LineChart} from 'echarts/charts'
import {GridComponent} from 'echarts/components'
import {CanvasRenderer} from 'echarts/renderers'

echarts.use([LineChart, GridComponent, CanvasRenderer])

export default {
  name: 'AuditLog',
  data() {
    return {
      loading: false,
      exporting: false,
      list: [],
      total: 0,
      dateRange: null,
      filters: {
        admin_name: '',
        action: '',
        success: null,
        source_service: ''
      },
      pagination: {page: 1, size: 20},
      stats: {success_count: 0, fail_count: 0},
      miniChart: null
    }
  },
  mounted() {
    this.fetchData()
    this.fetchStats()
  },
  beforeDestroy() {
    if (this.miniChart) { this.miniChart.dispose() }
  },
  methods: {
    async fetchData() {
      this.loading = true
      try {
        const params = {page: this.pagination.page, page_size: this.pagination.size}
        if (this.filters.admin_name) { params.admin_name = this.filters.admin_name }
        if (this.filters.action) { params.action = this.filters.action }
        if (this.filters.success !== null && this.filters.success !== '') { params.success = this.filters.success }
        if (this.filters.source_service) { params.source_service = this.filters.source_service }
        if (this.dateRange && this.dateRange.length === 2) {
          params.start_date = this.dateRange[0]
          params.end_date = this.dateRange[1]
        }
        const res = await getAuditLogs(params)
        this.list = res.data.data || []
        this.total = res.data.total || this.list.length
      } catch (e) {
        this.$message.error('获取审计日志失败')
      } finally {
        this.loading = false
      }
    },
    async fetchStats() {
      try {
        const res = await getAuditLogStats(30)
        const d = (res.data && res.data.data) || {}
        this.stats = {success_count: d.success_count || 0, fail_count: d.fail_count || 0}
        this.$nextTick(() => { this.renderMiniChart(d.daily || {}) })
      } catch (e) {
        // ignore
      }
    },
    renderMiniChart(daily) {
      const el = this.$refs.chartMini
      if (!el) { return }
      if (!this.miniChart) { this.miniChart = echarts.init(el) }
      this.miniChart.setOption({
        grid: {left: 0, right: 0, top: 0, bottom: 0},
        xAxis: {show: false, type: 'category', data: (daily.dates || []).map(d => d.slice(5))},
        yAxis: {show: false, type: 'value'},
        series: [{type: 'line', data: daily.counts || [], smooth: true, symbol: 'none', lineStyle: {color: '#409EFF', width: 2}, areaStyle: {color: '#409EFF20'}}]
      }, true)
    },
    async handleExport() {
      this.exporting = true
      try {
        const params = {}
        if (this.filters.action) { params.action = this.filters.action }
        if (this.filters.admin_name) { params.admin_name = this.filters.admin_name }
        if (this.filters.success !== null && this.filters.success !== '') { params.success = this.filters.success }
        if (this.dateRange && this.dateRange.length === 2) {
          params.start_date = this.dateRange[0]
          params.end_date = this.dateRange[1]
        }
        const res = await exportAuditLogs(params)
        const blob = new Blob([res.data], {type: 'text/csv'})
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'audit_logs.csv'
        a.click()
        window.URL.revokeObjectURL(url)
        this.$message.success('导出成功')
      } catch (e) {
        this.$message.error('导出失败')
      } finally {
        this.exporting = false
      }
    },
    handleDateChange(val) { this.dateRange = val; this.fetchData() },
    handleReset() {
      this.filters = {admin_name: '', action: '', success: null, source_service: ''}
      this.dateRange = null
      this.pagination.page = 1
      this.fetchData()
    },
    handleSizeChange(val) { this.pagination.size = val; this.pagination.page = 1; this.fetchData() },
    handleCurrentChange(val) { this.pagination.page = val; this.fetchData() },
    getActionTagType(action) {
      if (!action) { return '' }
      const a = action.toLowerCase()
      if (a.includes('create') || a.includes('新增')) { return 'success' }
      if (a.includes('update') || a.includes('编辑')) { return 'warning' }
      if (a.includes('delete') || a.includes('删除')) { return 'danger' }
      if (a.includes('login') || a.includes('登录')) { return 'primary' }
      return 'info'
    }
  }
}
</script>

<style scoped>
.toolbar { display: flex; align-items: center; flex-wrap: wrap; }
.stat-mini { text-align: center; }
.stat-mini-label { font-size: 12px; color: #909399; margin-bottom: 4px; }
.stat-mini-val { font-size: 22px; font-weight: 700; color: #303133; }
.text-success { color: #67C23A !important; }
.text-danger { color: #F56C6C !important; }
.change-before { color: #909399; font-size: 12px; }
.change-after { color: #409EFF; font-size: 12px; font-weight: 600; }
</style>
