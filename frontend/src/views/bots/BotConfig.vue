<template>
  <div class="bot-config-page">
    <!-- 顶部返回栏 -->
    <div class="config-header">
      <el-button :icon="ArrowLeft" text @click="goBack">返回列表</el-button>
      <h2 class="config-title">{{ isEdit ? '编辑机器人' : '新建机器人' }}</h2>
    </div>

    <!-- ============================================================ -->
    <!-- 统一配置卡片：机器人信息 + 策略参数 + 止盈止损                 -->
    <!-- ============================================================ -->
    <el-card class="unified-card" shadow="never">
      <template #header>
        <div class="card-head">
          <span class="card-head__title">基础配置</span>
          <el-text type="info" size="small">
            机器人信息 · 策略参数 · 止盈止损
          </el-text>
        </div>
      </template>

      <!-- ★ 左 60% / 右 40% 两栏 -->
      <div class="base-split">
        <div class="base-left">

          <!-- ── 第 1 节：机器人信息 ── -->
          <div class="config-section">
            <div class="section-label">机器人信息</div>

            <div class="field-list">
              <!-- 名称 -->
              <div class="field-row">
                <div class="field-label">机器人名称</div>
                <div class="field-value">
                  <el-input
                    v-model="botBaseInfo.name"
                    placeholder="如：BTC 多头激进"
                    style="width: 100%"
                  />
                </div>
              </div>

              <!-- 交易对 -->
              <div class="field-row">
                <div class="field-label">交易对</div>
                <div class="field-value">
                  <el-select
                    v-model="botBaseInfo.pair"
                    multiple
                    filterable
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="选择交易对（可多选）"
                    style="width: 100%"
                    :loading="pairLoading"
                  >
                    <el-option
                      v-for="p in pairOptions"
                      :key="p.name"
                      :label="p.name"
                      :value="p.name"
                    />
                  </el-select>
                </div>
              </div>

              <!-- 投入资金 -->
              <div class="field-row">
                <div class="field-label">投入资金 (USDT)</div>
                <div class="field-value">
                  <el-input-number
                    v-model="botBaseInfo.capital"
                    :min="1"
                    :step="100"
                    style="width: 100%"
                  />
                </div>
              </div>

              <!-- 开仓金额 -->
              <div class="field-row">
                <div class="field-label">开仓金额 (USDT)</div>
                <div class="field-value">
                  <el-input-number
                    v-model="botBaseInfo.stakeAmount"
                    :min="1"
                    :step="10"
                    style="width: 100%"
                  />
                </div>
              </div>

              <!-- 持仓杠杆 -->
              <div class="field-row">
                <div class="field-label">持仓杠杆</div>
                <div class="field-value">
                  <el-input-number
                    v-model="botBaseInfo.leverage"
                    :min="1"
                    :max="125"
                    :step="1"
                    style="width: 100%"
                  />
                </div>
              </div>

              <!-- 最大持仓数 -->
              <div class="field-row">
                <div class="field-label">最大持仓数</div>
                <div class="field-value">
                  <el-input-number
                    v-model="botBaseInfo.maxOpenTrades"
                    :min="1"
                    :max="100"
                    :step="1"
                    style="width: 100%"
                  />
                </div>
              </div>

              <!-- Dry Run -->
              <div class="field-row">
                <div class="field-label">Dry Run</div>
                <div class="field-value">
                  <el-switch
                    v-model="botBaseInfo.dryRun"
                    active-text="模拟"
                    inactive-text="实盘"
                    inline-prompt
                  />
                </div>
              </div>

              <!-- 方向 -->
              <div class="field-row">
                <div class="field-label">方向</div>
                <div class="field-value">
                  <el-radio-group v-model="botBaseInfo.direction" size="default">
                    <el-radio-button value="long">做多</el-radio-button>
                    <el-radio-button value="short">做空</el-radio-button>
                    <el-radio-button value="both">双向</el-radio-button>
                  </el-radio-group>
                </div>
              </div>
            </div>
          </div>

          <!-- ── 第 2 节：策略参数 ── -->
          <div class="config-section">
            <div class="section-label">策略参数</div>

            <div class="field-list">
              <!-- K 线周期 -->
              <div class="field-row">
                <div class="field-label">K 线周期</div>
                <div class="field-value">
                  <el-select
                    :model-value="currentStrategy.timeframe"
                    @update:model-value="val => currentStrategy.timeframe = val"
                    style="width: 100%"
                  >
                    <el-option label="1m"  value="1m" />
                    <el-option label="3m"  value="3m" />
                    <el-option label="5m"  value="5m" />
                    <el-option label="15m" value="15m" />
                    <el-option label="30m" value="30m" />
                    <el-option label="1h"  value="1h" />
                    <el-option label="2h"  value="2h" />
                    <el-option label="4h"  value="4h" />
                    <el-option label="6h"  value="6h" />
                    <el-option label="12h" value="12h" />
                    <el-option label="1d"  value="1d" />
                  </el-select>
                </div>
              </div>

              <!-- 金额模式 -->
              <div class="field-row">
                <div class="field-label">金额模式</div>
                <div class="field-value">
                  <el-radio-group
                    :model-value="currentStrategy.amount_mode"
                    @update:model-value="val => currentStrategy.amount_mode = val"
                  >
                    <el-radio-button value="percent">百分比</el-radio-button>
                    <el-radio-button value="amount">固定金额</el-radio-button>
                  </el-radio-group>
                </div>
              </div>
            </div>
          </div>

          <!-- ── 第 3 节：止盈止损 ── -->
          <div class="config-section">
            <div class="section-label">止盈止损</div>

            <div class="field-list">

              <!-- ========== 止盈 ========== -->
              <div class="field-row field-row--switch">
                <div class="field-label">
                  <span>启用止盈</span>
                  <p class="field-hint">达到目标自动平仓并停止机器人</p>
                </div>
                <div class="field-value field-value--right">
                  <el-switch v-model="botRisk.tp_enabled" />
                </div>
              </div>

              <template v-if="botRisk.tp_enabled">
                <!-- 止盈模式 -->
                <div class="field-row field-row--sub">
                  <div class="field-label">止盈模式</div>
                  <div class="field-value">
                    <el-radio-group v-model="botRisk.tp_mode" size="small">
                      <el-radio-button label="amount">金额</el-radio-button>
                      <el-radio-button label="ratio">百分比</el-radio-button>
                    </el-radio-group>
                  </div>
                </div>

                <!-- 止盈阈值 -->
                <div class="field-row field-row--sub">
                  <div class="field-label">
                    {{ botRisk.tp_mode === 'amount' ? '止盈阈值 (USDT)' : '止盈阈值 (%)' }}
                  </div>
                  <div class="field-value">
                    <el-input-number
                      v-if="botRisk.tp_mode === 'amount'"
                      v-model="botRisk.tp_amount"
                      :min="0"
                      :step="1"
                      style="width: 100%"
                    />
                    <el-input-number
                      v-else
                      v-model="botRisk.tp_ratio"
                      :min="0"
                      :step="0.1"
                      :precision="2"
                      style="width: 100%"
                    />
                  </div>
                </div>
              </template>

              <!-- ========== 止损 ========== -->
              <div class="field-row field-row--switch">
                <div class="field-label">
                  <span>启用止损</span>
                  <p class="field-hint">达到亏损限制自动平仓并停止机器人</p>
                </div>
                <div class="field-value field-value--right">
                  <el-switch v-model="botRisk.sl_enabled" />
                </div>
              </div>

              <template v-if="botRisk.sl_enabled">
                <div class="field-row field-row--sub">
                  <div class="field-label">止损模式</div>
                  <div class="field-value">
                    <el-radio-group v-model="botRisk.sl_mode" size="small">
                      <el-radio-button label="amount">金额</el-radio-button>
                      <el-radio-button label="ratio">百分比</el-radio-button>
                    </el-radio-group>
                  </div>
                </div>

                <div class="field-row field-row--sub">
                  <div class="field-label">
                    {{ botRisk.sl_mode === 'amount' ? '止损阈值 (USDT)' : '止损阈值 (%)' }}
                  </div>
                  <div class="field-value">
                    <el-input-number
                      v-if="botRisk.sl_mode === 'amount'"
                      v-model="botRisk.sl_amount"
                      :min="0"
                      :step="1"
                      style="width: 100%"
                    />
                    <el-input-number
                      v-else
                      v-model="botRisk.sl_ratio"
                      :min="0"
                      :step="0.1"
                      :precision="2"
                      style="width: 100%"
                    />
                  </div>
                </div>
              </template>

              <!-- ========== 追踪止损 ========== -->
              <div class="field-row field-row--switch">
                <div class="field-label">
                  <span>启用追踪止损</span>
                  <p class="field-hint">回撤/反弹到触发线自动平仓并停止机器人</p>
                </div>
                <div class="field-value field-value--right">
                  <el-switch v-model="botRisk.trail_enabled" />
                </div>
              </div>

              <template v-if="botRisk.trail_enabled">
                <div class="field-row field-row--sub">
                  <div class="field-label">追踪模式</div>
                  <div class="field-value">
                    <el-radio-group v-model="botRisk.trail_mode" size="small">
                      <el-radio-button label="amount">金额</el-radio-button>
                      <el-radio-button label="ratio">百分比</el-radio-button>
                    </el-radio-group>
                  </div>
                </div>

                <div class="field-row field-row--sub">
                  <div class="field-label">
                    {{ botRisk.trail_mode === 'amount' ? '触发盈亏 (USDT)' : '触发盈亏 (%)' }}
                  </div>
                  <div class="field-value">
                    <el-input-number
                      v-if="botRisk.trail_mode === 'amount'"
                      v-model="botRisk.trail_activate_amount"
                      :step="1"
                      style="width: 100%"
                    />
                    <el-input-number
                      v-else
                      v-model="botRisk.trail_activate_ratio"
                      :step="0.1"
                      :precision="2"
                      style="width: 100%"
                    />
                  </div>
                </div>

                <div class="field-row field-row--sub">
                  <div class="field-label">
                    {{ botRisk.trail_mode === 'amount' ? '追踪止损 (USDT)' : '追踪止损 (%)' }}
                  </div>
                  <div class="field-value">
                    <el-input-number
                      v-if="botRisk.trail_mode === 'amount'"
                      v-model="botRisk.trail_drawdown_amount"
                      :min="0"
                      :step="1"
                      style="width: 100%"
                    />
                    <el-input-number
                      v-else
                      v-model="botRisk.trail_drawdown_ratio"
                      :min="0"
                      :step="0.1"
                      :precision="2"
                      style="width: 100%"
                    />
                  </div>
                </div>
              </template>

              <!-- ========== 触发后行为（仅任一项启用时显示）========== -->
              <template v-if="botRisk.tp_enabled || botRisk.sl_enabled || botRisk.trail_enabled">
                <div class="field-row field-row--sub">
                  <div class="field-label">触发后自动停止机器人</div>
                  <div class="field-value">
                    <div class="checkbox-stack">
                      <el-checkbox
                        v-if="botRisk.tp_enabled"
                        v-model="botRisk.auto_stop_on_tp"
                      >
                        止盈后停止
                      </el-checkbox>
                      <el-checkbox
                        v-if="botRisk.sl_enabled"
                        v-model="botRisk.auto_stop_on_sl"
                      >
                        止损后停止
                      </el-checkbox>
                      <el-checkbox
                        v-if="botRisk.trail_enabled"
                        v-model="botRisk.auto_stop_on_trail"
                      >
                        追踪止损后停止
                      </el-checkbox>
                    </div>
                  </div>
                </div>
              </template>

            </div>
          </div>

        </div>

        <!-- 右栏：留空（与下方"回测"栏宽度对齐） -->
        <div class="base-right"></div>
      </div>
    </el-card>

    <!-- ============================================================ -->
    <!-- 策略配置区（多空 tab）                                        -->
    <!-- ============================================================ -->
    <el-card>
      <template #header>
        <el-tabs v-model="activeSide">
          <el-tab-pane v-if="showLong"  label="📈 多头策略" name="long" />
          <el-tab-pane v-if="showShort" label="📉 空头策略" name="short" />
        </el-tabs>
      </template>

      <StrategyPanel
        v-if="activeSide === 'long' && showLong && localConfig.long.entry"
        :config="localConfig.long"
        :trade-info="longTradeInfo"
        @save="handleSaveLong"
      />

      <StrategyPanel
        v-else-if="activeSide === 'short' && showShort && localConfig.short.entry"
        :config="localConfig.short"
        :trade-info="shortTradeInfo"
        @save="handleSaveShort"
      />
    </el-card>

    <!-- 底部保存栏 -->
    <div class="save-footer">
      <el-button
        type="primary"
        size="large"
        :loading="saving"
        @click="handleSaveAndStart"
      >
        保存配置
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import StrategyPanel from '@features/strategy/components/StrategyPanel.vue'
import {
  getDefaultLongConfig,
  getDefaultShortConfig
} from '@features/strategy/composables/useStrategyConfig.js'
import { useBotStore } from '@/stores/botStore.js'
import axios from 'axios'

