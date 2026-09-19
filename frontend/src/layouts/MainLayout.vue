<!-- src/layouts/MainLayout.vue -->
<template>
  <el-container class="layout">
    <!-- 侧边栏 -->
    <el-aside width="280px" class="sidebar">
      <div class="logo">
        <span class="logo-text">DcaTp Manager</span>
      </div>

      <el-menu
        router
        :default-active="$route.path"
        class="side-menu"
        background-color="transparent"
        text-color="#848E9C"
        active-text-color="#FFFFFF"
      >
        <el-menu-item index="/dashboard">
          <el-icon :size="20"><Odometer /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/control">
          <el-icon :size="20"><Monitor /></el-icon>
          <span>控制中心</span>
        </el-menu-item>
        <el-menu-item index="/strategyConfig">
          <el-icon :size="20"><SetUp /></el-icon>
          <span>策略配置</span>
        </el-menu-item>
        <el-menu-item index="/charts">
          <el-icon :size="20"><TrendCharts /></el-icon>
          <span>K线分析</span>
        </el-menu-item>
        <el-menu-item index="/logs">
          <el-icon :size="20"><Document /></el-icon>
          <span>系统日志</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <!-- 顶栏 -->
      <el-header class="topbar" height="72px">
        <div class="page-title">{{ pageTitle }}</div>
        <div class="topbar-right">
          <UserMenu />
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Odometer, Monitor, SetUp, TrendCharts, Document
} from '@element-plus/icons-vue'
import UserMenu from '@/components/layout/UserMenu.vue'

const route = useRoute()
const pageTitle = computed(() => route.meta?.title || '仪表盘')
</script>

<style scoped>
.layout {
  height: 100vh;
}

/* ============ 侧边栏 ============ */
.sidebar {
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-color);
}

.logo {
  height: 72px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 24px;
  color: var(--text-main);
  font-size: 24px;   /* 原来 18px，加大 */
  font-weight: 700;
  border-bottom: 1px solid var(--border-color);
}
.logo-mark {
  color: var(--primary-color);
  font-weight: 900;
  font-size: 22px;
}
.logo-text {
  letter-spacing: 0.3px;
}

/* 菜单容器 */
.side-menu {
  flex: 1;
  border-right: none;
  padding: 16px 12px;
}

/* 菜单项：加大高度与字体 */
.side-menu .el-menu-item {
  height: 80px;          /* 原 44px */
  line-height: 52px;
  margin: 6px 0;
  padding-left: 20px !important;  /* 覆盖 el-menu 默认 */
  border-radius: 8px;
  font-size: 18px;       /* 原 14px */
  font-weight: 500;
}

/* 图标与文字间距 */
.side-menu .el-menu-item .el-icon {
  margin-right: 14px;
}

/* hover */
.side-menu .el-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.06);
  color: var(--text-main);
}

/* 选中态 */
.side-menu .el-menu-item.is-active {
  background-color: rgba(43, 189, 246, 0.14);
  color: var(--text-main);
  font-weight: 600;
}

/* 选中态左侧小竖条（可选） */
.side-menu .el-menu-item.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 20%;
  height: 60%;
  width: 3px;
  background: var(--primary-color);
  border-radius: 0 4px 4px 0;
}
.side-menu .el-menu-item {
  position: relative;
}

/* ============ 顶栏 ============ */
.topbar {
  background: var(--bg-dark);
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  padding: 0 28px;
}

.page-title {
  font-size: 20px;      /* 原 18px */
  font-weight: 600;
  color: var(--text-main);
}

/* ============ 主内容 ============ */
.main-content {
  background: var(--bg-dark);
  padding: 24px 28px;
  overflow: auto;
}
</style>