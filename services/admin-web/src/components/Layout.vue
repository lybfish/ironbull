<template>
  <el-container class="layout">
    <el-aside width="200px" class="aside">
      <div class="logo">IronBull</div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard">概览</el-menu-item>
        <el-menu-item index="/orders">订单</el-menu-item>
        <el-menu-item index="/fills">成交</el-menu-item>
        <el-menu-item index="/positions">持仓</el-menu-item>
        <el-menu-item index="/accounts">资金账户</el-menu-item>
        <el-menu-item index="/transactions">流水</el-menu-item>
        <el-menu-item index="/analytics">绩效分析</el-menu-item>
        <el-menu-item index="/strategies">策略管理</el-menu-item>
        <el-menu-item index="/signal-monitor">信号监控</el-menu-item>
        <div class="menu-divider"></div>
        <el-menu-item index="/tenants">租户管理</el-menu-item>
        <el-menu-item index="/admins">管理员</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="title">{{ $route.meta.title || '管理后台' }}</span>
        <div class="header-right">
          <span class="user">{{ adminName }}</span>
          <el-button link type="danger" size="small" @click="onLogout">退出</el-button>
          <el-input-number v-model="tenantId" :min="1" size="small" controls-position="right" style="width:90px; margin-left:12px" @change="onTenantChange" />
          <span class="label">租户</span>
          <el-input-number v-model="accountId" :min="1" size="small" controls-position="right" style="width:90px; margin-left:8px" @change="onAccountChange" />
          <span class="label">账户</span>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { setTenantAccount, clearToken, getAdminName } from '../api'

const router = useRouter()
const tenantId = ref(1)
const accountId = ref(1)
const adminName = computed(() => getAdminName() || '管理员')

function onLogout() {
  clearToken()
  router.push('/login')
}

function applyParams() {
  setTenantAccount(tenantId.value, accountId.value)
}

function onTenantChange() {
  applyParams()
  window.location.reload()
}
function onAccountChange() {
  applyParams()
  window.location.reload()
}

onMounted(applyParams)
</script>

<style scoped>
.layout { height: 100vh; }
.aside { background: #304156; }
.logo { color: #fff; padding: 16px; font-weight: bold; text-align: center; }
.header {
  background: #fff;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}
.title { font-size: 18px; }
.header-right { display: flex; align-items: center; }
.header-right .user { color: #666; font-size: 12px; margin-right: 8px; }
.header-right .label { margin-left: 4px; color: #666; font-size: 12px; }
.main { background: #f0f2f5; padding: 16px; overflow: auto; }
.menu-divider { height: 1px; background: rgba(255,255,255,0.1); margin: 8px 16px; }
</style>
