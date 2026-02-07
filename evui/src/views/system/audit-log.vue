<template>
  <div class="ele-body">
    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="filters.admin_name" placeholder="操作人" clearable size="small" style="width:150px" @keyup.enter.native="fetchData" />
        <el-input v-model="filters.action" placeholder="操作类型" clearable size="small" style="width:150px; margin-left:8px" @keyup.enter.native="fetchData" />
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          size="small"
          style="width:240px; margin-left:8px"
          value-format="yyyy-MM-dd"
          @change="handleDateChange">
        </el-date-picker>
        <el-button type="primary" size="small" icon="el-icon-search" style="margin-left:8px" @click="fetchData">查询</el-button>
        <el-button size="small" icon="el-icon-refresh" @click="handleReset">重置</el-button>
      </div>
      <el-table v-loading="loading" :data="list" stripe border style="width:100%; margin-top:12px" size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="admin_name" label="操作人" width="100" />
        <el-table-column prop="action" label="操作类型" width="120">
          <template slot-scope="{row}">
            <el-tag size="mini" :type="getActionTagType(row.action)">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_type" label="目标类型" width="100" />
        <el-table-column prop="target_id" label="目标ID" width="80" />
        <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip>
          <template slot-scope="{row}">
            <el-tooltip :content="row.detail || '-'" placement="top" effect="dark">
              <span>{{ row.detail || '-' }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP" width="120" />
        <el-table-column prop="created_at" label="时间" width="170" />
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
        style="margin-top:16px; text-align:right">
      </el-pagination>
      <el-empty v-if="!loading && list.length === 0" description="暂无审计日志" />
    </el-card>
  </div>
</template>

<script>
import {getAuditLogs} from '@/api/monitor'

export default {
  name: 'AuditLog',
  data() {
    return {
      loading: false,
      list: [],
      total: 0,
      dateRange: null,
      filters: {
        admin_name: '',
        action: ''
      },
      pagination: {
        page: 1,
        size: 20
      }
    }
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    async fetchData() {
      this.loading = true
      try {
        const params = {
          page: this.pagination.page,
          page_size: this.pagination.size
        }
        if (this.filters.admin_name) {
          params.admin_name = this.filters.admin_name
        }
        if (this.filters.action) {
          params.action = this.filters.action
        }
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
    handleDateChange(val) {
      this.dateRange = val
      this.fetchData()
    },
    handleReset() {
      this.filters = {admin_name: '', action: ''}
      this.dateRange = null
      this.pagination.page = 1
      this.fetchData()
    },
    handleSizeChange(val) {
      this.pagination.size = val
      this.pagination.page = 1
      this.fetchData()
    },
    handleCurrentChange(val) {
      this.pagination.page = val
      this.fetchData()
    },
    getActionTagType(action) {
      if (!action) return ''
      const actionLower = action.toLowerCase()
      if (actionLower.includes('create') || actionLower.includes('新增') || actionLower.includes('创建')) {
        return 'success'
      } else if (actionLower.includes('update') || actionLower.includes('更新') || actionLower.includes('编辑')) {
        return 'warning'
      } else if (actionLower.includes('delete') || actionLower.includes('删除')) {
        return 'danger'
      } else if (actionLower.includes('login') || actionLower.includes('登录')) {
        return 'primary'
      }
      return 'info'
    }
  }
}
</script>

<style scoped>
.toolbar { display: flex; align-items: center; flex-wrap: wrap; }
</style>
