<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="6" :md="8" :sm="12">
        <stat-card title="策略总数" :value="list.length" icon="el-icon-s-opportunity" color="primary" :loading="loading"/>
      </el-col>
      <el-col :lg="6" :md="8" :sm="12">
        <stat-card title="已启用" :value="activeCount" icon="el-icon-circle-check" color="success" :loading="loading"/>
      </el-col>
      <el-col :lg="6" :md="8" :sm="12">
        <stat-card title="已禁用" :value="list.length - activeCount" icon="el-icon-remove-outline" color="info" :loading="loading"/>
      </el-col>
      <el-col :lg="6" :md="8" :sm="12">
        <stat-card title="交易所覆盖" :value="exchangeCount" icon="el-icon-connection" color="warning" :loading="loading"/>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <div class="toolbar">
        <el-button size="small" type="primary" icon="el-icon-plus" @click="openCreate">新建策略</el-button>
        <el-button size="small" icon="el-icon-refresh" @click="fetchData" :loading="loading">刷新</el-button>
      </div>
      <el-table v-loading="loading" :data="list" stripe border style="width:100%; margin-top:12px" size="small"
        :header-cell-style="{background:'#fafafa'}">
        <el-table-column prop="id" label="ID" width="60" align="center"/>
        <el-table-column prop="code" label="编码" width="100" show-overflow-tooltip/>
        <el-table-column prop="name" label="策略名称" width="140">
          <template slot-scope="{row}">
            <el-link type="primary" :underline="false" @click="showDetail(row)">{{ row.name }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip/>
        <el-table-column prop="symbol" label="交易对" width="100"/>
        <el-table-column prop="timeframe" label="周期" width="70" align="center"/>
        <el-table-column prop="exchange" label="交易所" width="90" align="center">
          <template slot-scope="{row}">
            <el-tag size="mini" v-if="row.exchange">{{ row.exchange }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="market_type" label="市场" width="70" align="center">
          <template slot-scope="{row}">
            <span>{{ row.market_type === 'future' ? '合约' : row.market_type === 'spot' ? '现货' : row.market_type || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="min_capital" label="最小资金" width="90" align="right">
          <template slot-scope="{row}">{{ row.min_capital != null ? row.min_capital : '-' }}</template>
        </el-table-column>
        <el-table-column prop="risk_level" label="风险等级" width="80" align="center"/>
        <el-table-column label="本金(U)" width="90" align="right">
          <template slot-scope="{row}">{{ row.capital > 0 ? row.capital : '-' }}</template>
        </el-table-column>
        <el-table-column prop="leverage" label="杠杆" width="65" align="center">
          <template slot-scope="{row}">
            <el-tag size="mini" type="warning" v-if="row.leverage">{{ row.leverage }}x</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="风险档位" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag size="mini" :type="row.risk_mode === 3 ? 'danger' : row.risk_mode === 2 ? 'warning' : 'success'">
              {{ {1:'稳健',2:'均衡',3:'激进'}[row.risk_mode] || '稳健' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="下单金额(U)" width="100" align="right">
          <template slot-scope="{row}">{{ row.amount_usdt > 0 ? row.amount_usdt : '-' }}</template>
        </el-table-column>
        <el-table-column prop="min_confidence" label="置信度" width="75" align="center"/>
        <el-table-column prop="cooldown_minutes" label="冷却(分)" width="85" align="center"/>
        <el-table-column prop="status" label="状态" width="75" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="mini">{{ row.status === 1 ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="165">
          <template slot-scope="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template slot-scope="{row}">
            <el-button size="mini" type="text" icon="el-icon-view" @click="showDetail(row)">详情</el-button>
            <el-button size="mini" type="text" icon="el-icon-edit" @click="openEdit(row)">编辑</el-button>
            <el-button size="mini" type="text" :icon="row.status === 1 ? 'el-icon-turn-off' : 'el-icon-open'" @click="toggleStrategy(row)">
              {{ row.status === 1 ? '禁用' : '启用' }}
            </el-button>
            <el-button size="mini" type="text" icon="el-icon-delete" style="color:#F56C6C" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && list.length === 0" description="暂无策略">
        <template slot="description">
          <p>暂无策略</p>
          <p class="empty-hint">若需初始化策略目录，请执行 <code>scripts/seed_dim_strategy.sql</code> 或联系管理员导入 dim_strategy 数据。</p>
        </template>
      </el-empty>
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog :title="'策略详情 - ' + (detailData ? detailData.name : '')" :visible.sync="detailVisible" width="720px" top="5vh">
      <div v-if="detailData">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="ID">{{ detailData.id }}</el-descriptions-item>
          <el-descriptions-item label="编码">{{ detailData.code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="名称">{{ detailData.name }}</el-descriptions-item>
          <el-descriptions-item label="交易对">{{ detailData.symbol || '-' }}</el-descriptions-item>
          <el-descriptions-item label="交易对列表">{{ Array.isArray(detailData.symbols) ? detailData.symbols.join(', ') : '-' }}</el-descriptions-item>
          <el-descriptions-item label="周期">{{ detailData.timeframe || '-' }}</el-descriptions-item>
          <el-descriptions-item label="交易所">{{ detailData.exchange || '-' }}</el-descriptions-item>
          <el-descriptions-item label="市场类型">{{ detailData.market_type === 'future' ? '合约' : detailData.market_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最小资金">{{ detailData.min_capital != null ? detailData.min_capital : '-' }} USDT</el-descriptions-item>
          <el-descriptions-item label="风险等级">{{ detailData.risk_level != null ? detailData.risk_level : '-' }}</el-descriptions-item>
          <el-descriptions-item label="本金">{{ detailData.capital > 0 ? detailData.capital + ' USDT' : '-' }}</el-descriptions-item>
          <el-descriptions-item label="杠杆">{{ detailData.leverage ? detailData.leverage + 'x' : '-' }}</el-descriptions-item>
          <el-descriptions-item label="风险档位">
            <el-tag size="small" :type="detailData.risk_mode === 3 ? 'danger' : detailData.risk_mode === 2 ? 'warning' : 'success'">
              {{ {1:'稳健(1%)',2:'均衡(1.5%)',3:'激进(2%)'}[detailData.risk_mode] || '稳健(1%)' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="仓位模式">
            <template v-if="detailData.config && detailData.config.risk_based_sizing">
              <el-tag type="warning" size="small">以损定仓</el-tag>
              <span style="color:#909399;font-size:12px;margin-left:4px">每笔最大亏损 = 本金 × 风险比例（仓位按止损距离自动调整）</span>
            </template>
            <template v-else>
              <el-tag size="small">固定金额</el-tag>
              <span v-if="detailData.amount_usdt > 0" style="margin-left:4px">{{ detailData.amount_usdt }} USDT</span>
              <span v-if="detailData.capital > 0" style="color:#909399;font-size:12px;margin-left:4px">(= 本金 × 风险比例 × 杠杆)</span>
            </template>
          </el-descriptions-item>
          <el-descriptions-item label="最低置信度">{{ detailData.min_confidence != null ? detailData.min_confidence : '-' }}</el-descriptions-item>
          <el-descriptions-item label="冷却(分钟)">{{ detailData.cooldown_minutes != null ? detailData.cooldown_minutes : '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="detailData.status === 1 ? 'success' : 'info'" size="small">{{ detailData.status === 1 ? '启用' : '禁用' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(detailData.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ detailData.description || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="detailData.config && Object.keys(detailData.config).length" style="margin-top: 15px;">
          <div style="font-weight: 600; margin-bottom: 8px;">策略配置:</div>
          <pre class="config-json">{{ JSON.stringify(detailData.config, null, 2) }}</pre>
        </div>
      </div>
    </el-dialog>

    <!-- 新建/编辑弹窗 -->
    <el-dialog :title="isCreating ? '新建策略' : '编辑策略'" :visible.sync="editVisible" width="640px" top="5vh" @close="editForm = {}">
      <el-form ref="editFormRef" :model="editForm" label-width="110px" size="small">
        <el-form-item label="编码" prop="code" :rules="isCreating ? [{required:true, message:'请输入策略编码'}] : []">
          <el-input v-model="editForm.code" :disabled="!isCreating" :placeholder="isCreating ? '唯一标识，如 rsi_btc_5m' : '编码不可修改'"/>
        </el-form-item>
        <el-form-item label="策略名称" prop="name">
          <el-input v-model="editForm.name" placeholder="策略名称"/>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="editForm.description" type="textarea" :rows="2" placeholder="描述"/>
        </el-form-item>
        <el-form-item label="主交易对" prop="symbol">
          <el-select v-model="editForm.symbol" placeholder="请选择主交易对" clearable filterable allow-create style="width:100%">
            <el-option v-for="s in symbolOptions" :key="s" :label="s" :value="s"/>
          </el-select>
          <div class="form-tip">统一规范格式，Binance/OKX/Gate.io/Bybit 均会自动识别（如 BTCUSDT、BTC-USDT、BTC_USDT 等）</div>
        </el-form-item>
        <el-form-item label="交易对列表" prop="symbols">
          <el-select v-model="editForm.symbols" multiple placeholder="可多选，为空则用主交易对" clearable style="width:100%">
            <el-option v-for="s in symbolOptions" :key="s" :label="s" :value="s"/>
          </el-select>
        </el-form-item>
        <el-form-item label="周期" prop="timeframe">
          <el-select v-model="editForm.timeframe" placeholder="请选择K线周期" clearable style="width:100%">
            <el-option label="1 分钟" value="1m"/>
            <el-option label="5 分钟" value="5m"/>
            <el-option label="15 分钟" value="15m"/>
            <el-option label="30 分钟" value="30m"/>
            <el-option label="1 小时" value="1h"/>
            <el-option label="2 小时" value="2h"/>
            <el-option label="4 小时" value="4h"/>
            <el-option label="8 小时" value="8h"/>
            <el-option label="1 天" value="1d"/>
          </el-select>
        </el-form-item>
        <el-form-item label="交易所" prop="exchange">
          <el-select v-model="editForm.exchange" placeholder="选填，空则跟随账户" clearable style="width:100%">
            <el-option label="Binance" value="binance"/>
            <el-option label="OKX" value="okx"/>
            <el-option label="Gate.io" value="gateio"/>
            <el-option label="Bybit" value="bybit"/>
          </el-select>
        </el-form-item>
        <el-form-item label="市场类型" prop="market_type">
          <el-select v-model="editForm.market_type" placeholder="市场类型" style="width:100%">
            <el-option label="合约" value="future"/>
            <el-option label="现货" value="spot"/>
          </el-select>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="最小资金" prop="min_capital">
              <el-input-number v-model="editForm.min_capital" :min="0" :precision="2" style="width:100%"/>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="风险等级" prop="risk_level">
              <el-input-number v-model="editForm.risk_level" :min="0" :max="5" style="width:100%"/>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="本金(USDT)" prop="capital">
              <el-input-number v-model="editForm.capital" :min="0" :precision="2" style="width:100%"/>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="杠杆" prop="leverage">
              <el-select v-model="editForm.leverage" placeholder="杠杆倍数" style="width:100%">
                <el-option :label="'5x'" :value="5"/>
                <el-option :label="'10x'" :value="10"/>
                <el-option :label="'20x'" :value="20"/>
                <el-option :label="'50x'" :value="50"/>
                <el-option :label="'75x'" :value="75"/>
                <el-option :label="'100x'" :value="100"/>
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="风险档位" prop="risk_mode">
              <el-radio-group v-model="editForm.risk_mode">
                <el-radio-button :label="1">稳健(1%)</el-radio-button>
                <el-radio-button :label="2">均衡(1.5%)</el-radio-button>
                <el-radio-button :label="3">激进(2%)</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="isRiskBasedSizing ? '每笔最大亏损' : '下单金额(U)'">
              <template v-if="isRiskBasedSizing">
                <div style="line-height:32px;">
                  <span style="font-size:16px;font-weight:600;color:#E6A23C">{{ calcMaxLoss }}</span>
                  <span style="color:#909399;font-size:12px;margin-left:4px">USDT (以损定仓)</span>
                </div>
                <div style="color:#909399;font-size:12px;">= 本金 {{ editForm.capital || 0 }} × {{ {1:'1%',2:'1.5%',3:'2%'}[editForm.risk_mode] || '1%' }}，仓位按止损距离自动调整</div>
              </template>
              <template v-else>
                <div style="line-height:32px;">
                  <span style="font-size:16px;font-weight:600;color:#409EFF">{{ calcAmountUsdt }}</span>
                  <span style="color:#909399;font-size:12px;margin-left:4px">USDT (自动计算)</span>
                </div>
                <div style="color:#909399;font-size:12px;">= 本金 × {{ {1:'1%',2:'1.5%',3:'2%'}[editForm.risk_mode] || '1%' }} × {{ editForm.leverage || 0 }}x</div>
              </template>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="最低置信度" prop="min_confidence">
              <el-input-number v-model="editForm.min_confidence" :min="0" :max="100" style="width:100%"/>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="冷却(分钟)" prop="cooldown_minutes">
              <el-input-number v-model="editForm.cooldown_minutes" :min="0" style="width:100%"/>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="editForm.status">
            <el-radio :label="1">启用</el-radio>
            <el-radio :label="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button size="small" @click="editVisible = false">取消</el-button>
        <el-button size="small" type="primary" @click="saveEdit" :loading="editSaving">保存</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import { getStrategies, createStrategy, updateStrategy, deleteStrategy, toggleStrategy } from '@/api/admin'

export default {
  name: 'StrategyList',
  data() {
    return {
      loading: false,
      list: [],
      detailVisible: false,
      detailData: null,
      editVisible: false,
      editForm: {},
      editSaving: false,
      isCreating: false,
      symbolOptions: [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT',
        'AVAXUSDT', 'LINKUSDT', 'DOTUSDT', 'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT',
        'ETCUSDT', 'XLMUSDT', 'NEARUSDT', 'APTUSDT', 'ARBUSDT', 'OPUSDT', 'INJUSDT', 'SUIUSDT'
      ]
    }
  },
  computed: {
    activeCount() { return this.list.filter(s => s.status === 1).length },
    exchangeCount() { return new Set(this.list.map(s => s.exchange).filter(Boolean)).size },
    isRiskBasedSizing() {
      // 编辑时判断当前策略是否开启了以损定仓
      const cfg = this.editForm._config || {}
      return !!cfg.risk_based_sizing
    },
    calcMaxLoss() {
      const cap = Number(this.editForm.capital) || 0
      const mode = Number(this.editForm.risk_mode) || 1
      const pct = {1: 0.01, 2: 0.015, 3: 0.02}[mode] || 0.01
      if (cap <= 0) return '0.00'
      return (cap * pct).toFixed(2)
    },
    calcAmountUsdt() {
      const cap = Number(this.editForm.capital) || 0
      const lev = Number(this.editForm.leverage) || 20
      const mode = Number(this.editForm.risk_mode) || 1
      const pct = {1: 0.01, 2: 0.015, 3: 0.02}[mode] || 0.01
      if (cap <= 0) return 0
      return (cap * pct * lev).toFixed(2)
    }
  },
  mounted() { this.fetchData() },
  methods: {
    formatTime(t) { return t ? t.replace('T', ' ').substring(0, 19) : '-' },
    showDetail(row) { this.detailData = row; this.detailVisible = true },
    openCreate() {
      this.isCreating = true
      this.editForm = {
        code: '',
        name: '',
        description: '',
        symbol: '',
        symbols: [],
        timeframe: '',
        exchange: '',
        market_type: 'future',
        min_capital: 200,
        risk_level: 1,
        capital: 0,
        leverage: 20,
        risk_mode: 1,
        min_confidence: 50,
        cooldown_minutes: 60,
        status: 1
      }
      this.editVisible = true
    },
    openEdit(row) {
      this.isCreating = false
      const symbols = row.symbols
      const symbolsArr = Array.isArray(symbols) ? [...symbols] : (row.symbol ? [row.symbol] : [])
      this.editForm = {
        id: row.id,
        code: row.code,
        name: row.name,
        description: row.description || '',
        symbol: row.symbol || '',
        symbols: symbolsArr,
        timeframe: row.timeframe || '',
        exchange: row.exchange || '',
        market_type: row.market_type || 'future',
        min_capital: row.min_capital != null ? Number(row.min_capital) : 200,
        risk_level: row.risk_level != null ? Number(row.risk_level) : 1,
        capital: row.capital != null ? Number(row.capital) : 0,
        leverage: row.leverage != null ? Number(row.leverage) : 20,
        risk_mode: row.risk_mode != null ? Number(row.risk_mode) : 1,
        min_confidence: row.min_confidence != null ? Number(row.min_confidence) : 50,
        cooldown_minutes: row.cooldown_minutes != null ? Number(row.cooldown_minutes) : 60,
        status: row.status != null ? Number(row.status) : 1,
        _config: row.config || {},
      }
      this.editVisible = true
    },
    async saveEdit() {
      const symbols = this.editForm.symbols && this.editForm.symbols.length ? this.editForm.symbols : null
      const payload = {
        name: this.editForm.name,
        description: this.editForm.description || null,
        symbol: this.editForm.symbol || null,
        symbols: symbols,
        timeframe: this.editForm.timeframe || null,
        exchange: this.editForm.exchange || null,
        market_type: this.editForm.market_type || null,
        min_capital: this.editForm.min_capital,
        risk_level: this.editForm.risk_level,
        capital: this.editForm.capital || 0,
        leverage: this.editForm.leverage || 20,
        risk_mode: this.editForm.risk_mode || 1,
        min_confidence: this.editForm.min_confidence,
        cooldown_minutes: this.editForm.cooldown_minutes,
        status: this.editForm.status
      }
      this.editSaving = true
      try {
        if (this.isCreating) {
          if (!this.editForm.code || !this.editForm.name) {
            this.$message.warning('编码和名称为必填项')
            this.editSaving = false
            return
          }
          payload.code = this.editForm.code
          await createStrategy(payload)
          this.$message.success('新建成功')
        } else {
          await updateStrategy(this.editForm.id, payload)
          this.$message.success('保存成功')
        }
        this.editVisible = false
        this.fetchData()
      } catch (e) {
        const msg = (e.response && e.response.data && (e.response.data.detail || e.response.data.message)) || e.message || '操作失败'
        this.$message.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      } finally {
        this.editSaving = false
      }
    },
    async handleDelete(row) {
      try {
        await this.$confirm(
          `确定要删除策略「${row.name}」(${row.code})吗？此操作不可恢复。`,
          '删除确认',
          { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'error' }
        )
      } catch { return }
      try {
        await deleteStrategy(row.id)
        this.$message.success('删除成功')
        this.fetchData()
      } catch (e) {
        const msg = (e.response && e.response.data && (e.response.data.detail || e.response.data.message)) || e.message || '删除失败'
        this.$message.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      }
    },
    async toggleStrategy(row) {
      const action = row.status === 1 ? '禁用' : '启用'
      try {
        await this.$confirm(`确定要${action}策略「${row.name}」吗？`, '提示', {
          type: 'warning'
        })
      } catch {
        return
      }
      try {
        await toggleStrategy(row.id)
        this.$message.success(action + '成功')
        this.fetchData()
      } catch (e) {
        const msg = (e.response && e.response.data && (e.response.data.detail || e.response.data.message)) || e.message || action + '失败'
        this.$message.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      }
    },
    async fetchData() {
      this.loading = true
      try {
        const res = await getStrategies()
        const body = res.data || {}
        let arr = body.data
        if (arr == null && Array.isArray(body)) arr = body
        this.list = Array.isArray(arr) ? arr : []
      } catch (e) {
        const msg = (e.response && e.response.data && (e.response.data.detail || e.response.data.message)) || e.message || '获取策略列表失败'
        this.$message.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 8px; }
.config-json {
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 12px;
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.empty-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
.empty-hint code {
  background: #f4f4f5;
  padding: 2px 6px;
  border-radius: 4px;
}
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