const API = 'http://localhost:9000'

const route = useRoute()
const router = useRouter()

const { createBot, updateBot } = useBotStore()
const activeSide = ref('long')

const botId = computed(() => route.params.id)
const isEdit = computed(() => !!botId.value)

const botBaseInfo = ref({
  name: '',
  pair: [],
  capital: 100,
  stakeAmount: 10,
  leverage: 10,
  maxOpenTrades: 3,
  dryRun: true,
  direction: 'long',
})

const showLong  = computed(() => ['long',  'both'].includes(botBaseInfo.value.direction))
const showShort = computed(() => ['short', 'both'].includes(botBaseInfo.value.direction))

const localConfig = ref({
  long: getDefaultLongConfig(),
  short: getDefaultShortConfig()
})

const currentStrategy = computed(() => {
  return activeSide.value === 'short'
    ? localConfig.value.short
    : localConfig.value.long
})

const longTradeInfo = computed(() => ({
  side: 'long',
  direction: '仅做多',
  timeframe: localConfig.value.long?.timeframe || '30m',
  leverage: `${localConfig.value.long?.leverage || 10}x`,
  stoploss: localConfig.value.long?.sl?.enable
    ? `${localConfig.value.long.sl.stoploss}%`
    : null,
  entrySignal: '见策略配置',
  pumpProtectSignal: null,
  tpSignal: null,
  lossTpSignal: null,
  trendSignal: null,
  dcaSignal: null,
  gridSignal: null,
  pairMaxPositionSignal: null,
  timeStopSignal: null,
  htfTrendSignal: null,
  roiLevels: []
}))

