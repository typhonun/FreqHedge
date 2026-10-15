<!-- src/components/common/StrategySelectDialog.vue -->
<template>
  <el-dialog
    v-model="visible"
    title="选择机器人类型"
    width="500px"
    align-center
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="strategy-options">
      <div
        v-for="def in strategyList"
        :key="def.key"
        class="strategy-card"
        @click="handleSelect(def.key)"
      >
        <div class="strategy-icon">
          <el-icon :size="40" :color="def.color">
            <component :is="iconMap[def.icon]" />
          </el-icon>
        </div>
        <div class="strategy-info">
          <h3>{{ def.label }}</h3>
          <p>{{ def.desc }}</p>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { TrendCharts, Grid } from '@element-plus/icons-vue'
import { listStrategyDefs } from '@/config/strategyRegistry.js'

const props = defineProps({
  modelValue: Boolean
})
const emit = defineEmits(['update:modelValue', 'select'])

const visible = ref(false)

watch(() => props.modelValue, (val) => { visible.value = val })
watch(visible, (val) => { emit('update:modelValue', val) })

// ★ 从注册表拿策略列表
const strategyList = computed(() => listStrategyDefs())

// ★ 图标名 → 组件（注册表里存字符串，避免循环依赖）
const iconMap = {
  TrendCharts,
  Grid,
  // 未来加：
  // Setting,
}

const handleSelect = (type) => {
  emit('select', type)
  visible.value = false
}

const handleClose = () => {
  visible.value = false
}
</script>

<style scoped>
/* 保持原样式不动 */
.strategy-options {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.strategy-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border: 2px solid var(--el-border-color-lighter);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--el-bg-color);
}

.strategy-card:hover {
  border-color: var(--el-color-primary);
  background: var(--el-fill-color-light);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.strategy-icon {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--el-fill-color-light);
  border-radius: 50%;
  flex-shrink: 0;
}

.strategy-info h3 {
  margin: 0 0 6px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.strategy-info p {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}
</style>