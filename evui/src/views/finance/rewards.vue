<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="8" :md="8" :sm="12">
        <stat-card
          title="总记录数"
          :value="summary.totalRecords"
          icon="el-icon-document"
          color="primary"
          help-text="当前筛选条件下的奖励记录总数"
          :loading="loading" />
      </el-col>
      <el-col :lg="8" :md="8" :sm="12">
        <stat-card
          title="总金额"
          icon="el-icon-money"
          color="success"
          help-text="当前筛选条件下的奖励总金额"
          :loading="loading">
          <template slot="value">
            <span style="font-weight: 600">{{ formatMoney(summary.totalAmount) }}</span>
          </template>
        </stat-card>
      </el-col>
      <el-col :lg="8" :md="8" :sm="12">
        <stat-card
          title="平均比例"
          icon="el-icon-data-analysis"
          color="warning"
          help-text="当前筛选条件下的平均奖励比例"
          :loading="loading">
          <template slot="value">
            <span>{{ formatRate(summary.averageRate) }}</span>
          </template>
        </stat-card>
      </el-col>
    </el-row>

    <!-- 搜索表单 + 表格 -->
    <el-card shadow="never">
      <!-- 搜索表单 -->
      <el-form
        :model="query"
        label-width="90px"
        class="ele-form-search"
        @keyup.enter.native="handleSearch"
        @submit.native.prevent>
        <el-row :gutter="15">
          <el-col :lg="6" :md="12">
            <el-form-item label="用户ID:">
              <el-input
                v-model="query.user_id"
                placeholder="请输入用户ID"
                clearable
                size="small" />
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12">
            <el-form-item label="奖励类型:">
              <el-select
                v-model="query.reward_type"
                placeholder="请选择奖励类型"
                clearable
                size="small"
                style="width: 100%">
                <el-option label="直推奖" value="direct" />
                <el-option label="级差奖" value="level_diff" />
                <el-option label="平级奖" value="peer" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12">
            <el-form-item label="结算批次:">
              <el-input
                v-model="query.settle_batch"
                placeholder="请输入结算批次"
                clearable
                size="small" />
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12">
            <div class="ele-form-actions">
              <el-button
                type="primary"
                icon="el-icon-search"
                class="ele-btn-icon"
                size="small"
                @click="handleSearch">
                查询
              </el-button>
              <el-button
                icon="el-icon-refresh"
                size="small"
                @click="handleReset">
                重置
              </el-button>
            </div>
          </el-col>
        </el-row>
      </el-form>

      <!-- 数据表格 -->
      <el-table
        v-loading="loading"
        :data="list"
        stripe
        border
        style="width: 100%; margin-top: 12px"
        size="small"
        row-key="id">
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="user_email" label="获奖用户" minWidth="150" show-overflow-tooltip>
          <template slot-scope="{ row }">
            <span>{{ row.user_email || `用户ID: ${row.user_id}` }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="source_email" label="来源用户" minWidth="150" show-overflow-tooltip>
          <template slot-scope="{ row }">
            <span v-if="row.source_email">{{ row.source_email }}</span>
            <span v-else-if="row.source_user_id">用户ID: {{ row.source_user_id }}</span>
            <span v-else style="color: #C0C4CC">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="reward_type" label="奖励类型" width="100" align="center">
          <template slot-scope="{ row }">
            <el-tag :type="getRewardTypeTag(row.reward_type)" size="small">
              {{ getRewardTypeName(row.reward_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="120" align="right">
          <template slot-scope="{ row }">
            <span style="font-weight: 600">{{ formatMoney(row.amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="rate" label="比例" width="100" align="center">
          <template slot-scope="{ row }">
            <span>{{ formatRate(row.rate) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="settle_batch" label="结算批次" minWidth="150" show-overflow-tooltip>
          <template slot-scope="{ row }">
            <span>{{ row.settle_batch || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" minWidth="150">
          <template slot-scope="{ row }">
            <el-tooltip
              v-if="row.remark"
              :content="row.remark"
              placement="top"
              :disabled="!row.remark">
              <span>{{ row.remark }}</span>
            </el-tooltip>
            <span v-else style="color: #C0C4CC">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" align="center">
          <template slot-scope="{ row }">
            <span>{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
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

      <!-- 空数据提示 -->
      <el-empty
        v-if="!loading && list.length === 0"
        description="暂无奖励记录"
        style="padding: 40px 0" />
    </el-card>
  </div>
</template>

<script>
import { getRewards } from '@/api/finance'

export default {
  name: 'RewardList',
  data() {
    return {
      loading: false,
      list: [],
      total: 0,
      query: {
        user_id: '',
        reward_type: '',
        settle_batch: '',
        page: 1,
        page_size: 20
      }
    }
  },
  computed: {
    summary() {
      const totalRecords = this.total || this.list.length
      let totalAmount = 0
      let totalRate = 0
      let rateCount = 0

      this.list.forEach(item => {
        const amount = Number(item.amount) || 0
        const rate = Number(item.rate) || 0
        totalAmount += amount
        if (rate > 0) {
          totalRate += rate
          rateCount++
        }
      })

      const averageRate = rateCount > 0 ? totalRate / rateCount : 0

      return {
        totalRecords,
        totalAmount,
        averageRate
      }
    }
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    /** 获取奖励类型名称 */
    getRewardTypeName(type) {
      const map = {
        direct: '直推奖',
        level_diff: '级差奖',
        peer: '平级奖'
      }
      return map[type] || type || '-'
    },
    /** 获取奖励类型标签颜色 */
    getRewardTypeTag(type) {
      const map = {
        direct: 'success',
        level_diff: 'warning',
        peer: 'primary'
      }
      return map[type] || 'info'
    },
    /** 金额格式化 */
    formatMoney(val) {
      const num = Number(val) || 0
      return num.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })
    },
    /** 比例格式化（百分比） */
    formatRate(val) {
      const num = Number(val) || 0
      if (num === 0) return '-'
      return (num * 100).toFixed(2) + '%'
    },
    /** 日期时间格式化 */
    formatDateTime(val) {
      if (!val) return '-'
      // 如果是 ISO 格式字符串，转换为本地时间显示
      if (typeof val === 'string') {
        try {
          const date = new Date(val)
          if (isNaN(date.getTime())) return val
          const year = date.getFullYear()
          const month = String(date.getMonth() + 1).padStart(2, '0')
          const day = String(date.getDate()).padStart(2, '0')
          const hours = String(date.getHours()).padStart(2, '0')
          const minutes = String(date.getMinutes()).padStart(2, '0')
          const seconds = String(date.getSeconds()).padStart(2, '0')
          return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
        } catch (e) {
          return val
        }
      }
      return val
    },
    /** 搜索 */
    handleSearch() {
      this.query.page = 1
      this.fetchData()
    },
    /** 重置 */
    handleReset() {
      this.query = {
        user_id: '',
        reward_type: '',
        settle_batch: '',
        page: 1,
        page_size: 20
      }
      this.fetchData()
    },
    /** 获取列表数据 */
    async fetchData() {
      this.loading = true
      try {
        const params = {
          page: this.query.page,
          page_size: this.query.page_size
        }
        if (this.query.user_id) {
          params.user_id = this.query.user_id
        }
        if (this.query.reward_type) {
          params.reward_type = this.query.reward_type
        }
        if (this.query.settle_batch) {
          params.settle_batch = this.query.settle_batch
        }

        const res = await getRewards(params)
        const resData = res.data

        if (resData && resData.success && Array.isArray(resData.data)) {
          this.list = resData.data
          this.total = resData.total || resData.data.length
        } else if (Array.isArray(resData)) {
          // 兼容旧格式
          this.list = resData
          this.total = resData.length
        } else {
          this.list = []
          this.total = 0
        }
      } catch (e) {
        this.$message.error('获取奖励记录失败：' + (e.response && e.response.data && e.response.data.message || '未知错误'))
        this.list = []
        this.total = 0
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.ele-form-search {
  margin-bottom: 0;
}

.ele-form-actions {
  display: flex;
  align-items: center;
  padding-top: 4px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding: 4px 0;
}
</style>