const shortTradeInfo = computed(() => ({
  side: 'short',
  direction: '仅做空',
  timeframe: localConfig.value.short?.timeframe || '30m',
  leverage: `${localConfig.value.short?.leverage || 10}x`,
  stoploss: localConfig.value.short?.sl?.enable
    ? `${localConfig.value.short.sl.stoploss}%`
    : null,
  entrySignal: '见策略配置',
  pumpProtectSignal: null,
  tpSignal: null,
  lossTpSignal: null,
  trendSignal: null,
  dcaSignal: null,
  gridSignal: null,
  pairMaxPositionSignal: null,
  timeStopSignal: null,
  htfTrendSignal: null,
  roiLevels: []
}))

watch(
  () => botBaseInfo.value.direction,
  (dir) => {
    if (dir === 'short') activeSide.value = 'short'
    else if (dir === 'long') activeSide.value = 'long'
    else if (dir === 'both' && !['long', 'short'].includes(activeSide.value)) {
      activeSide.value = 'long'
    }
  },
  { immediate: true }
)

const parseCfg = (v) => {
  if (!v) return null
  if (typeof v === 'string') {
    try { return JSON.parse(v) } catch { return null }
  }
  return v
}

const loadBotDetail = async () => {
  if (!isEdit.value) return
  try {
    const { data } = await axios.get(`${API}/bots/${botId.value}`)

    botBaseInfo.value = {
      name: data.name,
      pair: Array.isArray(data.pair)
        ? data.pair
        : (data.pair ? [data.pair] : []),
      capital: data.capital ?? 100,
      stakeAmount: data.stakeAmount ?? 10,
      leverage: data.leverage ?? 10,
      maxOpenTrades: data.maxOpenTrades ?? 5,
      dryRun: data.dryRun !== undefined ? !!data.dryRun : true,
      direction: (() => {
        const l = !!data.enableLong
        const s = !!data.enableShort
        if (l && s) return 'both'
        if (s) return 'short'
        return 'long'
      })(),
    }

    botRisk.value = {
      tp_enabled: !!data.tp_enabled,
      tp_mode: data.tp_mode || 'amount',
      tp_amount: data.tp_amount ?? 0,
      tp_ratio: data.tp_ratio ?? 0,
      sl_enabled: !!data.sl_enabled,
      sl_mode: data.sl_mode || 'amount',
      sl_amount: data.sl_amount ?? 0,
      sl_ratio: data.sl_ratio ?? 0,
      trail_enabled: !!data.trail_enabled,
      trail_mode: data.trail_mode || 'ratio',
      trail_activate_amount: data.trail_activate_amount ?? 10,
      trail_activate_ratio: data.trail_activate_ratio ?? 1,
      trail_drawdown_amount: data.trail_drawdown_amount ?? 5,
      trail_drawdown_ratio: data.trail_drawdown_ratio ?? 0.5,
      auto_stop_on_tp: data.auto_stop_on_tp !== false,
      auto_stop_on_sl: data.auto_stop_on_sl !== false,
      auto_stop_on_trail: data.auto_stop_on_trail !== false,
    }

    const longCfg = parseCfg(data.longConfig)
    const shortCfg = parseCfg(data.shortConfig)

    localConfig.value.long = (longCfg && longCfg.entry)
      ? longCfg
      : getDefaultLongConfig()

    localConfig.value.short = (shortCfg && shortCfg.entry)
      ? shortCfg
      : getDefaultShortConfig()
  } catch (e) {
    console.error(e)
    ElMessage.error('加载机器人详情失败')
    router.push({ name: 'BotList' })
  }
}

