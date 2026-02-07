<template>
  <div class="ele-body">
    <el-tabs v-model="activeTab" type="border-card">

      <!-- ═══════════ Tab 1: 数据同步 ═══════════ -->
      <el-tab-pane label="数据同步" name="sync">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-card shadow="never">
              <div slot="header"><span>余额同步</span></div>
              <el-form label-width="100px" size="small">
                <el-form-item label="目标节点">
                  <el-select v-model="balanceNodeId" placeholder="选择节点" clearable style="width:100%">
                    <el-option v-for="n in nodes" :key="n.id" :label="n.name + ' (' + n.node_code + ')'" :value="n.id" />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="syncingBalance" @click="handleSyncBalance">同步余额</el-button>
                </el-form-item>
              </el-form>
              <el-alert v-if="balanceResult" :title="balanceResult.message" :type="balanceResult.success ? 'success' : 'error'" :closable="false" show-icon style="margin-top:8px"/>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never">
              <div slot="header"><span>持仓同步</span></div>
              <el-form label-width="100px" size="small">
                <el-form-item label="目标节点">
                  <el-select v-model="positionNodeId" placeholder="选择节点" clearable style="width:100%">
                    <el-option v-for="n in nodes" :key="n.id" :label="n.name + ' (' + n.node_code + ')'" :value="n.id" />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="syncingPositions" @click="handleSyncPositions">同步持仓</el-button>
                </el-form-item>
              </el-form>
              <el-alert v-if="positionResult" :title="positionResult.message" :type="positionResult.success ? 'success' : 'error'" :closable="false" show-icon style="margin-top:8px"/>
            </el-card>
          </el-col>
        </el-row>
        <el-row :gutter="16" style="margin-top:16px">
          <el-col :span="12">
            <el-card shadow="never">
              <div slot="header"><span>成交同步</span></div>
              <el-form label-width="100px" size="small">
                <el-form-item label="目标节点">
                  <el-select v-model="tradesNodeId" placeholder="选择节点（不选=全部）" clearable style="width:100%">
                    <el-option v-for="n in nodes" :key="n.id" :label="n.name + ' (' + n.node_code + ')'" :value="n.id" />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="warning" :loading="syncingTrades" @click="handleSyncTrades">同步成交</el-button>
                </el-form-item>
              </el-form>
              <el-alert v-if="tradesResult" :title="tradesResult.message" :type="tradesResult.success ? 'success' : 'error'" :closable="false" show-icon style="margin-top:8px"/>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never">
              <div slot="header"><span>市场信息同步</span></div>
              <el-form label-width="100px" size="small">
                <el-form-item label="交易所">
                  <el-select v-model="marketExchange" placeholder="全部交易所" clearable style="width:100%">
                    <el-option label="Binance" value="binance"/>
                    <el-option label="Gate" value="gate"/>
                    <el-option label="OKX" value="okx"/>
                  </el-select>
                </el-form-item>
                <el-form-item label="市场类型">
                  <el-radio-group v-model="marketType">
                    <el-radio label="swap">永续合约</el-radio>
                    <el-radio label="spot">现货</el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item>
                  <el-button type="success" :loading="syncingMarkets" @click="handleSyncMarkets">同步市场信息</el-button>
                </el-form-item>
              </el-form>
              <el-alert v-if="marketsResult" :title="marketsResult.message" :type="marketsResult.success ? 'success' : 'error'" :closable="false" show-icon style="margin-top:8px"/>
            </el-card>
          </el-col>
        </el-row>

        <!-- 同步历史 -->
        <el-card shadow="never" style="margin-top:16px">
          <div slot="header">
            <span>同步历史</span>
            <el-button style="float:right;padding:3px 0" type="text" @click="clearHistory">清空</el-button>
          </div>
          <el-table :data="syncHistory" stripe border size="mini" max-height="300">
            <el-table-column prop="type" label="类型" width="90">
              <template slot-scope="{row}">
                <el-tag :type="syncTypeTag(row.type)" size="mini">{{ syncTypeLabel(row.type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="node_name" label="目标" width="160" />
            <el-table-column prop="message" label="结果" show-overflow-tooltip />
            <el-table-column prop="time" label="时间" width="170">
              <template slot-scope="{row}">{{ fmtDT(row.time) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="70" align="center">
              <template slot-scope="{row}">
                <el-tag :type="row.success ? 'success' : 'danger'" size="mini">{{ row.success ? '成功' : '失败' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="syncHistory.length === 0" description="暂无同步记录" :image-size="60" />
        </el-card>
      </el-tab-pane>

      <!-- ═══════════ Tab 2: 持仓监控 ═══════════ -->
      <el-tab-pane label="持仓监控 (SL/TP)" name="monitor">
        <div v-if="pmError" style="margin-bottom:12px">
          <el-alert :title="pmError" type="error" :closable="false" show-icon />
        </div>

        <!-- 状态卡片 -->
        <el-row :gutter="16">
          <el-col :span="5">
            <div class="pm-card">
              <div class="pm-label">监控状态</div>
              <div class="pm-value">
                <el-tag :type="pmStatus.enabled ? 'success' : 'info'" size="medium" effect="dark">
                  {{ pmStatus.enabled ? '运行中' : '未启用' }}
                </el-tag>
              </div>
              <div class="pm-desc">{{ pmStatus.enabled ? '自管SL/TP模式' : '交易所SL/TP模式' }}</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="pm-card">
              <div class="pm-label">监控持仓</div>
              <div class="pm-value pm-num">{{ pmStats.positions_monitored || 0 }}</div>
              <div class="pm-desc">带SL/TP的OPEN持仓</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="pm-card">
              <div class="pm-label">触发次数</div>
              <div class="pm-value pm-num">{{ pmStats.triggers_total || 0 }}</div>
              <div class="pm-desc">
                <span style="color:#67C23A">成功 {{ pmStats.closes_success || 0 }}</span>
                <span style="margin-left:4px;color:#F56C6C">失败 {{ pmStats.closes_failed || 0 }}</span>
              </div>
            </div>
          </el-col>
          <el-col :span="5">
            <div class="pm-card">
              <div class="pm-label">扫描频率</div>
              <div class="pm-value" style="font-size:20px;color:#409EFF">{{ pmConfig.interval || '?' }}s / 次</div>
              <div class="pm-desc">上次: {{ pmStats.last_scan_at ? fmtDT(pmStats.last_scan_at) : '-' }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="pm-card" style="display:flex;flex-direction:column;justify-content:center;align-items:center">
              <el-button type="primary" icon="el-icon-refresh" :loading="loadingPM" @click="refreshPM" style="margin-bottom:8px;width:100%">
                刷新状态
              </el-button>
              <el-button type="warning" icon="el-icon-aim" :loading="scanning" @click="handleTriggerScan" :disabled="!pmStatus.enabled" style="width:100%">
                手动扫描一次
              </el-button>
            </div>
          </el-col>
        </el-row>

        <!-- 监控持仓明细 + 实时价格 -->
        <el-card shadow="never" style="margin-top:16px">
          <div slot="header">
            <span style="font-weight:600">监控持仓明细</span>
            <el-button type="text" size="small" :loading="loadingPositions" @click="fetchMonitoredPositions" style="margin-left:12px">刷新</el-button>
            <el-button type="text" size="small" :loading="loadingPrices" @click="fetchPrices" style="margin-left:8px">
              <i class="el-icon-data-line"></i> 刷新价格
            </el-button>
            <el-switch v-model="autoRefreshPrices" active-text="自动刷新价格" inactive-text="" style="float:right;margin-top:2px" @change="toggleAutoRefresh"/>
          </div>

          <el-table :data="monitoredPositions" stripe border size="small" v-loading="loadingPositions"
            :header-cell-style="{background:'#fafafa'}" max-height="500">
            <el-table-column label="交易对" width="120">
              <template slot-scope="{row}">
                <span style="font-weight:600">{{ row.symbol }}</span>
              </template>
            </el-table-column>
            <el-table-column label="交易所" width="80" align="center">
              <template slot-scope="{row}">
                <el-tag size="mini" effect="plain">{{ (row.exchange || '').toUpperCase() }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="方向" width="60" align="center">
              <template slot-scope="{row}">
                <el-tag :type="row.position_side === 'LONG' ? 'success' : 'danger'" size="mini" effect="dark">
                  {{ row.position_side === 'LONG' ? '多' : '空' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="数量" width="100" align="right">
              <template slot-scope="{row}">{{ row.quantity }}</template>
            </el-table-column>
            <el-table-column label="入场价" width="110" align="right">
              <template slot-scope="{row}">
                <span v-if="row.entry_price">{{ fmtPrice(row.entry_price) }}</span>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="实时价格" width="120" align="right">
              <template slot-scope="{row}">
                <span v-if="getPrice(row)" :style="pnlColor(row)">
                  <b>{{ fmtPrice(getPrice(row)) }}</b>
                </span>
                <span v-else class="muted">{{ loadingPrices ? '加载中...' : '未获取' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="浮动盈亏" width="100" align="right">
              <template slot-scope="{row}">
                <span v-if="getPrice(row) && row.entry_price" :style="pnlColor(row)">
                  {{ calcPnlPct(row) }}
                </span>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="止损" width="110" align="right">
              <template slot-scope="{row}">
                <span v-if="row.stop_loss" style="color:#F56C6C;font-weight:600">{{ fmtPrice(row.stop_loss) }}</span>
                <span v-else class="muted">未设置</span>
              </template>
            </el-table-column>
            <el-table-column label="止盈" width="110" align="right">
              <template slot-scope="{row}">
                <span v-if="row.take_profit" style="color:#67C23A;font-weight:600">{{ fmtPrice(row.take_profit) }}</span>
                <span v-else class="muted">未设置</span>
              </template>
            </el-table-column>
            <el-table-column label="杠杆" width="55" align="center">
              <template slot-scope="{row}">{{ row.leverage || '-' }}x</template>
            </el-table-column>
            <el-table-column label="策略" width="130" show-overflow-tooltip>
              <template slot-scope="{row}">
                <span v-if="row.strategy_code">{{ row.strategy_code }}</span>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="用户" width="150" show-overflow-tooltip>
              <template slot-scope="{row}">
                <span v-if="row.user_email">{{ row.user_email }}</span>
                <span v-else class="muted">账户#{{ row.account_id }}</span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!loadingPositions && monitoredPositions.length === 0" description="当前没有被监控的持仓" :image-size="60"/>
        </el-card>
      </el-tab-pane>

      <!-- ═══════════ Tab 3: 市场信息 ═══════════ -->
      <el-tab-pane label="市场信息" name="markets">
        <el-card shadow="never">
          <div slot="header" style="display:flex;align-items:center;justify-content:space-between">
            <span style="font-weight:600">已同步的市场信息</span>
            <span class="muted" v-if="mkTotal > 0" style="font-size:12px">共 {{ mkTotal }} 个交易对</span>
          </div>
          <!-- 筛选栏 -->
          <el-form :inline="true" size="small" style="margin-bottom:12px">
            <el-form-item label="交易所">
              <el-select v-model="mkFilter.exchange" placeholder="全部" clearable style="width:120px" @change="fetchMarkets">
                <el-option label="Binance" value="binance"/>
                <el-option label="Gate" value="gate"/>
                <el-option label="OKX" value="okx"/>
              </el-select>
            </el-form-item>
            <el-form-item label="类型">
              <el-select v-model="mkFilter.market_type" placeholder="全部" clearable style="width:110px" @change="fetchMarkets">
                <el-option label="永续合约" value="swap"/>
                <el-option label="现货" value="spot"/>
              </el-select>
            </el-form-item>
            <el-form-item label="搜索">
              <el-input v-model="mkFilter.symbol" placeholder="输入币种如 BTC" clearable style="width:160px"
                @keyup.enter.native="fetchMarkets" @clear="fetchMarkets">
                <i slot="prefix" class="el-icon-search"></i>
              </el-input>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" icon="el-icon-search" @click="fetchMarkets">查询</el-button>
              <el-button icon="el-icon-refresh-left" @click="resetMkFilter">重置</el-button>
            </el-form-item>
          </el-form>

          <!-- 统计摘要 -->
          <el-row :gutter="12" style="margin-bottom:12px" v-if="mkList.length > 0">
            <el-col :span="6" v-for="ex in mkExchangeSummary" :key="ex.name">
              <div class="mk-summary-card">
                <span class="mk-summary-label">{{ ex.name.toUpperCase() }}</span>
                <span class="mk-summary-value">{{ ex.count }}</span>
                <span class="mk-summary-desc">个交易对</span>
              </div>
            </el-col>
          </el-row>

          <!-- 表格 -->
          <el-table :data="mkPagedList" stripe border size="small" v-loading="mkLoading"
            :header-cell-style="{background:'#fafafa'}" max-height="500">
            <el-table-column label="交易对" width="130" fixed>
              <template slot-scope="{row}">
                <span style="font-weight:600">{{ row.canonical_symbol }}</span>
              </template>
            </el-table-column>
            <el-table-column label="交易所" width="90" align="center">
              <template slot-scope="{row}">
                <el-tag size="mini" :type="mkExTagType(row.exchange)" effect="plain">{{ (row.exchange || '').toUpperCase() }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="类型" width="80" align="center">
              <template slot-scope="{row}">
                <el-tag size="mini" :type="row.market_type==='swap'?'warning':''" effect="plain">
                  {{ row.market_type === 'swap' ? '合约' : '现货' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="合约面值" width="100" align="right">
              <template slot-scope="{row}">
                <span v-if="row.contract_size && row.contract_size !== 1">{{ row.contract_size }}</span>
                <span v-else class="muted">1</span>
              </template>
            </el-table-column>
            <el-table-column label="价格精度" width="80" align="center">
              <template slot-scope="{row}">
                <span v-if="row.price_precision != null">{{ row.price_precision }}</span>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="数量精度" width="80" align="center">
              <template slot-scope="{row}">
                <span v-if="row.amount_precision != null">{{ row.amount_precision }}</span>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="最小数量" width="100" align="right">
              <template slot-scope="{row}">
                <span v-if="row.min_quantity">{{ row.min_quantity }}</span>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="最小金额" width="90" align="right">
              <template slot-scope="{row}">
                <span v-if="row.min_cost">{{ row.min_cost }}</span>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="Tick Size" width="100" align="right">
              <template slot-scope="{row}">
                <span v-if="row.tick_size">{{ row.tick_size }}</span>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="Step Size" width="100" align="right">
              <template slot-scope="{row}">
                <span v-if="row.step_size">{{ row.step_size }}</span>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="基础/计价" width="110" align="center">
              <template slot-scope="{row}">
                <span style="font-weight:500">{{ row.base_currency }}</span>
                <span class="muted"> / {{ row.quote_currency }}</span>
              </template>
            </el-table-column>
            <el-table-column label="同步时间" width="160">
              <template slot-scope="{row}">{{ fmtDT(row.synced_at) }}</template>
            </el-table-column>
          </el-table>

          <el-empty v-if="!mkLoading && mkList.length === 0" description="暂无市场数据，请先在「数据同步」中同步市场信息" :image-size="80"/>

          <!-- 分页 -->
          <div v-if="mkTotal > 0" style="margin-top:12px;display:flex;justify-content:space-between;align-items:center">
            <span class="muted" style="font-size:12px">
              显示 {{ (mkPage - 1) * mkPageSize + 1 }}–{{ Math.min(mkPage * mkPageSize, mkFilteredList.length) }} / {{ mkFilteredList.length }} 条
            </span>
            <el-pagination
              background
              layout="prev, pager, next, sizes"
              :total="mkFilteredList.length"
              :page-sizes="[20, 50, 100, 200]"
              :page-size.sync="mkPageSize"
              :current-page.sync="mkPage"
              @size-change="mkPage = 1"
              @current-change="() => {}"/>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- ═══════════ Tab 4: 信号冷却 ═══════════ -->
      <el-tab-pane label="信号冷却" name="cooldown">
        <el-card shadow="never">
          <div slot="header">
            <span>当前冷却中的策略-币对</span>
            <el-button style="float:right;padding:3px 0" type="text" :loading="loadingPM" @click="fetchPMStatus">刷新</el-button>
          </div>
          <el-table :data="pmCooldowns" stripe border size="small" :header-cell-style="{background:'#fafafa'}">
            <el-table-column prop="strategy" label="策略" width="220" />
            <el-table-column prop="symbol" label="交易对" width="140" />
            <el-table-column label="剩余冷却" width="120" align="center">
              <template slot-scope="{row}">
                <el-tag type="warning" size="small" effect="dark">{{ row.remaining_minutes }} 分钟</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cooldown_until" label="冷却截止">
              <template slot-scope="{row}">{{ fmtDT(row.cooldown_until) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="pmCooldowns.length === 0" description="当前没有冷却中的策略" :image-size="60"/>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import {
  getNodes, syncBalance, syncPositions, syncTrades, syncMarkets, getMarkets,
  getPositionMonitorStatus, getMonitoredPositions,
  triggerPositionMonitorScan, getRealtimePrices
} from '@/api/node'

export default {
  name: 'SyncManage',
  data() {
    return {
      activeTab: 'monitor',
      // ── 数据同步 ──
      nodes: [],
      balanceNodeId: null,
      positionNodeId: null,
      syncingBalance: false,
      syncingPositions: false,
      syncingTrades: false,
      syncingMarkets: false,
      balanceResult: null,
      positionResult: null,
      tradesResult: null,
      marketsResult: null,
      tradesNodeId: null,
      marketExchange: null,
      marketType: 'swap',
      syncHistory: [],
      // ── 持仓监控 ──
      loadingPM: false,
      pmError: null,
      pmStatus: { enabled: false },
      pmStats: {},
      pmConfig: {},
      pmCooldowns: [],
      monitoredPositions: [],
      loadingPositions: false,
      scanning: false,
      // ── 市场信息 ──
      mkLoading: false,
      mkList: [],
      mkTotal: 0,
      mkPage: 1,
      mkPageSize: 50,
      mkFilter: { exchange: '', market_type: '', symbol: '' },
      // ── 实时价格 ──
      priceMap: {},
      loadingPrices: false,
      autoRefreshPrices: false,
      priceTimer: null,
      positionTimer: null
    }
  },
  watch: {
    // 切换 Tab 时管理定时器：离开 monitor 暂停，回到 monitor 恢复
    activeTab(newTab, oldTab) {
      if (oldTab === 'monitor' && newTab !== 'monitor') {
        this.stopAutoRefresh()
      }
      if (newTab === 'monitor') {
        this.fetchMonitoredPositions()
      }
      if (newTab === 'markets' && this.mkList.length === 0) {
        this.fetchMarkets()
      }
    }
  },
  mounted() {
    this.fetchNodes()
    this.loadHistory()
    this.fetchPMStatus()
    this.fetchMonitoredPositions()
  },
  beforeDestroy() {
    this.stopAutoRefresh()
  },
  methods: {
    // ── 通用 ──
    fmtDT(dt) {
      if (!dt) return '-'
      try { return new Date(dt).toLocaleString('zh-CN') } catch { return dt }
    },
    fmtPrice(v) {
      if (v == null) return '-'
      const n = Number(v)
      if (isNaN(n)) return v
      if (n >= 100) return n.toFixed(2)
      if (n >= 1) return n.toFixed(4)
      return n.toFixed(6)
    },
    getPrice(row) {
      // 优先按 exchange:symbol 查找，回退到 symbol
      const ex = (row.exchange || '').toLowerCase()
      if (ex) {
        const key = `${ex}:${row.symbol}`
        if (this.priceMap[key]) return this.priceMap[key]
      }
      return this.priceMap[row.symbol] || null
    },
    pnlColor(row) {
      const price = this.getPrice(row)
      const entry = Number(row.entry_price)
      if (!price || !entry) return ''
      const isLong = row.position_side === 'LONG'
      const profit = isLong ? price > entry : price < entry
      return profit ? 'color:#67C23A;font-weight:600' : 'color:#F56C6C;font-weight:600'
    },
    calcPnlPct(row) {
      const price = this.getPrice(row)
      const entry = Number(row.entry_price)
      if (!price || !entry || entry === 0) return '-'
      const isLong = row.position_side === 'LONG'
      const pct = isLong ? ((price - entry) / entry * 100) : ((entry - price) / entry * 100)
      const sign = pct >= 0 ? '+' : ''
      return sign + pct.toFixed(2) + '%'
    },
    syncTypeLabel(t) {
      return { balance: '余额', position: '持仓', trades: '成交', markets: '市场' }[t] || t
    },
    syncTypeTag(t) {
      return { balance: 'primary', position: 'success', trades: 'warning', markets: '' }[t] || 'info'
    },

    // ── 数据同步 ──
    async fetchNodes() {
      try {
        const res = await getNodes()
        this.nodes = res.data.data || []
      } catch (e) {
        this.$message.error('获取节点列表失败')
      }
    },
    async handleSyncBalance() {
      if (!this.balanceNodeId) { this.$message.warning('请选择目标节点'); return }
      this.syncingBalance = true; this.balanceResult = null
      const node = this.nodes.find(n => n.id === this.balanceNodeId)
      const name = node ? `${node.name} (${node.node_code})` : '未知'
      const t = new Date()
      try {
        await syncBalance({ node_id: this.balanceNodeId })
        this.balanceResult = { success: true, message: '余额同步完成' }
        this.addHistory('balance', name, '余额同步完成', true, t)
        this.$message.success('余额同步完成')
      } catch (e) {
        const msg = '同步失败: ' + (e.response?.data?.detail || e.message)
        this.balanceResult = { success: false, message: msg }
        this.addHistory('balance', name, msg, false, t)
      } finally { this.syncingBalance = false }
    },
    async handleSyncPositions() {
      if (!this.positionNodeId) { this.$message.warning('请选择目标节点'); return }
      this.syncingPositions = true; this.positionResult = null
      const node = this.nodes.find(n => n.id === this.positionNodeId)
      const name = node ? `${node.name} (${node.node_code})` : '未知'
      const t = new Date()
      try {
        await syncPositions({ node_id: this.positionNodeId })
        this.positionResult = { success: true, message: '持仓同步完成' }
        this.addHistory('position', name, '持仓同步完成', true, t)
        this.$message.success('持仓同步完成')
      } catch (e) {
        const msg = '同步失败: ' + (e.response?.data?.detail || e.message)
        this.positionResult = { success: false, message: msg }
        this.addHistory('position', name, msg, false, t)
      } finally { this.syncingPositions = false }
    },
    async handleSyncTrades() {
      this.syncingTrades = true; this.tradesResult = null
      const node = this.tradesNodeId ? this.nodes.find(n => n.id === this.tradesNodeId) : null
      const name = node ? `${node.name} (${node.node_code})` : '全部节点'
      const t = new Date()
      try {
        const params = {}
        if (this.tradesNodeId) params.node_id = this.tradesNodeId
        await syncTrades(params)
        this.tradesResult = { success: true, message: '成交同步完成' }
        this.addHistory('trades', name, '成交同步完成', true, t)
        this.$message.success('成交同步完成')
      } catch (e) {
        const msg = '同步失败: ' + (e.response?.data?.detail || e.message)
        this.tradesResult = { success: false, message: msg }
        this.addHistory('trades', name, msg, false, t)
      } finally { this.syncingTrades = false }
    },
    async handleSyncMarkets() {
      this.syncingMarkets = true; this.marketsResult = null
      const t = new Date()
      const ex = this.marketExchange ? this.marketExchange.toUpperCase() : '全部'
      try {
        const params = { market_type: this.marketType }
        if (this.marketExchange) params.exchange = this.marketExchange
        await syncMarkets(params)
        this.marketsResult = { success: true, message: `市场信息同步完成 (${ex})` }
        this.addHistory('markets', ex, `市场信息同步完成`, true, t)
        this.$message.success('市场信息同步完成')
      } catch (e) {
        const msg = '同步失败: ' + (e.response?.data?.detail || e.message)
        this.marketsResult = { success: false, message: msg }
        this.addHistory('markets', ex, msg, false, t)
      } finally { this.syncingMarkets = false }
    },
    addHistory(type, nodeName, message, success, time) {
      this.syncHistory.unshift({ type, node_name: nodeName, message, success, time: time.toISOString() })
      if (this.syncHistory.length > 50) this.syncHistory = this.syncHistory.slice(0, 50)
      this.saveHistory()
    },
    saveHistory() {
      try { localStorage.setItem('sync_history', JSON.stringify(this.syncHistory)) } catch (e) { /* ignore */ }
    },
    loadHistory() {
      try {
        const s = localStorage.getItem('sync_history')
        if (s) { this.syncHistory = JSON.parse(s) }
      } catch (e) { /* ignore */ }
    },
    clearHistory() {
      this.$confirm('确定清空所有同步历史记录吗？', '提示', { type: 'warning' }).then(() => {
        this.syncHistory = []; this.saveHistory(); this.$message.success('已清空')
      }).catch(() => {})
    },

    // ── 持仓监控 ──
    refreshPM() {
      this.fetchPMStatus()
      this.fetchMonitoredPositions()
    },
    async fetchPMStatus() {
      this.loadingPM = true; this.pmError = null
      try {
        const res = await getPositionMonitorStatus()
        const d = res.data || {}
        const cfg = d.config || {}
        this.pmStatus = { enabled: cfg.position_monitor === true }
        this.pmStats = d.position_monitor_stats || {}
        this.pmConfig = {
          interval: cfg.position_monitor_interval || cfg.interval_seconds || '-',
          syncInterval: cfg.sync_interval_seconds || '-',
          strategiesCount: cfg.strategies_count || 0,
          exchangeSlTp: cfg.exchange_sl_tp || false
        }
        this.pmCooldowns = d.cooldowns || []
      } catch (e) {
        this.pmError = '无法获取持仓监控状态：' + (e.response?.data?.message || e.message || '服务不可达')
        this.pmStatus = { enabled: false }; this.pmStats = {}; this.pmConfig = {}; this.pmCooldowns = []
      } finally { this.loadingPM = false }
    },
    async fetchMonitoredPositions() {
      this.loadingPositions = true
      try {
        const res = await getMonitoredPositions()
        this.monitoredPositions = res.data.data || []
        // 有持仓时自动获取价格
        if (this.monitoredPositions.length > 0) {
          this.fetchPrices()
        }
      } catch (e) {
        this.monitoredPositions = []
      } finally { this.loadingPositions = false }
    },
    async handleTriggerScan() {
      this.scanning = true
      try {
        const res = await triggerPositionMonitorScan()
        const d = res.data || {}
        if (d.success) {
          this.$message.success(`扫描完成，监控持仓: ${d.data?.positions_monitored || 0}`)
          // 扫描后刷新状态和价格
          this.fetchPMStatus()
          this.fetchMonitoredPositions()
        } else {
          this.$message.warning(d.message || d.error || '扫描未成功')
        }
      } catch (e) {
        this.$message.error('手动扫描失败: ' + (e.response?.data?.detail || e.message))
      } finally { this.scanning = false }
    },

    // ── 实时价格（按交易所区分）──
    async fetchPrices() {
      if (this.monitoredPositions.length === 0) return
      this.loadingPrices = true
      try {
        // 按 exchange:symbol 去重，确保不同交易所的同币种分别获取价格
        const seen = new Set()
        const exchangeSymbolPairs = []
        this.monitoredPositions.forEach(p => {
          const ex = (p.exchange || '').toLowerCase()
          const key = ex ? `${ex}:${p.symbol}` : p.symbol
          if (!seen.has(key)) {
            seen.add(key)
            exchangeSymbolPairs.push(key)
          }
        })
        const symbols = [...new Set(this.monitoredPositions.map(p => p.symbol))].join(',')
        const exchangeSymbols = exchangeSymbolPairs.join(',')
        const res = await getRealtimePrices(symbols, exchangeSymbols)
        // 优先用 exchange_prices（按交易所区分）
        const exPrices = (res.data || {}).exchange_prices || {}
        const fallbackPrices = (res.data || {}).prices || {}
        const map = {}
        // 填充 exchange:symbol → price
        Object.keys(exPrices).forEach(key => {
          if (exPrices[key] && exPrices[key].last) {
            map[key] = exPrices[key].last
          }
        })
        // 回退：symbol → price（兼容旧逻辑）
        Object.keys(fallbackPrices).forEach(sym => {
          if (!map[sym] && fallbackPrices[sym] && fallbackPrices[sym].last) {
            map[sym] = fallbackPrices[sym].last
          }
        })
        this.priceMap = map
      } catch (e) {
        // silent
      } finally { this.loadingPrices = false }
    },
    toggleAutoRefresh(val) {
      if (val) {
        this.fetchPrices()
        this.priceTimer = setInterval(() => { this.fetchPrices() }, 10000) // 每10秒刷新价格
        // 每30秒刷新持仓列表，自动发现已平仓的持仓
        this.positionTimer = setInterval(() => { this.fetchMonitoredPositions() }, 30000)
      } else {
        this.stopAutoRefresh()
      }
    },
    stopAutoRefresh() {
      if (this.priceTimer) {
        clearInterval(this.priceTimer)
        this.priceTimer = null
      }
      if (this.positionTimer) {
        clearInterval(this.positionTimer)
        this.positionTimer = null
      }
      this.autoRefreshPrices = false
    },

    // ── 市场信息 ──
    async fetchMarkets() {
      this.mkLoading = true
      this.mkPage = 1
      try {
        const params = {}
        if (this.mkFilter.exchange) params.exchange = this.mkFilter.exchange
        if (this.mkFilter.market_type) params.market_type = this.mkFilter.market_type
        if (this.mkFilter.symbol) params.symbol = this.mkFilter.symbol
        const res = await getMarkets(params)
        this.mkList = res.data.data || []
        this.mkTotal = res.data.total || this.mkList.length
      } catch (e) {
        this.$message.error('获取市场信息失败: ' + (e.response?.data?.detail || e.message))
        this.mkList = []
        this.mkTotal = 0
      } finally {
        this.mkLoading = false
      }
    },
    resetMkFilter() {
      this.mkFilter = { exchange: '', market_type: '', symbol: '' }
      this.fetchMarkets()
    },
    mkExTagType(ex) {
      const m = { binance: 'warning', gate: '', okx: 'success' }
      return m[(ex || '').toLowerCase()] || 'info'
    }
  },
  computed: {
    mkFilteredList() {
      // 前端二次过滤（symbol 模糊搜索，因为后端是精确匹配）
      if (!this.mkFilter.symbol) return this.mkList
      const kw = this.mkFilter.symbol.toUpperCase()
      return this.mkList.filter(m =>
        (m.canonical_symbol || '').toUpperCase().includes(kw) ||
        (m.base_currency || '').toUpperCase().includes(kw)
      )
    },
    mkPagedList() {
      const start = (this.mkPage - 1) * this.mkPageSize
      return this.mkFilteredList.slice(start, start + this.mkPageSize)
    },
    mkExchangeSummary() {
      const map = {}
      this.mkList.forEach(m => {
        const ex = (m.exchange || 'unknown').toLowerCase()
        map[ex] = (map[ex] || 0) + 1
      })
      return Object.keys(map).sort().map(name => ({ name, count: map[name] }))
    }
  }
}
</script>

<style scoped>
.pm-card {
  text-align: center;
  padding: 16px 8px;
  background: #fafafa;
  border-radius: 8px;
  min-height: 100px;
}
.pm-label { font-size: 13px; color: #909399; margin-bottom: 8px; }
.pm-value { font-size: 18px; font-weight: 600; margin-bottom: 6px; }
.pm-num { color: #409EFF; font-size: 28px; }
.pm-desc { font-size: 12px; color: #C0C4CC; }
.muted { color: #C0C4CC; }
.mk-summary-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #EBEEF5;
}
.mk-summary-label { font-weight: 600; color: #303133; font-size: 13px; }
.mk-summary-value { font-size: 20px; font-weight: 700; color: #409EFF; }
.mk-summary-desc { font-size: 12px; color: #909399; }
</style>
