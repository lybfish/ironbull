<template>
  <div class="login-wrap">
    <el-card class="login-card" shadow="hover">
      <template #header>
        <span>IronBull 管理后台</span>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="管理员用户名" />
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
import { login as apiLogin, setToken } from '../api'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const form = reactive({
  username: '',
  password: '',
})
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onLogin() {
  await formRef.value?.validate().catch(() => {})
  loading.value = true
  try {
    const res = await apiLogin(form.username, form.password)
    setToken(res.token, res.nickname)
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
