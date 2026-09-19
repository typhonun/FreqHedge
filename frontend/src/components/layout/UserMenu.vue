<!-- src/components/layout/UserMenu.vue -->
<template>
  <el-dropdown trigger="click" placement="bottom-end" popper-class="user-menu-popper">
    <!-- 触发区 -->
    <div class="trigger">
      <div class="plan-info">
        <span class="plan-name">专业套餐</span>
        <span class="plan-expiry">6天后过期</span>
      </div>
      <el-badge is-dot class="bell-badge">
        <el-icon :size="20"><Bell /></el-icon>
      </el-badge>
      <el-avatar :size="36" class="avatar">U</el-avatar>
    </div>

    <!-- 下拉菜单 -->
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item>
          <el-icon :size="16"><Tickets /></el-icon>
          <span class="menu-text">订阅</span>
        </el-dropdown-item>
        <el-dropdown-item>
          <el-icon :size="16"><Present /></el-icon>
          <span class="menu-text">促销码</span>
        </el-dropdown-item>
        <el-dropdown-item>
          <el-icon :size="16"><Setting /></el-icon>
          <span class="menu-text">设置</span>
        </el-dropdown-item>
        <el-dropdown-item>
          <el-icon :size="16"><Moon /></el-icon>
          <span class="menu-text">主题</span>
        </el-dropdown-item>
        <el-dropdown-item>
          <el-icon :size="16"><Connection /></el-icon>
          <span class="menu-text">语言</span>
        </el-dropdown-item>
        <el-dropdown-item divided>
          <el-icon :size="16"><SwitchButton /></el-icon>
          <span class="menu-text" style="color:#F6465D">退出登录</span>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup>
import {
  Bell, Tickets, Present, Setting,
  Moon, Connection, SwitchButton
} from '@element-plus/icons-vue'
</script>

<style scoped>
.trigger {
  display: flex;
  align-items: center;   /* 垂直居中 */
  gap: 18px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  transition: background 0.2s;
}
.trigger:hover {
  background: rgba(255, 255, 255, 0.05);
}

/* 套餐信息：改为左对齐 */
.plan-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;   /* 关键：左对齐 */
  line-height: 1.3;
}
.plan-name {
  font-size: 15px;           /* 原 13px */
  color: var(--text-main);
  font-weight: 600;
}
.plan-expiry {
  font-size: 12px;           /* 原 11px */
  color: #F6465D;
  margin-top: 2px;
}

.avatar {
  background: var(--primary-color);
  color: #000;
  font-weight: 600;
  font-size: 16px;
}
</style>

<!-- 下拉面板全局样式 -->
<style>
.user-menu-popper {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-color) !important;
  padding: 4px !important;
  /* 宽度增加两倍：约 150px -> 300px */
  min-width: 300px !important;
  width: 300px !important;
}

.user-menu-popper .el-dropdown-menu {
  background: transparent;
  padding: 6px;
  width: 100%;          /* 撑满外层 300px */
  min-width: 100%;
}

/* 菜单项：左对齐 + 字号加大 */
.user-menu-popper .el-dropdown-menu__item {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;                 /* 图标与文字间距略加大，配合宽面板 */
  color: var(--text-main);
  border-radius: 6px;
  font-size: 15px;
  line-height: 44px;         /* 行高略加大，视觉更舒展 */
  padding: 0 16px;           /* 左右内边距加大，避免贴边 */
}

.user-menu-popper .el-dropdown-menu__item:not(.is-disabled):hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--primary-color);
}

.user-menu-popper .el-dropdown-menu__item--divided {
  border-top: 1px solid var(--border-color);
  margin-top: 6px;
}

.user-menu-popper .el-dropdown-menu__item .el-icon {
  margin-right: 0;
}

.menu-text {
  flex: 1;
  text-align: left;
}
</style>