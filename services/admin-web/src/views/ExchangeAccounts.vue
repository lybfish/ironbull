<template>
  <div>
    <div class="toolbar">
      <el-select v-model="filterTenant" placeholder="全部租户" clearable style="width:160px" @change="onFilter">
        <el-option v-for="t in tenantOptions" :key="t.id" :label="`#${t.id} ${t.name}`" :value="t.id" />
      </el-select>
    </div>
    <el-table :data="list" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="tenant_id" label="租户" width="70" />
      <el-table-column prop="user_email" label="用户" min-width="140" />
      <el-table-column prop="exchange" label="交易所" width="90" />
      <el-table-column prop="account_type" label="类型" width="80" />
      <el-table-column prop="api_key" label="ApiKey" width="120">
        <template #default="{ row }">
          <el-text size="small">{{ row.api_key }}</el-text>
        </template>
      </el-table-column>
      <el-table-column label="余额" width="100">
        <template #default="{ row }">
          {{ row.balance.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="合约余额" width="100">
        <template #default="{ row }">
          {{ row.futures_balance.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="合约可用" width="100">
        <template #default="{ row }">
          {{ row.futures_available.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column prop="execution_node_id" label="节点" width="60">
        <template #default="{ row }">
          {{ row.execution_node_id ?? '本机' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
            {{ row.status === 1 ? '正常' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_sync_at" label="最后同步" width="170" />
    </el-table>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchData"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getExchangeAccounts, getTenants } from '../api'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const filterTenant = ref(null)
const tenantOptions = ref([])

async function fetchData() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filterTenant.value) params.tenant_id = filterTenant.value
    const res = await getExchangeAccounts(params)
    list.value = res.data
    total.value = res.total
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function onFilter() {
  page.value = 1
  fetchData()
}

async function loadTenants() {
  try {
    const res = await getTenants({ page: 1, page_size: 100 })
    tenantOptions.value = res.data
  } catch {}
}

onMounted(() => {
  loadTenants()
  fetchData()
})
</script>

<style scoped>
.toolbar { margin-bottom: 16px; display: flex; gap: 12px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