const botRisk = ref({
  tp_enabled: false,
  tp_mode: 'amount',
  tp_amount: 0,
  tp_ratio: 0,

  sl_enabled: false,
  sl_mode: 'amount',
  sl_amount: 0,
  sl_ratio: 0,

  trail_enabled: false,
  trail_mode: 'ratio',
  trail_activate_amount: 10,
  trail_activate_ratio: 1,
  trail_drawdown_amount: 5,
  trail_drawdown_ratio: 0.5,

  auto_stop_on_tp: true,
  auto_stop_on_sl: true,
  auto_stop_on_trail: true,
})

const buildPayload = () => {
  const dir = botBaseInfo.value.direction

  return {
    base: {
      name: botBaseInfo.value.name,
      pair: botBaseInfo.value.pair,
      capital: botBaseInfo.value.capital,
      stakeAmount: botBaseInfo.value.stakeAmount,
      leverage: botBaseInfo.value.leverage,
      maxOpenTrades: botBaseInfo.value.maxOpenTrades,
      dryRun: botBaseInfo.value.dryRun,
      enableLong:  dir === 'long' || dir === 'both',
      enableShort: dir === 'short' || dir === 'both',
    },
    risk: botRisk.value,
    longConfig: localConfig.value.long,
    shortConfig: localConfig.value.short,
  }
}

