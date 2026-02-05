<template>
  <div class="analytics">
    <el-row :gutter="16">
      <el-col :span="24">
        <el-card v-loading="loadingPerf" shadow="hover">
          <template #header>绩效汇总</template>
          <el-descriptions v-if="summary" :column="3" border>
            <el-descriptions-item label="当前权益">{{ summary.current_equity != null ? Number(summary.current_equity).toFixed(2) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="累计收益率">{{ summary.total_return != null ? (Number(summary.total_return) * 100).toFixed(2) + '%' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="年化收益">{{ summary.annualized_return != null ? (Number(summary.annualized_return) * 100).toFixed(2) + '%' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="最大回撤">{{ summary.max_drawdown != null ? (Number(summary.max_drawdown) * 100).toFixed(2) + '%' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="夏普比率">{{ summary.sharpe_ratio != null ? Number(summary.sharpe_ratio).toFixed(2) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="总交易/胜率">{{ (summary.total_trades ?? '-') + ' / ' + (summary.win_rate != null ? (Number(summary.win_rate) * 100).toFixed(1) + '%' : '-') }}</el-descriptions-item>
          </el-descriptions>
          <div v-else class="empty">暂无绩效数据</div>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="24">
        <el-card v-loading="loadingCurve" shadow="hover">
          <template #header>净值曲线</template>
          <div ref="chartRef" style="height:320px"></div>
          <div v-if="!curvePoints.length && !loadingCurve" class="empty">暂无净值曲线数据（可传 start_date / end_date 到绩效接口）</div>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="24">
        <el-card v-loading="loadingRisk" shadow="hover">
          <template #header>风险指标（最新）</template>
          <el-descriptions v-if="risk" :column="3" border>
            <el-descriptions-item label="夏普">{{ risk.sharpe_ratio != null ? Number(risk.sharpe_ratio).toFixed(2) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="索提诺">{{ risk.sortino_ratio != null ? Number(risk.sortino_ratio).toFixed(2) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="最大回撤">{{ risk.max_drawdown != null ? (Number(risk.max_drawdown) * 100).toFixed(2) + '%' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="VaR(95%)">{{ risk.var_95 != null ? Number(risk.var_95).toFixed(4) : '-' }}</el-descriptions-item>
          </el-descriptions>
          <div v-else class="empty">暂无风险指标</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { getPerformance, getRisk } from '../api'
import * as echarts from 'echarts'

const loadingPerf = ref(true)
const loadingCurve = ref(true)
const loadingRisk = ref(true)
const summary = ref(null)
const curvePoints = ref([])
const risk = ref(null)
const chartRef = ref(null)
let chart = null

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  const dates = curvePoints.value.map(p => p.date)
  const equity = curvePoints.value.map(p => p.equity)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', name: '净值' },
    series: [{ name: '净值', type: 'line', data: equity, smooth: true }],
  })
}

onMounted(async () => {
  try {
    const [perfRes, riskRes] = await Promise.all([
      getPerformance({ start_date: '2025-01-01', end_date: '2025-12-31' }),
      getRisk(),
    ])
    loadingPerf.value = false
    loadingRisk.value = false
    summary.value = perfRes.data?.summary || null
    risk.value = riskRes.data || null
    const curve = perfRes.data?.equity_curve
    if (curve?.points?.length) {
      curvePoints.value = curve.points
      loadingCurve.value = false
      setTimeout(initChart, 100)
    } else {
      loadingCurve.value = false
    }
  } catch (e) {
    console.error(e)
    loadingPerf.value = false
    loadingCurve.value = false
    loadingRisk.value = false
  }
})

watch(curvePoints, () => {
  if (chart && curvePoints.value.length) initChart()
})
</script>

<style scoped>
.empty { color: #999; padding: 16px; }
</style>
