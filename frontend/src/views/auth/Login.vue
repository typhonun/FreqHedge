<!-- src/views/auth/Login.vue -->
<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="brand">
        <div class="brand-logo">D</div>
        <h1 class="brand-title">DcaTp</h1>
        <p class="brand-sub">登录你的量化账户</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="onSubmit">
        <el-form-item prop="email">
          <el-input
            v-model="form.email"
            placeholder="邮箱"
            size="large"
            :prefix-icon="Message"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
            :prefix-icon="Lock"
            @keyup.enter="onSubmit"
          />
        </el-form-item>

        <div class="auth-row">
          <el-checkbox v-model="form.remember">记住我</el-checkbox>
          <router-link to="/forgot-password" class="link">忘记密码？</router-link>
        </div>

        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="loading"
          @click="onSubmit"
        >
          登录
        </el-button>
      </el-form>

      <div class="auth-footer">
        还没有账号？
        <router-link to="/register" class="link">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Message, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/authStore'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref(null)
const loading = ref(false)
const form = reactive({ email: '', password: '', remember: true })

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
}

const onSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await auth.login({ email: form.email, password: form.password })
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/dashboard'
    router.push(redirect)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 20% 20%, #1a1f2c 0%, #0b0d12 60%);
  padding: 20px;
}

.auth-card {
  width: 400px;
  background: rgba(20, 24, 32, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  padding: 40px 32px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
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

.auth-row {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 20px;
}
.link { color: #2bbdf6; text-decoration: none; font-size: 13px; }
.link:hover { text-decoration: underline; }

.submit-btn { width: 100%; }

.auth-footer {
  text-align: center; margin-top: 20px; color: #8b95a5; font-size: 13px;
}
</style>