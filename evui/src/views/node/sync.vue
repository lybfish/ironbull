<template>
  <div class="ele-body">
    <el-row :gutter="16">
      <!-- 余额同步卡片 -->
      <el-col :span="12">
        <el-card shadow="never">
          <div slot="header">
            <span>余额同步</span>
          </div>
          <el-form label-width="100px">
            <el-form-item label="目标节点">
              <el-select v-model="balanceNodeId" placeholder="选择节点" clearable style="width:100%">
                <el-option v-for="n in nodes" :key="n.id" :label="n.name + ' (' + n.node_code + ')'" :value="n.id" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="syncingBalance" @click="handleSyncBalance">同步余额</el-button>
            </el-form-item>
          </el-form>
          <div v-if="balanceResult" class="result">
            <el-alert
              :title="balanceResult.message"
              :type="balanceResult.success ? 'success' : 'error'"
              :closable="false"
              show-icon />
          </div>
        </el-card>
      </el-col>

      <!-- 持仓同步卡片 -->
      <el-col :span="12">
        <el-card shadow="never">
          <div slot="header">
            <span>持仓同步</span>
          </div>
          <el-form label-width="100px">
            <el-form-item label="目标节点">
              <el-select v-model="positionNodeId" placeholder="选择节点" clearable style="width:100%">
                <el-option v-for="n in nodes" :key="n.id" :label="n.name + ' (' + n.node_code + ')'" :value="n.id" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="syncingPositions" @click="handleSyncPositions">同步持仓</el-button>
            </el-form-item>
          </el-form>
          <div v-if="positionResult" class="result">
            <el-alert
              :title="positionResult.message"
              :type="positionResult.success ? 'success' : 'error'"
              :closable="false"
              show-icon />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px;">
      <!-- 成交同步卡片 -->
      <el-col :span="12">
        <el-card shadow="never">
          <div slot="header">
            <span>成交同步</span>
          </div>
          <el-form label-width="100px">
            <el-form-item label="目标节点">
              <el-select v-model="tradesNodeId" placeholder="选择节点（不选=全部）" clearable style="width:100%">
                <el-option v-for="n in nodes" :key="n.id" :label="n.name + ' (' + n.node_code + ')'" :value="n.id" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="warning" :loading="syncingTrades" @click="handleSyncTrades">同步成交</el-button>
            </el-form-item>
          </el-form>
          <div v-if="tradesResult" class="result">
            <el-alert
              :title="tradesResult.message"
              :type="tradesResult.success ? 'success' : 'error'"
              :closable="false"
              show-icon />
          </div>
        </el-card>
      </el-col>

      <!-- 市场信息同步卡片 -->
      <el-col :span="12">
        <el-card shadow="never">
          <div slot="header">
            <span>市场信息同步</span>
          </div>
          <el-form label-width="100px">
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
          <div v-if="marketsResult" class="result">
            <el-alert
              :title="marketsResult.message"
              :type="marketsResult.success ? 'success' : 'error'"
              :closable="false"
              show-icon />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 持仓监控(SL/TP) -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="24">
        <el-card shadow="never">
          <div slot="header">
            <span>持仓监控 (自管 SL/TP)</span>
            <el-button style="float: right; padding: 3px 0" type="text" :loading="loadingPM || loadingPositions" @click="refreshPM">
              刷新状态
            </el-button>
          </div>

          <div v-if="pmError" style="margin-bottom:12px">
            <el-alert :title="pmError" type="error" :closable="false" show-icon />
          </div>

          <el-row :gutter="24">
            <!-- 运行状态 -->
            <el-col :span="6">
              <div class="pm-stat-card">
                <div class="pm-stat-label">监控状态</div>
                <div class="pm-stat-value">
                  <el-tag v-if="pmStatus.enabled" type="success" size="medium">运行中</el-tag>
                  <el-tag v-else type="info" size="medium">未启用</el-tag>
                </div>
                <div class="pm-stat-desc">
                  {{ pmStatus.enabled ? '自管模式：不在交易所挂止损单' : '交易所 SL/TP 模式' }}
                </div>
              </div>
            </el-col>
            <!-- 监控持仓数 -->
            <el-col :span="6">
              <div class="pm-stat-card">
                <div class="pm-stat-label">监控持仓数</div>
                <div class="pm-stat-value pm-stat-number">{{ pmStats.positions_monitored || 0 }}</div>
                <div class="pm-stat-desc">当前带 SL/TP 的 OPEN 持仓</div>
              </div>
            </el-col>
            <!-- 触发次数 -->
            <el-col :span="6">
              <div class="pm-stat-card">
                <div class="pm-stat-label">触发总次数</div>
                <div class="pm-stat-value pm-stat-number">{{ pmStats.triggers_total || 0 }}</div>
                <div class="pm-stat-desc">
                  <span style="color:#67C23A">成功 {{ pmStats.closes_success || 0 }}</span>
                  <span style="margin-left:8px;color:#F56C6C">失败 {{ pmStats.closes_failed || 0 }}</span>
                </div>
              </div>
            </el-col>
            <!-- 最近扫描 -->
            <el-col :span="6">
              <div class="pm-stat-card">
                <div class="pm-stat-label">最近扫描</div>
                <div class="pm-stat-value pm-stat-time">{{ pmStats.last_scan_at ? formatPMTime(pmStats.last_scan_at) : '-' }}</div>
                <div class="pm-stat-desc">每 {{ pmConfig.interval || '?' }} 秒扫描一次</div>
              </div>
            </el-col>
          </el-row>

          <!-- 冷却中的策略 -->
          <div v-if="pmCooldowns.length > 0" style="margin-top: 16px;">
            <el-divider content-position="left">止损冷却中的策略</el-divider>
            <el-table :data="pmCooldowns" stripe border size="small">
              <el-table-column prop="strategy" label="策略" width="200" />
              <el-table-column prop="symbol" label="交易对" width="150" />
              <el-table-column label="剩余冷却" width="120">
                <template slot-scope="{row}">
                  <el-tag type="warning" size="mini">{{ row.remaining_minutes }} 分钟</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="cooldown_until" label="冷却截止" />
            </el-table>
          </div>

          <!-- 监控持仓明细 -->
          <div style="margin-top: 16px;">
            <el-divider content-position="left">
              监控持仓明细
              <el-button type="text" size="mini" :loading="loadingPositions" @click="fetchMonitoredPositions" style="margin-left:8px">刷新</el-button>
            </el-divider>
            <el-table :data="monitoredPositions" stripe border size="small" v-loading="loadingPositions"
              :header-cell-style="{background:'#fafafa'}" max-height="500">
              <el-table-column label="交易对" width="130">
                <template slot-scope="{row}">
                  <span style="font-weight:600">{{ row.symbol }}</span>
                </template>
              </el-table-column>
              <el-table-column label="交易所" width="90" align="center">
                <template slot-scope="{row}">
                  <el-tag size="mini" effect="plain">{{ (row.exchange || '').toUpperCase() }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="方向" width="70" align="center">
                <template slot-scope="{row}">
                  <el-tag :type="row.position_side === 'LONG' ? 'success' : 'danger'" size="mini">
                    {{ row.position_side === 'LONG' ? '多' : '空' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="数量" width="110" align="right">
                <template slot-scope="{row}">{{ row.quantity }}</template>
              </el-table-column>
              <el-table-column label="入场价" width="110" align="right">
                <template slot-scope="{row}">
                  <span v-if="row.entry_price">{{ row.entry_price }}</span>
                  <span v-else style="color:#C0C4CC">-</span>
                </template>
              </el-table-column>
              <el-table-column label="止损价" width="110" align="right">
                <template slot-scope="{row}">
                  <span v-if="row.stop_loss" style="color:#F56C6C;font-weight:600">{{ row.stop_loss }}</span>
                  <span v-else style="color:#C0C4CC">未设置</span>
                </template>
              </el-table-column>
              <el-table-column label="止盈价" width="110" align="right">
                <template slot-scope="{row}">
                  <span v-if="row.take_profit" style="color:#67C23A;font-weight:600">{{ row.take_profit }}</span>
                  <span v-else style="color:#C0C4CC">未设置</span>
                </template>
              </el-table-column>
              <el-table-column label="杠杆" width="60" align="center">
                <template slot-scope="{row}">{{ row.leverage || '-' }}x</template>
              </el-table-column>
              <el-table-column label="策略" width="140">
                <template slot-scope="{row}">
                  <span v-if="row.strategy_code">{{ row.strategy_code }}</span>
                  <span v-else style="color:#C0C4CC">-</span>
                </template>
              </el-table-column>
              <el-table-column label="用户" width="160">
                <template slot-scope="{row}">
                  <span v-if="row.user_email">{{ row.user_email }}</span>
                  <span v-else style="color:#C0C4CC">账户#{{ row.account_id }}</span>
                </template>
              </el-table-column>
              <el-table-column label="更新时间" width="160">
                <template slot-scope="{row}">{{ row.updated_at ? formatPMTime(row.updated_at) : '-' }}</template>
              </el-table-column>
            </el-table>
            <el-empty v-if="!loadingPositions && monitoredPositions.length === 0" description="当前没有被监控的持仓" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 同步历史 -->
    <el-card shadow="never" style="margin-top: 16px;">
      <div slot="header">
        <span>同步历史</span>
        <el-button style="float: right; padding: 3px 0" type="text" @click="clearHistory">清空历史</el-button>
      </div>
      <el-table :data="syncHistory" stripe border size="small" max-height="400">
        <el-table-column prop="type" label="类型" width="100">
          <template slot-scope="{row}">
            <el-tag :type="syncTypeTag(row.type)" size="mini">
              {{ syncTypeLabel(row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="node_name" label="目标节点" width="200" />
        <el-table-column prop="message" label="结果" />
        <el-table-column prop="time" label="时间" width="180">
          <template slot-scope="{row}">
            {{ formatDateTime(row.time) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.success ? 'success' : 'danger'" size="mini">
              {{ row.success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="syncHistory.length === 0" description="暂无同步记录" />
    </el-card>
  </div>
</template>

<script>
import {getNodes, syncBalance, syncPositions, syncTrades, syncMarkets, getPositionMonitorStatus, getMonitoredPositions} from '@/api/node'

export default {
  name: 'SyncManage',
  data() {
    return {
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
      // 持仓监控
      loadingPM: false,
      pmError: null,
      pmStatus: { enabled: false },
      pmStats: {},
      pmConfig: {},
      pmCooldowns: [],
      // 监控持仓列表
      monitoredPositions: [],
      loadingPositions: false
    }
  },
  mounted() {
    this.fetchNodes()
    this.loadHistory()
    this.fetchPMStatus()
    this.fetchMonitoredPositions()
  },
  methods: {
    syncTypeLabel(t) {
      const m = { balance: '余额同步', position: '持仓同步', trades: '成交同步', markets: '市场同步' }
      return m[t] || t
    },
    syncTypeTag(t) {
      const m = { balance: 'primary', position: 'success', trades: 'warning', markets: '' }
      return m[t] || 'info'
    },
    async fetchNodes() {
      try {
        const res = await getNodes()
        this.nodes = res.data.data || []
      } catch (e) {
        this.$message.error('获取节点列表失败')
      }
    },
    async handleSyncBalance() {
      if (!this.balanceNodeId) {
        this.$message.warning('请选择目标节点')
        return
      }
      this.syncingBalance = true
      this.balanceResult = null
      const node = this.nodes.find(n => n.id === this.balanceNodeId)
      const nodeName = node ? `${node.name} (${node.node_code})` : '未知节点'
      const startTime = new Date()

      try {
        await syncBalance({node_id: this.balanceNodeId})
        const result = {
          success: true,
          message: '余额同步完成'
        }
        this.balanceResult = result
        this.addHistory('balance', nodeName, result.message, true, startTime)
        this.$message.success('余额同步完成')
      } catch (e) {
        const errorMsg = e.response?.data?.detail || e.message || '同步失败'
        const result = {
          success: false,
          message: '同步失败: ' + errorMsg
        }
        this.balanceResult = result
        this.addHistory('balance', nodeName, result.message, false, startTime)
        this.$message.error('余额同步失败')
      } finally {
        this.syncingBalance = false
      }
    },
    async handleSyncPositions() {
      if (!this.positionNodeId) {
        this.$message.warning('请选择目标节点')
        return
      }
      this.syncingPositions = true
      this.positionResult = null
      const node = this.nodes.find(n => n.id === this.positionNodeId)
      const nodeName = node ? `${node.name} (${node.node_code})` : '未知节点'
      const startTime = new Date()

      try {
        await syncPositions({node_id: this.positionNodeId})
        const result = {
          success: true,
          message: '持仓同步完成'
        }
        this.positionResult = result
        this.addHistory('position', nodeName, result.message, true, startTime)
        this.$message.success('持仓同步完成')
      } catch (e) {
        const errorMsg = e.response?.data?.detail || e.message || '同步失败'
        const result = {
          success: false,
          message: '同步失败: ' + errorMsg
        }
        this.positionResult = result
        this.addHistory('position', nodeName, result.message, false, startTime)
        this.$message.error('持仓同步失败')
      } finally {
        this.syncingPositions = false
      }
    },
    async handleSyncTrades() {
      this.syncingTrades = true
      this.tradesResult = null
      const node = this.tradesNodeId ? this.nodes.find(n => n.id === this.tradesNodeId) : null
      const nodeName = node ? `${node.name} (${node.node_code})` : '全部节点'
      const startTime = new Date()
      try {
        const params = {}
        if (this.tradesNodeId) params.node_id = this.tradesNodeId
        await syncTrades(params)
        const result = { success: true, message: '成交同步完成' }
        this.tradesResult = result
        this.addHistory('trades', nodeName, result.message, true, startTime)
        this.$message.success('成交同步完成')
      } catch (e) {
        const errorMsg = e.response?.data?.detail || e.message || '同步失败'
        const result = { success: false, message: '同步失败: ' + errorMsg }
        this.tradesResult = result
        this.addHistory('trades', nodeName, result.message, false, startTime)
        this.$message.error('成交同步失败')
      } finally {
        this.syncingTrades = false
      }
    },
    async handleSyncMarkets() {
      this.syncingMarkets = true
      this.marketsResult = null
      const startTime = new Date()
      const exName = this.marketExchange ? this.marketExchange.toUpperCase() : '全部'
      try {
        const params = { market_type: this.marketType }
        if (this.marketExchange) params.exchange = this.marketExchange
        await syncMarkets(params)
        const result = { success: true, message: `市场信息同步完成 (${exName} - ${this.marketType})` }
        this.marketsResult = result
        this.addHistory('markets', exName, result.message, true, startTime)
        this.$message.success('市场信息同步完成')
      } catch (e) {
        const errorMsg = e.response?.data?.detail || e.message || '同步失败'
        const result = { success: false, message: '同步失败: ' + errorMsg }
        this.marketsResult = result
        this.addHistory('markets', exName, result.message, false, startTime)
        this.$message.error('市场信息同步失败')
      } finally {
        this.syncingMarkets = false
      }
    },
    addHistory(type, nodeName, message, success, time) {
      this.syncHistory.unshift({
        type,
        node_name: nodeName,
        message,
        success,
        time: time.toISOString()
      })
      // 只保留最近50条记录
      if (this.syncHistory.length > 50) {
        this.syncHistory = this.syncHistory.slice(0, 50)
      }
      this.saveHistory()
    },
    formatDateTime(datetime) {
      if (!datetime) return '-'
      return new Date(datetime).toLocaleString('zh-CN')
    },
    saveHistory() {
      try {
        localStorage.setItem('sync_history', JSON.stringify(this.syncHistory))
      } catch (e) {
        console.error('保存同步历史失败', e)
      }
    },
    loadHistory() {
      try {
        const saved = localStorage.getItem('sync_history')
        if (saved) {
          this.syncHistory = JSON.parse(saved)
        }
      } catch (e) {
        console.error('加载同步历史失败', e)
      }
    },
    clearHistory() {
      this.$confirm('确定清空所有同步历史记录吗？', '提示', {type: 'warning'}).then(() => {
        this.syncHistory = []
        this.saveHistory()
        this.$message.success('已清空历史记录')
      }).catch(() => {})
    },
    refreshPM() {
      this.fetchPMStatus()
      this.fetchMonitoredPositions()
    },
    async fetchPMStatus() {
      this.loadingPM = true
      this.pmError = null
      try {
        const res = await getPositionMonitorStatus()
        const d = res.data || {}
        const cfg = d.config || {}
        this.pmStatus = {
          enabled: cfg.position_monitor === true
        }
        this.pmStats = d.position_monitor_stats || {}
        this.pmConfig = {
          interval: cfg.interval_seconds || '-',
          syncInterval: cfg.sync_interval_seconds || '-',
          strategiesCount: cfg.strategies_count || 0,
          exchangeSlTp: cfg.exchange_sl_tp || false
        }
        this.pmCooldowns = d.cooldowns || []
      } catch (e) {
        this.pmError = '无法获取持仓监控状态：' + (e.response?.data?.message || e.message || '服务不可达')
        this.pmStatus = { enabled: false }
        this.pmStats = {}
        this.pmConfig = {}
        this.pmCooldowns = []
      } finally {
        this.loadingPM = false
      }
    },
    formatPMTime(isoStr) {
      if (!isoStr) return '-'
      try {
        return new Date(isoStr).toLocaleString('zh-CN')
      } catch (e) {
        return isoStr
      }
    },
    async fetchMonitoredPositions() {
      this.loadingPositions = true
      try {
        const res = await getMonitoredPositions()
        this.monitoredPositions = (res.data.data || [])
      } catch (e) {
        console.error('获取监控持仓失败:', e)
        this.monitoredPositions = []
      } finally {
        this.loadingPositions = false
      }
    }
  }
}
</script>

<style scoped>
.result {
  margin-top: 12px;
}
.pm-stat-card {
  text-align: center;
  padding: 16px 8px;
  background: #fafafa;
  border-radius: 6px;
}
.pm-stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}
.pm-stat-value {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 6px;
}
.pm-stat-number {
  color: #409EFF;
  font-size: 28px;
}
.pm-stat-time {
  font-size: 14px;
  color: #606266;
}
.pm-stat-desc {
  font-size: 12px;
  color: #C0C4CC;
}
</style>
