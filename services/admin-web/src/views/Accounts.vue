<template>
  <el-card v-loading="loading" shadow="hover">
    <el-table :data="list" stripe border style="width:100%">
      <el-table-column prop="ledger_account_id" label="账本账户ID" width="160" show-overflow-tooltip />
      <el-table-column prop="account_id" label="账户ID" width="90" />
      <el-table-column prop="currency" label="币种" width="80" />
      <el-table-column prop="balance" label="余额" width="120" align="right" />
      <el-table-column prop="available" label="可用" width="120" align="right" />
      <el-table-column prop="frozen" label="冻结" width="100" align="right" />
      <el-table-column prop="realized_pnl" label="已实现盈亏" width="110" align="right" />
    </el-table>
    <div class="tip">共 {{ total }} 条</div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAccounts } from '../api'

const loading = ref(true)
const list = ref([])
const total = ref(0)

onMounted(async () => {
  try {
    const res = await getAccounts()
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
