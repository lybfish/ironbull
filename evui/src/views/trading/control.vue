<template>
  <div class="ele-body">
    <el-card shadow="never">
      <div class="toolbar">
        <span class="toolbar-title">交易控制台</span>
      </div>
      <p class="intro">手动向交易所提交市价/限价单，请谨慎操作。策略运行时请避免冲突。</p>

      <!-- 警告提示 -->
      <el-alert
        title="手动操作警告"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 16px">
        <div slot="description">
          此控制台用于手动向交易所发送订单，请谨慎操作。手动订单可能影响策略运行，请确保您了解相关风险。
        </div>
      </el-alert>

      <!-- 下单目标平台：显眼展示「下的哪个平台」 -->
      <div class="platform-target">
        <span class="platform-label">当前下单目标：</span>
        <el-tag type="primary" effect="dark" size="medium">
          {{ exchangeLabel }} · {{ marketTypeLabel }}
        </el-tag>
      </div>

      <!-- 手动下单表单 -->
      <el-form
        :model="orderForm"
        :rules="rules"
        ref="orderForm"
        label-width="100px"
        size="medium">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="交易所" prop="exchange">
              <el-select
                v-model="orderForm.exchange"
                placeholder="请选择交易所"
                style="width: 100%">
                <el-option label="Binance" value="binance" />
                <el-option label="OKX" value="okx" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="市场类型" prop="market_type">
              <el-select
                v-model="orderForm.market_type"
                placeholder="请选择市场"
                style="width: 100%">
                <el-option label="合约 (USDT-M)" value="future" />
                <el-option label="现货" value="spot" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="交易对" prop="symbol">
              <el-input
                v-model="orderForm.symbol"
                placeholder="如 BTC/USDT:USDT"
                clearable />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="方向" prop="side">
              <el-select
                v-model="orderForm.side"
                placeholder="请选择方向"
                style="width: 100%">
                <el-option label="买入 (BUY)" value="buy" />
                <el-option label="卖出 (SELL)" value="sell" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="订单类型" prop="order_type">
              <el-select
                v-model="orderForm.order_type"
                placeholder="请选择类型"
                style="width: 100%">
                <el-option label="市价单" value="market" />
                <el-option label="限价单" value="limit" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="数量" prop="amount">
              <el-input-number
                v-model="orderForm.amount"
                :min="0.001"
                :max="1000000"
                :precision="3"
                style="width: 100%"
                placeholder="请输入数量" />
            </el-form-item>
          </el-col>
          <el-col :span="8" v-if="orderForm.order_type === 'limit'">
            <el-form-item label="价格" prop="price">
              <el-input-number
                v-model="orderForm.price"
                :min="0"
                :precision="2"
                style="width: 100%"
                placeholder="请输入价格" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item>
              <el-button
                type="primary"
                @click="submitOrder"
                :loading="submitting"
                icon="el-icon-check">
                提交订单
              </el-button>
              <el-button
                @click="resetForm"
                icon="el-icon-refresh-left">
                重置
              </el-button>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- 操作日志 -->
    <el-card shadow="never" style="margin-top: 16px">
      <div slot="header">
        <span>操作日志</span>
        <el-button
          type="text"
          size="small"
          style="float: right"
          @click="clearLogs"
          :disabled="logs.length === 0">
          清空日志
        </el-button>
      </div>
      <div v-if="logs.length === 0" class="empty-log">
        <i class="el-icon-info"></i>
        <span>暂无操作记录</span>
      </div>
      <div v-else class="log-container">
        <div
          v-for="(log, idx) in logs"
          :key="idx"
          class="log-item">
          <span class="log-time">{{ log.time }}</span>
          <el-tag
            :type="log.success ? 'success' : 'danger'"
            size="mini"
            effect="plain">
            {{ log.success ? '成功' : '失败' }}
          </el-tag>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import { submitManualOrder } from '@/api/trading'

