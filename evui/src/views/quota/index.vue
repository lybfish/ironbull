<template>
  <div class="ele-body">
    <el-card shadow="never">
      <div class="toolbar">
        <el-button type="primary" size="small" icon="el-icon-plus" @click="showDialog()">新建套餐</el-button>
        <el-button size="small" icon="el-icon-refresh" @click="fetchData" :loading="loading">刷新</el-button>
      </div>
      <el-table v-loading="loading" :data="list" stripe border style="width:100%; margin-top:12px" size="small"
        :header-cell-style="{background:'#fafafa'}">
        <el-table-column prop="id" label="ID" width="60" align="center"/>
        <el-table-column prop="name" label="套餐名称" width="150"/>
        <el-table-column prop="code" label="编码" width="120"/>
        <el-table-column prop="max_strategies" label="最大策略数" width="100" align="right"/>
        <el-table-column prop="api_calls_daily" label="日API调用" width="100" align="right"/>
        <el-table-column prop="api_calls_monthly" label="月API调用" width="100" align="right"/>
        <el-table-column prop="max_users" label="最大用户" width="90" align="right"/>
        <el-table-column prop="max_exchange_accounts" label="最大账户" width="90" align="right"/>
        <el-table-column prop="price_monthly" label="月费" width="100" align="right">
          <template slot-scope="{row}">{{ formatPrice(row.price_monthly) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="mini">{{ row.status === 1 ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template slot-scope="{row}">
            <el-button size="mini" @click="showDialog(row)">编辑</el-button>
            <el-button size="mini" :type="row.status === 1 ? 'warning' : 'success'" @click="handleToggle(row)">
              {{ row.status === 1 ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && list.length === 0" description="暂无套餐"/>
    </el-card>

    <el-dialog :title="editId ? '编辑套餐' : '新建套餐'" :visible.sync="dialogVisible" width="520px" :close-on-click-modal="false">
      <el-form ref="form" :model="form" :rules="rules" label-width="120px" size="small">
        <el-form-item label="套餐名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入套餐名称"/>
        </el-form-item>
        <el-form-item label="编码" prop="code" v-if="!editId">
          <el-input v-model="form.code" placeholder="唯一编码（如 basic / pro / enterprise）"/>
        </el-form-item>
        <el-form-item label="最大策略数" prop="max_strategies">
          <el-input-number v-model="form.max_strategies" :min="0" style="width:100%"/>
        </el-form-item>
        <el-form-item label="日API调用" prop="api_calls_daily">
          <el-input-number v-model="form.api_calls_daily" :min="0" style="width:100%"/>
        </el-form-item>
        <el-form-item label="月API调用" prop="api_calls_monthly">
          <el-input-number v-model="form.api_calls_monthly" :min="0" style="width:100%"/>
        </el-form-item>
        <el-form-item label="最大用户数" prop="max_users">
          <el-input-number v-model="form.max_users" :min="0" style="width:100%"/>
        </el-form-item>
        <el-form-item label="最大账户数" prop="max_exchange_accounts">
          <el-input-number v-model="form.max_exchange_accounts" :min="0" style="width:100%"/>
        </el-form-item>
        <el-form-item label="月费" prop="price_monthly">
          <el-input-number v-model="form.price_monthly" :min="0" :precision="2" style="width:100%"/>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="套餐描述"/>
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确定</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import {getQuotaPlans, createQuotaPlan, updateQuotaPlan, toggleQuotaPlan} from '@/api/finance'

export default {
  name: 'QuotaPlanManage',
  data() {
    return {
      loading: false, saving: false,
      list: [],
      dialogVisible: false, editId: null,
      form: {
        name: '', code: '',
        max_strategies: 5,
        api_calls_daily: 1000,
        api_calls_monthly: 30000,
        max_users: 100,
        max_exchange_accounts: 10,
        price_monthly: 0,
        description: ''
      },
      rules: {
        name: [{required: true, message: '请输入套餐名称', trigger: 'blur'}],
        code: [{required: true, message: '请输入编码', trigger: 'blur'}]
      }
    }
  },
  mounted() { this.fetchData() },
  methods: {
    formatPrice(v) { return v != null ? Number(v).toFixed(2) : '0.00' },
    showDialog(row) {
      if (row) {
        this.editId = row.id
        this.form = {
          name: row.name, code: row.code || '',
          max_strategies: row.max_strategies || 0,
          api_calls_daily: row.api_calls_daily || 0,
          api_calls_monthly: row.api_calls_monthly || 0,
          max_users: row.max_users || 0,
          max_exchange_accounts: row.max_exchange_accounts || 0,
          price_monthly: row.price_monthly || 0,
          description: row.description || ''
        }
      } else {
        this.editId = null
        this.form = {name: '', code: '', max_strategies: 5, api_calls_daily: 1000, api_calls_monthly: 30000, max_users: 100, max_exchange_accounts: 10, price_monthly: 0, description: ''}
      }
      this.dialogVisible = true
      this.$nextTick(() => { this.$refs.form && this.$refs.form.clearValidate() })
    },
    async fetchData() {
      this.loading = true
      try {
        const res = await getQuotaPlans()
        this.list = res.data.data || []
      } catch (e) {
        this.$message.error('获取套餐失败')
      } finally { this.loading = false }
    },
    async handleSave() {
      try { await this.$refs.form.validate() } catch (e) { return }
      this.saving = true
      try {
        if (this.editId) {
          const {code, ...updates} = this.form
          await updateQuotaPlan(this.editId, updates)
        } else {
          await createQuotaPlan(this.form)
        }
        this.$message.success('保存成功')
        this.dialogVisible = false
        this.fetchData()
      } catch (e) {
        this.$message.error(e.response?.data?.detail || '保存失败')
      } finally { this.saving = false }
    },
    async handleToggle(row) {
      try {
        await toggleQuotaPlan(row.id)
        this.$message.success('操作成功')
        this.fetchData()
      } catch (e) { this.$message.error('操作失败') }
    }
  }
}
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 8px; }
</style>
