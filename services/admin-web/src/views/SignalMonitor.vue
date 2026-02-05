<template>
  <div class="signal-monitor-page">
    <el-card v-loading="loading" shadow="hover">
      <template #header>信号监控状态</template>
      <template v-if="error">
        <el-alert type="warning" :title="error" show-icon />
        <p class="tip">请确认 signal-monitor 已启动（默认端口 8020），或检查 config 中 signal_monitor_url。</p>
      </template>
      <template v-else>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="运行状态">
            <el-tag :type="state.running ? 'success' : 'info'">{{ state.running ? '运行中' : '已停止' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="上次检测">{{ state.last_check || '-' }}</el-descriptions-item>
          <el-descriptions-item label="检测次数">{{ state.total_checks ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="信号总数">{{ state.total_signals ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="错误次数">{{ state.errors ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="检测间隔(秒)">{{ config.interval_seconds ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="策略数量">{{ config.strategies_count ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="最低置信度">{{ config.min_confidence ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="通知开关">{{ config.notify_enabled ? '开' : '关' }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="state.last_signal" class="last-signal">
          <div class="label">最近一次信号</div>
          <pre>{{ JSON.stringify(state.last_signal, null, 2) }}</pre>
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSignalMonitorStatus } from '../api'

const loading = ref(true)
const error = ref('')
const state = ref({ running: false, last_check: null, last_signal: null, total_signals: 0, total_checks: 0, errors: 0 })
const config = ref({})

onMounted(async () => {
  try {
    const res = await getSignalMonitorStatus()
    if (res.error) {
      error.value = res.error
      if (res.message) error.value += ' — ' + res.message
    } else {
      state.value = res.state || {}
      config.value = res.config || {}
    }
  } catch (e) {
    error.value = e.message || '请求失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.signal-monitor-page { padding: 0; }
.tip { margin-top: 12px; color: #999; font-size: 12px; }
.last-signal { margin-top: 16px; }
.last-signal .label { font-size: 12px; color: #666; margin-bottom: 4px; }
.last-signal pre { background: #f5f7fa; padding: 12px; border-radius: 4px; font-size: 12px; overflow: auto; max-height: 200px; }
</style>