export default {
  name: 'TradeControl',
  data() {
    return {
      submitting: false,
      orderForm: {
        exchange: 'binance',
        market_type: 'future',
        symbol: '',
        side: 'buy',
        order_type: 'market',
        amount: null,
        price: null
      },
      rules: {
        exchange: [
          { required: true, message: '请选择交易所', trigger: 'change' }
        ],
        market_type: [
          { required: true, message: '请选择市场类型', trigger: 'change' }
        ],
        symbol: [
          {required: true, message: '请输入交易对', trigger: 'blur'}
        ],
        side: [
          {required: true, message: '请选择方向', trigger: 'change'}
        ],
        order_type: [
          {required: true, message: '请选择订单类型', trigger: 'change'}
        ],
        amount: [
          {required: true, message: '请输入数量', trigger: 'blur'},
          {type: 'number', min: 0.001, message: '数量必须大于0.001', trigger: 'blur'}
        ],
        price: [
          {required: true, message: '请输入价格', trigger: 'blur'},
          {type: 'number', min: 0, message: '价格必须大于0', trigger: 'blur'}
        ]
      },
      logs: []
    }
  },
  computed: {
    exchangeLabel() {
      const m = { binance: 'Binance', okx: 'OKX' }
      return m[this.orderForm.exchange] || this.orderForm.exchange || '—'
    },
    marketTypeLabel() {
      const m = { future: '合约 (USDT-M)', spot: '现货' }
      return m[this.orderForm.market_type] || this.orderForm.market_type || '—'
    }
  },
  watch: {
    'orderForm.order_type'(val) {
      if (val === 'market') {
        this.orderForm.price = null
        this.$refs.orderForm && this.$refs.orderForm.clearValidate('price')
      }
    }
  },
  methods: {
    async submitOrder() {
      this.$refs.orderForm.validate(async (valid) => {
        if (!valid) {
          return false
        }

        // 限价单必须填写价格
        if (this.orderForm.order_type === 'limit' && !this.orderForm.price) {
          this.$message.warning('限价单必须填写价格')
          return false
        }

        // ★ 安全确认对话框：防止误操作
        const sideLabel = this.orderForm.side === 'buy' ? '买入(做多)' : '卖出(做空)'
        const typeLabel = this.orderForm.order_type === 'market' ? '市价' : '限价'
        const priceInfo = this.orderForm.order_type === 'limit' ? ` @ ${this.orderForm.price}` : ''
        const confirmMsg = `即将向 ${this.exchangeLabel} 提交真实订单：\n\n`
          + `方向：${sideLabel}\n`
          + `类型：${typeLabel}\n`
          + `标的：${this.orderForm.symbol}\n`
          + `数量：${this.orderForm.amount}${priceInfo}\n\n`
          + `此操作将直接在交易所执行，请确认无误！`
        try {
          await this.$confirm(confirmMsg, '订单确认', {
            confirmButtonText: '确认下单',
            cancelButtonText: '取消',
            type: 'warning'
          })
        } catch (_) {
          return // 用户取消
        }

        this.submitting = true
        const now = new Date().toLocaleString('zh-CN')
        const orderData = {
          exchange: this.orderForm.exchange,
          market_type: this.orderForm.market_type,
          symbol: this.orderForm.symbol,
          side: this.orderForm.side,
          order_type: this.orderForm.order_type,
          amount: this.orderForm.amount
        }
        if (this.orderForm.order_type === 'limit') {
          orderData.price = this.orderForm.price
        }

        try {
          const res = await submitManualOrder(orderData)
          const resData = res.data || {}
          if (resData.success === false) {
            throw new Error(resData.error || resData.message || '下单失败')
          }
          const platform = `${this.exchangeLabel} ${this.marketTypeLabel}`
          const message = `[${platform}] ${this.orderForm.side.toUpperCase()} ${this.orderForm.symbol} ${this.orderForm.amount} ${this.orderForm.order_type === 'limit' ? `@ ${this.orderForm.price}` : ''}`
          this.logs.unshift({
            time: now,
            success: true,
            message: message
          })
          this.$message.success('订单提交成功')
          this.resetForm()
        } catch (e) {
          const d = e.response?.data
          const errorMsg = (d && (d.detail || d.message || d.error)) || e.message || '未知错误'
          this.logs.unshift({
            time: now,
            success: false,
            message: `订单提交失败: ${errorMsg}`
          })
          this.$message.error('订单提交失败: ' + errorMsg)
        } finally {
          this.submitting = false
        }
      })
    },
    resetForm() {
      this.$refs.orderForm.resetFields()
      this.orderForm = {
        exchange: 'binance',
        market_type: 'future',
        symbol: '',
        side: 'buy',
        order_type: 'market',
        amount: null,
        price: null
      }
    },
    clearLogs() {
      this.$confirm('确定要清空所有操作日志吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.logs = []
        this.$message.success('日志已清空')
      }).catch(() => {})
    }
  }
}
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.toolbar-title { font-size: 16px; font-weight: 500; color: #303133; }
.intro { color: #606266; font-size: 14px; margin-bottom: 16px; line-height: 1.5; }
.platform-target {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #ecf5ff;
  border-radius: 6px;
  border-left: 4px solid #409eff;
}
.platform-label { font-size: 14px; color: #606266; margin-right: 8px; }
.empty-log {
  text-align: center;
  color: #909399;
  padding: 40px 0;
  font-size: 14px;
}

.empty-log i {
  font-size: 48px;
  display: block;
  margin-bottom: 10px;
  color: #c0c4cc;
}

.log-container {
  max-height: 500px;
  overflow-y: auto;
}

.log-item {
  padding: 12px 0;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: background-color 0.2s;
}

.log-item:hover {
  background-color: #f5f7fa;
}

.log-item:last-child {
  border-bottom: none;
}

.log-time {
  color: #909399;
  font-size: 12px;
  min-width: 160px;
  font-family: 'Monaco', 'Menlo', monospace;
}

.log-message {
  font-size: 13px;
  color: #303133;
  flex: 1;
  word-break: break-all;
}
</style>
