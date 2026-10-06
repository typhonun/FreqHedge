<!-- src/views/settings/Preferences.vue -->
<template>
  <div class="preferences-page">
    <!-- 外观 -->
    <div class="card">
      <h2 class="card-title">外观</h2>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">主题模式</div>
          <div class="setting-desc">选择界面配色，跟随系统会自动根据操作系统切换</div>
        </div>
        <el-radio-group v-model="prefs.theme" size="default">
          <el-radio-button value="dark">深色</el-radio-button>
          <el-radio-button value="light">浅色</el-radio-button>
          <el-radio-button value="auto">跟随系统</el-radio-button>
        </el-radio-group>
      </div>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">主题色</div>
          <div class="setting-desc">用于按钮、链接、选中状态等</div>
        </div>
        <div class="color-picker">
          <div
            v-for="c in presetColors"
            :key="c.value"
            :class="['color-dot', { active: prefs.primaryColor === c.value }]"
            :style="{ background: c.value }"
            :title="c.label"
            @click="prefs.primaryColor = c.value"
          />
        </div>
      </div>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">界面密度</div>
          <div class="setting-desc">紧凑模式会减少间距，一屏显示更多内容</div>
        </div>
        <el-radio-group v-model="prefs.density" size="default">
          <el-radio-button value="comfortable">舒适</el-radio-button>
          <el-radio-button value="compact">紧凑</el-radio-button>
        </el-radio-group>
      </div>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">语言</div>
          <div class="setting-desc">界面显示语言</div>
        </div>
        <el-select v-model="prefs.language" style="width: 180px">
          <el-option label="简体中文" value="zh-CN" />
          <el-option label="English" value="en-US" />
        </el-select>
      </div>
    </div>

    <!-- 交易偏好 -->
    <div class="card">
      <h2 class="card-title">交易偏好</h2>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">默认杠杆</div>
          <div class="setting-desc">新建机器人时的默认杠杆倍数</div>
        </div>
        <el-input-number
          v-model="prefs.defaultLeverage"
          :min="1"
          :max="125"
          :step="1"
          style="width: 180px"
        />
      </div>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">默认投入资金 (USDT)</div>
          <div class="setting-desc">新建机器人时的默认资金</div>
        </div>
        <el-input-number
          v-model="prefs.defaultCapital"
          :min="1"
          :step="100"
          style="width: 180px"
        />
      </div>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">默认开仓金额 (USDT)</div>
          <div class="setting-desc">每笔交易的开仓金额</div>
        </div>
        <el-input-number
          v-model="prefs.defaultStakeAmount"
          :min="1"
          :step="10"
          style="width: 180px"
        />
      </div>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">默认 Dry Run 模式</div>
          <div class="setting-desc">新建机器人时默认使用模拟盘</div>
        </div>
        <el-switch v-model="prefs.defaultDryRun" />
      </div>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">下单前二次确认</div>
          <div class="setting-desc">手动下单或平仓时弹出确认对话框</div>
        </div>
        <el-switch v-model="prefs.confirmBeforeOrder" />
      </div>
    </div>

    <!-- 数据与展示 -->
    <div class="card">
      <h2 class="card-title">数据与展示</h2>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">默认回测区间</div>
          <div class="setting-desc">进入机器人配置页时默认选择的历史区间</div>
        </div>
        <el-select v-model="prefs.defaultBacktestRange" style="width: 180px">
          <el-option label="7 天" value="7" />
          <el-option label="30 天" value="30" />
          <el-option label="60 天" value="60" />
          <el-option label="90 天" value="90" />
          <el-option label="180 天" value="180" />
          <el-option label="365 天" value="365" />
        </el-select>
      </div>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">收益展示周期</div>
          <div class="setting-desc">机器人列表和详情页的默认统计周期</div>
        </div>
        <el-select v-model="prefs.profitPeriod" style="width: 180px">
          <el-option label="今日" value="today" />
          <el-option label="近 7 天" value="7d" />
          <el-option label="近 30 天" value="30d" />
          <el-option label="全部" value="all" />
        </el-select>
      </div>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">K 线主图类型</div>
          <div class="setting-desc">图表默认显示方式</div>
        </div>
        <el-radio-group v-model="prefs.chartType" size="default">
          <el-radio-button value="candle">蜡烛图</el-radio-button>
          <el-radio-button value="line">分时线</el-radio-button>
        </el-radio-group>
      </div>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">列表自动刷新</div>
          <div class="setting-desc">机器人列表页面自动刷新间隔</div>
        </div>
        <el-select v-model="prefs.autoRefresh" style="width: 180px">
          <el-option label="关闭" :value="0" />
          <el-option label="5 秒" :value="5" />
          <el-option label="10 秒" :value="10" />
          <el-option label="30 秒" :value="30" />
          <el-option label="60 秒" :value="60" />
        </el-select>
      </div>
    </div>

    <!-- 通知偏好 -->
    <div class="card">
      <h2 class="card-title">通知偏好</h2>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">止盈止损提醒</div>
          <div class="setting-desc">触发止盈/止损时发送通知</div>
        </div>
        <el-switch v-model="prefs.notifyRiskTrigger" />
      </div>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">开平仓提醒</div>
          <div class="setting-desc">每次开仓/平仓时发送通知</div>
        </div>
        <el-switch v-model="prefs.notifyOrder" />
      </div>

      <div class="setting-row">
        <div class="setting-label">
          <div class="setting-title">机器人异常提醒</div>
          <div class="setting-desc">机器人停止、报错时发送通知</div>
        </div>
        <el-switch v-model="prefs.notifyBotError" />
      </div>
    </div>

    <!-- 保存按钮 -->
    <div class="actions">
      <el-button @click="handleReset">恢复默认</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">
        保存偏好
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const STORAGE_KEY = 'user_preferences_v1'

