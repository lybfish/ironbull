<template>
  <div class="ele-body">
    <el-card shadow="never">
      <!-- 标题与刷新 -->
      <div class="toolbar">
        <span class="toolbar-title">策略绑定</span>
        <el-button size="small" icon="el-icon-refresh" :loading="loading" @click="fetchData">刷新</el-button>
      </div>

      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-form :inline="true" size="small">
          <el-form-item label="租户ID">
            <el-input v-model.number="where.tenant_id" placeholder="租户ID" clearable style="width:100px" @keyup.enter.native="onSearch"/>
          </el-form-item>
          <el-form-item label="用户ID">
            <el-input v-model.number="where.user_id" placeholder="用户ID" clearable style="width:100px" @keyup.enter.native="onSearch"/>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="where.status" placeholder="全部" clearable style="width:100px">
              <el-option label="运行" :value="1"/>
              <el-option label="停止" :value="0"/>
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" icon="el-icon-search" @click="onSearch">查询</el-button>
            <el-button icon="el-icon-refresh-left" @click="resetSearch">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table v-loading="loading" :data="list" stripe border style="width:100%; margin-top:12px" size="small"
        :header-cell-style="{background:'#fafafa'}">
        <el-table-column prop="id" label="ID" width="60" align="center"/>
        <el-table-column prop="tenant_name" label="租户" width="120" show-overflow-tooltip/>
        <el-table-column prop="user_email" label="用户" min-width="150" show-overflow-tooltip/>
        <el-table-column prop="strategy_name" label="策略" width="150" show-overflow-tooltip/>
        <el-table-column prop="exchange_account_label" label="交易所账户" width="150" show-overflow-tooltip/>
        <el-table-column prop="mode" label="模式" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.mode === 2 ? 'danger' : 'info'" size="mini">{{ row.mode === 2 ? '实盘' : '模拟' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="点卡" width="120" align="center">
          <template slot-scope="{row}">
            <div style="font-size:12px">自充: {{ formatNum(row.point_card_self) }}</div>
            <div style="font-size:12px; color:#909399">赠送: {{ formatNum(row.point_card_gift) }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="mini" effect="dark">{{ row.status === 1 ? '运行' : '停止' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="绑定时间" width="170">
          <template slot-scope="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template slot-scope="{row}">
            <el-button type="text" size="mini" icon="el-icon-view" @click="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && list.length === 0" description="暂无策略绑定"/>
      <div v-if="total > 0" style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center;">
        <span class="tip">共 {{ total }} 条</span>
        <el-pagination
          background
          :current-page.sync="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="fetchData"/>
      </div>
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog title="绑定详情" :visible.sync="detailVisible" width="560px" append-to-body>
      <el-descriptions v-if="detailRow" :column="1" border size="small">
        <el-descriptions-item label="绑定ID">{{ detailRow.id }}</el-descriptions-item>
        <el-descriptions-item label="租户">{{ detailRow.tenant_name || '-' }} (ID: {{ detailRow.tenant_id || '-' }})</el-descriptions-item>
        <el-descriptions-item label="用户">{{ detailRow.user_email || '-' }} (ID: {{ detailRow.user_id }})</el-descriptions-item>
        <el-descriptions-item label="策略">{{ detailRow.strategy_name || detailRow.strategy_code }} ({{ detailRow.strategy_code }})</el-descriptions-item>
        <el-descriptions-item label="交易所账户">{{ detailRow.exchange_account_label || '-' }} (账户ID: {{ detailRow.account_id }})</el-descriptions-item>
        <el-descriptions-item label="模式">{{ detailRow.mode === 2 ? '实盘' : '模拟' }}</el-descriptions-item>
        <el-descriptions-item label="点卡（自充/赠送）">{{ formatNum(detailRow.point_card_self) }} / {{ formatNum(detailRow.point_card_gift) }}</el-descriptions-item>
        <el-descriptions-item label="累计盈亏">{{ formatNum(detailRow.total_profit) }}</el-descriptions-item>
        <el-descriptions-item label="交易笔数">{{ detailRow.total_trades || 0 }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="detailRow.status === 1 ? 'success' : 'info'" size="small">{{ detailRow.status === 1 ? '运行' : '停止' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="绑定时间">{{ formatTime(detailRow.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <div slot="footer">
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="goToUser">前往用户管理</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import {getBindingsAdmin} from '@/api/admin'

export default {
  name: 'StrategyBindings',
  data() {
    return {
      loading: false,
      list: [],
      total: 0,
      page: 1,
      pageSize: 20,
      where: { tenant_id: null, user_id: null, status: null },
      detailVisible: false,
      detailRow: null
    }
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    formatNum(v) {
      return v !== null && v !== undefined ? parseFloat(v).toFixed(2) : '0.00'
    },
    formatTime(t) {
      return t ? t.replace('T', ' ').substring(0, 19) : '-'
    },
    onSearch() {
      this.page = 1
      this.fetchData()
    },
    resetSearch() {
      this.where = { tenant_id: null, user_id: null, status: null }
      this.page = 1
      this.fetchData()
    },
    showDetail(row) {
      this.detailRow = row
      this.detailVisible = true
    },
    goToUser() {
      if (!this.detailRow || !this.detailRow.user_id) return
      this.detailVisible = false
      this.$router.push({ path: '/operation/users', query: { user_id: this.detailRow.user_id } })
    },
    async fetchData() {
      this.loading = true
      try {
        const params = { page: this.page, page_size: this.pageSize }
        if (this.where.tenant_id != null && this.where.tenant_id !== '') {
          params.tenant_id = Number(this.where.tenant_id)
        }
        if (this.where.user_id != null && this.where.user_id !== '') {
          params.user_id = Number(this.where.user_id)
        }
        if (this.where.status !== null && this.where.status !== '') {
          params.status = Number(this.where.status)
        }
        const res = await getBindingsAdmin(params)
        const data = res.data
        this.list = data.data || data || []
        this.total = data.total != null ? data.total : this.list.length
      } catch (e) {
        this.$message.error(e.response?.data?.detail || '获取策略绑定失败')
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.toolbar-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}
.search-bar { margin-bottom: 8px; }
.tip { color: #909399; font-size: 12px; }
</style>
