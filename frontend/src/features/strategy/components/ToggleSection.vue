<!-- src/features/strategy/components/ToggleSection.vue -->
<template>
  <div
    class="toggle-section"
    :class="[`mode-${mode}`, { 'is-open': modelValue }]"
  >
    <!-- 头部 -->
    <div
      class="toggle-head"
      :class="{ 'is-clickable': mode === 'arrow' }"
      @click="onHeadClick"
    >
      <div class="toggle-head__left">
        <!-- 下拉箭头（仅 arrow 模式） -->
        <el-icon
          v-if="mode === 'arrow'"
          class="toggle-head__arrow"
          :class="{ 'is-open': modelValue }"
        >
          <ArrowRight />
        </el-icon>

        <span class="toggle-head__title">{{ title }}</span>

        <!-- 业务开关（仅 switch 模式） -->
        <el-switch
          v-if="mode === 'switch'"
          class="toggle-head__switch"
          :model-value="modelValue"
          size="small"
          @update:model-value="onSwitch"
          @click.stop
        />

        <el-tag
          v-if="tag"
          :type="modelValue ? 'success' : 'info'"
          size="small"
          effect="plain"
        >
          {{ modelValue ? tag.on : tag.off }}
        </el-tag>
      </div>

      <div class="toggle-head__right">
        <span v-if="desc" class="toggle-head__desc">{{ desc }}</span>
        <!-- 自定义操作区（如"新增规则"按钮） -->
        <div v-if="$slots.extra" class="toggle-head__extra" @click.stop>
          <slot name="extra" />
        </div>
      </div>
    </div>

    <!-- 内容：收起时不渲染，避免空白条 -->
    <div v-if="modelValue" class="toggle-body">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { ArrowRight } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  desc: { type: String, default: '' },
  tag: { type: Object, default: null },
  /**
   * 头部控件模式：
   *  - 'switch'（默认）：业务开关
   *  - 'arrow'：下拉箭头（纯展开收起，无业务含义）
   */
  mode: {
    type: String,
    default: 'switch',
    validator: (v) => ['switch', 'arrow'].includes(v),
  },
})

const emit = defineEmits(['update:modelValue'])

const onSwitch = (val) => {
  emit('update:modelValue', val)
}

// arrow 模式下点击整行都可以展开/收起
const onHeadClick = () => {
  if (props.mode !== 'arrow') return
  emit('update:modelValue', !props.modelValue)
}
</script>

<style scoped>
.toggle-section {
  border-radius: 8px;
  margin: 0;
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
  transition: border-color 0.15s ease;
  overflow: hidden;
}

.toggle-section + .toggle-section {
  margin-top: 6px;
}

.toggle-section.is-open {
  border-color: var(--el-color-primary-light-7);
}

/* ============ 头部 ============ */
.toggle-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  user-select: none;
}

.toggle-head.is-clickable {
  cursor: pointer;
}
.toggle-head.is-clickable:hover {
  background: var(--el-fill-color);
}

.toggle-section.is-open .toggle-head {
  background: var(--el-color-primary-light-9);
}

.toggle-head__left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

/* 下拉箭头 */
.toggle-head__arrow {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  transition: transform 0.2s;
  flex: none;
}
.toggle-head__arrow.is-open {
  transform: rotate(90deg);
}

.toggle-head__title {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toggle-head__switch {
  flex: none;
}

.toggle-head__right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.toggle-head__desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

/* ============ 内容 ============ */
.toggle-body {
  padding: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>