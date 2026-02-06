<template>
  <div class="ele-body">
    <el-card shadow="never">
      <!-- 搜索表单 -->
      <el-form
        :model="where"
        label-width="77px"
        class="ele-form-search"
        @keyup.enter.native="reload"
        @submit.native.prevent>
        <el-row :gutter="15">
          <el-col :lg="6" :md="12">
            <el-form-item label="用户账号:">
              <el-input
                v-model="where.username"
                placeholder="请输入用户账号"
                clearable/>
            </el-form-item>
          </el-col>
          <el-col :lg="6" :md="12">
            <div class="ele-form-actions">
              <el-button
                type="primary"
                @click="reload"
                icon="el-icon-search"
                class="ele-btn-icon">查询
              </el-button>
              <el-button @click="reset">重置</el-button>
            </div>
          </el-col>
        </el-row>
      </el-form>
      <!-- 数据表格 -->
      <ele-pro-table
        ref="table"
        :datasource="url"
        :columns="columns"
        :where="where"
        :parse-data="parseData"
        height="calc(100vh - 315px)">
        <!-- 表头工具栏 -->
        <template slot="toolbar">
          <el-button
            @click="exportData"
            type="primary"
            icon="el-icon-download"
            class="ele-btn-icon"
            size="small"
            v-if="permission.includes('sys:loginlog:export')">导出
          </el-button>
        </template>
        <!-- 操作类型列 -->
        <template slot="type" slot-scope="{row}">
          <el-tag
            :type="['success','danger','warning','info'][row.type-1]"
            size="mini">
            {{ ['登录系统', '注销系统', '操作日志'][row.type - 1] }}
          </el-tag>
        </template>
        <!-- 操作状态列 -->
        <template slot="status" slot-scope="{row}">
          <ele-dot :type="['', 'success'][row.status]" :ripple="row.status===0"
                   :text="['操作成功', '操作失败'][row.status]"/>
        </template>
        <!-- 操作列 -->
        <template slot="action" slot-scope="{row}">
          <el-popconfirm
            class="ele-action"
            title="确定要删除此登录日志吗？"
            @confirm="remove(row)">
            <el-link
              type="danger"
              slot="reference"
              :underline="false"
              icon="el-icon-delete"
              v-if="permission.includes('sys:loginlog:delete')">删除
            </el-link>
          </el-popconfirm>
        </template>
      </ele-pro-table>
    </el-card>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import XLSX from 'xlsx'

