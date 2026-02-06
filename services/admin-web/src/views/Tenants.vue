<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="showCreate">新建租户</el-button>
    </div>
    <el-table :data="list" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="app_key" label="AppKey" min-width="180">
        <template #default="{ row }">
          <el-text size="small" truncated>{{ row.app_key }}</el-text>
        </template>
      </el-table-column>
      <el-table-column label="点卡(自充/赠送)" width="160">
        <template #default="{ row }">
          {{ row.point_card_self.toFixed(2) }} / {{ row.point_card_gift.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column prop="total_users" label="用户数" width="80" />
      <el-table-column label="套餐" width="130">
        <template #default="{ row }">
          <el-tag v-if="row.quota_plan_name" size="small" type="info">{{ row.quota_plan_name }}</el-tag>
          <el-text v-else size="small" type="warning">未分配</el-text>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
            {{ row.status === 1 ? '正常' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="showEdit(row)">编辑</el-button>
          <el-button link :type="row.status === 1 ? 'danger' : 'success'" size="small" @click="onToggle(row)">
            {{ row.status === 1 ? '禁用' : '启用' }}
          </el-button>
          <el-button link type="success" size="small" @click="showRecharge(row)">充值</el-button>
          <el-button link type="warning" size="small" @click="showAssignPlan(row)">套餐</el-button>
          <el-button link type="info" size="small" @click="showSecret(row)">密钥</el-button>
        </template>
      </el-table-column>
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

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editId ? '编辑租户' : '新建租户'" width="400px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="租户名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 密钥对话框 -->
    <el-dialog v-model="secretVisible" title="API 密钥" width="480px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="AppKey">{{ secretData.app_key }}</el-descriptions-item>
        <el-descriptions-item label="AppSecret">{{ secretData.app_secret }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="secretVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 充值对话框 -->
    <el-dialog v-model="rechargeVisible" title="充值点卡" width="400px">
      <el-form :model="rechargeForm" label-width="80px">
        <el-form-item label="租户">
          <el-text>{{ rechargeName }}</el-text>
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="rechargeForm.cardType">
            <el-radio value="self">自充点卡</el-radio>
            <el-radio value="gift">赠送点卡</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number v-model="rechargeForm.amount" :min="0.01" :precision="2" :step="100" style="width:200px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rechargeVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onRecharge">确认充值</el-button>
      </template>
    </el-dialog>
    <!-- 分配套餐对话框 -->
    <el-dialog v-model="planVisible" title="分配套餐" width="400px">
      <el-form label-width="80px">
        <el-form-item label="租户">
          <el-text>{{ planTenantName }}</el-text>
        </el-form-item>
        <el-form-item label="套餐">
          <el-select v-model="planForm.planId" placeholder="选择套餐" style="width:100%">
            <el-option v-for="p in planOptions" :key="p.id" :label="`${p.name} (${p.code})`" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="planVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onAssignPlan">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTenants, createTenant, updateTenant, toggleTenant, rechargeTenant, getQuotaPlans, assignTenantPlan } from '../api'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const dialogVisible = ref(false)
const editId = ref(null)
const form = reactive({ name: '' })
const saving = ref(false)

const secretVisible = ref(false)
const secretData = reactive({ app_key: '', app_secret: '' })

async function fetchData() {
  loading.value = true
  try {
    const res = await getTenants({ page: page.value, page_size: pageSize })
    list.value = res.data
    total.value = res.total
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function showCreate() {
  editId.value = null
  form.name = ''
  dialogVisible.value = true
}

function showEdit(row) {
  editId.value = row.id
  form.name = row.name
  dialogVisible.value = true
}

async function onSave() {
  if (!form.name.trim()) return ElMessage.warning('请输入名称')
  saving.value = true
  try {
    if (editId.value) {
      await updateTenant(editId.value, { name: form.name })
      ElMessage.success('已更新')
    } else {
      await createTenant({ name: form.name })
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    await fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function onToggle(row) {
  const action = row.status === 1 ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定${action}租户「${row.name}」？`, '确认', { type: 'warning' })
    await toggleTenant(row.id)
    ElMessage.success(`已${action}`)
    await fetchData()
  } catch {}
}

function showSecret(row) {
  secretData.app_key = row.app_key
  secretData.app_secret = row.app_secret
  secretVisible.value = true
}

const rechargeVisible = ref(false)
const rechargeId = ref(null)
const rechargeName = ref('')
const rechargeForm = reactive({ amount: 100, cardType: 'self' })

function showRecharge(row) {
  rechargeId.value = row.id
  rechargeName.value = row.name
  rechargeForm.amount = 100
  rechargeForm.cardType = 'self'
  rechargeVisible.value = true
}

async function onRecharge() {
  if (rechargeForm.amount <= 0) return ElMessage.warning('金额必须大于0')
  saving.value = true
  try {
    await rechargeTenant(rechargeId.value, rechargeForm.amount, rechargeForm.cardType)
    ElMessage.success('充值成功')
    rechargeVisible.value = false
    await fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '充值失败')
  } finally {
    saving.value = false
  }
}

// ---- 套餐分配 ----
const planVisible = ref(false)
const planTenantId = ref(null)
const planTenantName = ref('')
const planForm = reactive({ planId: null })
const planOptions = ref([])

async function loadPlans() {
  try {
    const res = await getQuotaPlans()
    planOptions.value = (res.data || []).filter(p => p.status === 1)
  } catch {}
}

function showAssignPlan(row) {
  planTenantId.value = row.id
  planTenantName.value = row.name
  planForm.planId = row.quota_plan_id
  planVisible.value = true
}

async function onAssignPlan() {
  if (!planForm.planId) return ElMessage.warning('请选择套餐')
  saving.value = true
  try {
    await assignTenantPlan(planTenantId.value, planForm.planId)
    ElMessage.success('套餐分配成功')
    planVisible.value = false
    await fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '分配失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => { fetchData(); loadPlans() })
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
