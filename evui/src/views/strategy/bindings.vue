<template>
  <div class="ele-body">
    <el-card shadow="never">
      <!-- 标题与刷新 -->
      <div class="toolbar">
        <span class="toolbar-title">策略绑定</span>
        <el-button size="small" icon="el-icon-refresh" :loading="loading" @click="fetchData">刷新</el-button>
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
        <el-table-column prop="id" label="ID" width="60" align="center"/>
        <el-table-column prop="tenant_name" label="租户" width="120" show-overflow-tooltip/>
        <el-table-column prop="user_email" label="用户" min-width="150" show-overflow-tooltip/>
        <el-table-column prop="strategy_name" label="策略" width="150" show-overflow-tooltip/>
        <el-table-column label="交易所" width="90" align="center">
          <template slot-scope="{row}">
            <el-tag size="mini" effect="plain">{{ (row.exchange || '').toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="exchange_account_label" label="交易所账户" width="140" show-overflow-tooltip/>
        <el-table-column prop="mode" label="执行模式" width="90" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.mode === 2 ? 'warning' : 'info'" size="mini">{{ row.mode === 2 ? '循环' : '单次' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="跟单比例" width="80" align="center">
          <template slot-scope="{row}">
            <span>{{ row.ratio || 100 }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="本金" width="90" align="right">
          <template slot-scope="{row}">
            <span v-if="row.capital > 0">{{ formatNum(row.capital) }}</span>
            <span v-else style="color:#909399">-</span>
          </template>
        </el-table-column>
        <el-table-column label="杠杆" width="65" align="center">
          <template slot-scope="{row}">
            <span>{{ row.leverage || 20 }}X</span>
          </template>
        </el-table-column>
        <el-table-column label="风险档位" width="85" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.risk_mode === 3 ? 'danger' : row.risk_mode === 2 ? 'warning' : 'success'" size="mini">
              {{ row.risk_mode_label || '稳健' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="单笔仓位" width="100" align="right">
          <template slot-scope="{row}">
            <span v-if="row.amount_usdt > 0">{{ formatNum(row.amount_usdt) }}</span>
            <span v-else style="color:#909399">-</span>
          </template>
        </el-table-column>
        <el-table-column label="累计盈亏" width="110" align="right">
          <template slot-scope="{row}">
            <span :class="Number(row.total_profit || 0) >= 0 ? 'text-success' : 'text-danger'">
              {{ Number(row.total_profit || 0) >= 0 ? '+' : '' }}{{ formatNum(row.total_profit) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="成交笔数" width="80" align="center">
          <template slot-scope="{row}">
            <span>{{ row.total_trades || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="点卡" width="110" align="center">
          <template slot-scope="{row}">
            <div style="font-size:12px">自充: {{ formatNum(row.point_card_self) }}</div>
            <div style="font-size:12px; color:#909399">赠送: {{ formatNum(row.point_card_gift) }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="70" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="mini" effect="dark">{{ row.status === 1 ? '运行' : '停止' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="绑定时间" width="160">
          <template slot-scope="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" align="center" fixed="right">
          <template slot-scope="{row}">
            <el-button type="text" size="mini" icon="el-icon-view" @click="showDetail(row)">详情</el-button>
            <el-button type="text" size="mini" icon="el-icon-edit" @click="showEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && list.length === 0" description="暂无策略绑定"/>
      <div v-if="total > 0" style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center;">
        <span class="tip">共 {{ total }} 条</span>
        <el-pagination
          background
          :current-page.sync="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="fetchData"/>
      </div>
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog title="绑定详情" :visible.sync="detailVisible" width="560px" append-to-body>
      <el-descriptions v-if="detailRow" :column="1" border size="small">
        <el-descriptions-item label="绑定ID">{{ detailRow.id }}</el-descriptions-item>
        <el-descriptions-item label="租户">{{ detailRow.tenant_name || '-' }} (ID: {{ detailRow.tenant_id || '-' }})</el-descriptions-item>
        <el-descriptions-item label="用户">{{ detailRow.user_email || '-' }} (ID: {{ detailRow.user_id }})</el-descriptions-item>
        <el-descriptions-item label="策略">{{ detailRow.strategy_name || detailRow.strategy_code }} ({{ detailRow.strategy_code }})</el-descriptions-item>
        <el-descriptions-item label="交易所账户">{{ detailRow.exchange_account_label || '-' }} (账户ID: {{ detailRow.account_id }})</el-descriptions-item>
        <el-descriptions-item label="执行模式">{{ detailRow.mode === 2 ? '循环执行' : '单次执行' }}</el-descriptions-item>
        <el-descriptions-item label="跟单比例">{{ detailRow.ratio || 100 }}%</el-descriptions-item>
        <el-descriptions-item label="本金">{{ detailRow.capital > 0 ? formatNum(detailRow.capital) + ' USDT' : '未设置' }}</el-descriptions-item>
        <el-descriptions-item label="杠杆">{{ detailRow.leverage || 20 }}X</el-descriptions-item>
        <el-descriptions-item label="风险档位">{{ detailRow.risk_mode_label || '稳健' }}（{{ detailRow.risk_mode === 3 ? '2%' : detailRow.risk_mode === 2 ? '1.5%' : '1%' }}）</el-descriptions-item>
        <el-descriptions-item label="单笔保证金">{{ detailRow.margin_per_trade > 0 ? formatNum(detailRow.margin_per_trade) + ' USDT' : '-' }}</el-descriptions-item>
        <el-descriptions-item label="单笔仓位">{{ detailRow.amount_usdt > 0 ? formatNum(detailRow.amount_usdt) + ' USDT' : '-' }}</el-descriptions-item>
        <el-descriptions-item label="交易所">{{ (detailRow.exchange || '').toUpperCase() }}</el-descriptions-item>
        <el-descriptions-item label="点卡（自充/赠送）">{{ formatNum(detailRow.point_card_self) }} / {{ formatNum(detailRow.point_card_gift) }}</el-descriptions-item>
        <el-descriptions-item label="累计盈亏">{{ formatNum(detailRow.total_profit) }}</el-descriptions-item>
        <el-descriptions-item label="交易笔数">{{ detailRow.total_trades || 0 }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="detailRow.status === 1 ? 'success' : 'info'" size="small">{{ detailRow.status === 1 ? '运行' : '停止' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="绑定时间">{{ formatTime(detailRow.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <div slot="footer">
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="goToUser">前往用户管理</el-button>
      </div>
    </el-dialog>

    <!-- 编辑弹窗 -->
    <el-dialog title="编辑绑定参数" :visible.sync="editVisible" width="480px" append-to-body>
      <el-form v-if="editForm" label-width="100px" size="small">
        <el-form-item label="用户">
          <span>{{ editForm._user_email }} (ID: {{ editForm._user_id }})</span>
        </el-form-item>
        <el-form-item label="策略">
          <span>{{ editForm._strategy_name }}</span>
        </el-form-item>
        <el-form-item label="本金 (USDT)">
          <el-input-number v-model="editForm.capital" :min="0" :step="100" :precision="2" style="width:200px"/>
        </el-form-item>
        <el-form-item label="杠杆">
          <el-select v-model="editForm.leverage" style="width:200px">
            <el-option :label="'5X'" :value="5"/>
            <el-option :label="'10X'" :value="10"/>
            <el-option :label="'20X'" :value="20"/>
            <el-option :label="'50X'" :value="50"/>
            <el-option :label="'75X'" :value="75"/>
            <el-option :label="'100X'" :value="100"/>
          </el-select>
        </el-form-item>
        <el-form-item label="风险档位">
          <el-radio-group v-model="editForm.risk_mode">
            <el-radio-button :label="1">稳健 (1%)</el-radio-button>
            <el-radio-button :label="2">均衡 (1.5%)</el-radio-button>
            <el-radio-button :label="3">激进 (2%)</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="editForm.status" :active-value="1" :inactive-value="0" active-text="运行" inactive-text="停止"/>
        </el-form-item>
        <el-form-item label="预估">
          <div class="preview-box">
            <div>单笔保证金: <b>{{ calcMargin }} USDT</b></div>
            <div>单笔仓位: <b>{{ calcAmount }} USDT</b></div>
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
import {getBindingsAdmin, updateBinding} from '@/api/admin'

const RISK_PCT_MAP = {1: 0.01, 2: 0.015, 3: 0.02}

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
      detailVisible: false,
      detailRow: null,
      editVisible: false,
      editLoading: false,
      editForm: null,
      editBindingId: null,
    }
  },
  computed: {
    calcMargin() {
      if (!this.editForm || !this.editForm.capital) return '0.00'
      const pct = RISK_PCT_MAP[this.editForm.risk_mode] || 0.01
      return (this.editForm.capital * pct).toFixed(2)
    },
    calcAmount() {
      if (!this.editForm || !this.editForm.capital) return '0.00'
      const pct = RISK_PCT_MAP[this.editForm.risk_mode] || 0.01
      return (this.editForm.capital * pct * (this.editForm.leverage || 20)).toFixed(2)
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
    showDetail(row) {
      this.detailRow = row
      this.detailVisible = true
    },
    showEdit(row) {
      this.editBindingId = row.id
      this.editForm = {
        _user_email: row.user_email,
        _user_id: row.user_id,
        _strategy_name: row.strategy_name || row.strategy_code,
        capital: row.capital || 0,
        leverage: row.leverage || 20,
        risk_mode: row.risk_mode || 1,
        status: row.status,
      }
      this.editVisible = true
    },
    async submitEdit() {
      if (!this.editBindingId) return
      this.editLoading = true
      try {
        const data = {}
        if (this.editForm.capital > 0) data.capital = this.editForm.capital
        if (this.editForm.leverage > 0) data.leverage = this.editForm.leverage
        if (this.editForm.risk_mode) data.risk_mode = this.editForm.risk_mode
        data.status = this.editForm.status
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
    goToUser() {
      if (!this.detailRow || !this.detailRow.user_id) return
      this.detailVisible = false
      this.$router.push({ path: '/operation/users', query: { user_id: this.detailRow.user_id } })
    },
    async fetchData() {
      this.loading = true
      try {
        const params = { page: this.page, page_size: this.pageSize }
        if (this.where.tenant_id != null && this.where.tenant_id !== '') {
          params.tenant_id = Number(this.where.tenant_id)
        }
        if (this.where.user_id != null && this.where.user_id !== '') {
          params.user_id = Number(this.where.user_id)
        }
        if (this.where.status !== null && this.where.status !== '') {
          params.status = Number(this.where.status)
        }
        const res = await getBindingsAdmin(params)
        const data = res.data
        this.list = data.data || data || []
        this.total = data.total != null ? data.total : this.list.length
      } catch (e) {
        this.$message.error(e.response?.data?.detail || '获取策略绑定失败')
      } finally {
        this.loading = false
      }
    }
  }
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
