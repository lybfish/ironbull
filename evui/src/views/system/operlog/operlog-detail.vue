<!-- 详情弹窗 -->
<template>
  <el-dialog
    title="详情"
    width="640px"
    :visible="visible"
    :lock-scroll="false"
    :destroy-on-close="true"
    @update:visible="updateVisible">
    <el-form
      size="mini"
      label-width="82px"
      class="ele-form-detail">
      <el-row :gutter="15">
        <el-col :sm="12">
          <el-form-item label="操作模块:">
            <div class="ele-text-secondary">
              {{ data.module }}
            </div>
          </el-form-item>
          <el-form-item label="IP地址:">
            <div class="ele-text-secondary">
              {{ data.ip }}
            </div>
          </el-form-item>
          <el-form-item label="操作时间:">
            <div class="ele-text-secondary">
              {{ data.create_time | toDateString }}
            </div>
          </el-form-item>
        </el-col>
        <el-col :sm="12">
          <el-form-item label="操作人:">
            <div class="ele-text-secondary">
              {{ data.username }}
            </div>
          </el-form-item>
          <el-form-item label="IP区域:">
            <div class="ele-text-secondary">
              {{ data.ip_city }}
            </div>
          </el-form-item>
          <el-form-item label="日志类型:">
            <el-tag
              :type="['success','danger','warning','info'][data.type-1]"
              size="mini">
              {{ ['登录系统', '注销系统', '操作日志'][data.type-1] }}
            </el-tag>
          </el-form-item>
        </el-col>
      </el-row>
      <div style="margin: 12px 0;">
        <el-divider/>
      </div>
      <el-form-item label="请求地址:">
        <div class="ele-text-secondary">
          {{ data.url }}
        </div>
      </el-form-item>
      <el-form-item label="调用方法:">
        <div class="ele-text-secondary">
          {{ data.method }}
        </div>
      </el-form-item>
      <el-form-item label="用户代理:">
        <div class="ele-text-secondary">
          {{ data.user_agent }}
        </div>
      </el-form-item>
      <el-form-item label="请求参数:">
        <div class="ele-text-secondary">
          {{ data.param }}
        </div>
      </el-form-item>
    </el-form>
    <div slot="footer">
      <el-button @click="updateVisible(false)">关闭
      </el-button>
    </div>
  </el-dialog>
</template>

<script>
export default {
  name: 'OperRecordDetail',
  props: {
    // 弹窗是否打开
    visible: Boolean,
    // 数据
    data: Object
  },
  methods: {
    /* 更新visible */
    updateVisible(value) {
      this.$emit('update:visible', value)
    }
  }
}
</script>

<style scoped>
</style>
