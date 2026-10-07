<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="brand">
        <div class="brand-logo">D</div>
        <h1 class="brand-title">重置密码</h1>
        <p class="brand-sub">为你的账号设置新密码</p>
      </div>

      <el-form v-if="token" ref="formRef" :model="form" :rules="rules">
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="新密码（至少 8 位）" size="large" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item prop="confirm">
          <el-input v-model="form.confirm" type="password" placeholder="确认新密码" size="large" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="onSubmit">
          确认重置
        </el-button>
      </el-form>

      <el-empty v-else description="链接无效，请重新申请" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/authStore'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const token = route.query.token || ''
const formRef = ref(null)
const loading = ref(false)
const form = reactive({ password: '', confirm: '' })

const validateConfirm = (_r, v, cb) =>
  v !== form.password ? cb(new Error('两次密码不一致')) : cb()

const rules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
  confirm: [{ required: true, validator: validateConfirm, trigger: 'blur' }],
}

const onSubmit = async () => {
  try { await formRef.value.validate() } catch { return }
  loading.value = true
  try {
    await auth.reset(token, form.password)
    ElMessage.success('密码已重置，请重新登录')
    router.push('/login')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '重置失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: radial-gradient(circle at 20% 20%, #1a1f2c 0%, #0b0d12 60%); padding: 20px;
}
.auth-card {
  width: 400px; background: rgba(20,24,32,0.9);
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
.submit-btn { width: 100%; }
</style>