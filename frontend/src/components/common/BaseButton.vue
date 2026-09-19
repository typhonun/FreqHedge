<!-- src/components/common/BaseButton.vue -->
<template>
  <button
    class="base-btn"
    :class="[`base-btn--${type}`, { 'is-loading': loading }]"
    :disabled="disabled || loading"
    @click="$emit('click')"
  >
    <slot></slot>
  </button>
</template>

<script setup>
defineProps({
  type: {
    type: String,
    default: 'primary', // 可选值: primary, ghost, outline
  },
  disabled: Boolean,
  loading: Boolean
})
defineEmits(['click'])
</script>

<style scoped>
.base-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
  outline: none;
}

/* 主按钮：对应“创建新机器人” */
.base-btn--primary {
  background-color: var(--primary-color);
  color: #000; /* 原图这里文字是深色 */
}
.base-btn--primary:hover {
  background-color: var(--primary-hover);
}

/* 幽灵按钮/文本按钮：对应顶部“专业套餐” */
.base-btn--ghost {
  background-color: transparent;
  color: var(--text-main);
  padding: 4px 8px;
}
.base-btn--ghost:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

/* 轮廓按钮 */
.base-btn--outline {
  background-color: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-main);
}
.base-btn--outline:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.base-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>