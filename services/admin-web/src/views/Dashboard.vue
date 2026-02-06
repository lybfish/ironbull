<template>
  <div class="dashboard" v-loading="loading">
    <!-- 平台级汇总 -->
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">租户总数</div>
          <div class="stat-value">{{ platform.total_tenants }}</div>
          <div class="stat-sub">活跃 {{ platform.active_tenants }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">用户总数</div>
          <div class="stat-value">{{ platform.total_users }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">订单总数</div>
          <div class="stat-value">{{ platform.total_orders }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">执行节点</div>
          <div class="stat-value">{{ platform.total_nodes }}</div>
          <div class="stat-sub">在线 {{ platform.online_nodes }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">策略绑定</div>
          <div class="stat-value">{{ platform.active_bindings }}</div>
          <div class="stat-sub">运行中</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">当前租户订单</div>
          <div class="stat-value">{{ tenant.orders }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">当前租户持仓</div>
          <div class="stat-value">{{ tenant.positions }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">当前租户权益</div>
          <div class="stat-value">{{ tenant.equity != null ? tenant.equity.toFixed(2) : '-' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 当前租户绩效摘要 -->
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>当前租户绩效摘要</template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="累计收益率">{{ fmt(tenant.totalReturn, '%') }}</el-descriptions-item>
            <el-descriptions-item label="日收益">{{ tenant.dailyPnl != null ? tenant.dailyPnl.toFixed(2) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="最大回撤">{{ fmt(tenant.maxDrawdown, '%') }}</el-descriptions-item>
            <el-descriptions-item label="夏普比率">{{ tenant.sharpeRatio != null ? tenant.sharpeRatio.toFixed(2) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="总交易次数">{{ tenant.totalTrades ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="胜率">{{ fmt(tenant.winRate, '%', 1) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getDashboardSummary, getOrders, getPositions, getPerformance } from '../api'

const loading = ref(true)

const platform = reactive({
  total_tenants: 0,
  active_tenants: 0,
  total_users: 0,
  total_orders: 0,
  total_nodes: 0,
  online_nodes: 0,
  active_bindings: 0,
})

const tenant = reactive({
  orders: 0,
  positions: 0,
  equity: null,
  totalReturn: null,
  dailyPnl: null,
  maxDrawdown: null,
  sharpeRatio: null,
  totalTrades: null,
  winRate: null,
})

function fmt(val, suffix = '', decimals = 2) {
  if (val == null) return '-'
  return (val * 100).toFixed(decimals) + suffix
}

onMounted(async () => {
  try {
    const [summaryRes, ordersRes, positionsRes, perfRes] = await Promise.allSettled([
      getDashboardSummary(),
      getOrders({ limit: 1 }),
      getPositions({ limit: 1 }),
      getPerformance().catch(() => null),
    ])

    if (summaryRes.status === 'fulfilled' && summaryRes.value?.data) {
      Object.assign(platform, summaryRes.value.data)
    }
    if (ordersRes.status === 'fulfilled') {
      tenant.orders = ordersRes.value?.total ?? 0
    }
    if (positionsRes.status === 'fulfilled') {
      tenant.positions = positionsRes.value?.total ?? 0
    }
    if (perfRes.status === 'fulfilled' && perfRes.value?.data?.summary) {
      const p = perfRes.value.data.summary
      tenant.equity = p.current_equity
      tenant.totalReturn = p.total_return
      tenant.dailyPnl = p.daily_pnl
      tenant.maxDrawdown = p.max_drawdown
      tenant.sharpeRatio = p.sharpe_ratio
      tenant.totalTrades = p.total_trades
      tenant.winRate = p.win_rate
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-label { color: #909399; font-size: 13px; margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 600; color: #303133; }
.stat-sub { color: #909399; font-size: 12px; margin-top: 4px; }
</style>
