<!-- src/views/settings/Profile.vue -->
<template>
  <div class="profile-page">
    <!-- ============ 账户信息 ============ -->
    <div class="card">
      <h2 class="card-title">账户信息</h2>

      <!-- 头像 -->
      <div class="avatar-row">
        <el-avatar :size="72" class="avatar">
          {{ avatarLetter }}
        </el-avatar>
        <div class="avatar-actions">
          <el-button size="small" disabled>上传新头像</el-button>
          <el-button size="small" text disabled>移除</el-button>
          <div class="hint">推荐 200×200，JPG / PNG，小于 2MB（功能开发中）</div>
        </div>
      </div>

      <!-- 表单 -->
      <el-form
        ref="profileFormRef"
        :model="profileForm"
        :rules="profileRules"
        label-width="100px"
        class="form"
      >
        <el-form-item label="昵称" prop="nickname">
          <el-input
            v-model="profileForm.nickname"
            placeholder="请输入昵称"
            maxlength="32"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="邮箱">
          <el-input :model-value="auth.user?.email || '—'" disabled />

          <el-tag
            v-if="!auth.user?.is_verified"
            type="warning"
            size="small"
            effect="plain"
            style="margin-left: 12px"
          >
            未验证
          </el-tag>
          <el-tag
            v-else
            type="success"
            size="small"
            effect="plain"
            style="margin-left: 12px"
          >
            已验证
          </el-tag>

          <!-- ★ 未验证时提供重发按钮 -->
          <el-button
            v-if="!auth.user?.is_verified"
            size="small"
            text
            type="primary"
            :loading="sendingVerify"
            style="margin-left: 8px"
            @click="handleSendVerifyEmail"
          >
            重新发送验证邮件
          </el-button>
        </el-form-item>

        <el-form-item label="注册时间">
          <span class="readonly">{{ createdText }}</span>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="savingProfile"
            :disabled="!profileChanged"
            @click="handleSaveProfile"
          >
            保存修改
          </el-button>
          <el-button
            v-if="profileChanged"
            @click="resetProfileForm"
          >
            取消
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- ============ 安全 ============ -->
    <div class="card">
      <h2 class="card-title">安全</h2>

      <div class="row">
        <div>
          <div class="row-title">修改密码</div>
          <div class="row-desc">建议定期更换，长度至少 6 位</div>
        </div>
        <el-button @click="pwdDialogVisible = true">修改</el-button>
      </div>
    </div>

    <!-- ============ 修改密码弹窗 ============ -->
    <el-dialog
      v-model="pwdDialogVisible"
      title="修改密码"
      width="440px"
      :close-on-click-modal="false"
      @closed="resetPwdForm"
    >
      <el-form
        ref="pwdFormRef"
        :model="pwdForm"
        :rules="pwdRules"
        label-width="90px"
      >
        <el-form-item label="原密码" prop="oldPassword">
          <el-input
            v-model="pwdForm.oldPassword"
            type="password"
            placeholder="请输入原密码"
            show-password
            autocomplete="off"
          />
        </el-form-item>

        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="pwdForm.newPassword"
            type="password"
            placeholder="至少 8 位"
            show-password
            autocomplete="off"
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="pwdForm.confirmPassword"
            type="password"
            placeholder="再次输入新密码"
            show-password
            autocomplete="off"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="savingPwd"
          @click="handleChangePassword"
        >
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/authStore'
import { useRouter } from 'vue-router'
const router = useRouter()

const auth = useAuthStore()

/* ══════════════════════════════════════════════════════════════════
 * 账户信息表单
 * ══════════════════════════════════════════════════════════════════ */
const profileFormRef = ref(null)
const savingProfile = ref(false)

const profileForm = reactive({
  nickname: '',
})

// 原始昵称（用于对比是否变化）
const originNickname = ref('')

const profileRules = {
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    { min: 1, max: 32, message: '昵称长度 1-32 个字符', trigger: 'blur' },
  ],
}

// 头像首字母
const avatarLetter = computed(() => {
  const n = auth.user?.nickname || auth.user?.email || 'U'
  return n.charAt(0).toUpperCase()
})

// 注册时间格式化
const createdText = computed(() => {
  const t = auth.user?.created_at
  if (!t) return '—'
  try {
    const d = new Date(t)
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  } catch {
    return String(t)
  }
})

// 表单是否变化（启用"保存"按钮）
const profileChanged = computed(() => {
  return profileForm.nickname.trim() !== originNickname.value
})

// 从 auth.user 同步到表单
const syncProfileForm = () => {
  profileForm.nickname = auth.user?.nickname || ''
  originNickname.value = auth.user?.nickname || ''
}

// 取消修改
const resetProfileForm = () => {
  syncProfileForm()
}

// 保存
const handleSaveProfile = async () => {
  try {
    await profileFormRef.value.validate()
  } catch {
    return
  }

  savingProfile.value = true
  try {
    await auth.updateProfile(profileForm.nickname.trim())
    originNickname.value = profileForm.nickname.trim()
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    savingProfile.value = false
  }
}

const sendingVerify = ref(false)

const handleSendVerifyEmail = async () => {
  sendingVerify.value = true
  try {
    await auth.sendVerifyEmail()   // ← 需要新增 action
    ElMessage.success('验证邮件已发送，请查收')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '发送失败')
  } finally {
    sendingVerify.value = false
  }
}

/* ══════════════════════════════════════════════════════════════════
 * 修改密码
 * ══════════════════════════════════════════════════════════════════ */
const pwdDialogVisible = ref(false)
const pwdFormRef = ref(null)
const savingPwd = ref(false)

const pwdForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const validateConfirm = (_r, v, cb) => {
  if (v !== pwdForm.newPassword) cb(new Error('两次密码不一致'))
  else cb()
}

const pwdRules = {
  oldPassword: [
    { required: true, message: '请输入原密码', trigger: 'blur' },
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, validator: validateConfirm, trigger: 'blur' },
  ],
}

const resetPwdForm = () => {
  pwdFormRef.value?.clearValidate()
  pwdForm.oldPassword = ''
  pwdForm.newPassword = ''
  pwdForm.confirmPassword = ''
}

const handleChangePassword = async () => {
  try {
    await pwdFormRef.value.validate()
  } catch {
    return
  }

  savingPwd.value = true
  try {
    await auth.changePassword(pwdForm.oldPassword, pwdForm.newPassword)
    ElMessage.success('密码修改成功，请重新登录')

    // ★ 强制登出
    setTimeout(() => {
      auth.logout()
      router.push('/login')
    }, 800)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '修改失败')
  } finally {
    savingPwd.value = false
  }
}

/* ══════════════════════════════════════════════════════════════════
 * 生命周期
 * ══════════════════════════════════════════════════════════════════ */
onMounted(async () => {
  // 如果 store 里没有 user（比如直接刷新进这个页面），拉一次
  if (!auth.user) {
    await auth.fetchMe()
  }
  syncProfileForm()
})
</script>

<style scoped>
.profile-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 24px;
}

.card-title {
  margin: 0 0 20px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.avatar-row {
  display: flex;
  align-items: center;
  gap: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 20px;
}

.avatar {
  background: var(--primary-color);
  color: #000;
  font-size: 28px;
  font-weight: 600;
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hint {
  font-size: 12px;
  color: var(--text-muted);
}

.form {
  max-width: 560px;
}

.readonly {
  color: var(--text-muted);
}

.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.row-title {
  font-size: 14px;
  color: var(--text-main);
  margin-bottom: 4px;
}

.row-desc {
  font-size: 12px;
  color: var(--text-muted);
}
</style>