<!-- src/views/Settings.vue -->
<template>
  <div class="settings-page">
    <!-- 二级菜单 -->
    <aside class="settings-nav">
      <div class="nav-title">设置</div>

      <ul class="nav-list">
        <li
          v-for="item in menu"
          :key="item.path"
          :class="['nav-item', { active: isActive(item.path) }]"
          @click="go(item.path)"
        >
          <el-icon :size="16"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </li>
      </ul>
    </aside>

    <!-- 右侧内容 -->
    <section class="settings-content">
      <router-view />
    </section>
  </div>
</template>

<script setup>
import { useRouter, useRoute } from 'vue-router'
import {
  User, Setting, Key, TrendCharts, Warning,
  Bell, Folder, Delete
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

const menu = [
  { path: '/settings/profile',      label: '账户',        icon: User },
  { path: '/settings/preferences',  label: '偏好',        icon: Setting },
  { path: '/settings/exchanges',    label: '交易所 API',  icon: Key },
]

const isActive = (path) => route.path === path
const go = (path) => router.push(path)
</script>

<style scoped>
.settings-page {
  display: flex;
  gap: 20px;
  height: 100%;
}

/* ============ 二级菜单 ============ */
.settings-nav {
  width: 200px;
  flex-shrink: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px 8px;
  height: fit-content;
}

.nav-title {
  font-size: 14px;
  color: var(--text-muted);
  padding: 4px 12px 12px;
  font-weight: 600;
}

.nav-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  color: var(--text-muted);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 2px;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-main);
}

.nav-item.active {
  background: rgba(43, 189, 246, 0.14);
  color: var(--text-main);
  font-weight: 600;
}

/* ============ 右侧内容 ============ */
.settings-content {
  flex: 1;
  min-width: 0;
}
</style>