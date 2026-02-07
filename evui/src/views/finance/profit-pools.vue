<template>
  <div class="ele-body ele-body-card">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="6" :md="12" :sm="12">
        <el-card shadow="never" class="stat-card">
          <div class="stat-title">待结算</div>
          <div class="stat-value text-warning">{{ stats.pending ? stats.pending.count : 0 }}</div>
          <div class="stat-sub">{{ formatAmount(stats.pending ? stats.pending.total_amount : 0) }} USDT</div>
        </el-card>
      </el-col>
      <el-col :lg="6" :md="12" :sm="12">
        <el-card shadow="never" class="stat-card">
          <div class="stat-title">已结算</div>
          <div class="stat-value text-success">{{ stats.settled ? stats.settled.count : 0 }}</div>
          <div class="stat-sub">{{ formatAmount(stats.settled ? stats.settled.total_amount : 0) }} USDT</div>
        </el-card>
      </el-col>
      <el-col :lg="6" :md="12" :sm="12">
        <el-card shadow="never" class="stat-card">
          <div class="stat-title">
            <i class="el-icon-warning" style="color: #F56C6C;"></i> 分发失败
          </div>
          <div class="stat-value text-danger">{{ stats.failed ? stats.failed.count : 0 }}</div>
          <div class="stat-sub">{{ formatAmount(stats.failed ? stats.failed.total_amount : 0) }} USDT</div>
        </el-card>
      </el-col>
      <el-col :lg="6" :md="12" :sm="12">
        <el-card shadow="never" class="stat-card">
          <div class="stat-title">
            <i class="el-icon-circle-close" style="color: #909399;"></i> 超限无法恢复
          </div>
          <div class="stat-value" style="color: #909399;">{{ stats.stuck ? stats.stuck.count : 0 }}</div>
          <div class="stat-sub">{{ stats.stuck ? stats.stuck.description : '' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选栏 -->
    <el-card shadow="never">
      <div class="ele-toolbar" style="margin-bottom: 15px;">
        <el-select v-model="where.status" placeholder="状态" clearable size="small" style="width: 130px; margin-right: 10px;">
          <el-option label="全部" :value="null"/>
          <el-option label="待结算" :value="1"/>
          <el-option label="已结算" :value="2"/>
          <el-option label="分发失败" :value="3"/>
        </el-select>
        <el-input v-model="where.user_id" placeholder="用户ID" clearable size="small" style="width: 120px; margin-right: 10px;"
                  @keyup.enter.native="fetchData"/>
        <el-button type="primary" size="small" icon="el-icon-search" @click="fetchData">查询</el-button>
        <el-button size="small" icon="el-icon-refresh" @click="resetFilter">重置</el-button>
        <el-button size="small" type="warning" icon="el-icon-refresh-right" @click="batchRetry"
                   :loading="batchRetrying" :disabled="!hasFailedPools"
                   style="margin-left: auto;">
          批量重试失败
        </el-button>
      </div>

      <!-- 数据表格 -->
      <el-table :data="list" stripe size="small" v-loading="loading" border
                :header-cell-style="{background:'#fafafa'}" style="width: 100%;"
                :row-class-name="rowClass">
        <el-table-column prop="id" label="ID" width="70"/>
        <el-table-column label="用户" width="160">
          <template slot-scope="{row}">
            <div>
              <span class="user-link" @click="filterByUser(row.user_id)">{{ row.user_email || '-' }}</span>
            </div>
            <div style="font-size: 11px; color: #909399;">ID: {{ row.user_id }}</div>
          </template>
        </el-table-column>
        <el-table-column label="利润" width="120" align="right">
          <template slot-scope="{row}">
            <span style="color: #67C23A;">+{{ formatAmount(row.profit_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="扣费" width="100" align="right">
          <template slot-scope="{row}">
            <span style="color: #F56C6C;">-{{ formatAmount(row.deduct_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="进池金额" width="110" align="right">
          <template slot-scope="{row}">
            <span style="font-weight: 600;">{{ formatAmount(row.pool_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="分配详情" min-width="200">
          <template slot-scope="{row}">
            <template v-if="row.status === 2">
              <el-tag size="mini" type="info" style="margin-right:4px;">技术 {{ formatAmount(row.tech_amount) }}</el-tag>
              <el-tag size="mini" type="success" style="margin-right:4px;">直推 {{ formatAmount(row.direct_distributed) }}</el-tag>
              <el-tag size="mini" type="warning" style="margin-right:4px;">级差 {{ formatAmount(row.diff_distributed) }}</el-tag>
              <el-tag size="mini" style="margin-right:4px;">平级 {{ formatAmount(row.peer_distributed) }}</el-tag>
              <el-tag size="mini" type="info">留存 {{ formatAmount(row.platform_amount) }}</el-tag>
            </template>
            <template v-else-if="row.status === 3">
              <div style="color: #F56C6C; font-size: 12px;">
                <i class="el-icon-warning"></i>
                重试 {{ row.retry_count }} 次 · {{ row.last_error ? row.last_error.substring(0, 80) : '未知错误' }}
              </div>
            </template>
            <template v-else>
              <span style="color: #909399;">等待结算...</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template slot-scope="{row}">
            <el-tag :type="statusTagType(row.status)" size="small">{{ row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="165">
          <template slot-scope="{row}">
            <span style="font-size: 12px;">{{ row.created_at || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center" fixed="right">
          <template slot-scope="{row}">
            <el-button v-if="row.status === 3 || row.status === 1"
                       type="text" size="mini" icon="el-icon-refresh-right"
                       @click="handleRetry(row)" :loading="row._retrying">
              重试
            </el-button>
            <span v-else style="color: #C0C4CC; font-size: 12px;">-</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        style="margin-top: 15px; text-align: right;"
        background
        layout="total, prev, pager, next, sizes"
        :total="total"
        :current-page.sync="page"
        :page-size.sync="pageSize"
        :page-sizes="[20, 50, 100]"
        @size-change="fetchData"
        @current-change="fetchData"/>
    </el-card>
  </div>
</template>

<script>
import {getProfitPools, getProfitPoolStats, retryProfitPool} from '@/api/finance'

export default {
  name: 'ProfitPools',
  data() {
    return {
      loading: false,
      batchRetrying: false,
      list: [],
      total: 0,
      page: 1,
      pageSize: 20,
      where: {
        status: null,
        user_id: ''
      },
      stats: {}
    }
  },
  computed: {
    hasFailedPools() {
      return this.stats.failed && this.stats.failed.count > 0
    }
  },
  mounted() {
    this.fetchData()
    this.fetchStats()
  },
  methods: {
    formatAmount(val) {
      if (!val && val !== 0) return '0.00'
      return parseFloat(val).toFixed(4)
    },
    statusTagType(status) {
      return {1: 'warning', 2: 'success', 3: 'danger'}[status] || 'info'
    },
    rowClass({row}) {
      if (row.status === 3) return 'row-failed'
      return ''
    },
    filterByUser(userId) {
      this.where.user_id = String(userId)
      this.page = 1
      this.fetchData()
    },
    resetFilter() {
      this.where = {status: null, user_id: ''}
      this.page = 1
      this.fetchData()
    },
    async fetchStats() {
      try {
        const res = await getProfitPoolStats()
        this.stats = (res.data && res.data.data) || res.data || {}
      } catch (e) {
        console.error(e)
      }
    },
    async fetchData() {
      this.loading = true
      try {
        const params = {
          page: this.page,
          page_size: this.pageSize
        }
        if (this.where.status !== null && this.where.status !== '') {
          params.status = this.where.status
        }
        if (this.where.user_id) {
          params.user_id = parseInt(this.where.user_id) || undefined
        }
        const res = await getProfitPools(params)
        const d = res.data
        this.list = (d.data || []).map(r => ({...r, _retrying: false}))
        this.total = d.total || 0
      } catch (e) {
        this.$message.error('加载利润池数据失败')
      } finally {
        this.loading = false
      }
    },
    async handleRetry(row) {
      try {
        await this.$confirm(
          `确认重试利润池 #${row.id}（用户 ${row.user_email || row.user_id}，金额 ${this.formatAmount(row.pool_amount)} USDT）？`,
          '重试分发',
          {type: 'warning'}
        )
      } catch {
        return
      }
      row._retrying = true
      try {
        await retryProfitPool(row.id)
        this.$message.success(`利润池 #${row.id} 分发成功`)
        this.fetchData()
        this.fetchStats()
      } catch (e) {
        const msg = (e.response && e.response.data && e.response.data.detail) || '重试失败'
        this.$message.error(msg)
        this.fetchData()
        this.fetchStats()
      } finally {
        row._retrying = false
      }
    },
    async batchRetry() {
      const failedCount = this.stats.failed ? this.stats.failed.count : 0
      try {
        await this.$confirm(
          `将对 ${failedCount} 条失败记录逐一重试分发，是否继续？`,
          '批量重试',
          {type: 'warning'}
        )
      } catch {
        return
      }
      this.batchRetrying = true
      // 先筛选出失败的列表重试
      try {
        const res = await getProfitPools({status: 3, page: 1, page_size: 100})
        const failedItems = (res.data && res.data.data) || []
        let successCount = 0
        let failCount = 0
        for (const item of failedItems) {
          try {
            await retryProfitPool(item.id)
            successCount++
          } catch {
            failCount++
          }
        }
        this.$message.success(`批量重试完成：成功 ${successCount}，失败 ${failCount}`)
      } catch (e) {
        this.$message.error('批量重试出错')
      } finally {
        this.batchRetrying = false
        this.fetchData()
        this.fetchStats()
      }
    }
  }
}
</script>

<style scoped>
.stat-card {
  text-align: center;
  padding: 10px 0;
}
.stat-title {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
}
.stat-sub {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.user-link {
  color: #409EFF;
  cursor: pointer;
}
.user-link:hover {
  text-decoration: underline;
}

.text-success { color: #67C23A !important; }
.text-warning { color: #E6A23C !important; }
.text-danger { color: #F56C6C !important; }

::v-deep .row-failed {
  background-color: #FEF0F0 !important;
}
</style>
