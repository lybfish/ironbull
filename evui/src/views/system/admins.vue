<template>
  <div class="ele-body">
    <el-card shadow="never">
      <div class="toolbar">
        <el-button type="primary" size="small" icon="el-icon-plus" @click="showDialog()">新建管理员</el-button>
        <el-button size="small" icon="el-icon-refresh" @click="fetchData" :loading="loading">刷新</el-button>
      </div>
      <el-table v-loading="loading" :data="list" stripe border style="width:100%; margin-top:12px" size="small"
        :header-cell-style="{background:'#fafafa'}">
        <el-table-column prop="id" label="ID" width="60" align="center"/>
        <el-table-column prop="username" label="用户名" width="140"/>
        <el-table-column prop="nickname" label="昵称" width="140"/>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template slot-scope="{row}">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="mini">{{ row.status === 1 ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" width="170">
          <template slot-scope="{row}">{{ formatTime(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template slot-scope="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right" align="center">
          <template slot-scope="{row}">
            <el-button size="mini" @click="showDialog(row)">编辑</el-button>
            <el-button size="mini" :type="row.status === 1 ? 'warning' : 'success'" @click="handleToggle(row)">
              {{ row.status === 1 ? '禁用' : '启用' }}
            </el-button>
            <el-button size="mini" type="danger" @click="handleReset(row)">重置密码</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && list.length === 0" description="暂无管理员"/>
      <div v-if="total > 0" style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center;">
        <span style="color:#909399; font-size:12px">共 {{ total }} 条</span>
        <el-pagination background :current-page.sync="page" :page-size="pageSize" :total="total"
          layout="prev, pager, next" @current-change="fetchData"/>
      </div>
    </el-card>

    <!-- 新建/编辑弹窗 -->
    <el-dialog :title="editId ? '编辑管理员' : '新建管理员'" :visible.sync="dialogVisible" width="440px">
      <el-form :model="form" label-width="80px" :rules="rules" ref="adminForm">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="!!editId" placeholder="请输入用户名"/>
        </el-form-item>
        <el-form-item label="密码" v-if="!editId" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码"/>
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" placeholder="请输入昵称"/>
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确定</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import {getAdmins, createAdmin, updateAdmin, toggleAdmin, resetAdminPassword} from '@/api/admin'

export default {
  name: 'AdminManage',
  data() {
    return {
      loading: false, saving: false,
      list: [], total: 0, page: 1, pageSize: 20,
      dialogVisible: false, editId: null,
      form: {username: '', password: '', nickname: ''},
      rules: {
        username: [{required: true, message: '请输入用户名', trigger: 'blur'}],
        password: [{required: true, message: '请输入密码', trigger: 'blur'}, {min: 6, message: '密码至少6位', trigger: 'blur'}]
      }
    }
  },
  mounted() { this.fetchData() },
  methods: {
    formatTime(t) { return t ? t.replace('T', ' ').substring(0, 19) : '-' },
    showDialog(row) {
      if (row) {
        this.editId = row.id
        this.form = {username: row.username, password: '', nickname: row.nickname || ''}
      } else {
        this.editId = null
        this.form = {username: '', password: '', nickname: ''}
      }
      this.dialogVisible = true
      this.$nextTick(() => { this.$refs.adminForm && this.$refs.adminForm.clearValidate() })
    },
    async fetchData() {
      this.loading = true
      try {
        const res = await getAdmins({page: this.page, page_size: this.pageSize})
        this.list = res.data.data || []
        this.total = res.data.total || this.list.length
      } catch (e) {
        this.$message.error('获取管理员列表失败')
      } finally { this.loading = false }
    },
    async handleSave() {
      try { await this.$refs.adminForm.validate() } catch (e) { return }
      this.saving = true
      try {
        if (this.editId) {
          await updateAdmin(this.editId, {nickname: this.form.nickname})
        } else {
          await createAdmin(this.form)
        }
        this.$message.success('保存成功')
        this.dialogVisible = false
        this.fetchData()
      } catch (e) {
        this.$message.error(e.response ? e.response.data.detail : '保存失败')
      } finally { this.saving = false }
    },
    async handleToggle(row) {
      try {
        await toggleAdmin(row.id)
        this.$message.success('操作成功')
        this.fetchData()
      } catch (e) {
        this.$message.error(e.response ? e.response.data.detail : '操作失败')
      }
    },
    handleReset(row) {
      this.$prompt('请输入新密码', '重置密码 - ' + row.username, {
        inputType: 'password',
        inputPattern: /.{6,}/,
        inputErrorMessage: '密码至少6位'
      }).then(({value}) => {
        resetAdminPassword(row.id, {new_password: value}).then(() => {
          this.$message.success('密码已重置')
        }).catch(() => {
          this.$message.error('重置失败')
        })
      }).catch(() => {})
    }
  }
}
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 8px; }
</style>
