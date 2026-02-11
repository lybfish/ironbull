<template>
  <div class="ele-body">
    <el-card shadow="never">
      <!-- 标题与操作 -->
      <div class="toolbar">
        <span class="toolbar-title">策略绑定</span>
        <div>
          <el-button size="small" type="primary" icon="el-icon-plus" @click="openCreate">新增绑定</el-button>
          <el-button size="small" icon="el-icon-refresh" :loading="loading" @click="fetchData">刷新</el-button>
        </div>
      </div>

      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-form :inline="true" size="small">
          <el-form-item label="租户ID">
            <el-input v-model.number="where.tenant_id" placeholder="租户ID" clearable style="width:100px" @keyup.enter.native="onSearch"/>
          </el-form-item>
          <el-form-item label="用户ID">
            <el-input v-model.number="where.user_id" placeholder="用户ID" clearable style="width:100px" @keyup.enter.native="onSearch"/>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="where.status" placeholder="全部" clearable style="width:100px">
              <el-option label="运行" :value="1"/>
              <el-option label="停止" :value="0"/>
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" icon="el-icon-search" @click="onSearch">查询</el-button>
            <el-button icon="el-icon-refresh-left" @click="resetSearch">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table v-loading="loading" :data="list" stripe border style="width:100%; margin-top:12px" size="small"
        :header-cell-style="{background:'#fafafa'}">
        <el-table-column prop="id" label="ID" width="55" align="center"/>
        <el-table-column prop="tenant_name" label="租户" width="100" show-overflow-tooltip/>
        <el-table-column prop="user_email" label="用户" min-width="140" show-overflow-tooltip/>
        <el-table-column prop="strategy_name" label="策略" width="140" show-overflow-tooltip/>
        <el-table-column label="交易所" width="85" align="center">
          <template slot-scope="{row}">
            <el-tag size="mini" effect="plain">{{ (row.exchange || '').toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="exchange_account_label" label="交易所账户" width="130" show-overflow-tooltip/>
        <el-table-column prop="mode" label="模式" width="70" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.mode === 2 ? 'warning' : 'info'" size="mini">{{ row.mode === 2 ? '循环' : '单次' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="本金" width="80" align="right">
          <template slot-scope="{row}">
            <span v-if="row.capital > 0">{{ formatNum(row.capital) }}</span>
            <span v-else style="color:#909399">-</span>
          </template>
        </el-table-column>
        <el-table-column label="杠杆" width="55" align="center">
          <template slot-scope="{row}">{{ row.leverage || 20 }}X</template>
        </el-table-column>
        <el-table-column label="仓位/风控" width="140" align="right">
          <template slot-scope="{row}">
            <template v-if="row.risk_based_sizing">
              <div style="line-height:1.5">
                <el-tag type="warning" size="mini">以损定仓</el-tag><br/>
                <span style="font-size:11px;color:#E6A23C">每笔亏损≤{{ row.max_loss_per_trade }}U</span>
              </div>
            </template>
            <template v-else>
              <div style="line-height:1.5">
                <span v-if="row.amount_usdt > 0">{{ formatNum(row.amount_usdt) }}U</span>
                <span v-else style="color:#909399">-</span>
                <br v-if="row.risk_mode_label"/>
                <span style="font-size:11px;color:#909399">{{ row.risk_mode_label }}</span>
              </div>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="累计盈亏" width="100" align="right">
          <template slot-scope="{row}">
            <span :class="Number(row.total_profit || 0) >= 0 ? 'text-success' : 'text-danger'">
              {{ Number(row.total_profit || 0) >= 0 ? '+' : '' }}{{ formatNum(row.total_profit) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="笔数" width="55" align="center">
          <template slot-scope="{row}">{{ row.total_trades || 0 }}</template>
        </el-table-column>
        <el-table-column label="状态" width="65" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="mini" effect="dark">{{ row.status === 1 ? '运行' : '停止' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="140">
          <template slot-scope="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center" fixed="right">
          <template slot-scope="{row}">
            <el-button type="text" size="mini" icon="el-icon-view" @click="showDetail(row)">详情</el-button>
            <el-button type="text" size="mini" icon="el-icon-edit" @click="showEdit(row)">编辑</el-button>
            <el-button v-if="row.status === 0" type="text" size="mini" icon="el-icon-delete" style="color:#F56C6C" @click="handleDeleteBinding(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && list.length === 0" description="暂无策略绑定"/>
      <div v-if="total > 0" style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center;">
        <span class="tip">共 {{ total }} 条</span>
        <el-pagination background :current-page.sync="page" :page-size="pageSize" :total="total"
          layout="prev, pager, next" @current-change="fetchData"/>
      </div>
    </el-card>

    <!-- ==================== 详情弹窗 ==================== -->
    <el-dialog title="绑定详情" :visible.sync="detailVisible" width="560px" append-to-body>
      <el-descriptions v-if="detailRow" :column="1" border size="small">
        <el-descriptions-item label="绑定ID">{{ detailRow.id }}</el-descriptions-item>
        <el-descriptions-item label="租户">{{ detailRow.tenant_name || '-' }} (ID: {{ detailRow.tenant_id || '-' }})</el-descriptions-item>
        <el-descriptions-item label="用户">{{ detailRow.user_email || '-' }} (ID: {{ detailRow.user_id }})</el-descriptions-item>
        <el-descriptions-item label="策略">{{ detailRow.strategy_name || detailRow.strategy_code }}</el-descriptions-item>
        <el-descriptions-item label="交易所账户">{{ detailRow.exchange_account_label || '-' }} (ID: {{ detailRow.account_id }})</el-descriptions-item>
        <el-descriptions-item label="执行模式">{{ detailRow.mode === 2 ? '循环执行' : '单次执行' }}</el-descriptions-item>
        <el-descriptions-item label="本金">{{ detailRow.capital > 0 ? formatNum(detailRow.capital) + ' USDT' : '未设置' }}</el-descriptions-item>
        <el-descriptions-item label="杠杆">{{ detailRow.leverage || 20 }}X</el-descriptions-item>
        <el-descriptions-item label="仓位模式">
          <template v-if="detailRow.risk_based_sizing">
            <el-tag type="warning" size="small">以损定仓</el-tag>
            <span style="color:#909399;font-size:12px;margin-left:4px">每笔最大亏损 {{ detailRow.max_loss_per_trade }} USDT，仓位按止损距离自动调整</span>
          </template>
          <template v-else>
            {{ detailRow.amount_usdt > 0 ? formatNum(detailRow.amount_usdt) + ' USDT' : '-' }}
            <span v-if="detailRow.risk_mode_label" style="color:#909399;font-size:12px;margin-left:4px">({{ detailRow.risk_mode_label }})</span>
          </template>
        </el-descriptions-item>
        <el-descriptions-item label="累计盈亏">{{ formatNum(detailRow.total_profit) }}</el-descriptions-item>
        <el-descriptions-item label="交易笔数">{{ detailRow.total_trades || 0 }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="detailRow.status === 1 ? 'success' : 'info'" size="small">{{ detailRow.status === 1 ? '运行' : '停止' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="绑定时间">{{ formatTime(detailRow.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <div slot="footer">
        <el-button @click="detailVisible = false">关闭</el-button>
      </div>
    </el-dialog>

    <!-- ==================== 新增绑定弹窗 ==================== -->
    <el-dialog title="新增策略绑定" :visible.sync="createVisible" width="560px" append-to-body @open="loadFormOptions">
      <el-form ref="createForm" :model="createForm" label-width="110px" size="small" :rules="createRules">
        <!-- 用户 -->
        <el-form-item label="用户" prop="user_id">
          <el-select v-model="createForm.user_id" filterable placeholder="选择用户" style="width:100%"
            @change="onCreateUserChange">
            <el-option v-for="u in formOptions.users" :key="u.id"
              :label="`${u.email} (ID:${u.id}) ${u.tenant_name}`" :value="u.id"/>
          </el-select>
        </el-form-item>
        <!-- 交易所账户 -->
        <el-form-item label="交易所账户" prop="account_id">
          <el-select v-model="createForm.account_id" filterable placeholder="选择账户" style="width:100%">
            <el-option v-for="a in createUserAccounts" :key="a.id"
              :label="`${a.label} (ID:${a.id})`" :value="a.id"/>
          </el-select>
        </el-form-item>
        <!-- 策略 -->
        <el-form-item label="策略" prop="strategy_code">
          <el-select v-model="createForm.strategy_code" filterable placeholder="选择策略" style="width:100%"
            @change="onCreateStrategyChange">
            <el-option v-for="s in formOptions.strategies" :key="s.code"
              :label="`${s.name} (${s.code})`" :value="s.code"/>
          </el-select>
        </el-form-item>
        <!-- 执行模式 -->
        <el-form-item label="执行模式">
          <el-radio-group v-model="createForm.mode">
            <el-radio-button :label="2">循环执行</el-radio-button>
            <el-radio-button :label="1">单次执行</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <!-- 本金 -->
        <el-form-item label="本金 (USDT)">
          <el-input-number v-model="createForm.capital" :min="0" :step="100" :precision="2" style="width:200px"/>
        </el-form-item>
        <!-- 杠杆 -->
        <el-form-item label="杠杆">
          <el-select v-model="createForm.leverage" style="width:200px">
            <el-option v-for="l in leverageOptions" :key="l" :label="l+'X'" :value="l"/>
          </el-select>
        </el-form-item>
        <!-- 以损定仓策略: 每单最大亏损 -->
        <el-form-item v-if="createSelectedIsRiskBased" label="每单最大亏损">
          <el-input-number v-model="createForm.max_loss_per_trade" :min="1" :step="5" :precision="2" style="width:200px"/>
          <span style="color:#909399;font-size:12px;margin-left:8px">USDT</span>
        </el-form-item>
        <!-- 非以损定仓: 风险档位 -->
        <el-form-item v-else label="风险档位">
          <el-radio-group v-model="createForm.risk_mode">
            <el-radio-button :label="1">稳健 (1%)</el-radio-button>
            <el-radio-button :label="2">均衡 (1.5%)</el-radio-button>
            <el-radio-button :label="3">激进 (2%)</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <!-- 状态 -->
        <el-form-item label="状态">
          <el-switch v-model="createForm.status" :active-value="1" :inactive-value="0" active-text="运行" inactive-text="停止"/>
        </el-form-item>
        <!-- 预估 -->
        <el-form-item label="预估">
          <div class="preview-box">
            <template v-if="createSelectedIsRiskBased">
              <div>每笔最大亏损: <b style="color:#E6A23C">{{ createForm.max_loss_per_trade || 0 }} USDT</b>
                <el-tag type="warning" size="mini" style="margin-left:4px">以损定仓</el-tag>
              </div>
              <div style="color:#909399;font-size:12px">实际仓位按止损距离自动调整</div>
            </template>
            <template v-else>
              <div>单笔保证金: <b>{{ calcCreateMargin }} USDT</b></div>
              <div>单笔仓位: <b>{{ calcCreateAmount }} USDT</b></div>
              <div style="color:#909399;font-size:12px">= 本金 × {{ createRiskPctLabel }} × {{ createForm.leverage }}倍杠杆</div>
            </template>
          </div>
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="submitCreate">创建</el-button>
      </div>
    </el-dialog>

    <!-- ==================== 编辑绑定弹窗 ==================== -->
    <el-dialog title="编辑绑定参数" :visible.sync="editVisible" width="520px" append-to-body>
      <el-form v-if="editForm" label-width="110px" size="small">
        <el-form-item label="用户">
          <span>{{ editForm._user_email }} (ID: {{ editForm._user_id }})</span>
        </el-form-item>
        <el-form-item label="策略">
          <span>{{ editForm._strategy_name }}</span>
        </el-form-item>
        <!-- 执行模式 -->
        <el-form-item label="执行模式">
          <el-radio-group v-model="editForm.mode">
            <el-radio-button :label="2">循环执行</el-radio-button>
            <el-radio-button :label="1">单次执行</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <!-- 本金 -->
        <el-form-item label="本金 (USDT)">
          <el-input-number v-model="editForm.capital" :min="0" :step="100" :precision="2" style="width:200px"/>
        </el-form-item>
        <!-- 杠杆 -->
        <el-form-item label="杠杆">
          <el-select v-model="editForm.leverage" style="width:200px">
            <el-option v-for="l in leverageOptions" :key="l" :label="l+'X'" :value="l"/>
          </el-select>
        </el-form-item>
        <!-- 以损定仓: 每单最大亏损 -->
        <el-form-item v-if="editForm._risk_based_sizing" label="每单最大亏损">
          <el-input-number v-model="editForm.max_loss_per_trade" :min="1" :step="5" :precision="2" style="width:200px"/>
          <span style="color:#909399;font-size:12px;margin-left:8px">USDT</span>
        </el-form-item>
        <!-- 非以损定仓: 风险档位 -->
        <el-form-item v-else label="风险档位">
          <el-radio-group v-model="editForm.risk_mode">
            <el-radio-button :label="1">稳健 (1%)</el-radio-button>
            <el-radio-button :label="2">均衡 (1.5%)</el-radio-button>
            <el-radio-button :label="3">激进 (2%)</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <!-- 状态 -->
        <el-form-item label="状态">
          <el-switch v-model="editForm.status" :active-value="1" :inactive-value="0" active-text="运行" inactive-text="停止"/>
        </el-form-item>
        <!-- 预估 -->
        <el-form-item label="预估">
          <div class="preview-box">
            <template v-if="editForm._risk_based_sizing">
              <div>每笔最大亏损: <b style="color:#E6A23C">{{ editForm.max_loss_per_trade || 0 }} USDT</b>
                <el-tag type="warning" size="mini" style="margin-left:4px">以损定仓</el-tag>
              </div>
              <div style="color:#909399;font-size:12px">实际仓位按止损距离自动调整</div>
            </template>
            <template v-else>
              <div>单笔保证金: <b>{{ calcEditMargin }} USDT</b></div>
              <div>单笔仓位: <b>{{ calcEditAmount }} USDT</b></div>
            </template>
          </div>
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="submitEdit">保存</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import {getBindingsAdmin, getBindingFormOptions, createBinding, updateBinding, deleteBinding} from '@/api/admin'

const RISK_PCT_MAP = {1: 0.01, 2: 0.015, 3: 0.02}
const RISK_PCT_LABELS = {1: '1%', 2: '1.5%', 3: '2%'}

export default {
  name: 'StrategyBindings',
  data() {
    return {
      loading: false,
      list: [],
      total: 0,
      page: 1,
      pageSize: 20,
      where: { tenant_id: null, user_id: null, status: null },
      leverageOptions: [3, 5, 10, 15, 20, 25, 50, 75, 100],
      // 详情
      detailVisible: false,
      detailRow: null,
      // 新增
      createVisible: false,
      createLoading: false,
      formOptions: { strategies: [], users: [], accounts: [] },
      createForm: {
        user_id: null,
        account_id: null,
        strategy_code: '',
        mode: 2,
        capital: 200,
        leverage: 20,
        risk_mode: 1,
        max_loss_per_trade: 20,
        status: 1,
      },
      createRules: {
        user_id: [{ required: true, message: '请选择用户', trigger: 'change' }],
        account_id: [{ required: true, message: '请选择交易所账户', trigger: 'change' }],
        strategy_code: [{ required: true, message: '请选择策略', trigger: 'change' }],
      },
      // 编辑
      editVisible: false,
      editLoading: false,
      editForm: null,
      editBindingId: null,
    }
  },
  computed: {
    // ── 新增表单计算 ──
    createSelectedStrategy() {
      return this.formOptions.strategies.find(s => s.code === this.createForm.strategy_code) || null
    },
    createSelectedIsRiskBased() {
      return this.createSelectedStrategy && this.createSelectedStrategy.risk_based_sizing
    },
    createUserAccounts() {
      if (!this.createForm.user_id) return this.formOptions.accounts
      return this.formOptions.accounts.filter(a => a.user_id === this.createForm.user_id)
    },
    createRiskPctLabel() {
      return RISK_PCT_LABELS[this.createForm.risk_mode] || '1%'
    },
    calcCreateMargin() {
      const cap = Number(this.createForm.capital) || 0
      const pct = RISK_PCT_MAP[this.createForm.risk_mode] || 0.01
      return (cap * pct).toFixed(2)
    },
    calcCreateAmount() {
      const cap = Number(this.createForm.capital) || 0
      const lev = Number(this.createForm.leverage) || 20
      const pct = RISK_PCT_MAP[this.createForm.risk_mode] || 0.01
      return (cap * pct * lev).toFixed(2)
    },
    // ── 编辑表单计算 ──
    calcEditMargin() {
      if (!this.editForm) return '0.00'
      const pct = RISK_PCT_MAP[this.editForm.risk_mode] || 0.01
      return (Number(this.editForm.capital || 0) * pct).toFixed(2)
    },
    calcEditAmount() {
      if (!this.editForm) return '0.00'
      const pct = RISK_PCT_MAP[this.editForm.risk_mode] || 0.01
      return (Number(this.editForm.capital || 0) * pct * (this.editForm.leverage || 20)).toFixed(2)
    },
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    formatNum(v) {
      return v !== null && v !== undefined ? parseFloat(v).toFixed(2) : '0.00'
    },
    formatTime(t) {
      return t ? t.replace('T', ' ').substring(0, 19) : '-'
    },
    onSearch() {
      this.page = 1
      this.fetchData()
    },
    resetSearch() {
      this.where = { tenant_id: null, user_id: null, status: null }
      this.page = 1
      this.fetchData()
    },
    // ── 列表 ──
    async fetchData() {
      this.loading = true
      try {
        const params = { page: this.page, page_size: this.pageSize }
        if (this.where.tenant_id != null && this.where.tenant_id !== '') params.tenant_id = Number(this.where.tenant_id)
        if (this.where.user_id != null && this.where.user_id !== '') params.user_id = Number(this.where.user_id)
        if (this.where.status !== null && this.where.status !== '') params.status = Number(this.where.status)
        const res = await getBindingsAdmin(params)
        const data = res.data
        this.list = data.data || data || []
        this.total = data.total != null ? data.total : this.list.length
      } catch (e) {
        this.$message.error(e.response?.data?.detail || '获取策略绑定失败')
      } finally {
        this.loading = false
      }
    },
    // ── 详情 ──
    showDetail(row) {
      this.detailRow = row
      this.detailVisible = true
    },
    // ── 新增 ──
    async loadFormOptions() {
      if (this.formOptions.strategies.length > 0) return
      try {
        const res = await getBindingFormOptions()
        if (res.data.success) {
          this.formOptions = res.data.data
        }
      } catch (e) {
        this.$message.error('加载表单选项失败')
      }
    },
    openCreate() {
      this.createForm = {
        user_id: null, account_id: null, strategy_code: '',
        mode: 2, capital: 200, leverage: 20, risk_mode: 1, max_loss_per_trade: 20, status: 1,
      }
      this.createVisible = true
    },
    onCreateUserChange() {
      this.createForm.account_id = null
      // 自动选第一个该用户的账户
      const accs = this.createUserAccounts
      if (accs.length === 1) this.createForm.account_id = accs[0].id
    },
    onCreateStrategyChange() {
      const s = this.createSelectedStrategy
      if (s) {
        if (s.leverage) this.createForm.leverage = s.leverage
        if (s.capital > 0) this.createForm.capital = s.capital
        if (s.max_loss_per_trade > 0) this.createForm.max_loss_per_trade = s.max_loss_per_trade
        if (s.risk_mode) this.createForm.risk_mode = s.risk_mode
      }
    },
    async submitCreate() {
      this.$refs.createForm.validate(async (valid) => {
        if (!valid) return
        this.createLoading = true
        try {
          const data = {
            user_id: this.createForm.user_id,
            account_id: this.createForm.account_id,
            strategy_code: this.createForm.strategy_code,
            mode: this.createForm.mode,
            capital: this.createForm.capital,
            leverage: this.createForm.leverage,
            status: this.createForm.status,
          }
          if (this.createSelectedIsRiskBased) {
            data.max_loss_per_trade = this.createForm.max_loss_per_trade
          } else {
            data.risk_mode = this.createForm.risk_mode
          }
          const res = await createBinding(data)
          if (res.data.success) {
            this.$message.success(res.data.message || '创建成功')
            this.createVisible = false
            this.fetchData()
          } else {
            this.$message.error(res.data.message || '创建失败')
          }
        } catch (e) {
          this.$message.error(e.response?.data?.message || e.response?.data?.detail || '创建失败')
        } finally {
          this.createLoading = false
        }
      })
    },
    // ── 编辑 ──
    showEdit(row) {
      this.editBindingId = row.id
      this.editForm = {
        _user_email: row.user_email,
        _user_id: row.user_id,
        _strategy_name: row.strategy_name || row.strategy_code,
        _risk_based_sizing: !!row.risk_based_sizing,
        mode: row.mode || 2,
        capital: row.capital || 0,
        leverage: row.leverage || 20,
        risk_mode: row.risk_mode || 1,
        max_loss_per_trade: row.max_loss_per_trade || 0,
        status: row.status,
      }
      this.editVisible = true
    },
    async submitEdit() {
      if (!this.editBindingId) return
      this.editLoading = true
      try {
        const data = {
          mode: this.editForm.mode,
          status: this.editForm.status,
        }
        if (this.editForm.capital > 0) data.capital = this.editForm.capital
        if (this.editForm.leverage > 0) data.leverage = this.editForm.leverage
        if (this.editForm._risk_based_sizing) {
          data.max_loss_per_trade = this.editForm.max_loss_per_trade
        } else {
          if (this.editForm.risk_mode) data.risk_mode = this.editForm.risk_mode
        }
        const res = await updateBinding(this.editBindingId, data)
        const d = res.data
        if (d.success) {
          this.$message.success(d.message || '修改成功')
          this.editVisible = false
          this.fetchData()
        } else {
          this.$message.error(d.message || '修改失败')
        }
      } catch (e) {
        this.$message.error(e.response?.data?.message || '修改失败')
      } finally {
        this.editLoading = false
      }
    },
    // ── 删除 ──
    async handleDeleteBinding(row) {
      try {
        await this.$confirm(
          `确定要删除绑定 #${row.id}（用户: ${row.user_email}，策略: ${row.strategy_name}）吗？`,
          '删除确认',
          { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'error' }
        )
      } catch { return }
      try {
        const res = await deleteBinding(row.id)
        if (res.data.success) {
          this.$message.success('删除成功')
          this.fetchData()
        } else {
          this.$message.error(res.data.message || '删除失败')
        }
      } catch (e) {
        this.$message.error(e.response?.data?.message || e.response?.data?.detail || '删除失败')
      }
    },
  },
}
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.toolbar-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}
.search-bar { margin-bottom: 8px; }
.tip { color: #909399; font-size: 12px; }
.text-success { color: #67C23A; }
.text-danger { color: #F56C6C; }
.preview-box {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 13px;
  line-height: 1.8;
}
</style>
