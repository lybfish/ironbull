<template>
  <div class="ele-body ele-body-card">
    <el-row :gutter="15">
      <!-- 规则配置 -->
      <el-col :lg="14" :md="24">
        <el-card shadow="never" v-loading="loading">
          <div slot="header" class="hdr">
            <span>风控规则配置</span>
            <el-button type="primary" size="small" icon="el-icon-check" @click="saveRules" :loading="saving">保存</el-button>
          </div>
          <div v-for="rule in rules" :key="rule.name" class="rule-item">
            <div class="rule-header">
              <el-switch v-model="rule.enabled" :active-text="rule.description" style="margin-right: 12px;"/>
              <el-tag :type="severityType(rule.severity)" size="mini">{{ rule.severity }}</el-tag>
            </div>
            <div class="rule-params" v-if="rule.enabled">
              <template v-for="(val, key) in rule.params">
                <div :key="key" class="param-row" v-if="key !== 'symbols'">
                  <span class="param-label">{{ paramLabel(key) }}</span>
                  <el-input-number v-model="rule.params[key]" :min="0" size="small" style="width:160px;"/>
                </div>
                <div :key="key" class="param-row" v-else>
                  <span class="param-label">{{ paramLabel(key) }}</span>
                  <el-input v-model="rule.symbolsStr" placeholder="逗号分隔，如 BTC/USDT,ETH/USDT" size="small" style="width:300px;"/>
                </div>
              </template>
            </div>
          </div>
          <el-empty v-if="rules.length === 0 && !loading" description="无规则数据"/>
        </el-card>
      </el-col>

      <!-- 违规统计 -->
      <el-col :lg="10" :md="24">
        <el-card shadow="never" v-loading="violationLoading" style="margin-bottom: 15px;">
          <div slot="header" class="hdr">
            <span>风控违规统计</span>
            <el-radio-group v-model="violationDays" size="mini" @change="fetchViolations">
              <el-radio-button :label="7">7天</el-radio-button>
              <el-radio-button :label="14">14天</el-radio-button>
              <el-radio-button :label="30">30天</el-radio-button>
            </el-radio-group>
          </div>

          <!-- 违规趋势 -->
          <div ref="chartViolation" style="height: 200px;"></div>

          <!-- 按规则分布 -->
          <div style="margin-top: 12px;">
            <div class="violation-rule" v-for="item in violationByRule" :key="item.rule">
              <span class="violation-name">{{ item.rule }}</span>
              <el-progress :percentage="item.pct" :stroke-width="14" :color="item.count > 10 ? '#F56C6C' : '#E6A23C'" style="flex:1; margin: 0 12px;"/>
              <span class="violation-count">{{ item.count }}</span>
            </div>
            <el-empty v-if="violationByRule.length === 0 && !violationLoading" description="近期无违规" :image-size="50"/>
          </div>
        </el-card>

        <!-- 最近违规记录 -->
        <el-card shadow="never" v-if="recentViolations.length > 0">
          <div slot="header">最近违规记录</div>
          <el-table :data="recentViolations" size="mini" stripe max-height="300">
            <el-table-column prop="error_code" label="规则" width="160">
              <template slot-scope="{row}">
                <el-tag type="danger" size="mini">{{ row.error_code }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="error_message" label="描述" show-overflow-tooltip/>
            <el-table-column prop="created_at" label="时间" width="155">
              <template slot-scope="{row}">
                <span style="font-size:11px;">{{ (row.created_at || '').replace('T', ' ').slice(0, 19) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import {getRiskRules, updateRiskRules, getRiskViolations} from '@/api/monitor'
import * as echarts from 'echarts/core'
import {BarChart} from 'echarts/charts'
import {GridComponent, TooltipComponent} from 'echarts/components'
import {CanvasRenderer} from 'echarts/renderers'

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const PARAM_LABELS = {
  min_balance: '最小余额 (USDT)',
  max_positions: '最大持仓数',
  max_value: '最大仓位价值 (USDT)',
  max_trades: '最大交易次数',
  max_loss: '最大亏损 (USDT)',
  max_consecutive: '最大连续亏损次数',
  cooldown_minutes: '冷却分钟数',
  cooldown_seconds: '冷却秒数',
  symbols: '品种列表'
}

export default {
  name: 'RiskConfig',
  data() {
    return {
      loading: false, saving: false, violationLoading: false,
      rules: [],
      violationDays: 7,
      violationByRule: [],
      recentViolations: [],
      violationChart: null
    }
  },
  mounted() {
    this.fetchRules()
    this.fetchViolations()
  },
  beforeDestroy() {
    if (this.violationChart) { this.violationChart.dispose() }
  },
  methods: {
    paramLabel(key) { return PARAM_LABELS[key] || key },
    severityType(s) {
      return {critical: 'danger', error: 'warning', warning: 'info'}[s] || ''
    },
    async fetchRules() {
      this.loading = true
      try {
        const res = await getRiskRules()
        const data = (res.data && res.data.data) || []
        this.rules = data.map(r => {
          const obj = {...r}
          if (r.params && r.params.symbols) {
            obj.symbolsStr = (r.params.symbols || []).join(',')
          }
          return obj
        })
      } catch (e) {
        this.$message.error('加载风控规则失败')
      } finally {
        this.loading = false
      }
    },
    async saveRules() {
      this.saving = true
      try {
        const rulesMap = {}
        for (const r of this.rules) {
          const params = {...r.params}
          if (r.symbolsStr !== undefined) {
            params.symbols = r.symbolsStr.split(',').map(s => s.trim()).filter(Boolean)
          }
          rulesMap[r.name] = {enabled: r.enabled, ...params}
        }
        await updateRiskRules({rules: rulesMap})
        this.$message.success('风控规则已保存')
      } catch (e) {
        this.$message.error('保存失败')
      } finally {
        this.saving = false
      }
    },
    async fetchViolations() {
      this.violationLoading = true
      try {
        const res = await getRiskViolations(this.violationDays)
        const d = (res.data && res.data.data) || {}
        const byRule = d.by_rule || []
        const maxCount = Math.max(...byRule.map(r => r.count), 1)
        this.violationByRule = byRule.map(r => ({...r, pct: Math.round(r.count / maxCount * 100)}))
        this.recentViolations = d.recent || []
        this.$nextTick(() => { this.renderViolationChart(d.daily || {}) })
      } catch (e) {
        console.error(e)
      } finally {
        this.violationLoading = false
      }
    },
    renderViolationChart(daily) {
      const el = this.$refs.chartViolation
      if (!el) { return }
      if (!this.violationChart) { this.violationChart = echarts.init(el) }
      this.violationChart.setOption({
        tooltip: {trigger: 'axis'},
        grid: {left: 40, right: 10, top: 10, bottom: 25},
        xAxis: {type: 'category', data: (daily.dates || []).map(d => d.slice(5)), axisLabel: {fontSize: 11}},
        yAxis: {type: 'value', minInterval: 1, splitLine: {lineStyle: {color: '#F2F6FC'}}},
        series: [{type: 'bar', data: daily.counts || [], itemStyle: {color: '#F56C6C', borderRadius: [3, 3, 0, 0]}, barMaxWidth: 16}]
      }, true)
    }
  }
}
</script>

<style scoped>
.hdr { display: flex; justify-content: space-between; align-items: center; }
.rule-item { padding: 14px 0; border-bottom: 1px solid #F2F6FC; }
.rule-item:last-child { border-bottom: none; }
.rule-header { display: flex; align-items: center; }
.rule-params { margin-top: 10px; padding-left: 50px; }
.param-row { display: flex; align-items: center; margin-bottom: 8px; }
.param-label { width: 160px; font-size: 13px; color: #606266; }
.violation-rule { display: flex; align-items: center; margin-bottom: 8px; }
.violation-name { font-size: 12px; color: #606266; width: 140px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.violation-count { font-size: 13px; font-weight: 600; color: #303133; width: 40px; text-align: right; }
</style>
