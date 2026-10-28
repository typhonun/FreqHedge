<template>
  <div class="position-actions">
    <el-button
      type="primary"
      size="small"
      :disabled="!botId || closingAll"
      :loading="submitting"
      @click="openForceEnterDialog"
    >
      立即开仓
    </el-button>
    <el-button
      type="danger"
      size="small"
      :disabled="!botId || submitting"
      :loading="closingAll"
      @click="handleCloseAll"
    >
      全部平仓
    </el-button>

    <!-- 立即开仓弹窗 -->
    <el-dialog
      v-model="forceEnterVisible"
      title="立即开仓"
      width="480px"
      align-center
    >
      <el-form label-width="90px">
        <el-form-item label="机器人">
          <span>{{ botName }}</span>
        </el-form-item>

        <el-form-item label="交易对">
          <el-select
            v-model="forceForm.pair"
            filterable
            placeholder="请选择交易对"
            style="width: 100%"
            :loading="pairsLoading"
          >
            <el-option
              v-for="p in availablePairs"
              :key="p"
              :label="p"
              :value="p"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="开仓金额">
          <el-input-number
            v-model="forceForm.stakeamount"
            :min="minStakeAmount"
            :step="10"
            style="width: 100%"
          />
          <div class="tip">
            单位 USDT，杠杆沿用机器人配置。当前交易对最低需要 <b>{{ minStakeAmount }}</b> USDT。
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="forceEnterVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="submitForceEnter"
        >
          确认开仓
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import axios from 'axios'
const API = 'http://localhost:9000'
import { ElMessage, ElMessageBox } from 'element-plus'
import { forceEnter, closeAll, getAvailablePairs } from '@/api/position'
import { useBotStore } from '@/stores/botStore'
import { useTradeStore } from '@/stores/tradeStore'

const props = defineProps({
  botId: { type: [Number, String], default: null },
  // 传入当前页面的持仓（可选），用于"全部平仓"的方向判断
  positions: { type: [Array, Object], default: () => ({ long: [], short: [] }) },
})

const emit = defineEmits(['success'])

const botStore = useBotStore()
const tradeStore = useTradeStore()

const bots = computed(() => botStore.state.bots)

const bot = computed(() =>
  bots.value.find((b) => b.id === props.botId)
)
const botName = computed(() =>
  bot.value ? `${bot.value.name} (#${bot.value.id})` : ''
)

const forceForm = ref({
  side: 'long',
  pair: '',
  stakeamount: 10,
})

const minNotional = ref(10)
const minStakeAmount = computed(() => {
  const lev = bot.value?.leverage || 1
  return Number((minNotional.value / lev).toFixed(2))
})

// 监听 forceForm.pair 变化，请求限额
watch(() => forceForm.value.pair, async (newPair) => {
  if (!newPair) return
  try {
    const { data } = await axios.get(`${API}/exchange/pair_limits`, {
      params: { pair: newPair }
    })
    minNotional.value = Number(data.min_notional) || 10
  } catch (e) {
    minNotional.value = 10
  }
})

// ============ 开仓 ============
const forceEnterVisible = ref(false)
const submitting = ref(false)
const pairsLoading = ref(false)
const availablePairs = ref([])

// ============ 平仓 ============
const closingAll = ref(false)

const openForceEnterDialog = async () => {
  if (!props.botId) {
    ElMessage.warning('请先选择一个机器人')
    return
  }
  if (!bot.value) {
    ElMessage.error('机器人不存在')
    return
  }
  if (!bot.value.enableLong && !bot.value.enableShort) {
    ElMessage.error('该机器人没有启用任何方向')
    return
  }

  forceForm.value.side = bot.value.enableLong ? 'long' : 'short'
  forceForm.value.pair = ''
  forceForm.value.stakeamount = bot.value.stakeAmount || 10

  forceEnterVisible.value = true
  await loadAvailablePairs()
}

const loadAvailablePairs = async () => {
  pairsLoading.value = true
  try {
    const { data } = await getAvailablePairs({
      bot_id: props.botId,
      side: forceForm.value.side,
    })
    availablePairs.value = Array.isArray(data) ? data : []
  } catch (e) {
    availablePairs.value = []
    console.error('[PositionActions] loadAvailablePairs failed', e)
    ElMessage.error('获取可交易对失败')
  } finally {
    pairsLoading.value = false
  }
}

watch(
  () => forceForm.value.side,
  () => {
    forceForm.value.pair = ''
    if (forceEnterVisible.value) loadAvailablePairs()
  }
)

const submitForceEnter = async () => {
  if (submitting.value) return

  if (!forceForm.value.pair) {
    ElMessage.warning('请选择交易对')
    return
  }
  if (!forceForm.value.stakeamount || forceForm.value.stakeamount <= 0) {
    ElMessage.warning('请输入有效的开仓金额')
    return
  }
  if (forceForm.value.stakeamount * (bot.value?.leverage || 1) < minNotional.value) {
    ElMessage.warning(`开仓金额过小，当前交易对最小名义价值为 ${minNotional.value} USDT`)
    return
  }
  submitting.value = true
  try {
    await forceEnter({
      bot_id: props.botId,
      side: forceForm.value.side,
      pair: forceForm.value.pair,
      stakeamount: forceForm.value.stakeamount,
    })
    ElMessage.success('开仓成功')
    forceEnterVisible.value = false
    emit('success')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '开仓失败')
  } finally {
    submitting.value = false
  }
}

// ============ 全部平仓 ============
const handleCloseAll = async () => {
  if (closingAll.value) return

  if (!props.botId) {
    ElMessage.warning('请先选择一个机器人')
    return
  }

  // 优先用传入的 positions，否则用 store
  const p = props.positions || tradeStore.positions || {}
  const hasLong = (p.long || []).length > 0
  const hasShort = (p.short || []).length > 0

  if (!hasLong && !hasShort) {
    ElMessage.info('当前机器人没有持仓')
    return
  }

  let sides = []
  if (hasLong && hasShort) {
    let value
    try {
      const res = await ElMessageBox.prompt(
        '该机器人同时有多空持仓，请输入要平仓的方向（long / short / all）',
        '全部平仓',
        {
          inputValue: 'all',
          inputValidator: (v) =>
            ['long', 'short', 'all'].includes((v || '').toLowerCase()) ||
            '请输入 long / short / all',
        }
      )
      value = res.value
    } catch {
      return
    }
    const v = (value || '').toLowerCase()
    if (v === 'all') sides = ['long', 'short']
    else if (v === 'long' || v === 'short') sides = [v]
    else return
  } else {
    sides = hasLong ? ['long'] : ['short']
  }

  try {
    await ElMessageBox.confirm(
      `确认平掉机器人 ${botName.value} 的 ${sides.join(' / ')} 全部持仓？`,
      '全部平仓',
      { type: 'warning' }
    )
  } catch {
    return
  }

  closingAll.value = true
  try {
    for (const side of sides) {
      await closeAll({ bot_id: props.botId, side })
    }
    ElMessage.success('平仓指令已提交')
    emit('success')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '平仓失败')
  } finally {
    closingAll.value = false
  }
}
</script>

<style scoped>
.position-actions {
  display: inline-flex;
  gap: 8px;
}
.tip {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}
</style>