const presetColors = [
  { label: '默认蓝', value: '#2bbdf6' },
  { label: '青绿',   value: '#00b96b' },
  { label: '紫罗兰', value: '#8b5cf6' },
  { label: '橙',     value: '#f59e0b' },
  { label: '玫红',   value: '#ec4899' },
]

const defaultPrefs = {
  // 外观
  theme: 'dark',
  primaryColor: '#2bbdf6',
  density: 'comfortable',
  language: 'zh-CN',

  // 交易偏好
  defaultLeverage: 10,
  defaultCapital: 100,
  defaultStakeAmount: 10,
  defaultDryRun: true,
  confirmBeforeOrder: true,

  // 数据与展示
  defaultBacktestRange: '60',
  profitPeriod: 'all',
  chartType: 'candle',
  autoRefresh: 10,

  // 通知
  notifyRiskTrigger: true,
  notifyOrder: false,
  notifyBotError: true,
  notifyDailyReport: false,
}

const prefs = reactive({ ...defaultPrefs })
const saving = ref(false)

const loadPrefs = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const obj = JSON.parse(raw)
    Object.assign(prefs, defaultPrefs, obj)
  } catch (e) {
    console.warn('[preferences] load failed', e)
  }
}

const applyTheme = () => {
  // 简单示例：只处理 primary color，dark/light 由你的全局 theme 系统处理
  document.documentElement.style.setProperty('--primary-color', prefs.primaryColor)
}

const handleSave = async () => {
  saving.value = true
  try {
    // 模拟保存延迟
    await new Promise((r) => setTimeout(r, 300))
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
    applyTheme()
    ElMessage.success('偏好已保存')
  } catch (e) {
    console.error(e)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const handleReset = async () => {
  try {
    await ElMessageBox.confirm('确定恢复所有偏好为默认值吗？', '提示', {
      type: 'warning',
      confirmButtonText: '恢复默认',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  Object.assign(prefs, defaultPrefs)
  localStorage.removeItem(STORAGE_KEY)
  applyTheme()
  ElMessage.success('已恢复默认')
}

onMounted(() => {
  loadPrefs()
  applyTheme()
})
</script>

<style scoped>
.preferences-page {
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

/* 每行设置项 */
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 14px 0;
  border-bottom: 1px solid var(--border-color);
}
.setting-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.setting-row:first-of-type {
  padding-top: 0;
}

.setting-label {
  min-width: 0;
  flex: 1;
}

.setting-title {
  font-size: 14px;
  color: var(--text-main);
  margin-bottom: 4px;
}

.setting-desc {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

/* 主题色选择 */
.color-picker {
  display: flex;
  gap: 10px;
}

.color-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
  position: relative;
}

.color-dot:hover {
  transform: scale(1.1);
}

.color-dot.active {
  border-color: var(--text-main);
  box-shadow: 0 0 0 2px var(--bg-card) inset;
}

/* 底部按钮 */
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 8px 0 24px;
}
</style>