<template>
  <el-card class="toggle-section" :class="{ 'is-open': modelValue }" shadow="never">
    <template #header>
      <div class="toggle-head">
        <!-- 左侧：标题 + 开关（可选） -->
        <div class="toggle-head__left">
          <span class="toggle-head__title">{{ title }}</span>

          <!-- ★ 只有 hideSwitch=false 时才显示开关 -->
          <el-switch
            v-if="!hideSwitch"
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

        <!-- 右侧：说明文字 -->
        <div class="toggle-head__right">
          <span v-if="desc" class="toggle-head__desc">{{ desc }}</span>
        </div>
      </div>
    </template>

    <div v-show="modelValue" class="toggle-body">
      <slot />
    </div>
  </el-card>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  desc: { type: String, default: '' },
  icon: { type: [String, Object], default: null },
  tag: { type: Object, default: null },
  hideSwitch: { type: Boolean, default: false }   // ★ 新增
})

const emit = defineEmits(['update:modelValue'])

const onSwitch = (val) => {
  emit('update:modelValue', val)
}
</script>

<style scoped>
.toggle-section {
  border-radius: 8px;
  margin: 0;
  border: 1px solid var(--el-border-color-lighter);
  transition: all 0.15s ease;
}

.toggle-section + .toggle-section {
  margin-top: 6px;
}

.toggle-section.is-open {
  border-color: var(--el-color-primary-light-7);
}

.toggle-section :deep(.el-card__header) {
  padding: 8px 12px;
  background: var(--el-fill-color-light);
}

.toggle-section.is-open :deep(.el-card__header) {
  background: var(--el-color-primary-light-9);
}

.toggle-section :deep(.el-card__body) {
  padding: 12px;
}

.toggle-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  user-select: none;
}

.toggle-head__left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
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
  flex-shrink: 0;
}

.toggle-head__desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>