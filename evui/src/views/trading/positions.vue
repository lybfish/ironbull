<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="4" :md="8" :sm="12">
        <stat-card
          title="总持仓数"
          :value="stats.totalCount"
          icon="el-icon-s-data"
          color="primary"
          :loading="loading">
          <template v-slot:footer>
            <span class="ele-text-secondary">活跃仓位</span>
          </template>
        </stat-card>
      </el-col>
      <el-col :lg="4" :md="8" :sm="12">
        <stat-card
          title="总名义价值"
          icon="el-icon-coin"
          color="warning"
          :loading="loading">
          <template v-slot:value>
            <span>{{ formatMoney(stats.totalNotional) }}</span>
          </template>
          <template v-slot:footer>
            <span class="ele-text-secondary">USDT</span>
          </template>
        </stat-card>
      </el-col>
      <el-col :lg="4" :md="8" :sm="12">
        <stat-card
          title="未实现盈亏"
          icon="el-icon-data-analysis"
          :color="stats.totalPnl >= 0 ? 'success' : 'danger'"
          :loading="loading">
          <template v-slot:value>
            <span :class="stats.totalPnl >= 0 ? 'text-success' : 'text-danger'">
              {{ stats.totalPnl >= 0 ? '+' : '' }}{{ formatMoney(stats.totalPnl) }}
            </span>
          </template>
        </stat-card>
      </el-col>
      <el-col :lg="4" :md="8" :sm="12">
        <stat-card
          title="多头仓位"
          :value="stats.longCount"
          icon="el-icon-top"
          color="success"
          :loading="loading">
          <template v-slot:footer>
            <span class="ele-text-secondary">做多</span>
          </template>
        </stat-card>
      </el-col>
      <el-col :lg="4" :md="8" :sm="12">
        <stat-card
          title="空头仓位"
          :value="stats.shortCount"
          icon="el-icon-bottom"
          color="danger"
          :loading="loading">
          <template v-slot:footer>
            <span class="ele-text-secondary">做空</span>
          </template>
        </stat-card>
      </el-col>
      <el-col :lg="4" :md="8" :sm="12">
        <stat-card
          title="盈亏比"
          icon="el-icon-pie-chart"
          color="info"
          :loading="loading">
          <template v-slot:value>
            <span>
              <span class="text-success">{{ stats.profitCount }}</span>
              <span style="color: #C0C4CC; margin: 0 4px;">/</span>
              <span class="text-danger">{{ stats.lossCount }}</span>
            </span>
          </template>
          <template v-slot:footer>
            <span class="ele-text-secondary">盈利 / 亏损</span>
          </template>
        </stat-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <div class="toolbar">
        <span class="toolbar-title">持仓管理</span>
        <el-radio-group v-model="viewMode" size="small" @change="onViewModeChange">
          <el-radio-button label="open">当前持仓</el-radio-button>
          <el-radio-button label="closed">已平仓</el-radio-button>
          <el-radio-button label="all">全部</el-radio-button>
        </el-radio-group>
      </div>
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-form :inline="true" :model="where" class="search-form" size="small">
          <el-form-item label="标的">
            <el-input
              v-model="where.symbol"
              placeholder="如 BTC/USDT"
              clearable
              style="width: 150px"
              @keyup.enter.native="fetchData"/>
          </el-form-item>
          <el-form-item label="方向">
            <el-select v-model="where.position_side" placeholder="全部" clearable style="width: 100px">
              <el-option label="多头" value="long"/>
              <el-option label="空头" value="short"/>
            </el-select>
          </el-form-item>
          <el-form-item label="交易所">
            <el-select v-model="where.exchange" placeholder="全部" clearable style="width: 120px">
              <el-option
                v-for="ex in exchangeOptions"
                :key="ex"
                :label="ex.toUpperCase()"
                :value="ex"/>
            </el-select>
          </el-form-item>
          <el-form-item label="账户">
            <el-select v-model="where.account_id" placeholder="全部" clearable style="width: 160px">
              <el-option
                v-for="acc in accountOptions"
                :key="acc.id"
                :label="'[' + (acc.exchange || '').toUpperCase() + '] #' + acc.id"
                :value="acc.id"/>
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" icon="el-icon-search" @click="fetchData">查询</el-button>
            <el-button icon="el-icon-refresh-left" @click="resetQuery">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 操作栏 -->
      <div class="operation-bar">
        <el-button size="small" icon="el-icon-refresh" @click="fetchData" :loading="loading">刷新</el-button>
        <el-divider direction="vertical"/>
        <el-switch
          v-model="autoRefresh"
          active-text="自动刷新"
          inactive-text=""
          @change="handleAutoRefreshChange"
          style="margin-right: 8px;"/>
        <span class="last-update" v-if="lastUpdateTime">
          <i class="el-icon-time"></i> {{ lastUpdateTime }}
        </span>
        <span class="total-tip" v-if="total > 0" style="margin-left: auto;">共 <b>{{ total }}</b> 条持仓</span>
      </div>

      <!-- 表格 -->
      <el-table
        v-loading="loading"
        :data="filteredList"
        stripe
        border
        style="width: 100%"
        size="small"
        :header-cell-style="{background: '#fafafa', color: '#606266'}"
        :row-class-name="rowClassName">
        <el-table-column prop="symbol" label="标的" width="120" fixed>
          <template slot-scope="{row}">
            <span class="symbol-text">{{ row.symbol }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="exchange" label="交易所" width="100" align="center">
          <template slot-scope="{row}">
            <el-tag size="mini" effect="plain">{{ (row.exchange || '').toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="account_id" label="账户" width="70" align="center">
          <template slot-scope="{row}">
            <span class="text-muted">#{{ row.account_id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="方向" width="70" align="center">
          <template slot-scope="{row}">
            <el-tag
              :type="isLong(row) ? 'success' : 'danger'"
              size="mini"
              effect="dark">
              {{ isLong(row) ? '多' : '空' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="110" align="right">
          <template slot-scope="{row}">
            {{ formatNum(row.quantity) }}
          </template>
        </el-table-column>
        <el-table-column label="开仓均价" width="120" align="right">
          <template slot-scope="{row}">
            {{ formatPrice(row.avg_cost) }}
          </template>
        </el-table-column>
        <el-table-column label="名义价值" width="130" align="right">
          <template slot-scope="{row}">
            {{ formatMoney(calcNotional(row)) }}
          </template>
        </el-table-column>
        <el-table-column prop="leverage" label="杠杆" width="75" align="center">
          <template slot-scope="{row}">
            <el-tag size="mini" type="warning" effect="plain">{{ row.leverage || '-' }}x</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="未实现盈亏" width="140" align="right">
          <template slot-scope="{row}">
            <div class="pnl-cell">
              <span
                :class="pnlClass(row.unrealized_pnl)"
                class="pnl-value">
                {{ formatPnl(row.unrealized_pnl) }}
              </span>
              <span
                v-if="pnlPercent(row) !== null"
                :class="pnlClass(row.unrealized_pnl)"
                class="pnl-percent">
                ({{ pnlPercent(row) }})
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="liquidation_price" label="强平价" width="120" align="right">
          <template slot-scope="{row}">
            <span class="liq-price" v-if="row.liquidation_price">{{ formatPrice(row.liquidation_price) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="已实现盈亏" width="120" align="right">
          <template slot-scope="{row}">
            <span v-if="row.realized_pnl != null && row.realized_pnl != 0"
              :class="Number(row.realized_pnl) >= 0 ? 'text-success' : 'text-danger'">
              {{ formatPnl(row.realized_pnl) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.status === 'OPEN' ? 'success' : 'info'" size="mini" effect="dark">
              {{ row.status === 'OPEN' ? '持仓' : row.status === 'CLOSED' ? '已平' : (row.status || '-') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="开仓时间" width="160">
          <template slot-scope="{row}">
            {{ formatTime(row.opened_at) }}
          </template>
        </el-table-column>
        <el-table-column v-if="viewMode !== 'open'" label="平仓时间" width="160">
          <template slot-scope="{row}">
            {{ formatTime(row.closed_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" min-width="160">
          <template slot-scope="{row}">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && filteredList.length === 0" description="暂无持仓数据"/>
    </el-card>
  </div>
</template>

<script>
import { getPositions } from '@/api/trading'
import { getExchangeAccounts } from '@/api/admin'

export default {
  name: 'PositionList',
  data() {
    return {
      loading: false,
      list: [],
      total: 0,
      viewMode: 'open',
      where: {
        symbol: '',
        position_side: '',
        exchange: '',
        account_id: ''
      },
      autoRefresh: false,
      refreshTimer: null,
      lastUpdateTime: '',
      accountOptions: []
    }
  },
  computed: {
    /** 从已加载数据中提取交易所列表 */
    exchangeOptions() {
      const set = new Set()
      this.list.forEach(r => { if (r.exchange) set.add(r.exchange) })
      // 补充从账户列表中获取的交易所
      this.accountOptions.forEach(a => { if (a.exchange) set.add(a.exchange) })
      return Array.from(set).sort()
    },
    /** 前端二次过滤（方向 & 交易所 & 账户） */
    filteredList() {
      return this.list.filter(r => {
        if (this.where.position_side) {
          const side = (r.position_side || r.side || '').toLowerCase()
          if (side !== this.where.position_side) return false
        }
        if (this.where.exchange) {
          if ((r.exchange || '').toLowerCase() !== this.where.exchange.toLowerCase()) return false
        }
        if (this.where.account_id) {
          if (r.account_id !== this.where.account_id) return false
        }
        return true
      })
    },
    /** 统计指标 */
    stats() {
      const data = this.filteredList
      let totalNotional = 0
      let totalPnl = 0
      let longCount = 0
      let shortCount = 0
      let profitCount = 0
      let lossCount = 0
      data.forEach(r => {
        totalNotional += this.calcNotional(r)
        const pnl = Number(r.unrealized_pnl) || 0
        totalPnl += pnl
        if (this.isLong(r)) { longCount++ } else { shortCount++ }
        if (pnl >= 0) { profitCount++ } else { lossCount++ }
      })
      return {
        totalCount: data.length,
        totalNotional,
        totalPnl,
        longCount,
        shortCount,
        profitCount,
        lossCount
      }
    }
  },
  mounted() {
    this.fetchData()
    this.fetchAccounts()
  },
  beforeDestroy() {
    this.clearTimer()
  },
  methods: {
    /* ---------- 数据获取 ---------- */
    onViewModeChange() {
      this.fetchData()
    },
    async fetchData() {
      this.loading = true
      try {
        const params = {}
        if (this.viewMode === 'open') {
          params.has_position = true
        } else if (this.viewMode === 'closed') {
          params.status = 'CLOSED'
        }
        // else 'all' — no filter
        if (this.where.symbol) { params.symbol = this.where.symbol }
        const res = await getPositions(params)
        this.list = res.data.data || []
        this.total = res.data.total || this.list.length
        this.lastUpdateTime = this.nowStr()
      } catch (e) {
        this.$message.error('获取持仓失败')
      } finally {
        this.loading = false
      }
    },
    async fetchAccounts() {
      try {
        const res = await getExchangeAccounts({ status: 1 })
        this.accountOptions = (res.data.data || res.data || [])
      } catch (e) {
        // 静默失败
      }
    },
    resetQuery() {
      this.where = { symbol: '', position_side: '', exchange: '', account_id: '' }
      this.fetchData()
    },

    /* ---------- 计算字段 ---------- */
    calcNotional(row) {
      const qty = Number(row.quantity) || 0
      const price = Number(row.avg_cost) || 0
      return qty * price
    },

    /* ---------- 自动刷新 ---------- */
    handleAutoRefreshChange(val) {
      if (val) {
        this.startTimer()
        this.$message.success('已开启自动刷新（30秒）')
      } else {
        this.clearTimer()
        this.$message.info('已关闭自动刷新')
      }
    },
    startTimer() {
      this.clearTimer()
      this.refreshTimer = setInterval(() => {
        this.fetchData()
      }, 30000)
    },
    clearTimer() {
      if (this.refreshTimer) {
        clearInterval(this.refreshTimer)
        this.refreshTimer = null
      }
    },

    /* ---------- 格式化工具 ---------- */
    isLong(row) {
      const side = (row.position_side || row.side || '').toLowerCase()
      return side === 'long'
    },
    formatPrice(val) {
      if (val === null || val === undefined || val === '' || val === 0) return '-'
      const n = Number(val)
      if (isNaN(n)) return val
      if (n >= 1000) return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      if (n >= 1) return n.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
      return n.toLocaleString('en-US', { minimumFractionDigits: 6, maximumFractionDigits: 8 })
    },
    formatNum(val) {
      if (val === null || val === undefined || val === '') return '-'
      const n = Number(val)
      if (isNaN(n)) return val
      return n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 6 })
    },
    formatMoney(val) {
      if (val === null || val === undefined || val === '') return '-'
      const n = Number(val)
      if (isNaN(n)) return val
      return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    },
    formatPnl(val) {
      if (val === null || val === undefined) return '-'
      const n = Number(val)
      if (isNaN(n)) return val
      const sign = n >= 0 ? '+' : ''
      return sign + n.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
    },
    pnlPercent(row) {
      const pnl = Number(row.unrealized_pnl)
      const notional = this.calcNotional(row)
      if (!notional || isNaN(pnl) || isNaN(notional)) return null
      const pct = (pnl / notional) * 100
      const sign = pct >= 0 ? '+' : ''
      return sign + pct.toFixed(2) + '%'
    },
    pnlClass(val) {
      const n = Number(val)
      if (isNaN(n) || n === 0) return 'text-muted'
      return n > 0 ? 'text-success' : 'text-danger'
    },
    formatTime(val) {
      if (!val) return '-'
      const d = new Date(val)
      if (isNaN(d.getTime())) return val
      const pad = n => String(n).padStart(2, '0')
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
    },
    nowStr() {
      return this.formatTime(new Date())
    },
    rowClassName({ row }) {
      const pnl = Number(row.unrealized_pnl)
      if (isNaN(pnl)) return ''
      return pnl > 0 ? 'row-profit' : pnl < 0 ? 'row-loss' : ''
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
.search-bar {
  margin-bottom: 12px;
}
.operation-bar {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  gap: 8px;
  flex-wrap: wrap;
}
.last-update {
  color: #909399;
  font-size: 12px;
}
.last-update i {
  margin-right: 2px;
}
.total-tip {
  color: #909399;
  font-size: 13px;
}
.total-tip b {
  color: #409EFF;
}

/* 标的高亮 */
.symbol-text {
  font-weight: 600;
  color: #303133;
}

/* 盈亏单元格 */
.pnl-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  line-height: 1.4;
}
.pnl-value {
  font-weight: 600;
}
.pnl-percent {
  font-size: 11px;
}

/* 强平价 */
.liq-price {
  color: #F56C6C;
  font-weight: 500;
}

/* 颜色工具类 */
.text-success {
  color: #67C23A;
}
.text-danger {
  color: #F56C6C;
}
.text-muted {
  color: #C0C4CC;
}

/* 行底色提示 */
::v-deep .row-profit {
  background-color: rgba(103, 194, 58, 0.04) !important;
}
::v-deep .row-loss {
  background-color: rgba(245, 108, 108, 0.04) !important;
}
</style>
