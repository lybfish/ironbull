<template>
  <div class="strategies-page">
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card v-loading="strategiesLoading" shadow="hover">
          <template #header>策略目录（点击行查看详情）</template>
          <el-table :data="strategies" stripe border max-height="320" highlight-current-row @row-click="openStrategyDetail">
            <el-table-column prop="code" label="策略码" width="120" show-overflow-tooltip />
            <el-table-column prop="name" label="名称" min-width="100" show-overflow-tooltip />
            <el-table-column prop="symbol" label="标的" width="90" />
            <el-table-column prop="min_capital" label="最小资金" width="90" align="right" />
            <el-table-column prop="status" label="状态" width="70">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!strategiesLoading && strategies.length === 0" description="暂无策略" />
          <div v-else class="tip">共 {{ strategiesTotal }} 个策略</div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card v-loading="bindingsLoading" shadow="hover">
          <template #header>
            <span>策略绑定</span>
            <el-select v-model="bindingFilter" placeholder="全部策略" clearable size="small" style="width:140px; margin-left:12px" @change="loadBindings">
              <el-option v-for="s in strategies" :key="s.code" :label="s.name" :value="s.code" />
            </el-select>
          </template>
          <el-table :data="bindings" stripe border max-height="320">
            <el-table-column prop="user_email" label="用户" width="120" show-overflow-tooltip />
            <el-table-column prop="strategy_name" label="策略" width="100" show-overflow-tooltip />
            <el-table-column prop="exchange" label="交易所" width="80" />
            <el-table-column prop="point_card_total" label="点卡" width="80" align="right">
              <template #default="{ row }">
                <span :class="{ 'text-danger': row.point_card_total <= 0 }">{{ row.point_card_total.toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="70">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">{{ row.status === 1 ? '开启' : '关闭' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="total_trades" label="笔数" width="70" align="right" />
            <el-table-column prop="total_profit" label="累计盈亏" width="90" align="right">
              <template #default="{ row }">{{ row.total_profit != null ? row.total_profit.toFixed(2) : '-' }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!bindingsLoading && bindings.length === 0" description="暂无绑定" />
          <div v-else class="tip">共 {{ bindingsTotal }} 条绑定（点卡为 0 时该账户不执行信号）</div>
        </el-card>
      </el-col>
    </el-row>

    <el-drawer v-model="detailVisible" title="策略详情" size="400" direction="rtl">
      <div v-if="detailStrategy" class="strategy-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="策略码">{{ detailStrategy.code }}</el-descriptions-item>
          <el-descriptions-item label="名称">{{ detailStrategy.name }}</el-descriptions-item>
          <el-descriptions-item label="描述">{{ detailStrategy.description || '-' }}</el-descriptions-item>
          <el-descriptions-item label="标的">{{ detailStrategy.symbol || '-' }}</el-descriptions-item>
          <el-descriptions-item label="周期">{{ detailStrategy.timeframe || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最小资金(USDT)">{{ detailStrategy.min_capital != null ? detailStrategy.min_capital : '-' }}</el-descriptions-item>
          <el-descriptions-item label="风险等级">{{ detailStrategy.risk_level != null ? detailStrategy.risk_level : '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="detailStrategy.status === 1 ? 'success' : 'info'" size="small">{{ detailStrategy.status === 1 ? '启用' : '停用' }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getStrategies, getStrategyBindings } from '../api'

const strategiesLoading = ref(true)
const bindingsLoading = ref(true)
const strategies = ref([])
const strategiesTotal = ref(0)
const bindings = ref([])
const bindingsTotal = ref(0)
const bindingFilter = ref('')
const detailVisible = ref(false)
const detailStrategy = ref(null)

function openStrategyDetail(row) {
  detailStrategy.value = row
  detailVisible.value = true
}

async function loadStrategies() {
  strategiesLoading.value = true
  try {
    const res = await getStrategies()
    strategies.value = res.data || []
    strategiesTotal.value = res.total ?? strategies.value.length
  } catch (e) {
    console.error(e)
  } finally {
    strategiesLoading.value = false
  }
}

async function loadBindings() {
  bindingsLoading.value = true
  try {
    const res = await getStrategyBindings({ strategy_code: bindingFilter.value || undefined })
    bindings.value = res.data || []
    bindingsTotal.value = res.total ?? bindings.value.length
  } catch (e) {
    console.error(e)
  } finally {
    bindingsLoading.value = false
  }
}

onMounted(() => {
  loadStrategies()
  loadBindings()
})
</script>

<style scoped>
.strategies-page { padding: 0; }
.tip { margin-top: 8px; color: #999; font-size: 12px; }
.text-danger { color: #f56c6c; }
.strategy-detail { padding: 0 8px; }
</style>
