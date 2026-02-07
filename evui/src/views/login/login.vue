<template>
  <div :class="['login-wrapper', ['', 'login-form-right', 'login-form-left'][direction]]">
    <el-form
      ref="form"
      size="large"
      :model="form"
      :rules="rules"
      class="login-form ele-bg-white"
      @keyup.enter.native="doSubmit">
      <h4>Aigo 管理后台</h4>
      <el-form-item prop="username">
        <el-input
          clearable
          v-model="form.username"
          prefix-icon="el-icon-user"
          :placeholder="$t('login.username')"/>
      </el-form-item>
      <el-form-item prop="password">
        <el-input
          show-password
          v-model="form.password"
          prefix-icon="el-icon-lock"
          :placeholder="$t('login.password')"/>
      </el-form-item>
      <div class="el-form-item">
        <el-checkbox v-model="form.remember">{{ $t('login.remember') }}</el-checkbox>
      </div>
      <div class="el-form-item">
        <el-button
          size="large"
          type="primary"
          class="login-btn"
          :loading="loading"
          @click="doSubmit">
          {{ loading ? $t('login.loading') : $t('login.login') }}
        </el-button>
      </div>
    </el-form>
    <div class="login-copyright">Copyright &copy; 2026 Aigo. All rights reserved.</div>
  </div>
</template>

<script>
import setting from '@/config/setting'

export default {
  name: 'Login',
  data() {
    return {
      direction: 0,
      loading: false,
      form: {
        username: '',
        password: '',
        remember: true
      }
    }
  },
  computed: {
    rules() {
      return {
        username: [
          {required: true, message: this.$t('login.username'), type: 'string', trigger: 'blur'}
        ],
        password: [
          {required: true, message: this.$t('login.password'), type: 'string', trigger: 'blur'}
        ]
      }
    }
  },
  mounted() {
    if (setting.takeToken()) {
      this.goHome()
    }
  },
  methods: {
    /* 提交登录 — 对接 IronBull POST /api/auth/login */
    doSubmit() {
      this.$refs.form.validate((valid) => {
        if (!valid) {
          return false
        }
        this.loading = true
        this.$http.post('/auth/login', {
          username: this.form.username,
          password: this.form.password
        }).then((res) => {
          this.loading = false
          if (res.data && res.data.token) {
            this.$message.success('登录成功')
            this.$store.dispatch('user/setToken', {
              token: res.data.token,
              remember: this.form.remember
            }).then(() => {
              // 缓存管理员名称
              if (res.data.admin) {
                setting.cacheUser({
                  nickname: res.data.admin.username || 'Admin',
                  username: res.data.admin.username,
                  admin_id: res.data.admin.id
                })
              }
              this.goHome()
            })
          } else {
            this.$message.error(res.data.detail || res.data.msg || '登录失败')
          }
        }).catch((e) => {
          this.loading = false
          if (e.response && e.response.data) {
            this.$message.error(e.response.data.detail || '登录失败')
          } else {
            this.$message.error(e.message || '网络错误')
          }
        })
      })
    },
    /* 跳转到首页 */
    goHome() {
      const query = this.$route.query
      const path = query && query.from ? query.from : '/'
      this.$router.push(path).catch(() => {})
    }
  }
}
</script>

<style scoped>
.login-wrapper {
  padding: 50px 20px;
  position: relative;
  box-sizing: border-box;
  background-image: url("~@/assets/bg-login.png");
  background-repeat: no-repeat;
  background-size: cover;
  min-height: 100vh;
}

.login-wrapper:before {
  content: "";
  background-color: rgba(0, 0, 0, .2);
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.login-form {
  margin: 0 auto;
  width: 380px;
  max-width: 100%;
  padding: 25px 30px;
  position: relative;
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.15);
  box-sizing: border-box;
  border-radius: 4px;
  z-index: 2;
}

.login-form-right .login-form {
  margin: 0 15% 0 auto;
}

.login-form-left .login-form {
  margin: 0 auto 0 15%;
}

.login-form h4 {
  text-align: center;
  margin: 0 0 25px 0;
}

.login-form > .el-form-item {
  margin-bottom: 25px;
}

.login-btn {
  display: block;
  width: 100%;
}

.login-copyright {
  color: #eee;
  padding-top: 20px;
  text-align: center;
  position: relative;
  z-index: 1;
}

@media screen and (min-height: 550px) {
  .login-form {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translateX(-50%);
    margin-top: -180px;
  }

  .login-form-right .login-form,
  .login-form-left .login-form {
    left: auto;
    right: 15%;
    transform: translateX(0);
    margin: -180px auto auto auto;
  }

  .login-form-left .login-form {
    right: auto;
    left: 15%;
  }

  .login-copyright {
    position: absolute;
    bottom: 20px;
    right: 0;
    left: 0;
  }
}

@media screen and (max-width: 768px) {
  .login-form-right .login-form,
  .login-form-left .login-form {
    left: 50%;
    right: auto;
    transform: translateX(-50%);
    margin-right: auto;
  }
}
</style>