const pairOptions = ref([])
const pairLoading = ref(false)

const loadPairs = async () => {
  pairLoading.value = true
  try {
    const { data } = await axios.get(`${API}/exchange/pairs`, {
      params: { exchange: 'binance', market: 'futures' }
    })
    pairOptions.value = data || []
  } catch (e) {
    console.error('load pairs failed', e)
    ElMessage.error('加载交易对失败')
  } finally {
    pairLoading.value = false
  }
}

const validate = () => {
  if (!botBaseInfo.value.name) {
    ElMessage.warning('请输入机器人名称')
    return false
  }
  if (!botBaseInfo.value.pair || !botBaseInfo.value.pair.length) {
    ElMessage.warning('请至少选择一个交易对')
    return false
  }
  if (!botBaseInfo.value.capital || botBaseInfo.value.capital <= 0) {
    ElMessage.warning('投入资金必须大于 0')
    return false
  }
  if (!botBaseInfo.value.stakeAmount || botBaseInfo.value.stakeAmount <= 0) {
    ElMessage.warning('开仓金额必须大于 0')
    return false
  }
  if (!botBaseInfo.value.leverage || botBaseInfo.value.leverage < 1) {
    ElMessage.warning('持仓杠杆至少为 1')
    return false
  }
  if (!botBaseInfo.value.maxOpenTrades || botBaseInfo.value.maxOpenTrades < 1) {
    ElMessage.warning('最大持仓数至少为 1')
    return false
  }
  if (!['long', 'short', 'both'].includes(botBaseInfo.value.direction)) {
    ElMessage.warning('请选择方向')
    return false
  }
  return true
}

