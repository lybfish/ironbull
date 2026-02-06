<template>
  <div class="ele-body">
    <el-card shadow="never">
      <!-- 搜索表单 -->
      <el-form
        :model="where"
        label-width="100px"
        class="ele-form-search"
        @keyup.enter.native="reload"
        @submit.native.prevent>
        <el-row :gutter="15">
          <el-col :lg="6" :md="12">
            <el-form-item label="租户ID:">
              <el-input
                clearable
                v-model="where.tenant_id"
                placeholder="请输入租户ID"
                type="number"/>
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12">
            <el-form-item label="用户ID:">
              <el-input
                clearable
                v-model="where.user_id"
                placeholder="请输入用户ID"
                type="number"/>
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12">
            <el-form-item label="变动类型:">
              <el-select
                v-model="where.change_type"
                clearable
                placeholder="请选择变动类型"
                style="width: 100%">
                <el-option label="充值" :value="1"/>
                <el-option label="赠送" :value="2"/>
                <el-option label="分发/转出" :value="3"/>
                <el-option label="转入" :value="4"/>
                <el-option label="盈利扣费" :value="5"/>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :lg="12" :md="12">
            <el-form-item label="日期范围:">
              <el-date-picker
                v-model="dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="yyyy-MM-dd"
                style="width: 100%"
                @change="handleDateRangeChange"/>
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12">
            <div class="ele-form-actions">
              <el-button
                type="primary"
                icon="el-icon-search"
                class="ele-btn-icon"
                @click="reload">查询
              </el-button>
              <el-button @click="reset">重置</el-button>
            </div>
          </el-col>
        </el-row>
      </el-form>

      <!-- 统计汇总 -->
      <el-row :gutter="15" style="margin-bottom: 15px;">
        <el-col :lg="8" :md="12" :sm="12">
          <stat-card
            title="总记录数"
            :value="summary.totalCount"
            icon="el-icon-document"
            color="primary"
            help-text="当前查询条件下的记录总数"
            :loading="loading"/>
        </el-col>
        <el-col :lg="8" :md="12" :sm="12">
          <stat-card
            title="总正数金额"
            icon="el-icon-arrow-up"
            color="success"
            help-text="所有正数金额的总和"
            :loading="loading">
            <template v-slot:value>
              <span style="color: #67C23A; font-weight: bold;">
                {{ formatAmount(summary.totalPositive) }}
              </span>
            </template>
          </stat-card>
        </el-col>
        <el-col :lg="8" :md="12" :sm="12">
          <stat-card
            title="总负数金额"
            icon="el-icon-arrow-down"
            color="danger"
            help-text="所有负数金额的总和"
            :loading="loading">
            <template v-slot:value>
              <span style="color: #F56C6C; font-weight: bold;">
                {{ formatAmount(summary.totalNegative) }}
              </span>
            </template>
          </stat-card>
        </el-col>
      </el-row>

      <!-- 数据表格 -->
      <el-table
        ref="table"
        v-loading="loading"
        :data="tableData"
        border
        stripe
        style="width: 100%"
        size="small">
        <el-table-column prop="id" label="ID" width="80" align="center"/>
        <el-table-column prop="tenant_id" label="租户ID" width="100" align="center"/>
        <el-table-column prop="user_email" label="用户邮箱" min-width="180" align="left" show-overflow-tooltip/>
        <el-table-column prop="change_type" label="变动类型" width="120" align="center">
          <template slot-scope="{row}">
            <el-tag :type="getChangeTypeTagType(row.change_type)" size="mini">
              {{ row.change_type_name || getChangeTypeName(row.change_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="变动金额" width="130" align="right">
          <template slot-scope="{row}">
            <span
              :style="{
                color: parseFloat(row.amount) >= 0 ? '#67C23A' : '#F56C6C',
                fontWeight: 'bold'
              }">
              {{ parseFloat(row.amount) >= 0 ? '+' : '' }}{{ row.amount }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="card_type" label="卡类型" width="100" align="center">
          <template slot-scope="{row}">
            {{ getCardTypeName(row.card_type) }}
          </template>
        </el-table-column>
        <el-table-column label="自充余额" width="150" align="center">
          <template slot-scope="{row}">
            <span class="ele-text-secondary">{{ row.before_self }}</span>
            <span style="margin: 0 5px;">→</span>
            <span>{{ row.after_self }}</span>
          </template>
        </el-table-column>
        <el-table-column label="赠送余额" width="150" align="center">
          <template slot-scope="{row}">
            <span class="ele-text-secondary">{{ row.before_gift }}</span>
            <span style="margin: 0 5px;">→</span>
            <span>{{ row.after_gift }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="200" show-overflow-tooltip>
          <template slot-scope="{row}">
            <el-tooltip
              v-if="row.remark"
              :content="row.remark"
              placement="top"
              effect="dark">
              <span>{{ row.remark }}</span>
            </el-tooltip>
            <span v-else class="ele-text-secondary">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" align="center">
          <template slot-scope="{row}">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        style="margin-top: 15px; text-align: right;"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        :current-page="pagination.page"
        :page-sizes="[10, 20, 50, 100]"
        :page-size="pagination.page_size"
        layout="total, sizes, prev, pager, next, jumper"
        :total="pagination.total">
      </el-pagination>
    </el-card>
  </div>
</template>

<script>
import { getPointcardLogs } from '@/api/finance'

export default {
  name: 'PointcardLogs',
  data() {
    return {
      where: {
        tenant_id: '',
        user_id: '',
        change_type: null,
        start_date: '',
        end_date: ''
      },
      dateRange: null,
      tableData: [],
      loading: false,
      pagination: {
        page: 1,
        page_size: 20,
        total: 0
      },
      summary: {
        totalCount: 0,
        totalPositive: 0,
        totalNegative: 0
      }
    }
  },
  created() {
    this.loadData()
  },
  methods: {
    async loadData() {
      this.loading = true
      try {
        const params = {
          page: this.pagination.page,
          page_size: this.pagination.page_size
        }
        
        if (this.where.tenant_id) {
          params.tenant_id = parseInt(this.where.tenant_id)
        }
        if (this.where.user_id) {
          params.user_id = parseInt(this.where.user_id)
        }
        if (this.where.change_type !== null && this.where.change_type !== '') {
          params.change_type = this.where.change_type
        }
        if (this.where.start_date) {
          params.start_date = this.where.start_date
        }
        if (this.where.end_date) {
          params.end_date = this.where.end_date
        }

        const res = await getPointcardLogs(params)
        
        if (res.data.success) {
          this.tableData = Array.isArray(res.data.data) ? res.data.data : []
          this.pagination.total = res.data.total || 0
          this.calculateSummary()
        } else {
          this.$message.error('获取点卡流水失败')
          this.tableData = []
          this.pagination.total = 0
        }
      } catch (e) {
        this.$message.error('获取点卡流水失败: ' + (e.message || '未知错误'))
        this.tableData = []
        this.pagination.total = 0
      } finally {
        this.loading = false
      }
    },
    calculateSummary() {
      this.summary.totalCount = this.pagination.total
      let totalPositive = 0
      let totalNegative = 0
      
      if (Array.isArray(this.tableData)) {
        this.tableData.forEach(item => {
          const amount = parseFloat(item.amount) || 0
          if (amount > 0) {
            totalPositive += amount
          } else if (amount < 0) {
            totalNegative += Math.abs(amount)
          }
        })
      }
      
      this.summary.totalPositive = totalPositive
      this.summary.totalNegative = totalNegative
    },
    reload() {
      this.pagination.page = 1
      this.loadData()
    },
    reset() {
      this.where = {
        tenant_id: '',
        user_id: '',
        change_type: null,
        start_date: '',
        end_date: ''
      }
      this.dateRange = null
      this.reload()
    },
    handleDateRangeChange(val) {
      if (val && val.length === 2) {
        this.where.start_date = val[0]
        this.where.end_date = val[1]
      } else {
        this.where.start_date = ''
        this.where.end_date = ''
      }
    },
    handleSizeChange(val) {
      this.pagination.page_size = val
      this.loadData()
    },
    handleCurrentChange(val) {
      this.pagination.page = val
      this.loadData()
    },
    getChangeTypeName(type) {
      const map = {
        1: '充值',
        2: '赠送',
        3: '分发/转出',
        4: '转入',
        5: '盈利扣费'
      }
      return map[type] || String(type)
    },
    getChangeTypeTagType(type) {
      const map = {
        1: 'success',   // 充值 - 绿色
        2: 'warning',   // 赠送 - 橙色
        3: 'info',      // 分发/转出 - 蓝色
        4: 'primary',   // 转入 - 蓝色
        5: 'danger'     // 盈利扣费 - 红色
      }
      return map[type] || ''
    },
    getCardTypeName(type) {
      if (!type) return '-'
      const map = {
        'self': '自充',
        'gift': '赠送'
      }
      return map[type] || String(type)
    },
    formatAmount(amount) {
      if (amount === 0) return '0.00'
      return amount.toFixed(2)
    },
    formatDateTime(datetime) {
      if (!datetime) return '-'
      // Handle ISO format datetime string
      const date = new Date(datetime)
      if (isNaN(date.getTime())) return datetime
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      const hours = String(date.getHours()).padStart(2, '0')
      const minutes = String(date.getMinutes()).padStart(2, '0')
      const seconds = String(date.getSeconds()).padStart(2, '0')
      return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
    }
  }
}
</script>

<style scoped>
.ele-form-search {
  margin-bottom: 15px;
}

.ele-form-actions {
  display: flex;
  align-items: center;
  height: 32px;
}
</style>
