<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="8" :md="8" :sm="12">
        <stat-card
          title="租户总数"
          :value="stats.totalTenants"
          icon="el-icon-office-building"
          color="primary"
          help-text="系统中的租户总数"
          :loading="statsLoading"/>
      </el-col>
      <el-col :lg="8" :md="8" :sm="12">
        <stat-card
          title="已启用租户"
          :value="stats.activeTenants"
          icon="el-icon-circle-check"
          color="success"
          help-text="状态为启用的租户数"
          :loading="statsLoading"/>
      </el-col>
      <el-col :lg="8" :md="8" :sm="12">
        <stat-card
          title="点卡余额总计"
          :value="stats.totalPointBalance"
          icon="el-icon-coin"
          color="warning"
          help-text="所有租户点卡余额之和（自购+赠送）"
          :loading="statsLoading"/>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <!-- 工具栏 -->
      <div class="toolbar">
        <el-button type="primary" size="small" icon="el-icon-plus" @click="openEditDialog()">新建租户</el-button>
        <el-button size="small" icon="el-icon-refresh" @click="fetchData">刷新</el-button>
        <div style="flex:1"></div>
        <el-input
          v-model="keyword"
          placeholder="搜索租户名称"
          clearable
          size="small"
          style="width:200px"
          @keyup.enter.native="fetchData"
          @clear="fetchData"/>
      </div>

      <!-- 主表格 -->
      <el-table
        v-loading="loading"
        :data="list"
        stripe
        border
        style="width:100%; margin-top:12px"
        size="small">
        <el-table-column prop="id" label="ID" width="60" align="center"/>
        <el-table-column prop="name" label="租户名称" min-width="130"/>
        <el-table-column label="AppKey" width="180">
          <template slot-scope="{row}">
            <span class="masked-key" @click="copyText(row.app_key, 'AppKey')">
              {{ maskKey(row.app_key) }}
              <i class="el-icon-document-copy copy-icon"></i>
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="point_card_self" label="自购点卡" width="100" align="right">
          <template slot-scope="{row}">
            <span>{{ formatNum(row.point_card_self) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="point_card_gift" label="赠送点卡" width="100" align="right">
          <template slot-scope="{row}">
            <span>{{ formatNum(row.point_card_gift) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_users" label="用户数" width="80" align="center"/>
        <el-table-column prop="tech_reward_total" label="技术累计" width="100" align="right">
          <template slot-scope="{row}">
            <span>{{ formatNum(row.tech_reward_total) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="undist_reward_total" label="未分配累计" width="110" align="right">
          <template slot-scope="{row}">
            <span>{{ formatNum(row.undist_reward_total) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="quota_plan_name" label="配额套餐" width="120">
          <template slot-scope="{row}">
            <span>{{ row.quota_plan_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="mini">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170"/>
        <el-table-column label="操作" width="280" fixed="right">
          <template slot-scope="{row}">
            <el-button size="mini" @click="openEditDialog(row)">编辑</el-button>
            <el-button
              size="mini"
              :type="row.status === 1 ? 'warning' : 'success'"
              @click="handleToggle(row)">
              {{ row.status === 1 ? '禁用' : '启用' }}
            </el-button>
            <el-button size="mini" type="primary" @click="openRechargeDialog(row)">充值</el-button>
            <el-button size="mini" type="info" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrap" v-if="total > 0">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          :page-size.sync="pageSize"
          :current-page.sync="page"
          @size-change="fetchData"
          @current-change="fetchData"/>
      </div>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog
      :title="editId ? '编辑租户' : '新建租户'"
      :visible.sync="editDialogVisible"
      width="480px"
      :close-on-click-modal="false">
      <el-form :model="editForm" :rules="editRules" ref="editForm" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="editForm.name" placeholder="请输入租户名称" maxlength="50" show-word-limit/>
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确定</el-button>
      </div>
    </el-dialog>

    <!-- 充值对话框 -->
    <el-dialog
      title="点卡充值"
      :visible.sync="rechargeDialogVisible"
      width="440px"
      :close-on-click-modal="false">
      <el-form :model="rechargeForm" :rules="rechargeRules" ref="rechargeForm" label-width="80px">
        <el-form-item label="租户">
          <span style="font-weight:600;">{{ rechargeTenantName }}</span>
        </el-form-item>
        <el-form-item label="类型" prop="card_type">
          <el-radio-group v-model="rechargeForm.card_type">
            <el-radio-button label="self">自购充值</el-radio-button>
            <el-radio-button label="gift">赠送充值</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="金额" prop="amount">
          <el-input-number
            v-model="rechargeForm.amount"
            :min="1"
            :max="999999"
            :precision="2"
            style="width:100%"/>
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="rechargeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="recharging" @click="handleRecharge">确认充值</el-button>
      </div>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog
      :title="detailData ? `租户详情 - ${detailData.name}` : '租户详情'"
      :visible.sync="detailVisible"
      width="960px"
      top="5vh"
      :close-on-click-modal="false"
      custom-class="tenant-detail-dialog">
      <div v-loading="detailLoading" class="detail-content">
        <!-- 基本信息 -->
        <div class="detail-section">
          <div class="section-title">基本信息</div>
          <el-row :gutter="20" v-if="detailData">
            <el-col :span="6">
              <div class="info-item">
                <span class="info-label">租户ID</span>
                <span class="info-value">{{ detailData.id }}</span>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="info-item">
                <span class="info-label">名称</span>
                <span class="info-value">{{ detailData.name }}</span>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="info-item">
                <span class="info-label">状态</span>
                <el-tag :type="detailData.status === 1 ? 'success' : 'info'" size="small">
                  {{ detailData.status === 1 ? '启用' : '禁用' }}
                </el-tag>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="info-item">
                <span class="info-label">创建时间</span>
                <span class="info-value" style="font-size:12px;">{{ detailData.created_at }}</span>
              </div>
            </el-col>
          </el-row>
          <el-row :gutter="20" v-if="detailData" style="margin-top:8px;">
            <el-col :span="12">
              <div class="info-item">
                <span class="info-label">AppKey</span>
                <span class="info-value" style="font-family:monospace;">{{ detailData.app_key }}</span>
                <el-button size="mini" type="text" icon="el-icon-document-copy" @click="copyText(detailData.app_key, 'AppKey')">复制</el-button>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="info-item">
                <span class="info-label">AppSecret</span>
                <span class="info-value" style="font-family:monospace;">
                  {{ showSecret ? detailData.app_secret : '********************************' }}
                </span>
                <el-button size="mini" type="text" :icon="showSecret ? 'el-icon-view' : 'el-icon-hide'" @click="showSecret = !showSecret">
                  {{ showSecret ? '隐藏' : '显示' }}
                </el-button>
                <el-button size="mini" type="text" icon="el-icon-document-copy" @click="copyText(detailData.app_secret, 'AppSecret')">复制</el-button>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 点卡余额 -->
        <div class="detail-section">
          <div class="section-title">
            点卡余额
            <el-button size="mini" type="primary" icon="el-icon-plus" style="float:right;" @click="openRechargeDialog(detailData)">充值</el-button>
          </div>
          <el-row :gutter="15" style="margin-top:15px;" v-if="detailData">
            <el-col :span="8">
              <div class="stat-box">
                <div class="stat-value">{{ formatNum(detailData.point_card_self) }}</div>
                <div class="stat-label">自购余额</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-box">
                <div class="stat-value">{{ formatNum(detailData.point_card_gift) }}</div>
                <div class="stat-label">赠送余额</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-box primary">
                <div class="stat-value">{{ formatNum(Number(detailData.point_card_self || 0) + Number(detailData.point_card_gift || 0)) }}</div>
                <div class="stat-label">总余额</div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 奖励分配 -->
        <div class="detail-section" v-if="detailData">
          <div class="section-title">奖励分配</div>
          <el-row :gutter="15" style="margin-top:15px;">
            <el-col :span="8">
              <div class="stat-box">
                <div class="stat-value">{{ formatNum(detailData.tech_reward_total) }}</div>
                <div class="stat-label">技术团队累计 (10%)</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-box">
                <div class="stat-value">{{ formatNum(detailData.undist_reward_total) }}</div>
                <div class="stat-label">网体未分配累计</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-box primary">
                <div class="stat-value">{{ formatNum(Number(detailData.tech_reward_total || 0) + Number(detailData.undist_reward_total || 0)) }}</div>
                <div class="stat-label">根账户累计收入</div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 根用户信息 -->
        <div class="detail-section" v-if="detailData">
          <div class="section-title">根用户信息</div>
          <template v-if="detailData.root_user_id">
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">Root用户ID</span>
                  <span class="info-value">{{ detailData.root_user_id }}</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">用户数</span>
                  <span class="info-value">{{ detailData.total_users || 0 }}</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">配额套餐</span>
                  <span class="info-value">{{ detailData.quota_plan_name || '-' }}</span>
                </div>
              </el-col>
            </el-row>
          </template>
          <el-empty v-else description="暂无根用户" :image-size="50"/>
        </div>

        <!-- 配额套餐分配 -->
        <div class="detail-section" v-if="detailData">
          <div class="section-title">配额套餐分配</div>
          <el-row :gutter="15" style="margin-top:10px;">
            <el-col :span="16">
              <el-select
                v-model="assignPlanId"
                placeholder="选择配额套餐"
                clearable
                size="small"
                style="width:100%;">
                <el-option
                  v-for="plan in quotaPlans"
                  :key="plan.id"
                  :label="plan.name"
                  :value="plan.id"/>
              </el-select>
            </el-col>
            <el-col :span="8">
              <el-button type="primary" size="small" :loading="assigning" @click="handleAssignPlan" :disabled="!assignPlanId">
                分配套餐
              </el-button>
            </el-col>
          </el-row>
        </div>

        <!-- 点卡流水 -->
        <div class="detail-section">
          <div class="section-title">点卡流水</div>
          <el-table :data="pointcardLogs" size="mini" border v-loading="logsLoading" max-height="260">
            <el-table-column prop="id" label="ID" width="60"/>
            <el-table-column prop="change_type" label="类型" width="90">
              <template slot-scope="{row}">
                <el-tag :type="logTagType(row.change_type)" size="mini">
                  {{ row.change_type_name || row.change_type || '-' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="金额" width="100">
              <template slot-scope="{row}">
                <span :style="{color: parseFloat(row.amount) >= 0 ? '#67c23a' : '#f56c6c', fontWeight: 600}">
                  {{ parseFloat(row.amount) >= 0 ? '+' : '' }}{{ row.amount }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="card_type" label="卡类型" width="80">
              <template slot-scope="{row}">
                {{ row.card_type === 'self' ? '自购' : row.card_type === 'gift' ? '赠送' : (row.card_type || '-') }}
              </template>
            </el-table-column>
            <el-table-column prop="after_balance" label="变动后余额" width="100"/>
            <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip/>
            <el-table-column prop="created_at" label="时间" width="160"/>
          </el-table>
          <el-pagination
            v-if="logsTotal > logsPageSize"
            style="margin-top:10px; text-align:right;"
            background
            small
            layout="total, prev, pager, next"
            :total="logsTotal"
            :page-size="logsPageSize"
            :current-page.sync="logsPage"
            @current-change="loadPointcardLogs"/>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import {
  getTenants,
  createTenant,
  updateTenant,
  toggleTenant,
  rechargeTenant,
  assignTenantPlan
} from '@/api/admin'
import {getQuotaPlans, getPointcardLogs} from '@/api/finance'

export default {
  name: 'TenantManage',
  data() {
    return {
      // 主列表
      loading: false,
      list: [],
      total: 0,
      page: 1,
      pageSize: 20,
      keyword: '',
      // 统计
      stats: {
        totalTenants: 0,
        activeTenants: 0,
        totalPointBalance: 0
      },
      statsLoading: false,
      // 新建/编辑
      editDialogVisible: false,
      editId: null,
      editForm: {name: ''},
      editRules: {
        name: [{required: true, message: '请输入租户名称', trigger: 'blur'}]
      },
      saving: false,
      // 充值
      rechargeDialogVisible: false,
      rechargeTenantId: null,
      rechargeTenantName: '',
      rechargeForm: {amount: 100, card_type: 'self'},
      rechargeRules: {
        amount: [{required: true, message: '请输入充值金额', trigger: 'blur'}],
        card_type: [{required: true, message: '请选择充值类型', trigger: 'change'}]
      },
      recharging: false,
      // 详情
      detailVisible: false,
      detailLoading: false,
      detailData: null,
      showSecret: false,
      // 配额套餐
      quotaPlans: [],
      assignPlanId: null,
      assigning: false,
      // 点卡流水
      pointcardLogs: [],
      logsLoading: false,
      logsPage: 1,
      logsPageSize: 10,
      logsTotal: 0
    }
  },
  mounted() {
    this.fetchData()
    this.loadQuotaPlans()
  },
  methods: {
    // ---- 主列表 ----
    async fetchData() {
      this.loading = true
      try {
        const params = {page: this.page, page_size: this.pageSize}
        if (this.keyword) params.keyword = this.keyword
        const res = await getTenants(params)
        const data = res.data.data
        this.list = Array.isArray(data) ? data : []
        this.total = res.data.total || 0
        this.computeStats()
      } catch (e) {
        this.$message.error('获取租户列表失败')
      } finally {
        this.loading = false
      }
    },
    computeStats() {
      const all = this.list
      this.stats.totalTenants = this.total
      this.stats.activeTenants = all.filter(t => t.status === 1).length
      this.stats.totalPointBalance = all.reduce((sum, t) => {
        return sum + Number(t.point_card_self || 0) + Number(t.point_card_gift || 0)
      }, 0).toFixed(2)
    },

    // ---- 新建/编辑 ----
    openEditDialog(row) {
      if (row) {
        this.editId = row.id
        this.editForm = {name: row.name}
      } else {
        this.editId = null
        this.editForm = {name: ''}
      }
      this.editDialogVisible = true
      this.$nextTick(() => {
        this.$refs.editForm && this.$refs.editForm.clearValidate()
      })
    },
    async handleSave() {
      try {
        await this.$refs.editForm.validate()
      } catch (e) {
        return
      }
      this.saving = true
      try {
        const payload = {name: this.editForm.name, status: 1}
        if (this.editId) {
          await updateTenant(this.editId, payload)
        } else {
          await createTenant(payload)
        }
        this.$message.success('保存成功')
        this.editDialogVisible = false
        this.fetchData()
      } catch (e) {
        const msg = e.response && e.response.data && e.response.data.detail
          ? e.response.data.detail
          : '保存失败'
        this.$message.error(msg)
      } finally {
        this.saving = false
      }
    },

    // ---- 切换状态 ----
    async handleToggle(row) {
      const action = row.status === 1 ? '禁用' : '启用'
      try {
        await this.$confirm(`确定要${action}租户「${row.name}」吗？`, '提示', {type: 'warning'})
      } catch (e) {
        return
      }
      try {
        await toggleTenant(row.id)
        this.$message.success(`${action}成功`)
        this.fetchData()
      } catch (e) {
        this.$message.error(`${action}失败`)
      }
    },

    // ---- 充值 ----
    openRechargeDialog(row) {
      if (!row) return
      this.rechargeTenantId = row.id
      this.rechargeTenantName = row.name
      this.rechargeForm = {amount: 100, card_type: 'self'}
      this.rechargeDialogVisible = true
      this.$nextTick(() => {
        this.$refs.rechargeForm && this.$refs.rechargeForm.clearValidate()
      })
    },
    async handleRecharge() {
      try {
        await this.$refs.rechargeForm.validate()
      } catch (e) {
        return
      }
      this.recharging = true
      try {
        await rechargeTenant(this.rechargeTenantId, {
          amount: this.rechargeForm.amount,
          card_type: this.rechargeForm.card_type
        })
        this.$message.success('充值成功')
        this.rechargeDialogVisible = false
        this.fetchData()
        // 如果详情面板打开，刷新详情
        if (this.detailVisible && this.detailData && this.detailData.id === this.rechargeTenantId) {
          this.refreshDetail()
        }
      } catch (e) {
        const msg = e.response && e.response.data && e.response.data.detail
          ? e.response.data.detail
          : '充值失败'
        this.$message.error(msg)
      } finally {
        this.recharging = false
      }
    },

    // ---- 详情 ----
    openDetail(row) {
      this.detailData = {...row}
      this.detailVisible = true
      this.showSecret = false
      this.assignPlanId = row.quota_plan_id || null
      this.logsPage = 1
      this.loadPointcardLogs()
    },
    async refreshDetail() {
      // 重新拉列表找到当前详情行的最新数据
      try {
        const params = {page: this.page, page_size: this.pageSize}
        if (this.keyword) params.keyword = this.keyword
        const res = await getTenants(params)
        const data = res.data.data
        this.list = Array.isArray(data) ? data : []
        this.total = res.data.total || 0
        this.computeStats()
        if (this.detailData) {
          const updated = this.list.find(t => t.id === this.detailData.id)
          if (updated) {
            this.detailData = {...updated}
          }
        }
      } catch (e) {
        // 静默处理
      }
      this.loadPointcardLogs()
    },

    // ---- 点卡流水 ----
    async loadPointcardLogs() {
      if (!this.detailData) return
      this.logsLoading = true
      try {
        const res = await getPointcardLogs({
          tenant_id: this.detailData.id,
          page: this.logsPage,
          page_size: this.logsPageSize
        })
        this.pointcardLogs = res.data.data || []
        this.logsTotal = res.data.total || 0
      } catch (e) {
        this.pointcardLogs = []
        this.logsTotal = 0
      } finally {
        this.logsLoading = false
      }
    },

    // ---- 配额套餐 ----
    async loadQuotaPlans() {
      try {
        const res = await getQuotaPlans()
        this.quotaPlans = res.data.data || []
      } catch (e) {
        this.quotaPlans = []
      }
    },
    async handleAssignPlan() {
      if (!this.assignPlanId || !this.detailData) return
      this.assigning = true
      try {
        await assignTenantPlan(this.detailData.id, this.assignPlanId)
        this.$message.success('套餐分配成功')
        this.refreshDetail()
      } catch (e) {
        const msg = e.response && e.response.data && e.response.data.detail
          ? e.response.data.detail
          : '分配失败'
        this.$message.error(msg)
      } finally {
        this.assigning = false
      }
    },

    // ---- 工具方法 ----
    maskKey(key) {
      if (!key) return '-'
      if (key.length <= 8) return key
      return key.substring(0, 4) + '****' + key.substring(key.length - 4)
    },
    formatNum(val) {
      const n = Number(val)
      if (isNaN(n)) return '0.00'
      return n.toFixed(2)
    },
    logTagType(type) {
      const map = {recharge: 'primary', gift: 'success', deduct: 'danger', refund: 'warning'}
      return map[type] || 'info'
    },
    copyText(text, label) {
      if (!text) return
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
          this.$message.success(`已复制${label}`)
        }).catch(() => {
          this.fallbackCopy(text, label)
        })
      } else {
        this.fallbackCopy(text, label)
      }
    },
    fallbackCopy(text, label) {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.left = '-9999px'
      document.body.appendChild(ta)
      ta.select()
      try {
        document.execCommand('copy')
        this.$message.success(`已复制${label}`)
      } catch (e) {
        this.$message.error('复制失败，请手动复制')
      }
      document.body.removeChild(ta)
    }
  }
}
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pagination-wrap {
  margin-top: 15px;
  text-align: right;
}
.masked-key {
  font-family: monospace;
  font-size: 13px;
  color: #606266;
  cursor: pointer;
  transition: color 0.2s;
}
.masked-key:hover {
  color: #409eff;
}
.masked-key .copy-icon {
  margin-left: 4px;
  font-size: 12px;
  color: #909399;
}
.masked-key:hover .copy-icon {
  color: #409eff;
}

/* 详情弹窗 */
.detail-content {
  max-height: 72vh;
  overflow-y: auto;
}
.detail-section {
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}
.detail-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 15px;
  padding-left: 10px;
  border-left: 3px solid #409eff;
  line-height: 1.4;
  overflow: hidden;
}
.info-item {
  margin-bottom: 12px;
}
.info-label {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.info-value {
  font-size: 14px;
  color: #303133;
}
.stat-box {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}
.stat-box.primary {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
}
.stat-box.primary .stat-value,
.stat-box.primary .stat-label {
  color: #fff;
}
.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  line-height: 1.2;
}
.stat-label {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}
</style>

<style>
.tenant-detail-dialog .el-dialog__body {
  padding: 15px 20px;
}
</style>
