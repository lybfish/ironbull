<template>
  <div>
    <div class="toolbar">
      <el-select v-model="filterTenant" placeholder="全部租户" clearable style="width:160px" @change="onFilter">
        <el-option v-for="t in tenantOptions" :key="t.id" :label="`#${t.id} ${t.name}`" :value="t.id" />
      </el-select>
    </div>
    <el-table :data="list" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="user_id" label="用户ID" width="80" />
      <el-table-column prop="user_email" label="用户邮箱" min-width="150" />
      <el-table-column prop="account_id" label="账户ID" width="80" />
      <el-table-column prop="strategy_code" label="策略" min-width="120" />
      <el-table-column label="模式" width="80">
        <template #default="{ row }">
          {{ row.mode === 1 ? '通知' : row.mode === 2 ? '自动' : row.mode }}
        </template>
      </el-table-column>
      <el-table-column prop="ratio" label="比例%" width="70" />
      <el-table-column label="累计盈亏" width="100">
        <template #default="{ row }">
          <span :style="{ color: row.total_profit >= 0 ? '#67C23A' : '#F56C6C' }">
            {{ row.total_profit.toFixed(2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="total_trades" label="交易次数" width="90" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ row.status === 1 ? '运行中' : '已停' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170" />
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
import { getBindingsAdmin, getTenants } from '../api'

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
    const res = await getBindingsAdmin(params)
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