export default {
  name: 'SystemLoginLog',
  computed: {
    ...mapGetters(['permission'])
  },
  data() {
    return {
      // 表格数据接口
      url: '/loginlog/index',
      // 表格列配置
      columns: [
        {
          columnKey: 'selection',
          type: 'selection',
          width: 45,
          align: 'center',
          fixed: 'left'
        },
        {
          prop: 'id',
          label: 'ID',
          width: 60,
          align: 'center',
          showOverflowTooltip: true,
          fixed: 'left'
        },
        {
          prop: 'username',
          label: '操作账号',
          align: 'center',
          showOverflowTooltip: true,
          minWidth: 100
        },
        {
          prop: 'method',
          label: '请求方法',
          align: 'center',
          showOverflowTooltip: true,
          minWidth: 100
        },
        {
          prop: 'module',
          label: '操作模块',
          align: 'center',
          showOverflowTooltip: true,
          minWidth: 100
        },
        {
          prop: 'param',
          label: '请求参数',
          align: 'center',
          showOverflowTooltip: true,
          minWidth: 100
        },
        {
          prop: 'url',
          label: '请求地址',
          align: 'center',
          showOverflowTooltip: true,
          minWidth: 100
        },
        {
          prop: 'ip',
          label: 'IP地址',
          align: 'center',
          showOverflowTooltip: true,
          minWidth: 130
        },
        {
          prop: 'ip_city',
          label: 'IP所属地',
          align: 'center',
          showOverflowTooltip: true,
          minWidth: 120
        },
        {
          prop: 'os',
          label: '操作系统',
          align: 'center',
          showOverflowTooltip: true,
          minWidth: 100
        },
        {
          prop: 'browser',
          label: '浏览器',
          align: 'center',
          showOverflowTooltip: true,
          minWidth: 100
        },
        {
          prop: 'type',
          label: '操作类型',
          align: 'center',
          showOverflowTooltip: true,
          minWidth: 100,
          slot: 'type'
        },
        {
          prop: 'create_time',
          label: '操作时间',
          sortable: 'custom',
          showOverflowTooltip: true,
          minWidth: 160,
          formatter: (row, column, cellValue) => {
            return this.$util.toDateString(cellValue)
          }
        },
        {
          columnKey: 'action',
          label: '操作',
          width: 90,
          align: 'center',
          resizable: false,
          slot: 'action',
          fixed: 'right'
        }
      ],
      // 表格搜索条件
      where: {},
      // 筛选日期范围
      daterange: null,
      // 日期时间选择器快捷项
      pickerOptions: {
        shortcuts: [
          {
            text: '最近一周',
            onClick(picker) {
              const end = new Date()
              const start = new Date()
              start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
              picker.$emit('pick', [start, end])
            }
          },
          {
            text: '最近一个月',
            onClick(picker) {
              const end = new Date()
              const start = new Date()
              start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
              picker.$emit('pick', [start, end])
            }
          },
          {
            text: '最近三个月',
            onClick(picker) {
              const end = new Date()
              const start = new Date()
              start.setTime(start.getTime() - 3600 * 1000 * 24 * 90)
              picker.$emit('pick', [start, end])
            }
          }
        ]
      }
    }
  },
  methods: {
    /* 解析接口返回数据 */
    parseData(res) {
      // 如果返回的数据格式是 {list: [...], total: 100}，需要转换为 EleProTable 期望的格式
      if (res.data && typeof res.data === 'object' && res.data.list && Array.isArray(res.data.list)) {
        const total = res.data.total || 0
        res.data = res.data.list
        res.count = total
      }
      // 确保 data 是数组
      if (!Array.isArray(res.data)) {
        res.data = []
      }
      return res
    },
    /* 刷新表格 */
    reload() {
      this.$refs.table.reload({where: this.where})
    },
    /* 重置搜索 */
    reset() {
      this.where = {}
      this.daterange = null
      this.reload()
    },
    /* 日期选择改变回调 */
    onDateRangeChoose() {
      if (this.daterange && this.daterange.length === 2) {
        this.where.createTimeStart = this.daterange[0]
        this.where.createTimeEnd = this.daterange[1]
      } else {
        this.where.createTimeStart = null
        this.where.createTimeEnd = null
      }
    },
    /* 导出数据 */
    exportData() {
      const array = [['ID编号', '操作账号', '请求方法', '请求地址', 'IP地址', 'IP区域', '操作系统', '请求参数', '操作类型', '操作状态', '登录时间']]
      const loading = this.$loading({lock: true})
      this.$http.get('/loginlog/index?page=1&limit=2000').then(res => {
        loading.close()
        if (res.data.code === 0) {
          res.data.data.forEach(d => {
            array.push([
              d.id,
              d.username,
              d.method,
              d.operUrl,
              d.operIp,
              d.operLocation,
              d.os,
              d.requestParam,
              ['登录成功', '登录失败', '注销成功', '注销失败'][d.type - 1],
              ['操作成功', '操作失败'][d.status],
              this.$util.toDateString(d.createTime)
            ])
          })
          this.$util.exportSheet(XLSX, array, '登录日志')
        } else {
          this.$message.error(res.data.msg)
        }
      }).catch(e => {
        loading.close()
        this.$message.error(e.message)
      })
    },
    /* 删除 */
    remove(row) {
      const loading = this.$loading({lock: true})
      this.$http.delete('/loginlog/delete?id=' + row.id).then(res => {
        loading.close()
        if (res.data.code === 0) {
          this.$message.success(res.data.msg)
          this.reload()
        } else {
          this.$message.error(res.data.msg)
        }
      }).catch(e => {
        loading.close()
        this.$message.error(e.message)
      })
    }
  }
}
</script>

<style scoped>
</style>
