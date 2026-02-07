<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="6" :md="12" :sm="12">
        <stat-card
          title="待审核"
          :value="stats.pendingCount"
          icon="el-icon-bell"
          color="warning"
          help-text="当前待审核的提现申请数"
          :loading="loading" />
      </el-col>
      <el-col :lg="6" :md="12" :sm="12">
        <stat-card
          title="待打款"
          :value="stats.approvedCount"
          icon="el-icon-wallet"
          color="primary"
          help-text="已审核通过待打款的提现数"
          :loading="loading" />
      </el-col>
      <el-col :lg="6" :md="12" :sm="12">
        <stat-card
          title="累计提现"
          :value="stats.totalAmount"
          icon="el-icon-money"
          color="success"
          format="money"
          :precision="2"
          help-text="所有提现申请的累计金额"
          :loading="loading">
          <template slot="value">
            ${{ formatMoney(stats.totalAmount) }}
          </template>
        </stat-card>
      </el-col>
      <el-col :lg="6" :md="12" :sm="12">
        <stat-card
          title="累计服务费"
          :value="stats.totalFee"
          icon="el-icon-coin"
          color="danger"
          format="money"
          :precision="2"
          help-text="所有提现扣除的服务费总计"
          :loading="loading">
          <template slot="value">
            ${{ formatMoney(stats.totalFee) }}
          </template>
        </stat-card>
      </el-col>
    </el-row>

    <!-- 搜索表单 + 表格 -->
    <el-card shadow="never">
      <div class="toolbar">
        <el-select
          v-model="query.status"
          placeholder="提现状态"
          clearable
          size="small"
          style="width: 140px"
          @change="handleSearch">
          <el-option label="全部" value="" />
          <el-option label="待审核" :value="0" />
          <el-option label="已通过" :value="1" />
          <el-option label="已拒绝" :value="2" />
          <el-option label="已完成" :value="3" />
        </el-select>
        <el-input
          v-model="query.user_id"
          placeholder="用户ID"
          clearable
          size="small"
          style="width: 100px; margin-left: 8px"
          @clear="handleSearch" />
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="yyyy-MM-dd"
          size="small"
          style="width: 280px; margin-left: 8px"
          @change="handleSearch" />
        <el-button
          type="primary"
          size="small"
          icon="el-icon-search"
          style="margin-left: 8px"
          @click="handleSearch">
          查询
        </el-button>
        <el-button
          size="small"
          icon="el-icon-refresh"
          @click="handleReset">
          重置
        </el-button>
        <el-button
          size="small"
          icon="el-icon-download"
          type="success"
          plain
          :disabled="list.length === 0"
          @click="exportCSV">
          导出CSV
        </el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="list"
        stripe
        border
        style="width: 100%; margin-top: 12px"
        size="small"
        row-key="id">
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="user_id" label="用户ID" width="80" align="center" />
        <el-table-column label="用户邮箱" width="180">
          <template slot-scope="{ row }">
            <span v-if="row.user_email" style="font-size: 12px">{{ row.user_email }}</span>
            <span v-else style="color: #C0C4CC">-</span>
          </template>
        </el-table-column>
        <el-table-column label="提现金额" width="120" align="right">
          <template slot-scope="{ row }">
            <span style="font-weight: 600">${{ formatMoney(row.amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="服务费" width="100" align="right">
          <template slot-scope="{ row }">
            <span style="color: #F56C6C">${{ formatMoney(row.fee) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="实际到账" width="120" align="right">
          <template slot-scope="{ row }">
            <span style="color: #67C23A; font-weight: 600">${{ formatMoney(row.actual_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="钱包地址" width="160">
          <template slot-scope="{ row }">
            <el-tooltip :content="row.wallet_address" placement="top" :disabled="!row.wallet_address">
              <span class="address-text">{{ truncateAddress(row.wallet_address) }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="wallet_network" label="网络" width="90" align="center">
          <template slot-scope="{ row }">
            <el-tag size="mini" type="info" v-if="row.wallet_network">{{ row.wallet_network }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template slot-scope="{ row }">
            <el-tag :type="statusTagType(row.status)" size="mini">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="170" />
        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template slot-scope="{ row }">
            <el-button
              v-if="row.status === 0"
              size="mini"
              type="success"
              plain
              @click="openApproveDialog(row)">
              通过
            </el-button>
            <el-button
              v-if="row.status === 0"
              size="mini"
              type="danger"
              plain
              @click="openRejectDialog(row)">
              拒绝
            </el-button>
            <el-button
              v-if="row.status === 1"
              size="mini"
              type="primary"
              plain
              @click="openCompleteDialog(row)">
              打款完成
            </el-button>
            <el-button
              size="mini"
              type="info"
              plain
              @click="openDetailDialog(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          :page-size.sync="query.page_size"
          :current-page.sync="query.page"
          :page-sizes="[10, 20, 50, 100]"
          @size-change="fetchData"
          @current-change="fetchData" />
      </div>
    </el-card>

    <!-- 审核通过确认弹窗 -->
    <el-dialog
      title="审核通过确认"
      :visible.sync="approveDialog.visible"
      width="480px"
      :close-on-click-modal="false">
      <div v-if="approveDialog.row" class="confirm-info">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="提现ID">{{ approveDialog.row.id }}</el-descriptions-item>
          <el-descriptions-item label="用户ID">{{ approveDialog.row.user_id }}</el-descriptions-item>
          <el-descriptions-item label="提现金额">${{ formatMoney(approveDialog.row.amount) }}</el-descriptions-item>
          <el-descriptions-item label="服务费">${{ formatMoney(approveDialog.row.fee) }}</el-descriptions-item>
          <el-descriptions-item label="实际到账">${{ formatMoney(approveDialog.row.actual_amount) }}</el-descriptions-item>
          <el-descriptions-item label="钱包地址">{{ approveDialog.row.wallet_address }}</el-descriptions-item>
          <el-descriptions-item label="网络">{{ approveDialog.row.wallet_network || '-' }}</el-descriptions-item>
        </el-descriptions>
        <el-alert
          title="确认通过此提现申请？通过后将进入待打款状态。"
          type="warning"
          :closable="false"
          show-icon
          style="margin-top: 16px" />
      </div>
      <span slot="footer">
        <el-button size="small" @click="approveDialog.visible = false">取消</el-button>
        <el-button
          type="success"
          size="small"
          :loading="approveDialog.loading"
          @click="handleApprove">
          确认通过
        </el-button>
      </span>
    </el-dialog>

    <!-- 拒绝弹窗 -->
    <el-dialog
      title="拒绝提现"
      :visible.sync="rejectDialog.visible"
      width="480px"
      :close-on-click-modal="false">
      <div v-if="rejectDialog.row" style="margin-bottom: 12px">
        <span style="color: #909399; font-size: 13px">
          提现ID: {{ rejectDialog.row.id }} | 金额: ${{ formatMoney(rejectDialog.row.amount) }}
        </span>
      </div>
      <el-form label-width="80px">
        <el-form-item label="拒绝原因" required>
          <el-input
            v-model="rejectDialog.reason"
            type="textarea"
            :rows="4"
            placeholder="请输入拒绝原因（必填）"
            maxlength="500"
            show-word-limit />
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button size="small" @click="rejectDialog.visible = false">取消</el-button>
        <el-button
          type="danger"
          size="small"
          :loading="rejectDialog.loading"
          :disabled="!rejectDialog.reason.trim()"
          @click="handleReject">
          确认拒绝
        </el-button>
      </span>
    </el-dialog>

    <!-- 打款完成弹窗 -->
    <el-dialog
      title="确认打款完成"
      :visible.sync="completeDialog.visible"
      width="480px"
      :close-on-click-modal="false">
      <div v-if="completeDialog.row" style="margin-bottom: 12px">
        <span style="color: #909399; font-size: 13px">
          提现ID: {{ completeDialog.row.id }} | 实际到账: ${{ formatMoney(completeDialog.row.actual_amount) }}
        </span>
      </div>
      <el-form label-width="80px">
        <el-form-item label="交易哈希">
          <el-input
            v-model="completeDialog.txHash"
            placeholder="请输入链上交易哈希（可选）"
            clearable />
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button size="small" @click="completeDialog.visible = false">取消</el-button>
        <el-button
          type="primary"
          size="small"
          :loading="completeDialog.loading"
          @click="handleComplete">
          确认完成
        </el-button>
      </span>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog
      title="提现详情"
      :visible.sync="detailDialog.visible"
      width="600px">
      <el-descriptions
        v-if="detailDialog.row"
        :column="2"
        border
        size="small">
        <el-descriptions-item label="提现ID">{{ detailDialog.row.id }}</el-descriptions-item>
          <el-descriptions-item label="用户ID">{{ detailDialog.row.user_id }}</el-descriptions-item>
          <el-descriptions-item label="用户邮箱" :span="2">{{ detailDialog.row.user_email || '-' }}</el-descriptions-item>
        <el-descriptions-item label="提现金额">${{ formatMoney(detailDialog.row.amount) }}</el-descriptions-item>
        <el-descriptions-item label="服务费">${{ formatMoney(detailDialog.row.fee) }}</el-descriptions-item>
        <el-descriptions-item label="实际到账">${{ formatMoney(detailDialog.row.actual_amount) }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTagType(detailDialog.row.status)" size="mini">
            {{ statusLabel(detailDialog.row.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="钱包地址" :span="2">
          {{ detailDialog.row.wallet_address || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="钱包网络">{{ detailDialog.row.wallet_network || '-' }}</el-descriptions-item>
        <el-descriptions-item label="申请时间">{{ detailDialog.row.created_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="交易哈希" :span="2">
          <span v-if="detailDialog.row.tx_hash" class="tx-hash-text">{{ detailDialog.row.tx_hash }}</span>
          <span v-else style="color: #C0C4CC">-</span>
        </el-descriptions-item>
        <el-descriptions-item label="拒绝原因" :span="2" v-if="detailDialog.row.status === 2">
          <span style="color: #F56C6C">{{ detailDialog.row.reject_reason || '-' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="审核人">{{ detailDialog.row.audit_by || '-' }}</el-descriptions-item>
        <el-descriptions-item label="审核时间">{{ detailDialog.row.audit_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="完成时间" :span="2" v-if="detailDialog.row.status === 3">
          {{ detailDialog.row.completed_at || '-' }}
        </el-descriptions-item>
      </el-descriptions>
      <span slot="footer">
        <el-button size="small" @click="detailDialog.visible = false">关闭</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import {
  getWithdrawals,
  approveWithdrawal,
  rejectWithdrawal,
  completeWithdrawal
} from '@/api/finance'

export default {
  name: 'WithdrawalManage',
  data() {
    return {
      loading: false,
      list: [],
      total: 0,
      query: {
        page: 1,
        page_size: 20,
        status: '',
        user_id: ''
      },
      dateRange: null,
      // 审核通过弹窗
      approveDialog: {
        visible: false,
        loading: false,
        row: null
      },
      // 拒绝弹窗
      rejectDialog: {
        visible: false,
        loading: false,
        row: null,
        reason: ''
      },
      // 打款完成弹窗
      completeDialog: {
        visible: false,
        loading: false,
        row: null,
        txHash: ''
      },
      // 详情弹窗
      detailDialog: {
        visible: false,
        row: null
      },
      // 服务端统计
      stats: {
        pendingCount: 0,
        approvedCount: 0,
        totalAmount: 0,
        totalFee: 0
      }
    }
  },
  computed: {
    // stats 从服务端获取，不依赖当前页数据
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    /** 状态标签映射 */
    statusLabel(s) {
      const map = { 0: '待审核', 1: '已通过', 2: '已拒绝', 3: '已完成' }
      return map[s] !== undefined ? map[s] : s
    },
    /** 状态标签颜色 */
    statusTagType(s) {
      const map = { 0: 'warning', 1: '', 2: 'danger', 3: 'success' }
      return map[s] !== undefined ? map[s] : 'info'
    },
    /** 金额格式化 */
    formatMoney(val) {
      const num = Number(val) || 0
      return num.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })
    },
    /** 截断钱包地址 */
    truncateAddress(addr) {
      if (!addr) return '-'
      if (addr.length <= 16) return addr
      return addr.slice(0, 8) + '...' + addr.slice(-6)
    },
    /** 搜索 */
    handleSearch() {
      this.query.page = 1
      this.fetchData()
    },
    /** 重置 */
    handleReset() {
      this.query = { page: 1, page_size: 20, status: '', user_id: '' }
      this.dateRange = null
      this.fetchData()
    },
    /** 获取列表 */
    async fetchData() {
      this.loading = true
      try {
        const params = {
          page: this.query.page,
          page_size: this.query.page_size
        }
        if (this.query.status !== '' && this.query.status !== null) {
          params.status = this.query.status
        }
        if (this.query.user_id) {
          params.user_id = this.query.user_id
        }
        if (this.dateRange && this.dateRange.length === 2) {
          params.start_date = this.dateRange[0]
          params.end_date = this.dateRange[1]
        }
        const res = await getWithdrawals(params)
        const resData = res.data.data
        if (Array.isArray(resData)) {
          this.list = resData
          this.total = res.data.total || resData.length
        } else {
          this.list = []
          this.total = 0
        }
        // 使用服务端统计
        const serverStats = res.data.stats
        if (serverStats) {
          this.stats = {
            pendingCount: serverStats.pending || 0,
            approvedCount: serverStats.approved || 0,
            totalAmount: serverStats.total_amount || 0,
            totalFee: serverStats.total_fee || 0
          }
        }
      } catch (e) {
        this.$message.error('获取提现记录失败')
        this.list = []
        this.total = 0
      } finally {
        this.loading = false
      }
    },
    /** 打开审核通过弹窗 */
    openApproveDialog(row) {
      this.approveDialog = { visible: true, loading: false, row: { ...row } }
    },
    /** 确认通过 */
    async handleApprove() {
      this.approveDialog.loading = true
      try {
        await approveWithdrawal(this.approveDialog.row.id)
        this.$message.success('审核已通过')
        this.approveDialog.visible = false
        this.fetchData()
      } catch (e) {
        this.$message.error('操作失败：' + (e.response && e.response.data && e.response.data.message || '未知错误'))
      } finally {
        this.approveDialog.loading = false
      }
    },
    /** 打开拒绝弹窗 */
    openRejectDialog(row) {
      this.rejectDialog = { visible: true, loading: false, row: { ...row }, reason: '' }
    },
    /** 确认拒绝 */
    async handleReject() {
      if (!this.rejectDialog.reason.trim()) {
        this.$message.warning('请输入拒绝原因')
        return
      }
      this.rejectDialog.loading = true
      try {
        await rejectWithdrawal(this.rejectDialog.row.id, this.rejectDialog.reason.trim())
        this.$message.success('已拒绝提现')
        this.rejectDialog.visible = false
        this.fetchData()
      } catch (e) {
        this.$message.error('操作失败：' + (e.response && e.response.data && e.response.data.message || '未知错误'))
      } finally {
        this.rejectDialog.loading = false
      }
    },
    /** 打开打款完成弹窗 */
    openCompleteDialog(row) {
      this.completeDialog = { visible: true, loading: false, row: { ...row }, txHash: '' }
    },
    /** 确认打款完成 */
    async handleComplete() {
      this.completeDialog.loading = true
      try {
        await completeWithdrawal(this.completeDialog.row.id, this.completeDialog.txHash.trim())
        this.$message.success('已标记为打款完成')
        this.completeDialog.visible = false
        this.fetchData()
      } catch (e) {
        this.$message.error('操作失败：' + (e.response && e.response.data && e.response.data.message || '未知错误'))
      } finally {
        this.completeDialog.loading = false
      }
    },
    /** 导出CSV */
    exportCSV() {
      const headers = ['ID', '用户ID', '用户邮箱', '金额', '服务费', '实际到账', '钱包地址', '网络', '状态', '申请时间']
      const rows = this.list.map(r => [
        r.id, r.user_id, r.user_email || '', r.amount, r.fee, r.actual_amount,
        r.wallet_address, r.wallet_network, this.statusLabel(r.status), r.created_at || ''
      ])
      const csv = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n')
      const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = `提现记录_${new Date().toISOString().slice(0,10)}.csv`
      a.click(); URL.revokeObjectURL(url)
    },
    /** 打开详情弹窗 */
    openDetailDialog(row) {
      this.detailDialog = { visible: true, row: { ...row } }
    }
  }
}
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding: 4px 0;
}

.address-text {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 12px;
  color: #606266;
  cursor: default;
}

.tx-hash-text {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 12px;
  word-break: break-all;
  color: #409EFF;
}

.confirm-info {
  padding: 0 4px;
}
</style>
