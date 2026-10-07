<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="brand">
        <div class="brand-logo">D</div>
        <h1 class="brand-title">注册 DcaTp</h1>
        <p class="brand-sub">开启你的量化之旅</p>
      </div>

      <!-- ★ 错误横幅 -->
      <el-alert
        v-if="errorMsg"
        :title="errorMsg"
        type="error"
        show-icon
        :closable="false"
        class="error-alert"
      />

      <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="onSubmit">
        <el-form-item prop="email">
          <el-input
            v-model="form.email"
            placeholder="邮箱"
            size="large"
            :prefix-icon="Message"
            @input="errorMsg = ''"
          />
        </el-form-item>
        <el-form-item prop="nickname">
          <el-input v-model="form.nickname" placeholder="昵称（可选）" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码（至少 8 位）" size="large" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item prop="confirm">
          <el-input v-model="form.confirm" type="password" placeholder="确认密码" size="large" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="loading"
          :disabled="loading"
          @click="onSubmit"
        >
          注册
        </el-button>
      </el-form>

      <div class="auth-footer">
        已有账号？<router-link to="/login" class="link">去登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Message, Lock, User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/authStore'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const form = reactive({ email: '', nickname: '', password: '', confirm: '' })

const validateConfirm = (_r, v, cb) => {
  if (v !== form.password) cb(new Error('两次密码不一致'))
  else cb()
}

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
  confirm: [{ required: true, validator: validateConfirm, trigger: 'blur' }],
}

const onSubmit = async () => {
  // 1. 前端表单校验
  try { await formRef.value.validate() } catch { return }

  // 2. 进入 loading，清空旧错误
  loading.value = true
  errorMsg.value = ''

  try {
    await auth.register({
      email: form.email,
      password: form.password,
      nickname: form.nickname,
    })
    ElMessage.success('注册成功')
    router.push('/dashboard')
  } catch (e) {
    // ★ 3. 从多个可能的位置提取错误信息
    const detail =
      e?.response?.data?.detail ||       // FastAPI 标准
      e?.response?.data?.message ||
      e?.response?.data?.error ||
      e?.message ||                       // 网络层
      '注册失败，请稍后重试'

    errorMsg.value = typeof detail === 'string' ? detail : JSON.stringify(detail)
    ElMessage.error(errorMsg.value)
  } finally {
    // ★ 4. 无论成功失败，一定解除 loading
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: radial-gradient(circle at 20% 20%, #1a1f2c 0%, #0b0d12 60%);
  padding: 20px;
}
.auth-card {
  width: 400px; background: rgba(20, 24, 32, 0.9);
  border: 1px solid rgba(255,255,255,0.06); border-radius: 14px;
  padding: 40px 32px; box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}
.brand { text-align: center; margin-bottom: 28px; }
.brand-logo {
  width: 52px; height: 52px; border-radius: 14px;
  background: linear-gradient(135deg, #2bbdf6, #7c5cff);
  color: #fff; font-size: 26px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 12px;
}
.brand-title { margin: 0; font-size: 22px; color: #fff; font-weight: 600; }
.brand-sub { margin: 6px 0 0; font-size: 13px; color: #8b95a5; }

.error-alert {
  margin-bottom: 16px;
  border-radius: 8px;
}

.submit-btn { width: 100%; }
.auth-footer { text-align: center; margin-top: 20px; color: #8b95a5; font-size: 13px; }
.link { color: #2bbdf6; text-decoration: none; font-size: 13px; }
.link:hover { text-decoration: underline; }
</style>