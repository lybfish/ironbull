<template>
  <div class="ele-body">
    <el-card shadow="never" v-loading="loading">
      <div slot="header" class="card-header">
        <span>系统监控</span>
        <div>
          <el-tag :type="overallType" size="small" style="margin-right:12px">{{ overallLabel }}</el-tag>
          <el-switch
            v-model="autoRefresh"
            active-text="自动刷新"
            inactive-text="手动刷新"
            @change="handleAutoRefreshChange">
          </el-switch>
          <el-button type="primary" size="mini" icon="el-icon-refresh" style="margin-left:12px" @click="fetchData">刷新</el-button>
        </div>
      </div>

      <!-- 服务状态卡片 -->
      <el-row :gutter="15" style="margin-bottom: 20px;">
        <el-col :span="6" v-for="svc in services" :key="svc.name">
          <stat-card
            :title="svc.name"
            :value="svc.healthy ? '在线' : '离线'"
            icon="el-icon-connection"
            :color="svc.healthy ? 'success' : 'danger'"
            :help-text="svc.latency_ms ? `响应 ${svc.latency_ms}ms` : (svc.error || '未知')"
            :loading="loading">
          </stat-card>
        </el-col>
        <el-col :span="6">
          <stat-card
            title="数据库"
            :value="dbStatus.mysql_ok ? '正常' : '异常'"
            icon="el-icon-coin"
            :color="dbStatus.mysql_ok ? 'success' : 'danger'"
            help-text="MySQL 连接状态"
            :loading="loading">
          </stat-card>
        </el-col>
        <el-col :span="6">
          <stat-card
            title="Redis"
            :value="dbStatus.redis_ok ? '正常' : '异常'"
            icon="el-icon-box"
            :color="dbStatus.redis_ok ? 'success' : 'danger'"
            help-text="Redis 连接状态"
            :loading="loading">
          </stat-card>
        </el-col>
      </el-row>

      <!-- 服务健康详情 -->
      <el-card shadow="never" style="margin-bottom: 16px;">
        <div slot="header">服务健康详情</div>
        <el-table :data="services" stripe border size="small">
          <el-table-column prop="name" label="服务名" width="180"/>
          <el-table-column prop="url" label="健康检查地址" min-width="250" show-overflow-tooltip/>
          <el-table-column label="状态" width="100" align="center">
            <template slot-scope="{row}">
              <el-tag :type="row.healthy ? 'success' : 'danger'" size="mini">{{ row.healthy ? '健康' : '异常' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="延迟" width="100" align="center">
            <template slot-scope="{row}">
              <span v-if="row.latency_ms">{{ row.latency_ms }}ms</span>
              <span v-else style="color:#909399">-</span>
            </template>
          </el-table-column>
          <el-table-column label="错误" min-width="200" show-overflow-tooltip>
            <template slot-scope="{row}">
              <span v-if="row.error" style="color:#F56C6C">{{ row.error }}</span>
              <span v-else style="color:#67C23A">无</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 基础设施状态 -->
      <el-card shadow="never" style="margin-bottom: 16px;">
        <div slot="header">基础设施</div>
        <el-descriptions :column="4" border size="small">
          <el-descriptions-item label="MySQL">
            <el-tag :type="dbStatus.mysql_ok ? 'success' : 'danger'" size="mini">{{ dbStatus.mysql_ok ? '正常' : '异常' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Redis">
            <el-tag :type="dbStatus.redis_ok ? 'success' : 'danger'" size="mini">{{ dbStatus.redis_ok ? '正常' : '异常' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="MySQL 延迟" v-if="dbStatus.mysql_latency_ms">
            {{ dbStatus.mysql_latency_ms }}ms
          </el-descriptions-item>
          <el-descriptions-item label="Redis 延迟" v-if="dbStatus.redis_latency_ms">
            {{ dbStatus.redis_latency_ms }}ms
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </el-card>

    <!-- 节点心跳表 -->
    <el-card shadow="never" style="margin-top:16px" v-if="nodes.length > 0">
      <div slot="header">
        <span>执行节点心跳</span>
        <el-tag size="mini" style="margin-left:8px">{{ nodes.length }} 个节点</el-tag>
      </div>
      <el-table :data="nodes" stripe border size="small" :header-cell-style="{background:'#fafafa'}">
        <el-table-column prop="code" label="节点编码" width="150"/>
        <el-table-column prop="name" label="节点名称" width="150"/>
        <el-table-column label="状态" width="100" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.online ? 'success' : 'danger'" size="mini">
              {{ row.online ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后心跳" width="170">
          <template slot-scope="{row}">{{ formatTime(row.last_heartbeat) }}</template>
        </el-table-column>
        <el-table-column label="延迟/超时" width="120" align="center">
          <template slot-scope="{row}">
            <span v-if="row.seconds_since_heartbeat != null">{{ row.seconds_since_heartbeat }}s</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-card shadow="never" style="margin-top:16px" v-else-if="!loading">
      <el-empty description="暂无节点心跳数据"/>
    </el-card>
  </div>
</template>

<script>
import {getMonitorStatus} from '@/api/monitor'

export default {
  name: 'SystemMonitor',
  data() {
    return {
      loading: false,
      overall: '',
      services: [],
      nodes: [],
      dbStatus: {mysql_ok: false, redis_ok: false},
      autoRefresh: false,
      refreshTimer: null
    }
  },
  computed: {
    overallType() {
      return this.overall === 'healthy' ? 'success' : (this.overall === 'degraded' ? 'warning' : 'info')
    },
    overallLabel() {
      return this.overall === 'healthy' ? '系统正常' : (this.overall === 'degraded' ? '系统降级' : '加载中...')
    }
  },
  mounted() { this.fetchData() },
  beforeDestroy() { this.clearRefreshTimer() },
  methods: {
    formatTime(t) { return t ? t.replace('T', ' ').substring(0, 19) : '-' },
    async fetchData() {
      this.loading = true
      try {
        const res = await getMonitorStatus()
        // 后端返回 {code: 0, data: {overall, services, nodes, db}}
        const d = res.data.data || res.data || {}
        this.overall = d.overall || ''
        this.services = d.services || []
        this.nodes = d.nodes || []
        this.dbStatus = d.db || {mysql_ok: false, redis_ok: false}
      } catch (e) {
        this.$message.error('获取监控状态失败')
        console.error(e)
      } finally {
        this.loading = false
      }
    },
    handleAutoRefreshChange(val) {
      if (val) { this.startAutoRefresh() } else { this.clearRefreshTimer() }
    },
    startAutoRefresh() {
      this.clearRefreshTimer()
      this.refreshTimer = setInterval(() => { this.fetchData() }, 30000)
    },
    clearRefreshTimer() {
      if (this.refreshTimer) { clearInterval(this.refreshTimer); this.refreshTimer = null }
    }
  }
}
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
