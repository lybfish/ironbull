<template>
  <div class="ele-body">
    <el-card shadow="never">
      <div class="toolbar">
        <span class="toolbar-label">选择租户：</span>
        <el-select
          v-model="tenantId"
          placeholder="请选择租户"
          clearable
          filterable
          size="small"
          style="width: 280px"
          @change="onTenantChange">
          <el-option
            v-for="t in tenantList"
            :key="t.id"
            :label="`${t.name || '租户#' + t.id} (ID: ${t.id})`"
            :value="t.id"/>
        </el-select>
        <el-button size="small" icon="el-icon-refresh" @click="fetchTenants" :loading="tenantLoading">刷新租户</el-button>
        <template v-if="tenantId">
          <el-button type="primary" size="small" icon="el-icon-plus" @click="openAdd" :loading="loading">新增实例</el-button>
          <el-button size="small" icon="el-icon-refresh" @click="fetchList" :loading="loading">刷新列表</el-button>
        </template>
        <div style="flex:1"></div>
      </div>

      <template v-if="tenantId">
        <el-table
          v-loading="loading"
          :data="list"
          stripe
          border
          style="width:100%; margin-top:12px"
          size="small">
          <el-table-column prop="id" label="实例ID" width="80" align="center"/>
          <el-table-column prop="strategy_code" label="主策略编码" width="100" show-overflow-tooltip/>
          <el-table-column prop="strategy_name" label="主策略名称" width="120" show-overflow-tooltip/>
          <el-table-column prop="display_name" label="展示名称" width="120" show-overflow-tooltip/>
          <el-table-column prop="display_description" label="展示描述" min-width="140" show-overflow-tooltip/>
          <el-table-column label="本金(U)" width="90" align="right">
            <template slot-scope="{row}">{{ row.capital > 0 ? row.capital : '继承' }}</template>
          </el-table-column>
          <el-table-column label="杠杆" width="75" align="center">
            <template slot-scope="{row}">
              <el-tag size="mini" type="warning" v-if="row.leverage != null">{{ row.leverage }}x</el-tag>
              <span v-else class="text-placeholder">继承</span>
            </template>
          </el-table-column>
          <el-table-column label="风险档位" width="80" align="center">
            <template slot-scope="{row}">
              <template v-if="row.risk_mode != null">
                <el-tag size="mini" :type="row.risk_mode === 3 ? 'danger' : row.risk_mode === 2 ? 'warning' : 'success'">
                  {{ {1:'稳健',2:'均衡',3:'激进'}[row.risk_mode] || '继承' }}
                </el-tag>
              </template>
              <span v-else class="text-placeholder">继承</span>
            </template>
          </el-table-column>
          <el-table-column label="单笔仓位/风控" width="140" align="right">
            <template slot-scope="{row}">
              <template v-if="row.risk_based_sizing">
                <div style="line-height:1.5">
                  <span style="color:#E6A23C;font-weight:500">以损定仓</span><br/>
                  <span style="font-size:11px;color:#909399">每笔最大亏损: {{ row.max_loss_per_trade }}U</span>
                </div>
              </template>
              <template v-else>
                <span>{{ row.amount_usdt > 0 ? row.amount_usdt + 'U' : '继承' }}</span>
              </template>
            </template>
          </el-table-column>
          <el-table-column prop="min_capital" label="最低资金" width="90" align="right">
            <template slot-scope="{row}">{{ row.min_capital != null ? row.min_capital : '继承' }}</template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="75" align="center">
            <template slot-scope="{row}">
              <el-tag :type="row.status === 1 ? 'success' : 'info'" size="mini">{{ row.status === 1 ? '启用' : '禁用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="sort_order" label="排序" width="70" align="center"/>
          <el-table-column label="操作" width="240" align="center" fixed="right">
            <template slot-scope="{row}">
              <el-button size="mini" type="text" icon="el-icon-edit" @click="openEdit(row)">编辑</el-button>
              <el-button size="mini" type="text" icon="el-icon-document-copy" @click="copyFromMaster(row)">复制主策略</el-button>
              <el-button size="mini" type="text" icon="el-icon-delete" class="ele-text-danger" @click="remove(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && list.length === 0" description="该租户下暂无策略实例">
          <el-button type="primary" size="small" @click="openAdd">新增实例</el-button>
        </el-empty>
      </template>
      <el-empty v-else description="请先选择租户"/>
    </el-card>

    <!-- 新增实例 -->
    <el-dialog title="新增策略实例" :visible.sync="addVisible" width="560px" :close-on-click-modal="false" @close="addForm = {}">
      <el-form ref="addFormRef" :model="addForm" :rules="addRules" label-width="120px" size="small" class="tenant-strategy-form">
        <el-form-item label="主策略" prop="strategy_id">
          <el-select
            v-model="addForm.strategy_id"
            placeholder="选择主策略"
            filterable
            style="width:100%"
            @change="onAddFormStrategyChange">
            <el-option
              v-for="s in masterStrategies"
              :key="s.id"
              :label="`${s.code} - ${s.name}`"
              :value="s.id"/>
          </el-select>
        </el-form-item>
        <el-form-item label=" " class="copy-option-item">
          <el-checkbox v-model="addForm.copy_from_master" @change="onCopyFromMasterChange">一键复制主策略参数</el-checkbox>
          <div class="form-item-hint">勾选后将自动带入：本金、杠杆、风险档位、最低资金、展示名与描述</div>
        </el-form-item>
        <el-form-item label="展示名称">
          <el-input v-model="addForm.display_name" placeholder="留空则用主策略名称"/>
        </el-form-item>
        <el-form-item label="展示描述">
          <el-input v-model="addForm.display_description" type="textarea" :rows="2" placeholder="留空则用主策略描述"/>
        </el-form-item>
        <el-form-item label="本金(USDT)">
          <el-input-number v-model="addForm.capital" :min="0" :precision="2" style="width:100%" placeholder="留空继承主策略"/>
        </el-form-item>
        <el-form-item label="杠杆">
          <el-select v-model="addForm.leverage" placeholder="留空继承主策略" clearable style="width:100%">
            <el-option :label="'5x'" :value="5"/>
            <el-option :label="'10x'" :value="10"/>
            <el-option :label="'20x'" :value="20"/>
            <el-option :label="'50x'" :value="50"/>
            <el-option :label="'75x'" :value="75"/>
            <el-option :label="'100x'" :value="100"/>
          </el-select>
        </el-form-item>
        <!-- 以损定仓: 每单最大亏损 -->
        <el-form-item v-if="addStrategyIsRiskBased" label="每单最大亏损(U)">
          <el-input-number v-model="addForm.max_loss_per_trade" :min="1" :step="5" :precision="2" style="width:200px"/>
          <div style="font-size:12px;color:#909399;margin-top:2px">
            <el-tag type="warning" size="mini">以损定仓</el-tag>
            实际仓位按止损距离自动调整
          </div>
        </el-form-item>
        <!-- 非以损定仓: 风险档位 + 金额 -->
        <template v-else>
          <el-form-item label="风险档位">
            <el-radio-group v-model="addForm.risk_mode">
              <el-radio-button :label="1">稳健(1%)</el-radio-button>
              <el-radio-button :label="2">均衡(1.5%)</el-radio-button>
              <el-radio-button :label="3">激进(2%)</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="addForm.capital > 0" label="下单金额(U)">
            <div style="line-height:32px;">
              <span style="font-size:16px;font-weight:600;color:#409EFF">{{ calcAddAmountUsdt }}</span>
              <span style="color:#909399;font-size:12px;margin-left:4px">USDT (自动计算)</span>
            </div>
          </el-form-item>
        </template>
        <el-form-item label="最低资金(USDT)">
          <el-input-number v-model="addForm.min_capital" :min="0" :precision="2" style="width:100%" placeholder="留空继承"/>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="addForm.status">
            <el-radio :label="1">启用</el-radio>
            <el-radio :label="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="addForm.sort_order" :min="0" style="width:100%"/>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button size="small" @click="addVisible = false">取消</el-button>
        <el-button size="small" type="primary" @click="submitAdd" :loading="addSaving">确定</el-button>
      </span>
    </el-dialog>

    <!-- 编辑实例 -->
    <el-dialog title="编辑策略实例" :visible.sync="editVisible" width="520px" :close-on-click-modal="false" @close="editForm = {}">
      <el-form ref="editFormRef" :model="editForm" label-width="120px" size="small">
        <el-form-item label="主策略">
          <span>{{ editForm.strategy_code }} - {{ editForm.strategy_name }}</span>
        </el-form-item>
        <el-form-item label="展示名称">
          <el-input v-model="editForm.display_name" placeholder="留空则用主策略名称"/>
        </el-form-item>
        <el-form-item label="展示描述">
          <el-input v-model="editForm.display_description" type="textarea" :rows="2" placeholder="留空则用主策略描述"/>
        </el-form-item>
        <el-form-item label="本金(USDT)">
          <el-input-number v-model="editForm.capital" :min="0" :precision="2" style="width:100%"/>
        </el-form-item>
        <el-form-item label="杠杆">
          <el-select v-model="editForm.leverage" placeholder="留空继承" clearable style="width:100%">
            <el-option :label="'5x'" :value="5"/>
            <el-option :label="'10x'" :value="10"/>
            <el-option :label="'20x'" :value="20"/>
            <el-option :label="'50x'" :value="50"/>
            <el-option :label="'75x'" :value="75"/>
            <el-option :label="'100x'" :value="100"/>
          </el-select>
        </el-form-item>
        <!-- 以损定仓: 每单最大亏损 -->
        <el-form-item v-if="editStrategyIsRiskBased" label="每单最大亏损(U)">
          <el-input-number v-model="editForm.max_loss_per_trade" :min="1" :step="5" :precision="2" style="width:200px"/>
          <div style="font-size:12px;color:#909399;margin-top:2px">
            <el-tag type="warning" size="mini">以损定仓</el-tag>
            实际仓位按止损距离自动调整
          </div>
        </el-form-item>
        <!-- 非以损定仓: 风险档位 + 金额 -->
        <template v-else>
          <el-form-item label="风险档位">
            <el-radio-group v-model="editForm.risk_mode">
              <el-radio-button :label="1">稳健(1%)</el-radio-button>
              <el-radio-button :label="2">均衡(1.5%)</el-radio-button>
              <el-radio-button :label="3">激进(2%)</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="editForm.capital > 0" label="下单金额(U)">
            <div style="line-height:32px;">
              <span style="font-size:16px;font-weight:600;color:#409EFF">{{ calcEditAmountUsdt }}</span>
              <span style="color:#909399;font-size:12px;margin-left:4px">USDT (自动计算)</span>
            </div>
          </el-form-item>
        </template>
        <el-form-item label="最低资金(USDT)">
          <el-input-number v-model="editForm.min_capital" :min="0" :precision="2" style="width:100%"/>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="editForm.status">
            <el-radio :label="1">启用</el-radio>
            <el-radio :label="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="editForm.sort_order" :min="0" style="width:100%"/>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button size="small" @click="editVisible = false">取消</el-button>
        <el-button size="small" type="primary" @click="submitEdit" :loading="editSaving">保存</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import {
  getTenants,
  getStrategies,
  getStrategyDetail,
  getTenantStrategies,
  createTenantStrategy,
  updateTenantStrategy,
  copyTenantStrategyFromMaster,
  deleteTenantStrategy
} from '@/api/admin'

export default {
  name: 'TenantStrategies',
  data() {
    return {
      tenantId: null,
      tenantList: [],
      tenantLoading: false,
      list: [],
      loading: false,
      masterStrategies: [],
      addVisible: false,
      addForm: {
        strategy_id: null,
        copy_from_master: true,
        display_name: '',
        display_description: '',
        capital: null,
        leverage: null,
        risk_mode: 1,
        max_loss_per_trade: 20,
        min_capital: null,
        status: 1,
        sort_order: 0
      },
      addRules: {
        strategy_id: [{ required: true, message: '请选择主策略', trigger: 'change' }]
      },
      addSaving: false,
      editVisible: false,
      editForm: {},
      editSaving: false
    }
  },
  computed: {
    addStrategyIsRiskBased() {
      if (!this.addForm.strategy_id) return false
      const s = this.masterStrategies.find(x => x.id === this.addForm.strategy_id)
      if (!s) return false
      const cfg = s.config || {}
      return !!cfg.risk_based_sizing
    },
    editStrategyIsRiskBased() {
      return !!this.editForm.risk_based_sizing
    },
    calcAddAmountUsdt() {
      const cap = Number(this.addForm.capital) || 0
      const lev = Number(this.addForm.leverage) || 20
      const mode = Number(this.addForm.risk_mode) || 1
      const pct = {1: 0.01, 2: 0.015, 3: 0.02}[mode] || 0.01
      return cap > 0 ? (cap * pct * lev).toFixed(2) : '0.00'
    },
    calcEditAmountUsdt() {
      const cap = Number(this.editForm.capital) || 0
      const lev = Number(this.editForm.leverage) || 20
      const mode = Number(this.editForm.risk_mode) || 1
      const pct = {1: 0.01, 2: 0.015, 3: 0.02}[mode] || 0.01
      return cap > 0 ? (cap * pct * lev).toFixed(2) : '0.00'
    },
  
  },
  mounted() {
    this.fetchTenants()
  },
  methods: {
    async fetchTenants() {
      this.tenantLoading = true
      try {
        const res = await getTenants({ page_size: 500 })
        const body = res.data || {}
        this.tenantList = body.data || []
        if (!Array.isArray(this.tenantList)) this.tenantList = []
      } catch (e) {
        this.$message.error((e.response && e.response.data && (e.response.data.detail || e.response.data.message)) || e.message || '获取租户列表失败')
      } finally {
        this.tenantLoading = false
      }
    },
    onTenantChange() {
      this.list = []
      if (this.tenantId) this.fetchList()
    },
    async fetchList() {
      if (!this.tenantId) return
      this.loading = true
      try {
        const res = await getTenantStrategies(this.tenantId, {})
        const body = res.data || {}
        this.list = body.data || []
        if (!Array.isArray(this.list)) this.list = []
      } catch (e) {
        this.$message.error((e.response && e.response.data && (e.response.data.detail || e.response.data.message)) || e.message || '获取列表失败')
      } finally {
        this.loading = false
      }
    },
    async loadMasterStrategies() {
      try {
        const res = await getStrategies({})
        const body = res.data || {}
        this.masterStrategies = body.data || []
        if (!Array.isArray(this.masterStrategies)) this.masterStrategies = []
      } catch {
        this.masterStrategies = []
      }
    },
    openAdd() {
      this.loadMasterStrategies()
      this.addForm = {
        strategy_id: null,
        copy_from_master: true,
        display_name: '',
        display_description: '',
        capital: null,
        leverage: null,
        risk_mode: 1,
        min_capital: null,
        status: 1,
        sort_order: 0
      }
      this.addVisible = true
    },
    async fillFormFromMasterStrategy() {
      if (!this.addForm.strategy_id || !this.addForm.copy_from_master) return
      try {
        const res = await getStrategyDetail(this.addForm.strategy_id)
        const body = res.data || {}
        const s = body.data || body
        if (!s) return
        this.addForm.display_name = (s.user_display_name || s.name || '').toString().trim() || ''
        this.addForm.display_description = (s.user_description || s.description || '').toString().trim() || ''
        this.addForm.capital = s.capital != null ? Number(s.capital) : null
        this.addForm.leverage = s.leverage != null ? Number(s.leverage) : null
        this.addForm.risk_mode = s.risk_mode != null ? Number(s.risk_mode) : 1
        this.addForm.max_loss_per_trade = s.max_loss_per_trade != null ? Number(s.max_loss_per_trade) : 20
        this.addForm.min_capital = s.min_capital != null ? Number(s.min_capital) : null
      } catch (e) {
        this.$message.warning('获取主策略参数失败，可手动填写或提交时由后端复制')
      }
    },
    onAddFormStrategyChange() {
      if (this.addForm.copy_from_master && this.addForm.strategy_id) {
        this.fillFormFromMasterStrategy()
      }
    },
    onCopyFromMasterChange(checked) {
      if (checked && this.addForm.strategy_id) {
        this.fillFormFromMasterStrategy()
      }
    },
    async submitAdd() {
      await this.$refs.addFormRef.validate().catch(() => { throw new Error('请填写必填项') })
      const payload = {
        strategy_id: this.addForm.strategy_id,
        copy_from_master: !!this.addForm.copy_from_master,
        status: this.addForm.status,
        sort_order: this.addForm.sort_order
      }
      if (this.addForm.display_name !== undefined && this.addForm.display_name !== '') payload.display_name = this.addForm.display_name
      if (this.addForm.display_description !== undefined && this.addForm.display_description !== '') payload.display_description = this.addForm.display_description
      if (this.addForm.capital != null && this.addForm.capital !== '') payload.capital = Number(this.addForm.capital)
      if (this.addForm.leverage != null && this.addForm.leverage !== '') payload.leverage = Number(this.addForm.leverage)
      if (this.addStrategyIsRiskBased) {
        if (this.addForm.max_loss_per_trade > 0) payload.max_loss_per_trade = Number(this.addForm.max_loss_per_trade)
      } else {
        if (this.addForm.risk_mode != null) payload.risk_mode = Number(this.addForm.risk_mode)
      }
      if (this.addForm.min_capital != null && this.addForm.min_capital !== '') payload.min_capital = Number(this.addForm.min_capital)
      this.addSaving = true
      try {
        await createTenantStrategy(this.tenantId, payload)
        this.$message.success('新增成功')
        this.addVisible = false
        this.fetchList()
      } catch (e) {
        const msg = (e.response && e.response.data && (e.response.data.detail || e.response.data.message)) || e.message || '新增失败'
        this.$message.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      } finally {
        this.addSaving = false
      }
    },
    openEdit(row) {
      this.editForm = {
        id: row.id,
        strategy_code: row.strategy_code,
        strategy_name: row.strategy_name,
        risk_based_sizing: !!row.risk_based_sizing,
        display_name: row.display_name || '',
        display_description: row.display_description || '',
        capital: row.capital != null ? Number(row.capital) : null,
        leverage: row.leverage != null ? Number(row.leverage) : null,
        risk_mode: row.risk_mode != null ? Number(row.risk_mode) : 1,
        max_loss_per_trade: row.max_loss_per_trade != null ? Number(row.max_loss_per_trade) : 20,
        min_capital: row.min_capital != null ? Number(row.min_capital) : null,
        status: row.status != null ? Number(row.status) : 1,
        sort_order: row.sort_order != null ? Number(row.sort_order) : 0
      }
      this.editVisible = true
    },
    async submitEdit() {
      if (!this.editForm.id) {
        this.$message.error('策略实例ID无效，请重新打开编辑')
        return
      }
      const payload = {
        display_name: this.editForm.display_name || null,
        display_description: this.editForm.display_description || null,
        capital: this.editForm.capital,
        leverage: this.editForm.leverage,
        min_capital: this.editForm.min_capital,
        status: this.editForm.status,
        sort_order: this.editForm.sort_order
      }
      if (this.editStrategyIsRiskBased) {
        payload.max_loss_per_trade = this.editForm.max_loss_per_trade > 0 ? this.editForm.max_loss_per_trade : null
      } else {
        payload.risk_mode = this.editForm.risk_mode
      }
      this.editSaving = true
      try {
        await updateTenantStrategy(this.tenantId, this.editForm.id, payload)
        this.$message.success('保存成功')
        this.editVisible = false
        this.fetchList()
      } catch (e) {
        const msg = (e.response && e.response.data && (e.response.data.detail || e.response.data.message)) || e.message || '保存失败'
        this.$message.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      } finally {
        this.editSaving = false
      }
    },
    async copyFromMaster(row) {
      if (!row.id) { this.$message.error('策略实例ID无效'); return }
      try {
        await this.$confirm('确定用主策略参数覆盖当前实例的杠杆、单笔金额、最低资金及展示名/描述？', '一键复制主策略', { type: 'warning' })
      } catch {
        return
      }
      try {
        await copyTenantStrategyFromMaster(this.tenantId, row.id)
        this.$message.success('已从主策略复制参数')
        this.fetchList()
      } catch (e) {
        const msg = (e.response && e.response.data && (e.response.data.detail || e.response.data.message)) || e.message || '复制失败'
        this.$message.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      }
    },
    async remove(row) {
      if (!row.id) { this.$message.error('策略实例ID无效'); return }
      try {
        await this.$confirm(`确定删除该租户下的策略实例「${row.display_name || row.strategy_name}」？`, '删除', { type: 'warning' })
      } catch {
        return
      }
      try {
        await deleteTenantStrategy(this.tenantId, row.id)
        this.$message.success('已删除')
        this.fetchList()
      } catch (e) {
        const msg = (e.response && e.response.data && (e.response.data.detail || e.response.data.message)) || e.message || '删除失败'
        this.$message.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      }
    }
  }
}
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.toolbar-label { font-size: 14px; color: #606266; }
.text-placeholder { color: #909399; font-size: 12px; }

.tenant-strategy-form .copy-option-item { margin-bottom: 8px; }
.tenant-strategy-form .copy-option-item >>> .el-form-item__content { line-height: 1.5; }
.tenant-strategy-form .form-item-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}
</style>
