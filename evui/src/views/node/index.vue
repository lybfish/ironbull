<template>
  <div class="ele-body">
    <!-- 统计卡片 -->
    <el-row :gutter="15" style="margin-bottom: 15px;">
      <el-col :lg="8" :md="12" :sm="12">
        <stat-card
          title="总节点数"
          :value="stats.total"
          icon="el-icon-s-platform"
          color="primary"
          :loading="loading" />
      </el-col>
      <el-col :lg="8" :md="12" :sm="12">
        <stat-card
          title="在线节点"
          :value="stats.online"
          icon="el-icon-success"
          color="success"
          :loading="loading" />
      </el-col>
      <el-col :lg="8" :md="12" :sm="12">
        <stat-card
          title="离线节点"
          :value="stats.offline"
          icon="el-icon-error"
          color="danger"
          :loading="loading" />
      </el-col>
    </el-row>

    <!-- 主内容区 -->
    <el-card shadow="never">
      <div class="toolbar">
        <el-button type="primary" size="small" icon="el-icon-plus" @click="showDialog()">新建节点</el-button>
        <el-button size="small" icon="el-icon-refresh" @click="fetchData">刷新</el-button>
      </div>
      <el-table v-loading="loading" :data="list" stripe border style="width:100%; margin-top:12px" size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="node_code" label="节点编码" width="120" />
        <el-table-column prop="name" label="名称" width="150" />
        <el-table-column prop="base_url" label="地址" width="220">
          <template slot-scope="{row}">
            <span :title="row.base_url">{{ truncateUrl(row.base_url) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100" align="center">
          <template slot-scope="{row}">
            <el-tag :type="isNodeOnline(row) ? 'success' : 'info'" size="mini">
              {{ isNodeOnline(row) ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="account_count" label="绑定账户" width="90" align="center" />
        <el-table-column prop="last_heartbeat_at" label="最后心跳" width="170">
          <template slot-scope="{row}">
            {{ formatDateTime(row.last_heartbeat_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template slot-scope="{row}">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template slot-scope="{row}">
            <el-button size="mini" @click="showDialog(row)">编辑</el-button>
            <el-button size="mini" type="info" @click="viewAccounts(row)">查看账户</el-button>
            <el-button size="mini" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog :title="editId ? '编辑节点' : '新建节点'" :visible.sync="dialogVisible" width="480px">
      <el-form ref="form" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="节点编码" prop="node_code">
          <el-input v-model="form.node_code" :disabled="!!editId" placeholder="唯一标识" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="节点名称" />
        </el-form-item>
        <el-form-item label="基础地址" prop="base_url">
          <el-input v-model="form.base_url" placeholder="如 http://192.168.1.10:19101" />
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确定</el-button>
      </div>
    </el-dialog>

    <!-- 账户列表对话框 -->
    <el-dialog title="节点关联账户" :visible.sync="accountsVisible" width="700px">
      <el-table :data="nodeAccounts" stripe border size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="exchange" label="交易所" width="100" />
        <el-table-column prop="account_label" label="标签" width="150" />
        <el-table-column prop="tenant_name" label="租户" width="120" />
        <el-table-column prop="api_key" label="API Key" show-overflow-tooltip>
          <template slot-scope="{row}">
            {{ maskApiKey(row.api_key) }}
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loadingAccounts && nodeAccounts.length === 0" description="暂无关联账户" />
    </el-dialog>
  </div>
</template>

<script>
import {getNodes, createNode, updateNode, deleteNode, getNodeAccounts} from '@/api/node'

export default {
  name: 'NodeManage',
  data() {
    return {
      loading: false,
      saving: false,
      loadingAccounts: false,
      list: [],
      stats: {
        total: 0,
        online: 0,
        offline: 0
      },
      dialogVisible: false,
      editId: null,
      form: {node_code: '', name: '', base_url: ''},
      rules: {
        node_code: [
          {required: true, message: '请输入节点编码', trigger: 'blur'},
          {min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur'}
        ],
        name: [
          {required: true, message: '请输入节点名称', trigger: 'blur'},
          {min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur'}
        ],
        base_url: [
          {required: true, message: '请输入基础地址', trigger: 'blur'},
          {type: 'url', message: '请输入有效的URL地址', trigger: 'blur'}
        ]
      },
      accountsVisible: false,
      nodeAccounts: []
    }
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    async fetchData() {
      this.loading = true
      try {
        const res = await getNodes()
        this.list = res.data.data || []
        this.calculateStats()
      } catch (e) {
        this.$message.error('获取节点列表失败')
      } finally {
        this.loading = false
      }
    },
    calculateStats() {
      this.stats.total = this.list.length
      this.stats.online = this.list.filter(node => this.isNodeOnline(node)).length
      this.stats.offline = this.stats.total - this.stats.online
    },
    isNodeOnline(node) {
      if (!node.last_heartbeat_at) return false
      const heartbeatTime = new Date(node.last_heartbeat_at).getTime()
      const now = Date.now()
      // 如果心跳时间在5分钟内，认为在线
      return (now - heartbeatTime) < 5 * 60 * 1000
    },
    truncateUrl(url) {
      if (!url) return '-'
      if (url.length <= 30) return url
      return url.substring(0, 27) + '...'
    },
    formatDateTime(datetime) {
      if (!datetime) return '-'
      return new Date(datetime).toLocaleString('zh-CN')
    },
    maskApiKey(apiKey) {
      if (!apiKey) return '-'
      if (apiKey.length <= 8) return apiKey
      return apiKey.substring(0, 4) + '****' + apiKey.substring(apiKey.length - 4)
    },
    showDialog(row) {
      if (row) {
        this.editId = row.id
        this.form = {
          node_code: row.node_code,
          name: row.name,
          base_url: row.base_url || ''
        }
      } else {
        this.editId = null
        this.form = {node_code: '', name: '', base_url: ''}
      }
      this.dialogVisible = true
      this.$nextTick(() => {
        if (this.$refs.form) {
          this.$refs.form.clearValidate()
        }
      })
    },
    async handleSave() {
      this.$refs.form.validate(async (valid) => {
        if (!valid) return
        this.saving = true
        try {
          if (this.editId) {
            await updateNode(this.editId, {
              name: this.form.name,
              base_url: this.form.base_url
            })
          } else {
            await createNode(this.form)
          }
          this.$message.success('保存成功')
          this.dialogVisible = false
          this.fetchData()
        } catch (e) {
          const msg = e.response?.data?.detail || e.message || '保存失败'
          this.$message.error(msg)
        } finally {
          this.saving = false
        }
      })
    },
    handleDelete(row) {
      this.$confirm('确定删除节点 ' + row.name + '?', '提示', {type: 'warning'}).then(async () => {
        try {
          await deleteNode(row.id)
          this.$message.success('已删除')
          this.fetchData()
        } catch (e) {
          const msg = e.response?.data?.detail || e.message || '删除失败'
          this.$message.error(msg)
        }
      }).catch(() => {})
    },
    async viewAccounts(row) {
      this.accountsVisible = true
      this.loadingAccounts = true
      try {
        const res = await getNodeAccounts(row.id)
        this.nodeAccounts = res.data.data || []
      } catch (e) {
        this.$message.error('获取关联账户失败')
        this.nodeAccounts = []
      } finally {
        this.loadingAccounts = false
      }
    }
  }
}
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
