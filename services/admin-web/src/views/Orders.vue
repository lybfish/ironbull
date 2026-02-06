<template>
  <el-card v-loading="loading" shadow="hover">
    <div class="toolbar">
      <el-input v-model="filterSymbol" placeholder="标的" clearable style="width:120px" @keyup.enter="fetch" />
      <el-select v-model="filterStatus" placeholder="状态" clearable style="width:120px; margin-left:8px" @change="fetch">
        <el-option label="全部" value="" />
        <el-option label="PENDING" value="PENDING" />
        <el-option label="FILLED" value="FILLED" />
        <el-option label="CANCELLED" value="CANCELLED" />
        <el-option label="REJECTED" value="REJECTED" />
      </el-select>
      <el-button type="primary" size="small" style="margin-left:8px" @click="fetch">查询</el-button>
    </div>
    <el-table :data="list" stripe border style="width:100%; margin-top:12px">
      <el-table-column prop="order_id" label="订单ID" width="160" show-overflow-tooltip />
      <el-table-column prop="symbol" label="标的" width="100" />
      <el-table-column prop="side" label="方向" width="70" />
      <el-table-column prop="order_type" label="类型" width="80" />
      <el-table-column prop="quantity" label="数量" width="90" align="right" />
      <el-table-column prop="filled_quantity" label="已成交" width="90" align="right" />
      <el-table-column prop="status" label="状态" width="90" />
      <el-table-column prop="created_at" label="创建时间" width="170" />
    </el-table>
    <el-empty v-if="!loading && list.length === 0" description="暂无订单" />
    <div v-else class="tip">共 {{ total }} 条（最多显示 50 条）</div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getOrders } from '../api'

const loading = ref(true)
const list = ref([])
const total = ref(0)
const filterSymbol = ref('')
const filterStatus = ref('')

async function fetch() {
  loading.value = true
  try {
    const params = {}
    if (filterSymbol.value) params.symbol = filterSymbol.value
    if (filterStatus.value) params.status = filterStatus.value
    const res = await getOrders(params)
    list.value = res.data || []
    total.value = res.total ?? list.value.length
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(fetch)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; flex-wrap: wrap; }
.tip { margin-top: 8px; color: #999; font-size: 12px; }
</style>
