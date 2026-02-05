<template>
  <el-card v-loading="loading" shadow="hover">
    <el-table :data="list" stripe border style="width:100%">
      <el-table-column prop="fill_id" label="成交ID" width="140" show-overflow-tooltip />
      <el-table-column prop="order_id" label="订单ID" width="140" show-overflow-tooltip />
      <el-table-column prop="symbol" label="标的" width="100" />
      <el-table-column prop="side" label="方向" width="70" />
      <el-table-column prop="quantity" label="数量" width="90" align="right" />
      <el-table-column prop="price" label="价格" width="100" align="right" />
      <el-table-column prop="fee" label="手续费" width="90" align="right" />
      <el-table-column prop="filled_at" label="成交时间" width="170" />
    </el-table>
    <div class="tip">共 {{ total }} 条</div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getFills } from '../api'

const loading = ref(true)
const list = ref([])
const total = ref(0)

onMounted(async () => {
  try {
    const res = await getFills()
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
