<!-- src/views/settings/Profile.vue -->
<template>
  <div class="profile-page">
    <!-- 账户信息 -->
    <div class="card">
      <h2 class="card-title">账户信息</h2>

      <div class="avatar-row">
        <el-avatar :size="72" class="avatar">U</el-avatar>
        <div class="avatar-actions">
          <el-button size="small">上传新头像</el-button>
          <el-button size="small" text>移除</el-button>
          <div class="hint">推荐 200×200，JPG / PNG，小于 2MB</div>
        </div>
      </div>

      <el-form label-width="100px" class="form">
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" placeholder="请输入昵称" />
        </el-form-item>

        <el-form-item label="邮箱">
          <el-input v-model="form.email" disabled />
          <span class="warn">未验证</span>
        </el-form-item>

        <el-form-item label="注册时间">
          <span class="readonly">{{ form.createdAt }}</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary">保存修改</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 安全 -->
    <div class="card">
      <h2 class="card-title">安全</h2>

      <div class="row">
        <div>
          <div class="row-title">修改密码</div>
          <div class="row-desc">建议定期更换，长度至少 8 位，包含大小写和数字</div>
        </div>
        <el-button>修改</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'

const form = reactive({
  nickname: 'Trader',
  email: 'user@example.com',
  createdAt: '2026-01-15',
  twoFA: false
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

.warn {
  margin-left: 12px;
  color: #F6465D;
  font-size: 12px;
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