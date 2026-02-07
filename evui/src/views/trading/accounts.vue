<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px">
      <el-col :xs="24" :sm="12" :md="6">
        <stat-card title="账户总数" :value="list.length" icon="el-icon-s-custom" color="primary" :loading="loading" help-text="当前筛选结果"/>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <stat-card title="总权益" :value="totalEquity" icon="el-icon-wallet" color="success" :loading="loading">
          <template slot="value">{{ formatCurrency(totalEquity) }}</template>
        </stat-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <stat-card title="总余额" :value="totalBalance" icon="el-icon-coin" color="warning" :loading="loading">
          <template slot="value">{{ formatCurrency(totalBalance) }}</template>
        </stat-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <stat-card title="未实现盈亏" :value="totalUnrealizedPnl" icon="el-icon-data-analysis" :color="totalUnrealizedPnl >= 0 ? 'success' : 'danger'" :loading="loading">
          <template slot="value">
            <span :style="{ color: totalUnrealizedPnl >= 0 ? '#67C23A' : '#F56C6C' }">{{ formatCurrency(totalUnrealizedPnl) }}</span>
          </template>
        </stat-card>
      </el-col>
    </el-row>
    <el-row :gutter="15" style="margin-bottom: 15px">
      <el-col :xs="24" :sm="12" :md="6">
        <stat-card title="已实现盈亏" icon="el-icon-s-finance" :color="totalRealizedPnl >= 0 ? 'success' : 'danger'" :loading="loading">
          <template slot="value">
            <span :style="{ color: totalRealizedPnl >= 0 ? '#67C23A' : '#F56C6C' }">{{ formatCurrency(totalRealizedPnl) }}</span>
          </template>
        </stat-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <stat-card title="累计入金" icon="el-icon-upload2" color="success" :loading="loading">
          <template slot="value">{{ formatCurrency(totalDeposit) }}</template>
        </stat-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <stat-card title="累计出金" icon="el-icon-download" color="warning" :loading="loading">
          <template slot="value">{{ formatCurrency(totalWithdraw) }}</template>
        </stat-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <stat-card title="累计手续费" icon="el-icon-price-tag" color="info" :loading="loading">
          <template slot="value">{{ formatCurrency(totalFee) }}</template>
        </stat-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <div class="toolbar">
        <span class="toolbar-title">资金账户</span>
        <div>
          <el-select v-model="filterCurrency" placeholder="币种筛选" clearable size="small" style="width:120px; margin-right:8px" @change="fetchData">
            <el-option label="USDT" value="USDT"/>
            <el-option label="BTC" value="BTC"/>
            <el-option label="全部" value=""/>
          </el-select>
          <el-button size="small" icon="el-icon-refresh" :loading="loading" @click="fetchData">刷新</el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="list"
        stripe
        border
        style="width:100%; margin-top:12px"
        size="small"
        :header-cell-style="{background:'#fafafa'}">
        <el-table-column prop="ledger_account_id" label="账本ID" width="140" show-overflow-tooltip>
          <template slot-scope="{row}">
            <span class="mono">{{ row.ledger_account_id || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="account_id" label="账户ID" width="90" align="center"/>
        <el-table-column prop="currency" label="币种" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag size="mini" type="info">{{ row.currency }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="balance" label="余额" width="120" align="right">
          <template slot-scope="{row}">{{ formatCurrency(row.balance) }}</template>
        </el-table-column>
        <el-table-column prop="available" label="可用" width="120" align="right">
          <template slot-scope="{row}">{{ formatCurrency(row.available) }}</template>
        </el-table-column>
        <el-table-column prop="frozen" label="冻结" width="120" align="right">
          <template slot-scope="{row}">{{ formatCurrency(row.frozen) }}</template>
        </el-table-column>
        <el-table-column prop="equity" label="权益" width="120" align="right">
          <template slot-scope="{row}">
            <span style="font-weight: 600">{{ formatCurrency(row.equity != null ? row.equity : row.balance) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="margin_ratio" label="保证金率" width="100" align="right">
          <template slot-scope="{row}">{{ formatPercentage(row.margin_ratio) }}</template>
        </el-table-column>
        <el-table-column label="占用保证金" width="110" align="right">
          <template slot-scope="{row}">
            <span v-if="row.margin_used">{{ formatCurrency(row.margin_used) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="unrealized_pnl" label="未实现盈亏" width="110" align="right">
          <template slot-scope="{row}">
            <span :style="{ color: (row.unrealized_pnl || 0) >= 0 ? '#67C23A' : '#F56C6C' }">
              {{ formatCurrency(row.unrealized_pnl) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="已实现盈亏" width="110" align="right">
          <template slot-scope="{row}">
            <span :style="{ color: (row.realized_pnl || 0) >= 0 ? '#67C23A' : '#F56C6C' }">
              {{ formatCurrency(row.realized_pnl) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="累计入金" width="100" align="right">
          <template slot-scope="{row}">
            <span v-if="row.total_deposit" style="color:#67C23A">{{ formatCurrency(row.total_deposit) }}</span>
            <span v-else class="text-muted">0.00</span>
          </template>
        </el-table-column>
        <el-table-column label="累计出金" width="100" align="right">
          <template slot-scope="{row}">
            <span v-if="row.total_withdraw" style="color:#F56C6C">{{ formatCurrency(row.total_withdraw) }}</span>
            <span v-else class="text-muted">0.00</span>
          </template>
        </el-table-column>
        <el-table-column label="累计手续费" width="100" align="right">
          <template slot-scope="{row}">
            <span v-if="row.total_fee" style="color:#E6A23C">{{ formatCurrency(row.total_fee) }}</span>
            <span v-else class="text-muted">0.00</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="70" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'" size="mini">{{ row.status || 'ACTIVE' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="160">
          <template slot-scope="{row}">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && list.length === 0" description="暂无账户数据">
        <span slot="description">暂无资金账户数据，请确认当前租户下已绑定交易账户并完成 Ledger 同步。</span>
      </el-empty>

      <div v-if="list.length > 0" class="footer-tip">
        共 {{ list.length }} 个账户（Ledger 层 · 按租户筛选）
      </div>
    </el-card>
  </div>
</template>

<script>
import { getAccounts } from '@/api/trading'

export default {
  name: 'AccountList',
  data() {
    return {
      loading: false,
      list: [],
      filterCurrency: ''
    }
  },
  computed: {
    totalEquity() {
      return this.list.reduce((sum, item) => sum + (parseFloat(item.equity != null ? item.equity : item.balance) || 0), 0)
    },
    totalBalance() {
      return this.list.reduce((sum, item) => sum + (parseFloat(item.balance) || 0), 0)
    },
    totalUnrealizedPnl() {
      return this.list.reduce((sum, item) => sum + (parseFloat(item.unrealized_pnl) || 0), 0)
    },
    totalRealizedPnl() {
      return this.list.reduce((sum, item) => sum + (parseFloat(item.realized_pnl) || 0), 0)
    },
    totalDeposit() {
      return this.list.reduce((sum, item) => sum + (parseFloat(item.total_deposit) || 0), 0)
    },
    totalWithdraw() {
      return this.list.reduce((sum, item) => sum + (parseFloat(item.total_withdraw) || 0), 0)
    },
    totalFee() {
      return this.list.reduce((sum, item) => sum + (parseFloat(item.total_fee) || 0), 0)
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
    formatPercentage(value) {
      if (value == null || value === '') return '-'
      const num = parseFloat(value)
      return isNaN(num) ? '-' : (num * 100).toFixed(2) + '%'
    },
    async fetchData() {
      this.loading = true
      try {
        const params = {}
        if (this.filterCurrency) params.currency = this.filterCurrency
        const res = await getAccounts(params)
        const data = res.data
        this.list = data.data || []
      } catch (e) {
        this.$message.error(e.response?.data?.detail || '获取资金账户失败')
        this.list = []
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
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.toolbar-title { font-size: 16px; font-weight: 500; color: #303133; }
.mono { font-family: 'Monaco', 'Menlo', monospace; font-size: 12px; }
.footer-tip { margin-top: 12px; color: #909399; font-size: 12px; }
.text-muted { color: #C0C4CC; }
</style>
