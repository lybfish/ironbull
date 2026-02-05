<template>
  <el-card v-loading="loading" shadow="hover">
    <el-table :data="list" stripe border style="width:100%">
      <el-table-column prop="transaction_id" label="流水ID" width="140" show-overflow-tooltip />
      <el-table-column prop="transaction_type" label="类型" width="100" />
      <el-table-column prop="amount" label="金额" width="120" align="right" />
      <el-table-column prop="fee" label="手续费" width="90" align="right" />
      <el-table-column prop="balance_after" label="余额(后)" width="110" align="right" />
      <el-table-column prop="source_type" label="来源" width="100" />
      <el-table-column prop="transaction_at" label="时间" width="170" />
    </el-table>
    <div class="tip">共 {{ total }} 条</div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTransactions } from '../api'

const loading = ref(true)
const list = ref([])
const total = ref(0)

onMounted(async () => {
  try {
    const res = await getTransactions()
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
