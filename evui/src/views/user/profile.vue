<template>
  <div class="ele-body">
    <el-card shadow="never">
      <div slot="header">
        <span>基本信息</span>
      </div>
      <el-form
        ref="infoForm"
        :model="form"
        :rules="rules"
        label-width="90px"
        style="max-width: 500px;padding: 20px 0;"
        @keyup.enter.native="save"
        @submit.native.prevent>
        <el-form-item label="头像:">
          <uploadImage :limit="1" v-model="form.avatar"></uploadImage>
        </el-form-item>
        <el-form-item label="姓名:" prop="realname">
          <el-input v-model="form.realname" placeholder="请输入姓名" clearable/>
        </el-form-item>
        <el-form-item label="昵称:" prop="nickname">
          <el-input v-model="form.nickname" placeholder="请输入昵称" clearable/>
        </el-form-item>
        <el-form-item label="性别:" prop="gender">
          <el-select v-model="form.gender" placeholder="请选择性别" class="ele-fluid" clearable>
            <el-option label="男" :value="1"/>
            <el-option label="女" :value="2"/>
            <el-option label="保密" :value="3"/>
          </el-select>
        </el-form-item>
        <el-form-item label="联系方式:" prop="mobile">
          <el-input v-model="form.mobile" placeholder="请输入联系方式" clearable/>
        </el-form-item>
        <el-form-item label="邮箱:" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" clearable/>
        </el-form-item>
        <el-form-item label="详细地址:">
          <el-input v-model="form.address" placeholder="请输入详细地址" clearable/>
        </el-form-item>
        <el-form-item label="个人简介:">
          <el-input v-model="form.intro" placeholder="请输入个人简介" :rows="4" type="textarea"/>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            @click="save"
            :loading="loading">保存更改
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import setting from '@/config/setting'
import uploadImage from '@/components/uploadImage'

export default {
  name: 'UserInfo',
  components: {uploadImage},
  data() {
    return {
      // 表单数据
      form: {},
      // 表单验证规则
      rules: {
        realname: [
          {required: true, message: '请输入姓名', trigger: 'blur'}
        ],
        nickname: [
          {required: true, message: '请输入昵称', trigger: 'blur'}
        ],
        gender: [
          {required: true, message: '请选择性别', trigger: 'blur'}
        ],
        email: [
          {required: true, message: '请输入邮箱', trigger: 'blur'}
        ]
      },
      // 保存按钮loading
      loading: false
    }
  },
  mounted() {
    // 获取用户信息
    this.getUserInfo()
  },
  methods: {
    /* 获取当前用户信息 */
    getUserInfo() {
      if (setting.userUrl) {
        this.$http.get(setting.userUrl).then((res) => {
          const result = setting.parseUser ? setting.parseUser(res.data) : res.data
          if (result.code === 0) {
            // 赋予对象值
            this.form = JSON.parse(JSON.stringify(result.data))
          } else {
            this.$message.error(result.msg)
          }
        }).catch((e) => {
          console.error(e)
          this.$message.error(e.message)
        })
      }
    },
    /* 保存更改 */
    save() {
      this.$refs['infoForm'].validate((valid) => {
        if (valid) {
          this.loading = true
          this.$http.post('/index/updateUserInfo', this.form).then(res => {
            this.loading = false
            if (res.data.code === 0) {
              this.$message.success('保存成功')
            } else {
              this.$message.error(res.data.msg)
            }
          }).catch(e => {
            this.loading = false
            this.$message.error(e.message)
          })
        } else {
          return false
        }
      })
    }
  }
}
</script>

<style scoped>
.ele-body {
  padding-bottom: 0;
}

.el-card {
  margin-bottom: 15px;
}
</style>
