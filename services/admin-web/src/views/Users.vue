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
      <el-table-column prop="email" label="邮箱" min-width="160" />
      <el-table-column label="根用户" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.is_root" type="warning" size="small">根</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="invite_code" label="邀请码" width="100" />
      <el-table-column prop="inviter_id" label="邀请人" width="80">
        <template #default="{ row }">
          {{ row.inviter_id || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="member_level" label="等级" width="60" />
      <el-table-column label="点卡(自充/赠送)" width="150">
        <template #default="{ row }">
          {{ row.point_card_self.toFixed(2) }} / {{ row.point_card_gift.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="奖励(USDT)" width="100">
        <template #default="{ row }">
          {{ row.reward_usdt.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
            {{ row.status === 1 ? '正常' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="170" />
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
import { getUsers, getTenants } from '../api'

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
    const res = await getUsers(params)
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
