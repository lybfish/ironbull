<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2 style="margin:0">套餐管理</h2>
      <el-button type="primary" @click="showCreate">新建套餐</el-button>
    </div>

    <el-table :data="plans" v-loading="loading" stripe border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="套餐名称" width="120" />
      <el-table-column prop="code" label="编码" width="100" />
      <el-table-column label="API 限额">
        <template #default="{ row }">
          <div>日: {{ row.api_calls_daily || '不限' }}</div>
          <div>月: {{ row.api_calls_monthly || '不限' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="资源限额">
        <template #default="{ row }">
          <div>用户: {{ row.max_users || '不限' }}</div>
          <div>策略: {{ row.max_strategies || '不限' }}</div>
          <div>账户: {{ row.max_exchange_accounts || '不限' }}</div>
        </template>
      </el-table-column>
      <el-table-column label="月费" width="80">
        <template #default="{ row }">{{ row.price_monthly > 0 ? `¥${row.price_monthly}` : '免费' }}</template>
      </el-table-column>
      <el-table-column prop="description" label="说明" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
            {{ row.status === 1 ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button size="small" @click="showEdit(row)">编辑</el-button>
          <el-button size="small" :type="row.status === 1 ? 'danger' : 'success'" @click="handleToggle(row)">
            {{ row.status === 1 ? '停用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建/编辑对话框 -->
    <el-dialog :title="editingPlan ? '编辑套餐' : '新建套餐'" v-model="dialogVisible" width="540px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="套餐名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="编码" required v-if="!editingPlan">
          <el-input v-model="form.code" placeholder="如 free/basic/pro" />
        </el-form-item>
        <el-form-item label="每日 API 限额">
          <el-input-number v-model="form.api_calls_daily" :min="0" />
          <span style="margin-left:8px;color:#999">0=不限</span>
        </el-form-item>
        <el-form-item label="每月 API 限额">
          <el-input-number v-model="form.api_calls_monthly" :min="0" />
          <span style="margin-left:8px;color:#999">0=不限</span>
        </el-form-item>
        <el-form-item label="最大用户数">
          <el-input-number v-model="form.max_users" :min="0" />
        </el-form-item>
        <el-form-item label="最大策略数">
          <el-input-number v-model="form.max_strategies" :min="0" />
        </el-form-item>
        <el-form-item label="最大账户数">
          <el-input-number v-model="form.max_exchange_accounts" :min="0" />
        </el-form-item>
        <el-form-item label="月费 (¥)">
          <el-input-number v-model="form.price_monthly" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getQuotaPlans, createQuotaPlan, updateQuotaPlan, toggleQuotaPlan } from '../api'

const plans = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const editingPlan = ref(null)

const defaultForm = {
  name: '', code: '', api_calls_daily: 0, api_calls_monthly: 0,
  max_users: 0, max_strategies: 0, max_exchange_accounts: 0,
  price_monthly: 0, description: '', sort_order: 0,
}
const form = ref({ ...defaultForm })

async function load() {
  loading.value = true
  try {
    const res = await getQuotaPlans()
    plans.value = res.data || []
  } catch (e) {
    ElMessage.error('加载套餐失败')
  } finally {
    loading.value = false
  }
}

function showCreate() {
  editingPlan.value = null
  form.value = { ...defaultForm }
  dialogVisible.value = true
}

function showEdit(row) {
  editingPlan.value = row
  form.value = {
    name: row.name, code: row.code,
    api_calls_daily: row.api_calls_daily, api_calls_monthly: row.api_calls_monthly,
    max_users: row.max_users, max_strategies: row.max_strategies,
    max_exchange_accounts: row.max_exchange_accounts,
    price_monthly: row.price_monthly, description: row.description,
    sort_order: row.sort_order,
  }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editingPlan.value) {
      const { code, ...rest } = form.value
      await updateQuotaPlan(editingPlan.value.id, rest)
      ElMessage.success('更新成功')
    } else {
      await createQuotaPlan(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleToggle(row) {
  try {
    await toggleQuotaPlan(row.id)
    ElMessage.success(row.status === 1 ? '已停用' : '已启用')
    await load()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

onMounted(load)
</script>
