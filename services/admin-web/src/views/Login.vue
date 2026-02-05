<template>
  <div class="login-wrap">
    <el-card class="login-card" shadow="hover">
      <template #header>
        <span>IronBull 管理后台</span>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="租户ID" prop="tenant_id">
          <el-input-number v-model="form.tenant_id" :min="1" controls-position="right" style="width:100%" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="登录邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" show-password @keyup.enter="onLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" style="width:100%" @click="onLogin">登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api, { login as apiLogin, setToken } from '../api'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const form = reactive({
  tenant_id: 1,
  email: '',
  password: '',
})
const rules = {
  tenant_id: [{ required: true, message: '请输入租户ID', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onLogin() {
  await formRef.value?.validate().catch(() => {})
  loading.value = true
  try {
    const res = await apiLogin(form.tenant_id, form.email, form.password)
    setToken(res.token, res.email)
    ElMessage.success('登录成功')
    router.replace('/')
  } catch (e) {
    const msg = e.response?.data?.detail || e.message || '登录失败'
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
}
.login-card {
  width: 380px;
}
</style>
