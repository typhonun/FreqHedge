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
      <div class="strategy-card" @click="handleSelect('dca')">
        <div class="strategy-icon">
          <el-icon :size="40" color="#409EFF"><TrendCharts /></el-icon>
        </div>
        <div class="strategy-info">
          <h3>DCA 机器人</h3>
          <p>经典马丁格尔加仓策略，支持 RSI/KDJ 过滤、动态止盈、网格等丰富配置</p>
        </div>
      </div>

      <div class="strategy-card" @click="handleSelect('grid')">
        <div class="strategy-icon">
          <el-icon :size="40" color="#67C23A"><Grid /></el-icon>
        </div>
        <div class="strategy-info">
          <h3>网格机器人</h3>
          <p>在设定价格区间内自动低买高卖，适合震荡行情（目前为空白占位页面）</p>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { TrendCharts, Grid } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: Boolean
})
const emit = defineEmits(['update:modelValue', 'select'])

const visible = ref(false)

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

const handleSelect = (type) => {
  emit('select', type)
  visible.value = false
}

const handleClose = () => {
  visible.value = false
}
</script>

<style scoped>
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