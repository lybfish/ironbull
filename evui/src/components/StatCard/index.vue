<template>
  <div
    class="stat-card"
    :class="[`stat-card--${color}`, { 'stat-card--clickable': clickable }]"
    @click="handleClick">
    <!-- 骨架屏加载状态 -->
    <template v-if="loading">
      <div class="stat-card__skeleton">
        <el-skeleton :rows="2" animated />
      </div>
    </template>
    <!-- 正常内容 -->
    <template v-else>
      <!-- 头部：图标和帮助提示 -->
      <div class="stat-card__header">
        <div class="stat-card__icon" v-if="icon">
          <el-tag :type="tagType" size="medium" class="stat-card__icon-tag">
            <i :class="icon"></i>
          </el-tag>
        </div>
        <el-tooltip
          v-if="helpText"
          :content="helpText"
          placement="top"
          effect="dark">
          <i class="el-icon-question stat-card__help"></i>
        </el-tooltip>
      </div>
      <!-- 主体：数值 -->
      <div class="stat-card__body">
        <div class="stat-card__value">
          <slot name="value">{{ formattedValue }}</slot>
        </div>
        <div class="stat-card__title">{{ title }}</div>
      </div>
      <!-- 底部：趋势 -->
      <div class="stat-card__footer" v-if="trend !== null && trend !== undefined">
        <span :class="trendClass">
          <i :class="trendIcon"></i>
          {{ Math.abs(trend) }}%
        </span>
        <span class="stat-card__trend-label">{{ trendLabel }}</span>
      </div>
      <!-- 自定义底部插槽 -->
      <div class="stat-card__footer" v-else-if="$slots.footer">
        <slot name="footer"></slot>
      </div>
    </template>
  </div>
</template>

<script>
export default {
  name: 'StatCard',
  props: {
    // 标题
    title: {
      type: String,
      required: true
    },
    // 数值
    value: {
      type: [Number, String],
      default: 0
    },
    // 图标类名
    icon: {
      type: String,
      default: ''
    },
    // 主题色：primary / success / warning / danger / info
    color: {
      type: String,
      default: 'default',
      validator: (val) => ['default', 'primary', 'success', 'warning', 'danger', 'info'].includes(val)
    },
    // 趋势值（百分比，正数为上升，负数为下降）
    trend: {
      type: Number,
      default: null
    },
    // 趋势标签
    trendLabel: {
      type: String,
      default: '较昨日'
    },
    // 帮助提示文字
    helpText: {
      type: String,
      default: ''
    },
    // 是否加载中
    loading: {
      type: Boolean,
      default: false
    },
    // 是否可点击
    clickable: {
      type: Boolean,
      default: false
    },
    // 数值格式化：number / money / percent
    format: {
      type: String,
      default: 'number'
    },
    // 小数位数
    precision: {
      type: Number,
      default: 0
    }
  },
  computed: {
    formattedValue() {
      const val = Number(this.value) || 0
      switch (this.format) {
        case 'money':
          return val.toLocaleString('en-US', {
            minimumFractionDigits: this.precision,
            maximumFractionDigits: this.precision
          })
        case 'percent':
          return val.toFixed(this.precision) + '%'
        default:
          if (val >= 10000) {
            return (val / 10000).toFixed(1) + 'w'
          }
          return val.toLocaleString()
      }
    },
    tagType() {
      const map = {
        default: 'info',
        primary: '',
        success: 'success',
        warning: 'warning',
        danger: 'danger',
        info: 'info'
      }
      return map[this.color] || 'info'
    },
    trendClass() {
      if (this.trend > 0) {return 'stat-card__trend stat-card__trend--up'}
      if (this.trend < 0) {return 'stat-card__trend stat-card__trend--down'}
      return 'stat-card__trend'
    },
    trendIcon() {
      if (this.trend > 0) {return 'el-icon-top'}
      if (this.trend < 0) {return 'el-icon-bottom'}
      return ''
    }
  },
  methods: {
    handleClick() {
      if (this.clickable) {
        this.$emit('click')
      }
    }
  }
}
</script>

<style scoped>
.stat-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
  position: relative;
  transition: all 0.3s;
  height: 100%;
  min-height: 120px;
  display: flex;
  flex-direction: column;
}

.stat-card--clickable {
  cursor: pointer;
}

.stat-card--clickable:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

/* 颜色主题 */
.stat-card--default {
  background: #f5f7fa;
}

.stat-card--primary {
  background: linear-gradient(135deg, #ecf5ff 0%, #d9ecff 100%);
}

.stat-card--primary .stat-card__value {
  color: #409eff;
}

.stat-card--success {
  background: linear-gradient(135deg, #f0f9eb 0%, #e1f3d8 100%);
}

.stat-card--success .stat-card__value {
  color: #67c23a;
}

.stat-card--warning {
  background: linear-gradient(135deg, #fdf6ec 0%, #faecd8 100%);
}

.stat-card--warning .stat-card__value {
  color: #e6a23c;
}

.stat-card--danger {
  background: linear-gradient(135deg, #fef0f0 0%, #fde2e2 100%);
}

.stat-card--danger .stat-card__value {
  color: #f56c6c;
}

.stat-card--info {
  background: linear-gradient(135deg, #f4f4f5 0%, #e9e9eb 100%);
}

.stat-card--info .stat-card__value {
  color: #909399;
}

/* 头部 */
.stat-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.stat-card__icon-tag {
  border-radius: 8px;
}

.stat-card__icon-tag i {
  font-size: 16px;
}

.stat-card__help {
  color: #909399;
  cursor: pointer;
  font-size: 14px;
}

.stat-card__help:hover {
  color: #409eff;
}

/* 主体 */
.stat-card__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.stat-card__value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  line-height: 1.2;
  margin-bottom: 4px;
}

.stat-card__title {
  font-size: 13px;
  color: #909399;
}

/* 底部趋势 */
.stat-card__footer {
  margin-top: 8px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-card__trend {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.stat-card__trend--up {
  color: #67c23a;
}

.stat-card__trend--down {
  color: #f56c6c;
}

.stat-card__trend-label {
  color: #c0c4cc;
}

/* 骨架屏 */
.stat-card__skeleton {
  padding: 10px 0;
}

/* 响应式 */
@media screen and (max-width: 768px) {
  .stat-card__value {
    font-size: 22px;
  }
}
</style>