const saving = ref(false)

const handleSaveAndStart = async () => {
  if (!validate()) return
  saving.value = true

  try {
    const payload = buildPayload()

    let id
    if (isEdit.value) {
      await updateBot(botId.value, payload)
      id = botId.value
    } else {
      const bot = await createBot(payload)
      id = bot.id
    }

    await axios.post(`${API}/bots/${id}/start`)

    ElMessage.success(isEdit.value ? '已保存并重启' : '已保存并启动')
    router.push({ name: 'BotList' })
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleSaveLong = () => {
  ElMessage.success('多头策略已更新')
}

const handleSaveShort = () => {
  ElMessage.success('空头策略已更新')
}

const goBack = () => {
  router.push({ name: 'BotList' })
}

onMounted(async () => {
  await loadPairs()
  await loadBotDetail()
})
</script>

<style scoped>
.bot-config-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.config-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-main);
  flex: 1;
}

/* ============================================================ */
/* 基础配置卡片                                                  */
/* ============================================================ */
.unified-card {
  border-radius: 12px;
}

.unified-card :deep(.el-card__header) {
  padding: 12px 16px;
  background: var(--el-fill-color-light);
}

.unified-card :deep(.el-card__body) {
  padding: 0;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}

.card-head__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
}

/* ============================================================ */
/* 左 60% / 右 40% 两栏                                          */
/* ============================================================ */
.base-split {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
  gap: 0;
  align-items: start;
}

.base-left {
  min-width: 0;
  border-right: 1px solid var(--el-border-color-lighter);
}

.base-right {
  min-width: 0;
  min-height: 100px;
}

/* ============================================================ */
/* Section 结构                                                 */
/* ============================================================ */
.config-section {
  padding: 16px 20px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.config-section:last-child {
  border-bottom: none;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin-bottom: 12px;
  padding-left: 8px;
  border-left: 3px solid var(--el-color-primary);
}

/* ============================================================ */
/* ★ 核心：每行只放一个字段                                     */
/* ============================================================ */
.field-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed var(--el-border-color-lighter);
  min-height: 40px;
}

.field-row:last-child {
  border-bottom: none;
}

/* 开关行：描述可能两行，垂直居中 */
.field-row--switch {
  align-items: flex-start;
  padding: 12px 0;
}

/* 参数行（缩进 + 浅色背景，视觉上从属于上面的开关）*/
.field-row--sub {
  background: var(--el-fill-color-extra-light);
  padding: 10px 12px;
  margin-left: 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
  border-radius: 0;
}

.field-row--sub:last-child {
  border-bottom: none;
  border-radius: 0 0 6px 6px;
}

/* label */
.field-label {
  flex: 0 0 150px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.4;
}

.field-label > span {
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.field-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-weight: normal;
  line-height: 1.4;
}

/* value */
.field-value {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
}

/* 开关按钮靠右对齐 */
.field-value--right {
  justify-content: flex-end;
}

/* 复选框堆叠（触发后行为）*/
.checkbox-stack {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.checkbox-stack :deep(.el-checkbox) {
  margin-right: 0;
}

/* ============================================================ */
/* 底部保存栏                                                    */
/* ============================================================ */
.save-footer {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: flex-end;
  padding: 16px 24px;
  margin-top: 8px;
  background: var(--el-bg-color);
  border-top: 1px solid var(--el-border-color);
  z-index: 10;
}

/* ============================================================ */
/* 响应式                                                        */
/* ============================================================ */
@media (max-width: 1200px) {
  .base-split {
    grid-template-columns: minmax(0, 1fr);
  }
  .base-left {
    border-right: none;
  }
  .base-right {
    display: none;
  }
}
</style>