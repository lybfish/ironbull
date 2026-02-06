<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="showCreate">新建管理员</el-button>
    </div>
    <el-table :data="list" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="nickname" label="昵称" min-width="120" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
            {{ row.status === 1 ? '正常' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_login_at" label="最后登录" width="170" />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="showEdit(row)">编辑</el-button>
          <el-button link type="warning" size="small" @click="showResetPwd(row)">重置密码</el-button>
          <el-button link :type="row.status === 1 ? 'danger' : 'success'" size="small" @click="onToggle(row)">
            {{ row.status === 1 ? '禁用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建对话框 -->
    <el-dialog v-model="createVisible" title="新建管理员" width="400px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="createForm.username" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="createForm.password" type="password" placeholder="登录密码" show-password />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="createForm.nickname" placeholder="显示昵称（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editVisible" title="编辑管理员" width="400px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="昵称">
          <el-input v-model="editForm.nickname" placeholder="显示昵称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="pwdVisible" title="重置密码" width="400px">
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.newPassword" type="password" placeholder="输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onResetPwd">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAdmins, createAdmin, updateAdmin, toggleAdmin, resetAdminPassword } from '../api'

const loading = ref(false)
const list = ref([])
const saving = ref(false)

const createVisible = ref(false)
const createForm = reactive({ username: '', password: '', nickname: '' })

const editVisible = ref(false)
const editId = ref(null)
const editForm = reactive({ nickname: '' })

const pwdVisible = ref(false)
const pwdId = ref(null)
const pwdForm = reactive({ newPassword: '' })

async function fetchData() {
  loading.value = true
  try {
    const res = await getAdmins()
    list.value = res.data
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function showCreate() {
  createForm.username = ''
  createForm.password = ''
  createForm.nickname = ''
  createVisible.value = true
}

async function onCreate() {
  if (!createForm.username.trim() || !createForm.password) {
    return ElMessage.warning('用户名和密码不能为空')
  }
  saving.value = true
  try {
    await createAdmin({
      username: createForm.username,
      password: createForm.password,
      nickname: createForm.nickname,
    })
    ElMessage.success('已创建')
    createVisible.value = false
    await fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    saving.value = false
  }
}

function showEdit(row) {
  editId.value = row.id
  editForm.nickname = row.nickname
  editVisible.value = true
}

async function onEdit() {
  saving.value = true
  try {
    await updateAdmin(editId.value, { nickname: editForm.nickname })
    ElMessage.success('已更新')
    editVisible.value = false
    await fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '更新失败')
  } finally {
    saving.value = false
  }
}

async function onToggle(row) {
  const action = row.status === 1 ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定${action}管理员「${row.username}」？`, '确认', { type: 'warning' })
    await toggleAdmin(row.id)
    ElMessage.success(`已${action}`)
    await fetchData()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e.response?.data?.detail || '操作失败')
    }
  }
}

function showResetPwd(row) {
  pwdId.value = row.id
  pwdForm.newPassword = ''
  pwdVisible.value = true
}

async function onResetPwd() {
  if (!pwdForm.newPassword) return ElMessage.warning('请输入新密码')
  saving.value = true
  try {
    await resetAdminPassword(pwdId.value, pwdForm.newPassword)
    ElMessage.success('密码已重置')
    pwdVisible.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重置失败')
  } finally {
    saving.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
</style>
