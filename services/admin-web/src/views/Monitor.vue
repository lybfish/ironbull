<template>
  <div class="monitor" v-loading="loading">
    <!-- 总体状态 -->
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card" :class="overallClass">
          <div class="stat-label">系统状态</div>
          <div class="stat-value">{{ overallText }}</div>
          <div class="stat-sub">最后检查: {{ lastCheckTime }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">服务</div>
          <div class="stat-value">{{ healthyCount }} / {{ totalServices }}</div>
          <div class="stat-sub">在线 / 总计</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">执行节点</div>
          <div class="stat-value">{{ onlineNodes }} / {{ totalNodes }}</div>
          <div class="stat-sub">在线 / 总计</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">数据存储</div>
          <div class="stat-value">
            <span :class="dbData.mysql_ok ? 'dot-green' : 'dot-red'"></span> MySQL
            <span style="margin-left:12px" :class="dbData.redis_ok ? 'dot-green' : 'dot-red'"></span> Redis
          </div>
          <div class="stat-sub">
            {{ dbData.mysql_latency_ms }}ms / {{ dbData.redis_latency_ms }}ms
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 服务健康列表 -->
    <el-card shadow="hover" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>服务健康状态</span>
          <el-button type="primary" size="small" :loading="refreshing" @click="refresh">刷新</el-button>
        </div>
      </template>
      <el-table :data="services" stripe>
        <el-table-column prop="name" label="服务名称" width="180" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.healthy ? 'success' : 'danger'" size="small">
              {{ row.healthy ? '正常' : '异常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="latency_ms" label="延迟(ms)" width="120">
          <template #default="{ row }">
            <span :class="row.latency_ms > 1000 ? 'text-warning' : ''">{{ row.latency_ms }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="url" label="端点" />
        <el-table-column prop="error" label="错误信息">
          <template #default="{ row }">
            <span class="text-danger" v-if="row.error">{{ row.error }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 节点列表 -->
    <el-card shadow="hover" style="margin-top: 16px">
      <template #header>执行节点心跳</template>
      <el-table :data="nodes" stripe>
        <el-table-column prop="node_code" label="节点编码" width="160" />
        <el-table-column prop="name" label="名称" width="160" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.online ? 'success' : 'danger'" size="small">
              {{ row.online ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_heartbeat" label="最后心跳" width="200">
          <template #default="{ row }">
            {{ row.last_heartbeat || '无记录' }}
          </template>
        </el-table-column>
        <el-table-column label="距今(秒)">
          <template #default="{ row }">
            {{ row.seconds_since_heartbeat != null ? row.seconds_since_heartbeat : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="base_url" label="地址" />
      </el-table>
      <div v-if="nodes.length === 0" class="empty-tip">暂无活跃节点</div>
    </el-card>

    <!-- DB/Redis 详情 -->
    <el-card shadow="hover" style="margin-top: 16px">
      <template #header>数据存储状态</template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="MySQL 状态">
          <el-tag :type="dbData.mysql_ok ? 'success' : 'danger'" size="small">
            {{ dbData.mysql_ok ? '正常' : '异常' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="MySQL 延迟">{{ dbData.mysql_latency_ms }} ms</el-descriptions-item>
        <el-descriptions-item label="MySQL 错误">
          <span class="text-danger" v-if="dbData.mysql_error">{{ dbData.mysql_error }}</span>
          <span v-else class="text-muted">-</span>
        </el-descriptions-item>
        <el-descriptions-item label="Redis 状态">
          <el-tag :type="dbData.redis_ok ? 'success' : 'danger'" size="small">
            {{ dbData.redis_ok ? '正常' : '异常' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Redis 延迟">{{ dbData.redis_latency_ms }} ms</el-descriptions-item>
        <el-descriptions-item label="Redis 错误">
          <span class="text-danger" v-if="dbData.redis_error">{{ dbData.redis_error }}</span>
          <span v-else class="text-muted">-</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { getMonitorStatus } from '../api'

const loading = ref(true)
const refreshing = ref(false)

const services = ref([])
const nodes = ref([])
const dbData = reactive({
  mysql_ok: false, mysql_latency_ms: 0, mysql_error: null,
  redis_ok: false, redis_latency_ms: 0, redis_error: null,
})
const overall = ref('unknown')
const lastCheck = ref(null)

const overallText = computed(() => {
  const map = { healthy: '正常', degraded: '异常', unknown: '未知' }
  return map[overall.value] || overall.value
})
const overallClass = computed(() => {
  if (overall.value === 'healthy') return 'card-healthy'
  if (overall.value === 'degraded') return 'card-degraded'
  return ''
})
const lastCheckTime = computed(() => {
  if (!lastCheck.value) return '-'
  return new Date(lastCheck.value * 1000).toLocaleTimeString()
})
const healthyCount = computed(() => services.value.filter(s => s.healthy).length)
const totalServices = computed(() => services.value.length)
const onlineNodes = computed(() => nodes.value.filter(n => n.online).length)
const totalNodes = computed(() => nodes.value.length)

async function fetchData() {
  try {
    const res = await getMonitorStatus()
    if (res?.data) {
      const d = res.data
      overall.value = d.overall
      services.value = d.services || []
      nodes.value = d.nodes || []
      Object.assign(dbData, d.db || {})
      // 用 db.checked_at 作为最后检查时间
      if (d.db?.checked_at) lastCheck.value = d.db.checked_at
    }
  } catch (e) {
    console.error('监控数据加载失败:', e)
  }
}

async function refresh() {
  refreshing.value = true
  await fetchData()
  refreshing.value = false
}

let timer = null

onMounted(async () => {
  await fetchData()
  loading.value = false
  // 每 30 秒自动刷新
  timer = setInterval(fetchData, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-label { color: #909399; font-size: 13px; margin-bottom: 8px; }
.stat-value { font-size: 24px; font-weight: 600; color: #303133; }
.stat-sub { color: #909399; font-size: 12px; margin-top: 4px; }
.card-healthy { border-top: 3px solid #67C23A; }
.card-degraded { border-top: 3px solid #F56C6C; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.dot-green::before { content: ''; display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #67C23A; margin-right: 4px; }
.dot-red::before { content: ''; display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #F56C6C; margin-right: 4px; }
.text-danger { color: #F56C6C; }
.text-warning { color: #E6A23C; }
.text-muted { color: #C0C4CC; }
.empty-tip { text-align: center; color: #909399; padding: 20px 0; }
</style>
