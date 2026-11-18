<!-- frontend/src/components/GridScannerDialog.vue -->
<template>
  <el-dialog v-model="visible" title="AI 多因子选币雷达" width="800px" @close="onClose">
    <div class="controls">
      <div class="control-group">
        <span>目标做多数量：</span>
        <el-input-number v-model="longCount" :min="0" :max="10" size="small" />
      </div>
      <div class="control-group">
        <span>目标做空数量：</span>
        <el-input-number v-model="shortCount" :min="0" :max="10" size="small" />
      </div>
      <el-button type="primary" :loading="loading" @click="startScan">
        {{ loading ? '扫描中(约需1分钟)...' : '立即扫描市场' }}
      </el-button>
    </div>

    <el-table
      v-if="results.length > 0"
      :data="results"
      height="350"
      border
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="45" />
      <el-table-column prop="symbol" label="币种" min-width="130" />
      <el-table-column label="建议方向" width="90">
        <template #default="{ row }">
          <el-tag :type="row.direction === 'LONG' ? 'success' : 'danger'" size="small">
            {{ row.direction === 'LONG' ? '做多' : '做空' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="atr_pct" label="波动率%" width="90" />
      <el-table-column prop="hurst" label="Hurst" width="80" />
      <el-table-column prop="adx" label="ADX" width="80" />
      <el-table-column prop="z_score" label="Z-Score" width="90" />
      <el-table-column prop="rsi" label="RSI" width="80" />
    </el-table>

    <template #footer>
      <el-button @click="onClose">取消</el-button>
      <el-button type="primary" :disabled="selectedRows.length === 0" @click="confirm">
        确认选择 (已选 {{ selectedRows.length }} 个)
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const API = 'http://localhost:9000/api/scanner'
const emit = defineEmits(['confirm'])

const visible = defineModel({ type: Boolean, default: false })

const longCount = ref(3)
const shortCount = ref(0)
const loading = ref(false)
const results = ref([])
const selectedRows = ref([])

const startScan = async () => {
  loading.value = true
  try {
    const { data } = await axios.get(`${API}/grid`, {
      params: { long_count: longCount.value, short_count: shortCount.value }
    })

    // 把多和空合并成一个列表方便展示
    const merged = []
    data.longs.forEach(item => merged.push({ ...item, direction: 'LONG' }))
    data.shorts.forEach(item => merged.push({ ...item, direction: 'SHORT' }))

    results.value = merged
    if (merged.length === 0) {
      ElMessage.warning('当前市场没有符合标准的币种，请尝试增加目标数量或稍后重试')
    }
  } catch (e) {
    ElMessage.error('扫描失败，请检查后端服务')
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (val) => {
  selectedRows.value = val
}

const confirm = () => {
  emit('confirm', selectedRows.value)
  onClose()
}

const onClose = () => {
  visible.value = false
}
</script>

<style scoped>
.controls {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 16px;
  background: var(--el-fill-color-light);
  padding: 12px;
  border-radius: 8px;
}
.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}
</style>