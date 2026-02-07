<template>
  <div class="ele-body">
    <!-- 连接异常提示 -->
    <el-alert v-if="connectionError" title="无法连接 signal-monitor 服务" type="error" :closable="false" show-icon style="margin-bottom: 16px">
      <div slot="description">{{ connectionError }}</div>
    </el-alert>

    <!-- 状态卡片 -->
    <el-row :gutter="15" style="margin-bottom: 16px">
      <el-col :span="6">
        <stat-card
          title="运行状态"
          :value="statusRunning ? '运行中' : '已停止'"
          icon="el-icon-video-play"
          :color="statusRunning ? 'success' : 'info'"
          :loading="statusLoading"
          help-text="信号监控主循环"
        />
      </el-col>
      <el-col :span="6">
        <stat-card
          title="活跃策略"
          :value="statusConfig.strategies_count || 0"
          icon="el-icon-s-opportunity"
          color="primary"
          :loading="statusLoading"
          help-text="当前加载的策略数"
        />
      </el-col>
      <el-col :span="6">
        <stat-card
          title="已处理信号"
          :value="state.total_signals || 0"
          icon="el-icon-s-data"
          color="warning"
          :loading="statusLoading"
          help-text="累计检测到的信号数"
        />
      </el-col>
      <el-col :span="6">
        <stat-card
          title="检测轮次"
          :value="state.total_checks || 0"
          icon="el-icon-refresh"
          color="info"
          :loading="statusLoading"
          help-text="已执行检测次数"
        />
      </el-col>
    </el-row>

    <!-- 工具栏：启动/停止/刷新/自动刷新 -->
    <el-card shadow="never" style="margin-bottom: 16px">
      <div class="toolbar">
        <span class="toolbar-title">控制</span>
        <div>
          <el-button
            v-if="!statusRunning"
            type="success"
            size="small"
            icon="el-icon-video-play"
            :loading="actionLoading"
            @click="handleStart"
          >启动监控</el-button>
          <el-button
            v-else
            type="danger"
            size="small"
            icon="el-icon-video-pause"
            :loading="actionLoading"
            @click="handleStop"
          >停止监控</el-button>
          <el-button type="primary" size="small" icon="el-icon-refresh" :loading="statusLoading" @click="fetchAll">刷新</el-button>
          <el-switch
            v-model="autoRefresh"
            active-text="自动刷新"
            inactive-text=""
            style="margin-left: 12px"
            @change="handleAutoRefreshChange"
          />
          <el-button type="warning" size="small" icon="el-icon-message" :loading="testNotifyLoading" @click="handleTestNotify" style="margin-left: 8px">测试通知</el-button>
        </div>
      </div>
    </el-card>

    <el-row :gutter="16">
      <!-- 状态详情 -->
      <el-col :span="12">
        <el-card shadow="never" v-loading="statusLoading">
          <div slot="header">状态详情</div>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="运行状态">
              <el-tag :type="statusRunning ? 'success' : 'info'" size="small">{{ statusRunning ? '运行中' : '已停止' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="最后检测时间">{{ formatTime(state.last_check) }}</el-descriptions-item>
            <el-descriptions-item label="信号检测间隔">{{ statusConfig.interval_seconds || '-' }} 秒</el-descriptions-item>
            <el-descriptions-item label="数据同步间隔">{{ statusConfig.sync_interval_seconds || '-' }} 秒</el-descriptions-item>
            <el-descriptions-item label="错误次数">{{ state.errors || 0 }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <!-- 全局配置 -->
      <el-col :span="12">
        <el-card shadow="never" v-loading="configLoading">
          <div slot="header">全局配置</div>
          <el-form :model="config" label-width="140px" size="small">
            <el-form-item label="信号检测间隔(秒)">
              <el-input-number v-model="config.interval_seconds" :min="10" :max="600" :step="10" style="width: 140px" />
              <span class="form-tip">建议 60–300 秒</span>
            </el-form-item>
            <el-form-item label="数据同步间隔(秒)">
              <el-input-number v-model="config.sync_interval_seconds" :min="10" :max="600" :step="10" style="width: 140px" />
              <span class="form-tip">余额/持仓/成交同步频率</span>
            </el-form-item>
            <el-form-item label="有信号时通知">
              <el-switch v-model="config.notify_on_signal" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="configSaving" @click="saveConfig">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近一次信号 -->
    <el-card v-if="state.last_signal" shadow="never" style="margin-top: 16px">
      <div slot="header">最近一次信号</div>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="交易对">{{ state.last_signal.symbol }}</el-descriptions-item>
        <el-descriptions-item label="方向">
          <el-tag :type="state.last_signal.side === 'BUY' ? 'success' : 'danger'" size="mini">{{ state.last_signal.side }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="入场价">{{ state.last_signal.entry_price }}</el-descriptions-item>
        <el-descriptions-item label="置信度">{{ state.last_signal.confidence }}%</el-descriptions-item>
        <el-descriptions-item label="策略">{{ state.last_signal.strategy || '-' }}</el-descriptions-item>
        <el-descriptions-item label="时间">{{ formatTime(state.last_signal.timestamp) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 冷却状态 -->
    <el-card v-if="cooldowns.length > 0" shadow="never" style="margin-top: 16px">
      <div slot="header" class="card-header">
        <span>信号冷却状态</span>
        <el-tag size="small" type="warning">{{ cooldowns.length }} 个冷却中</el-tag>
      </div>
      <el-table :data="cooldowns" stripe border size="small" :header-cell-style="{ background: '#fafafa' }">
        <el-table-column prop="strategy" label="策略" width="140"/>
        <el-table-column prop="symbol" label="交易对" width="140">
          <template slot-scope="{row}">
            <span style="font-weight:600">{{ row.symbol }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="remaining_minutes" label="剩余冷却" width="120" align="center">
          <template slot-scope="{row}">
            <span style="color:#E6A23C;font-weight:600">{{ row.remaining_minutes }} 分钟</span>
          </template>
        </el-table-column>
        <el-table-column prop="cooldown_until" label="冷却到期" min-width="180">
          <template slot-scope="{row}">{{ formatTime(row.cooldown_until) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 策略列表 -->
    <el-card shadow="never" style="margin-top: 16px" v-loading="strategiesLoading">
      <div slot="header" class="card-header">
        <span>策略列表（信号监控加载）</span>
        <el-button size="mini" icon="el-icon-refresh" @click="fetchStrategies" :loading="strategiesLoading">刷新</el-button>
      </div>
      <el-table :data="strategies" stripe border size="small" :header-cell-style="{ background: '#fafafa' }">
        <el-table-column prop="code" label="策略编码" width="120" />
        <el-table-column prop="name" label="策略名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="exchange" label="交易所" width="100" align="center">
          <template slot-scope="{ row }">{{ row.exchange || '-' }}</template>
        </el-table-column>
        <el-table-column prop="timeframe" label="周期" width="80" align="center" />
        <el-table-column label="交易对" min-width="180" show-overflow-tooltip>
          <template slot-scope="{ row }">{{ formatSymbols(row.symbols) }}</template>
        </el-table-column>
        <el-table-column prop="min_confidence" label="最低置信度" width="100" align="center">
          <template slot-scope="{ row }">{{ row.min_confidence != null ? row.min_confidence + '%' : '-' }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!strategiesLoading && strategies.length === 0" description="暂无策略或服务未就绪" />
    </el-card>
  </div>
</template>

<script>
import {
  getSignalStatus,
  getSignalConfig,
  updateSignalConfig,
  getSignalStrategies,
  startSignalMonitor,
  stopSignalMonitor,
  testSignalNotify
} from '@/api/signal'

export default {
  name: 'SignalControl',
  data() {
    return {
      statusLoading: false,
      configLoading: false,
      configSaving: false,
      strategiesLoading: false,
      actionLoading: false,
      testNotifyLoading: false,
      connectionError: '',
      autoRefresh: false,
      refreshTimer: null,
      state: {},
      statusConfig: {},
      config: { interval_seconds: 300, sync_interval_seconds: 300, notify_on_signal: true },
      strategies: [],
      cooldowns: []
    }
  },
  computed: {
    statusRunning() {
      return !!this.state.running
    }
  },
  mounted() {
    this.fetchAll()
  },
  beforeDestroy() {
    this.clearRefreshTimer()
  },
  methods: {
    formatTime(t) {
      if (!t) return '-'
      const s = typeof t === 'string' ? t : (t.toISOString && t.toISOString())
      return s ? s.replace('T', ' ').substring(0, 19) : '-'
    },
    formatSymbols(symbols) {
      if (!symbols) return '-'
      return Array.isArray(symbols) ? symbols.join(', ') : String(symbols)
    },
    handleAutoRefreshChange(val) {
      if (val) this.startAutoRefresh()
      else this.clearRefreshTimer()
    },
    startAutoRefresh() {
      this.clearRefreshTimer()
      this.refreshTimer = setInterval(() => {
        this.fetchStatus()
      }, 10000)
    },
    clearRefreshTimer() {
      if (this.refreshTimer) {
        clearInterval(this.refreshTimer)
        this.refreshTimer = null
      }
    },
    fetchAll() {
      this.fetchStatus()
      this.fetchConfig()
      this.fetchStrategies()
    },
    async fetchStatus() {
      this.statusLoading = true
      this.connectionError = ''
      try {
        const res = await getSignalStatus()
        const data = res.data
        this.state = data.state || data || {}
        this.statusConfig = data.config || {}
        this.cooldowns = data.cooldowns || []
      } catch (e) {
        this.connectionError = e.message || (e.response && e.response.data && (e.response.data.error || e.response.data.detail)) || '请确认 signal-monitor 已启动（端口 8020）'
        this.state = {}
        this.statusConfig = {}
        this.cooldowns = []
      } finally {
        this.statusLoading = false
      }
    },
    async fetchConfig() {
      this.configLoading = true
      try {
        const res = await getSignalConfig()
        const data = res.data
        const cfg = data.config || data || {}
        if (cfg.interval_seconds != null) this.config.interval_seconds = cfg.interval_seconds
        if (cfg.sync_interval_seconds != null) this.config.sync_interval_seconds = cfg.sync_interval_seconds
        if (cfg.notify_on_signal !== undefined) this.config.notify_on_signal = !!cfg.notify_on_signal
      } catch (e) {
        this.$message.error('获取配置失败')
      } finally {
        this.configLoading = false
      }
    },
    async saveConfig() {
      this.configSaving = true
      try {
        await updateSignalConfig({
          interval_seconds: this.config.interval_seconds,
          sync_interval_seconds: this.config.sync_interval_seconds,
          notify_on_signal: this.config.notify_on_signal
        })
        this.$message.success('配置已保存')
        this.fetchStatus()
      } catch (e) {
        this.$message.error(e.response?.data?.error || '保存失败')
      } finally {
        this.configSaving = false
      }
    },
    async fetchStrategies() {
      this.strategiesLoading = true
      try {
        const res = await getSignalStrategies()
        const data = res.data
        this.strategies = data.strategies || data.data || data || []
      } catch (e) {
        this.strategies = []
      } finally {
        this.strategiesLoading = false
      }
    },
    async handleStart() {
      this.actionLoading = true
      try {
        const res = await startSignalMonitor()
        const data = res.data
        if (data.success) {
          this.$message.success(data.message || '监控已启动')
          this.fetchStatus()
        } else {
          this.$message.warning(data.error || '启动失败')
        }
      } catch (e) {
        this.$message.error(e.response?.data?.error || '启动失败')
      } finally {
        this.actionLoading = false
      }
    },
    async handleStop() {
      this.actionLoading = true
      try {
        const res = await stopSignalMonitor()
        const data = res.data
        if (data.success) {
          this.$message.success(data.message || '监控已停止')
          this.fetchStatus()
        } else {
          this.$message.warning(data.error || '停止失败')
        }
      } catch (e) {
        this.$message.error(e.response?.data?.error || '停止失败')
      } finally {
        this.actionLoading = false
      }
    },
    async handleTestNotify() {
      this.testNotifyLoading = true
      try {
        const res = await testSignalNotify()
        const data = res.data
        if (data.success) {
          this.$message.success('测试通知已发送')
        } else {
          this.$message.warning(data.error || '发送失败')
        }
      } catch (e) {
        this.$message.error(e.response?.data?.error || '测试通知失败')
      } finally {
        this.testNotifyLoading = false
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
}
.toolbar-title {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.form-tip {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}
</style>
