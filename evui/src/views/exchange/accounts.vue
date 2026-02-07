<template>
  <div class="ele-body">
    <el-card shadow="never">
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-form :inline="true" size="small">
          <el-form-item label="交易所">
            <el-select v-model="where.exchange" placeholder="全部" clearable style="width:110px">
              <el-option label="Binance" value="binance"/>
              <el-option label="OKX" value="okx"/>
              <el-option label="Gate" value="gate"/>
            </el-select>
          </el-form-item>
          <el-form-item label="节点">
            <el-select v-model="where.node_id" placeholder="全部" clearable style="width:160px">
              <el-option v-for="n in nodes" :key="n.id" :label="n.name + ' (' + n.node_code + ')'" :value="n.id"/>
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="where.unassigned">仅未分配</el-checkbox>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" icon="el-icon-search" @click="fetchData">查询</el-button>
            <el-button icon="el-icon-refresh-left" @click="resetSearch">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 批量操作 -->
      <div class="batch-bar" v-if="selection.length > 0">
        <el-alert type="info" :closable="false" show-icon>
          <span>已选择 <strong>{{ selection.length }}</strong> 个账户</span>
          <el-button size="mini" type="primary" style="margin-left: 12px;" @click="showBatchAssign">批量分配节点</el-button>
          <el-button size="mini" type="warning" style="margin-left: 8px;" @click="handleBatchUnassign">批量解绑</el-button>
        </el-alert>
      </div>

      <el-table v-loading="loading" :data="list" stripe border style="width:100%; margin-top:12px" size="small"
        :header-cell-style="{background:'#fafafa'}" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="45"/>
        <el-table-column prop="id" label="ID" width="60" align="center"/>
        <el-table-column prop="tenant_id" label="租户ID" width="80" align="center"/>
        <el-table-column prop="user_email" label="用户" min-width="140" show-overflow-tooltip/>
        <el-table-column prop="exchange" label="交易所" width="100" align="center">
          <template slot-scope="{row}">
            <el-tag size="mini" :type="row.exchange === 'binance' ? 'warning' : row.exchange === 'okx' ? '' : 'success'">{{ row.exchange }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="account_type" label="账户类型" width="100" align="center">
          <template slot-scope="{row}">
            <el-tag size="mini" type="info">{{ row.account_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="API Key" width="130">
          <template slot-scope="{row}">
            <span style="font-family:monospace; font-size:12px">{{ row.api_key || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="合约余额" width="110" align="right">
          <template slot-scope="{row}">{{ formatNum(row.futures_balance) }}</template>
        </el-table-column>
        <el-table-column label="执行节点" width="120" align="center">
          <template slot-scope="{row}">
            <el-tag v-if="getNodeCode(row.execution_node_id)" size="mini" type="success">{{ getNodeCode(row.execution_node_id) }}</el-tag>
            <el-tag v-else size="mini" type="info">未分配</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="mini">{{ row.status === 1 ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template slot-scope="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template slot-scope="{row}">
            <el-button size="mini" type="primary" @click="showAssign(row)">分配节点</el-button>
            <el-button v-if="row.execution_node_id" size="mini" type="warning" @click="handleUnassign(row)">解绑</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && list.length === 0" description="暂无交易所账户"/>
      <div style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center;">
        <span style="color: #909399; font-size: 12px;">共 {{ total }} 条</span>
        <el-pagination background :current-page.sync="page" :page-size="pageSize" :total="total"
          layout="prev, pager, next" @current-change="fetchData"/>
      </div>
    </el-card>

    <!-- 分配节点弹窗 -->
    <el-dialog title="分配执行节点" :visible.sync="assignVisible" width="420px" :close-on-click-modal="false">
      <el-form label-width="80px" size="small">
        <el-form-item label="账户">
          <span v-if="assignRow">
            #{{ assignRow.id }} - {{ assignRow.exchange }} ({{ assignRow.account_type }})
          </span>
        </el-form-item>
        <el-form-item label="节点">
          <el-select v-model="assignNodeId" style="width:100%" placeholder="选择节点" clearable>
            <el-option v-for="n in nodes" :key="n.id" :label="n.name + ' (' + n.node_code + ')'" :value="n.id"/>
          </el-select>
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :loading="assigning" @click="handleAssign">确定</el-button>
      </div>
    </el-dialog>

    <!-- 批量分配弹窗 -->
    <el-dialog title="批量分配执行节点" :visible.sync="batchAssignVisible" width="420px" :close-on-click-modal="false">
      <el-alert type="info" :closable="false" style="margin-bottom:12px">
        将为 <strong>{{ selection.length }}</strong> 个账户分配节点
      </el-alert>
      <el-form label-width="80px" size="small">
        <el-form-item label="节点">
          <el-select v-model="batchNodeId" style="width:100%" placeholder="选择节点">
            <el-option v-for="n in nodes" :key="n.id" :label="n.name + ' (' + n.node_code + ')'" :value="n.id"/>
          </el-select>
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="batchAssignVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchAssigning" @click="handleBatchAssign">确定</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import {getExchangeAccounts, assignNode, batchAssignNode} from '@/api/admin'
import {getNodes} from '@/api/node'

export default {
  name: 'ExchangeAccountList',
  data() {
    return {
      loading: false, list: [], total: 0, page: 1, pageSize: 20,
      nodes: [], nodesMap: {},
      selection: [],
      where: {exchange: '', node_id: '', unassigned: false},
      assignVisible: false, assignRow: null, assignNodeId: null, assigning: false,
      batchAssignVisible: false, batchNodeId: null, batchAssigning: false
    }
  },
  mounted() {
    this.fetchNodes().then(() => this.fetchData())
  },
  methods: {
    formatNum(v) { return v != null ? parseFloat(v).toFixed(2) : '0.00' },
    formatTime(t) { return t ? t.replace('T', ' ').substring(0, 19) : '-' },
    getNodeCode(nodeId) {
      if (!nodeId) return ''
      const node = this.nodesMap[nodeId]
      return node ? node.node_code : `#${nodeId}`
    },
    handleSelectionChange(v) { this.selection = v },
    resetSearch() { this.where = {exchange: '', node_id: '', unassigned: false}; this.page = 1; this.fetchData() },
    showAssign(row) { this.assignRow = row; this.assignNodeId = row.execution_node_id || null; this.assignVisible = true },
    showBatchAssign() { this.batchNodeId = null; this.batchAssignVisible = true },
    async fetchNodes() {
      try {
        const res = await getNodes()
        this.nodes = res.data.data || []
        this.nodesMap = {}
        this.nodes.forEach(n => { this.nodesMap[n.id] = n })
      } catch (e) { console.error(e) }
    },
    async fetchData() {
      this.loading = true
      try {
        const params = {page: this.page, page_size: this.pageSize}
        if (this.where.exchange) params.exchange = this.where.exchange
        if (this.where.node_id) params.execution_node_id = this.where.node_id
        if (this.where.unassigned) params.unassigned = true
        const res = await getExchangeAccounts(params)
        this.list = res.data.data || []
        this.total = res.data.total || this.list.length
      } catch (e) { this.$message.error('获取交易所账户失败') }
      finally { this.loading = false }
    },
    async handleAssign() {
      this.assigning = true
      try {
        await assignNode(this.assignRow.id, {execution_node_id: this.assignNodeId || null})
        this.$message.success(this.assignNodeId ? '分配成功' : '已解绑节点')
        this.assignVisible = false
        this.fetchData()
      } catch (e) { this.$message.error(e.response?.data?.detail || '操作失败') }
      finally { this.assigning = false }
    },
    async handleUnassign(row) {
      try {
        await this.$confirm(`确认将账户 #${row.id} (${row.exchange}) 从节点解绑？`, '解绑节点', {
          confirmButtonText: '确认解绑',
          cancelButtonText: '取消',
          type: 'warning',
        })
        await assignNode(row.id, {execution_node_id: null})
        this.$message.success('已解绑节点，该账户将由本机执行')
        this.fetchData()
      } catch (e) {
        if (e !== 'cancel') {
          this.$message.error(e.response?.data?.detail || '解绑失败')
        }
      }
    },
    async handleBatchUnassign() {
      const ids = this.selection.filter(r => r.execution_node_id).map(r => r.id)
      if (ids.length === 0) {
        this.$message.warning('选中的账户均未绑定节点')
        return
      }
      try {
        await this.$confirm(`确认将 ${ids.length} 个账户从节点解绑？`, '批量解绑', {
          confirmButtonText: '确认解绑',
          cancelButtonText: '取消',
          type: 'warning',
        })
        await batchAssignNode({account_ids: ids, execution_node_id: null})
        this.$message.success(`已解绑 ${ids.length} 个账户`)
        this.fetchData()
      } catch (e) {
        if (e !== 'cancel') {
          this.$message.error(e.response?.data?.detail || '批量解绑失败')
        }
      }
    },
    async handleBatchAssign() {
      if (!this.batchNodeId) { this.$message.warning('请选择节点'); return }
      this.batchAssigning = true
      try {
        const ids = this.selection.map(r => r.id)
        await batchAssignNode({account_ids: ids, execution_node_id: this.batchNodeId})
        this.$message.success(`已为 ${ids.length} 个账户分配节点`)
        this.batchAssignVisible = false
        this.fetchData()
      } catch (e) { this.$message.error(e.response?.data?.detail || '批量分配失败') }
      finally { this.batchAssigning = false }
    }
  }
}
</script>

<style scoped>
.search-bar { margin-bottom: 8px; }
.batch-bar { margin-bottom: 8px; }
</style>
