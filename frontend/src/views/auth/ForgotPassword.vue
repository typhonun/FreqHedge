<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="brand">
        <div class="brand-logo">D</div>
        <h1 class="brand-title">忘记密码</h1>
        <p class="brand-sub">输入邮箱，我们会发送重置链接</p>
      </div>

      <template v-if="!sent">
        <el-form ref="formRef" :model="form" :rules="rules">
          <el-form-item prop="email">
            <el-input
              v-model="form.email"
              placeholder="邮箱"
              size="large"
              :prefix-icon="Message"
              @keyup.enter="onSubmit"
            />
          </el-form-item>
          <el-button
            type="primary"
            size="large"
            class="submit-btn"
            :loading="loading"
            @click="onSubmit"
          >
            发送重置链接
          </el-button>
        </el-form>
      </template>

      <!-- 成功页 -->
      <template v-else>
        <el-result
          icon="success"
          :title="devResetUrl ? '重置链接已生成' : '邮件已发送'"
          :sub-title="devResetUrl
            ? '开发模式：请点击下方链接重置密码'
            : '请检查你的邮箱（包括垃圾箱）'"
        >
          <template #extra>
            <!-- ★ 开发模式：显示可点击的重置链接 -->
            <div v-if="devResetUrl" class="dev-link-box">
              <p class="dev-link-tip">【开发模式】直接点击重置：</p>
              <router-link :to="resetPath" class="dev-link">
                {{ devResetUrl }}
              </router-link>
              <el-button
                size="small"
                text
                @click="copyDevLink"
                class="copy-btn"
              >
                复制链接
              </el-button>
            </div>

            <div class="result-actions">
              <el-button @click="reset">重新发送</el-button>
              <router-link to="/login">
                <el-button type="primary">返回登录</el-button>
              </router-link>
            </div>
          </template>
        </el-result>
      </template>

      <div class="auth-footer">
        想起来了？<router-link to="/login" class="link">去登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Message } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/authStore'

const auth = useAuthStore()
const formRef = ref(null)
const loading = ref(false)
const sent = ref(false)
const devResetUrl = ref('')
const form = reactive({ email: '' })

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
}

// 从完整 URL 里取出 path + query，方便 router-link 用
const resetPath = computed(() => {
  if (!devResetUrl.value) return '/login'
  try {
    const u = new URL(devResetUrl.value)
    return u.pathname + u.search
  } catch {
    return '/login'
  }
})

const onSubmit = async () => {
  try { await formRef.value.validate() } catch { return }

  loading.value = true
  try {
    const res = await auth.forgot(form.email)
    // 后端开发模式返回 { dev_mode: true, dev_reset_url: "..." }
    if (res?.dev_reset_url) {
      devResetUrl.value = res.dev_reset_url
    } else {
      devResetUrl.value = ''
    }
    sent.value = true
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '发送失败')
  } finally {
    loading.value = false
  }
}

const reset = () => {
  sent.value = false
  devResetUrl.value = ''
}

const copyDevLink = async () => {
  try {
    await navigator.clipboard.writeText(devResetUrl.value)
    ElMessage.success('链接已复制')
  } catch {
    ElMessage.warning('复制失败，请手动选中复制')
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
.auth-footer { text-align: center; margin-top: 20px; color: #8b95a5; font-size: 13px; }
.link { color: #2bbdf6; text-decoration: none; font-size: 13px; }
.link:hover { text-decoration: underline; }

/* ★ 开发模式链接样式 */
.dev-link-box {
  width: 100%;
  background: rgba(43, 189, 246, 0.08);
  border: 1px dashed rgba(43, 189, 246, 0.4);
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 16px;
  text-align: left;
}
.dev-link-tip {
  margin: 0 0 6px;
  font-size: 12px;
  color: #8b95a5;
}
.dev-link {
  display: block;
  color: #2bbdf6;
  font-size: 12px;
  word-break: break-all;
  text-decoration: none;
  line-height: 1.5;
}
.dev-link:hover { text-decoration: underline; }
.copy-btn {
  margin-top: 6px;
  padding: 0;
  font-size: 12px;
  color: #2bbdf6;
}

.result-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 8px;
}
</style>