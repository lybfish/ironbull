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
import {getNodes, syncBalance, syncPositions, syncTrades, syncMarkets} from '@/api/node'

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
      syncHistory: []
    }
  },
  mounted() {
    this.fetchNodes()
    // 从本地存储加载历史记录
    this.loadHistory()
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
    }
  }
}
</script>

<style scoped>
.result {
  margin-top: 12px;
}
</style>
