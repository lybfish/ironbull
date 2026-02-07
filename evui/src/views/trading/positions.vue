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
        <el-table-column v-if="viewMode !== 'open'" label="平仓原因" width="100" align="center">
          <template slot-scope="{row}">
            <template v-if="row.close_reason">
              <el-tag :type="closeReasonType(row.close_reason)" size="mini">
                {{ closeReasonLabel(row.close_reason) }}
              </el-tag>
            </template>
            <span v-else class="text-muted">-</span>
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
        <el-table-column prop="updated_at" label="更新时间" width="160">
          <template slot-scope="{row}">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template slot-scope="{row}">
            <el-button type="text" size="mini" @click="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && filteredList.length === 0" description="暂无持仓数据"/>
    </el-card>

    <!-- 持仓详情弹窗 -->
    <el-dialog :title="'持仓详情 - ' + (detailRow.symbol || '')" :visible.sync="detailVisible" width="900px" top="5vh" append-to-body>
      <div v-if="detailRow.symbol" class="detail-content">
        <!-- 持仓基本信息 -->
        <el-descriptions :column="3" border size="small" style="margin-bottom:16px">
          <el-descriptions-item label="标的">{{ detailRow.symbol }}</el-descriptions-item>
          <el-descriptions-item label="交易所">{{ (detailRow.exchange || '').toUpperCase() }}</el-descriptions-item>
          <el-descriptions-item label="方向">
            <el-tag :type="isLong(detailRow) ? 'success' : 'danger'" size="mini" effect="dark">{{ isLong(detailRow) ? '多头' : '空头' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="数量">{{ formatNum(detailRow.quantity) }}</el-descriptions-item>
          <el-descriptions-item label="开仓均价">{{ formatPrice(detailRow.avg_cost) }}</el-descriptions-item>
          <el-descriptions-item label="杠杆">{{ detailRow.leverage || '-' }}x</el-descriptions-item>
          <el-descriptions-item label="名义价值">{{ formatMoney(calcNotional(detailRow)) }} USDT</el-descriptions-item>
          <el-descriptions-item label="保证金">{{ detailRow.margin ? formatMoney(detailRow.margin) : '-' }}</el-descriptions-item>
          <el-descriptions-item label="强平价">
            <span v-if="detailRow.liquidation_price" class="liq-price">{{ formatPrice(detailRow.liquidation_price) }}</span>
            <span v-else class="text-muted">-</span>
          </el-descriptions-item>
          <el-descriptions-item label="未实现盈亏">
            <span :class="pnlClass(detailRow.unrealized_pnl)">{{ formatPnl(detailRow.unrealized_pnl) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="已实现盈亏">
            <span :class="pnlClass(detailRow.realized_pnl)">{{ formatPnl(detailRow.realized_pnl) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="detailRow.status === 'OPEN' ? 'success' : 'info'" size="mini">{{ detailRow.status === 'OPEN' ? '持仓中' : '已平仓' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailRow.close_reason" label="平仓原因">
            <el-tag :type="closeReasonType(detailRow.close_reason)" size="mini">
              {{ closeReasonLabel(detailRow.close_reason) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 止盈止损信息（从关联订单汇总） -->
        <div v-if="detailSlTp.stop_loss || detailSlTp.take_profit" class="sltp-bar">
          <el-tag v-if="detailSlTp.stop_loss" type="danger" size="small" effect="plain">
            <i class="el-icon-bottom"></i> 止损 {{ formatPrice(detailSlTp.stop_loss) }}
          </el-tag>
          <el-tag v-if="detailSlTp.take_profit" type="success" size="small" effect="plain">
            <i class="el-icon-top"></i> 止盈 {{ formatPrice(detailSlTp.take_profit) }}
          </el-tag>
          <span class="text-muted" style="font-size:12px;margin-left:8px">（来自关联订单）</span>
        </div>

        <!-- 手续费汇总 -->
        <div class="fee-summary" v-if="detailTotalFee > 0">
          <el-tag size="small" type="warning" effect="plain">
            累计手续费：{{ formatMoney(detailTotalFee) }} USDT
          </el-tag>
        </div>

        <!-- 关联订单 -->
        <h4 style="margin:16px 0 8px"><i class="el-icon-s-order"></i> 关联订单 <span v-if="detailOrders.length" class="text-muted" style="font-size:12px">({{ detailOrders.length }}笔)</span></h4>
        <el-table :data="detailOrders" stripe border size="mini" v-loading="detailLoading" :header-cell-style="{background:'#fafafa'}" max-height="260">
          <el-table-column prop="order_id" label="订单ID" width="130">
            <template slot-scope="{row}">
              <el-tooltip :content="row.order_id" placement="top">
                <span class="id-text">{{ (row.order_id || '').slice(0, 10) }}...</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column prop="side" label="方向" width="70" align="center">
            <template slot-scope="{row}">
              <el-tag :type="(row.side||'').toUpperCase()==='BUY' ? 'success' : 'danger'" size="mini" effect="dark">{{ (row.side||'').toUpperCase()==='BUY' ? '买入' : '卖出' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="order_type" label="类型" width="70" align="center"/>
          <el-table-column label="开/平仓" width="90" align="center">
            <template slot-scope="{row}">
              <el-tag :type="(row.trade_type||'OPEN')==='CLOSE'?'warning':''" size="mini" effect="plain">
                {{ {OPEN:'开仓',CLOSE:'平仓',ADD:'加仓',REDUCE:'减仓'}[(row.trade_type||'OPEN').toUpperCase()] || '开仓' }}
              </el-tag>
              <div v-if="row.close_reason" style="font-size:10px;margin-top:1px">
                <el-tag :type="row.close_reason==='TP'?'success':'danger'" size="mini" effect="plain">
                  {{ {SL:'止损',TP:'止盈',SIGNAL:'信号',MANUAL:'手动',LIQUIDATION:'强平'}[(row.close_reason||'').toUpperCase()] || row.close_reason }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="数量" width="100" align="right">
            <template slot-scope="{row}">{{ formatNum(row.filled_quantity) }} / {{ formatNum(row.quantity) }}</template>
          </el-table-column>
          <el-table-column label="成交均价" width="100" align="right">
            <template slot-scope="{row}">{{ formatPrice(row.avg_price) }}</template>
          </el-table-column>
          <el-table-column label="止损" width="90" align="right">
            <template slot-scope="{row}">
              <span v-if="row.stop_loss" style="color:#F56C6C">{{ formatPrice(row.stop_loss) }}</span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="止盈" width="90" align="right">
            <template slot-scope="{row}">
              <span v-if="row.take_profit" style="color:#67C23A">{{ formatPrice(row.take_profit) }}</span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="手续费" width="80" align="right">
            <template slot-scope="{row}">
              <span v-if="row.total_fee">{{ formatNum(row.total_fee) }}</span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="80" align="center">
            <template slot-scope="{row}">
              <el-tag :type="row.status==='FILLED'?'success':row.status==='CANCELLED'?'info':'warning'" size="mini">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="时间" min-width="140">
            <template slot-scope="{row}">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>

        <!-- 关联成交 -->
        <h4 style="margin:16px 0 8px"><i class="el-icon-tickets"></i> 成交记录 <span v-if="detailFills.length" class="text-muted" style="font-size:12px">({{ detailFills.length }}笔)</span></h4>
        <el-table :data="detailFills" stripe border size="mini" v-loading="detailLoading" :header-cell-style="{background:'#fafafa'}" max-height="220">
          <el-table-column prop="fill_id" label="成交ID" width="130">
            <template slot-scope="{row}">
              <span class="id-text">{{ (row.fill_id || '').slice(0, 10) }}...</span>
            </template>
          </el-table-column>
          <el-table-column prop="side" label="方向" width="70" align="center">
            <template slot-scope="{row}">
              <el-tag :type="(row.side||'').toUpperCase()==='BUY' ? 'success' : 'danger'" size="mini">{{ (row.side||'').toUpperCase()==='BUY' ? '买入' : '卖出' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="数量" width="100" align="right">
            <template slot-scope="{row}">{{ formatNum(row.quantity) }}</template>
          </el-table-column>
          <el-table-column label="成交价" width="110" align="right">
            <template slot-scope="{row}">{{ formatPrice(row.price) }}</template>
          </el-table-column>
          <el-table-column label="成交额" width="110" align="right">
            <template slot-scope="{row}">{{ formatMoney(row.value || row.quantity * row.price) }}</template>
          </el-table-column>
          <el-table-column label="手续费" width="90" align="right">
            <template slot-scope="{row}">
              <span v-if="row.fee" style="color:#E6A23C">{{ formatNum(row.fee) }}</span>
              <span v-else class="text-muted">0</span>
            </template>
          </el-table-column>
          <el-table-column label="时间" min-width="140">
            <template slot-scope="{row}">{{ formatTime(row.filled_at) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { getPositions, getOrders, getFills } from '@/api/trading'
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
      accountOptions: [],
      // 详情弹窗
      detailVisible: false,
      detailLoading: false,
      detailRow: {},
      detailOrders: [],
      detailFills: []
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
    /** 从关联订单中汇总止盈止损（取最新有效值） */
    detailSlTp() {
      let sl = null, tp = null
      for (const o of this.detailOrders) {
        if (o.stop_loss && !sl) sl = o.stop_loss
        if (o.take_profit && !tp) tp = o.take_profit
      }
      return { stop_loss: sl, take_profit: tp }
    },
    /** 从关联订单中汇总手续费 */
    detailTotalFee() {
      return this.detailOrders.reduce((sum, o) => sum + (Number(o.total_fee) || 0), 0)
        + this.detailFills.reduce((sum, f) => {
          // 若订单未记录fee但成交记录有fee，用成交的（避免重复）
          const orderHasFee = this.detailOrders.some(o => o.order_id === f.order_id && Number(o.total_fee) > 0)
          return sum + (orderHasFee ? 0 : (Number(f.fee) || 0))
        }, 0)
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

    /* ---------- 详情弹窗 ---------- */
    async showDetail(row) {
      this.detailRow = row
      this.detailOrders = []
      this.detailFills = []
      this.detailVisible = true
      this.detailLoading = true
      try {
        // 用持仓的开仓/平仓时间限定查询范围，避免拉到其他持仓周期的订单
        const params = { symbol: row.symbol, account_id: row.account_id, limit: 100 }
        const fillParams = { symbol: row.symbol, account_id: row.account_id, limit: 200 }
        if (row.opened_at) {
          // 开仓前 1 分钟作为起始时间，确保不漏
          const start = new Date(new Date(row.opened_at).getTime() - 60000).toISOString()
          params.start_time = start
          fillParams.start_time = start
        }
        if (row.closed_at) {
          // 平仓后 1 分钟作为结束时间
          const end = new Date(new Date(row.closed_at).getTime() + 60000).toISOString()
          params.end_time = end
          fillParams.end_time = end
        }
        const [ordersRes, fillsRes] = await Promise.all([
          getOrders(params),
          getFills(fillParams)
        ])
        this.detailOrders = (ordersRes.data.data || []).sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        this.detailFills = (fillsRes.data.data || []).sort((a, b) => new Date(b.filled_at) - new Date(a.filled_at))
      } catch (e) {
        this.$message.error('获取关联数据失败')
      } finally {
        this.detailLoading = false
      }
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
    closeReasonLabel(r) {
      const m = { SL: '止损', TP: '止盈', SIGNAL: '信号平仓', MANUAL: '手动平仓', LIQUIDATION: '强平' }
      return m[(r || '').toUpperCase()] || r || '-'
    },
    closeReasonType(r) {
      const m = { SL: 'danger', TP: 'success', SIGNAL: 'warning', MANUAL: 'info', LIQUIDATION: 'danger' }
      return m[(r || '').toUpperCase()] || 'info'
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

/* 详情弹窗 */
.detail-content {
  max-height: 70vh;
  overflow-y: auto;
}
.sltp-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.fee-summary {
  margin-bottom: 12px;
}
.id-text {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #606266;
}
</style>
