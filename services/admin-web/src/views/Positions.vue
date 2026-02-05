<template>
  <el-card v-loading="loading" shadow="hover">
    <el-table :data="list" stripe border style="width:100%">
      <el-table-column prop="symbol" label="标的" width="100" />
      <el-table-column prop="position_side" label="方向" width="80" />
      <el-table-column prop="quantity" label="数量" width="100" align="right" />
      <el-table-column prop="avg_cost" label="成本价" width="100" align="right" />
      <el-table-column prop="realized_pnl" label="已实现盈亏" width="110" align="right" />
      <el-table-column prop="market_type" label="市场" width="80" />
      <el-table-column prop="updated_at" label="更新时间" width="170" />
    </el-table>
    <div class="tip">共 {{ total }} 条</div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getPositions } from '../api'

const loading = ref(true)
const list = ref([])
const total = ref(0)

onMounted(async () => {
  try {
    const res = await getPositions()
    list.value = res.data || []
    total.value = res.total ?? list.value.length
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.tip { margin-top: 8px; color: #999; font-size: 12px; }
</style>
