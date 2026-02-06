<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>提现管理</span>
          <el-select v-model="statusFilter" placeholder="全部状态" clearable size="small" style="width:140px" @change="fetchData">
            <el-option label="待审核" :value="0" />
            <el-option label="已通过" :value="1" />
            <el-option label="已拒绝" :value="2" />
            <el-option label="已完成" :value="3" />
          </el-select>
        </div>
      </template>
      <el-table :data="list" v-loading="loading" border stripe style="width:100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="user_id" label="用户ID" width="80" />
        <el-table-column prop="amount" label="申请金额" width="120">
          <template #default="{ row }">{{ row.amount.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="fee" label="手续费" width="100">
          <template #default="{ row }">{{ row.fee.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="actual_amount" label="实到金额" width="120">
          <template #default="{ row }">{{ row.actual_amount.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="wallet_address" label="钱包地址" min-width="180" show-overflow-tooltip />
        <el-table-column prop="wallet_network" label="网络" width="80" />
        <el-table-column prop="status_text" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tx_hash" label="TxHash" width="140" show-overflow-tooltip />
        <el-table-column prop="reject_reason" label="拒绝原因" width="140" show-overflow-tooltip />
        <el-table-column prop="created_at" label="申请时间" width="160" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 0">
              <el-button type="success" size="small" @click="onApprove(row)">通过</el-button>
              <el-button type="danger" size="small" @click="onReject(row)">拒绝</el-button>
            </template>
            <template v-if="row.status === 1">
              <el-button type="primary" size="small" @click="onComplete(row)">标记完成</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        style="margin-top:16px;justify-content:flex-end"
        background
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        v-model:current-page="page"
        @current-change="fetchData"
      />
    </el-card>

    <!-- 拒绝弹窗 -->
    <el-dialog v-model="rejectVisible" title="拒绝提现" width="400px">
      <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="拒绝原因（可选）" />
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="danger" @click="doReject" :loading="rejecting">确认拒绝</el-button>
      </template>
    </el-dialog>

    <!-- 完成弹窗 -->
    <el-dialog v-model="completeVisible" title="标记打款完成" width="400px">
      <el-input v-model="txHash" placeholder="链上 TxHash（可选）" />
      <template #footer>
        <el-button @click="completeVisible = false">取消</el-button>
        <el-button type="primary" @click="doComplete" :loading="completing">确认完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getWithdrawals, approveWithdrawal, rejectWithdrawal, completeWithdrawal } from '../api'

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const statusFilter = ref(null)

// 拒绝
const rejectVisible = ref(false)
const rejectReason = ref('')
const rejecting = ref(false)
let rejectTarget = null

// 完成
const completeVisible = ref(false)
const txHash = ref('')
const completing = ref(false)
let completeTarget = null

function statusTagType(s) {
  return { 0: 'warning', 1: 'primary', 2: 'danger', 3: 'success' }[s] || 'info'
}

async function fetchData() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (statusFilter.value !== null && statusFilter.value !== '') params.status = statusFilter.value
    const res = await getWithdrawals(params)
    list.value = res.data || []
    total.value = res.total || 0
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function onApprove(row) {
  try {
    await ElMessageBox.confirm(`确认通过用户#${row.user_id}的提现申请（${row.amount} USDT）？`, '审核通过')
    await approveWithdrawal(row.id)
    ElMessage.success('已通过')
    fetchData()
  } catch {}
}

function onReject(row) {
  rejectTarget = row
  rejectReason.value = ''
  rejectVisible.value = true
}

async function doReject() {
  rejecting.value = true
  try {
    await rejectWithdrawal(rejectTarget.id, rejectReason.value)
    ElMessage.success('已拒绝，余额已退回')
    rejectVisible.value = false
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    rejecting.value = false
  }
}

function onComplete(row) {
  completeTarget = row
  txHash.value = ''
  completeVisible.value = true
}

async function doComplete() {
  completing.value = true
  try {
    await completeWithdrawal(completeTarget.id, txHash.value)
    ElMessage.success('已标记完成')
    completeVisible.value = false
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    completing.value = false
  }
}

onMounted(fetchData)
</script>
