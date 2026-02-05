<template>
  <div class="dashboard">
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>订单数</template>
          <div class="stat-value">{{ summary.orders }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>成交笔数</template>
          <div class="stat-value">{{ summary.fills }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>持仓数</template>
          <div class="stat-value">{{ summary.positions }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>当前权益</template>
          <div class="stat-value">{{ summary.equity != null ? summary.equity.toFixed(2) : '-' }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="24">
        <el-card v-loading="loading" shadow="hover">
          <template #header>绩效摘要</template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="累计收益率">{{ (summary.totalReturn != null ? (summary.totalReturn * 100).toFixed(2) : '-') }}%</el-descriptions-item>
            <el-descriptions-item label="日收益">{{ summary.dailyPnl != null ? summary.dailyPnl.toFixed(2) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="最大回撤">{{ (summary.maxDrawdown != null ? (summary.maxDrawdown * 100).toFixed(2) : '-') }}%</el-descriptions-item>
            <el-descriptions-item label="夏普比率">{{ summary.sharpeRatio != null ? summary.sharpeRatio.toFixed(2) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="总交易次数">{{ summary.totalTrades ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="胜率">{{ (summary.winRate != null ? (summary.winRate * 100).toFixed(1) : '-') }}%</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getOrders, getFills, getPositions, getPerformance } from '../api'

const loading = ref(true)
const summary = ref({
  orders: 0,
  fills: 0,
  positions: 0,
  equity: null,
  totalReturn: null,
  dailyPnl: null,
  maxDrawdown: null,
  sharpeRatio: null,
  totalTrades: null,
  winRate: null,
})

onMounted(async () => {
  try {
    const [ordersRes, fillsRes, positionsRes, perfRes] = await Promise.all([
      getOrders({ limit: 1 }),
      getFills({ limit: 1 }),
      getPositions({ limit: 1 }),
      getPerformance(),
    ])
    summary.value.orders = ordersRes.total ?? ordersRes.data?.length ?? 0
    summary.value.fills = fillsRes.total ?? fillsRes.data?.length ?? 0
    summary.value.positions = positionsRes.total ?? positionsRes.data?.length ?? 0
    const perf = perfRes.data?.summary
    if (perf) {
      summary.value.equity = perf.current_equity
      summary.value.totalReturn = perf.total_return
      summary.value.dailyPnl = perf.daily_pnl
      summary.value.maxDrawdown = perf.max_drawdown
      summary.value.sharpeRatio = perf.sharpe_ratio
      summary.value.totalTrades = perf.total_trades
      summary.value.winRate = perf.win_rate
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stat-value { font-size: 24px; font-weight: 600; }
</style>
