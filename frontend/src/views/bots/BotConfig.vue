<template>
  <div class="bot-config-page">
    <!-- 顶部返回栏 -->
    <div class="config-header">
      <el-button :icon="ArrowLeft" text @click="goBack">返回列表</el-button>
      <h2 class="config-title">{{ isEdit ? '编辑机器人' : '新建机器人' }}</h2>
    </div>

    <!-- 基础信息 -->
    <el-card class="base-info-card">
      <template #header>
        <span class="card-title">基础信息</span>
      </template>

      <el-form :model="botBaseInfo" label-width="120px" size="default">
        <!-- 第 1 行：名称 / 交易对 / 投入资金 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="机器人名称">
              <el-input v-model="botBaseInfo.name" placeholder="如：BTC 多头激进" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="交易对">
              <el-select
                v-model="botBaseInfo.pair"
                multiple
                collapse-tags
                collapse-tags-tooltip
                placeholder="选择交易对（可多选）"
                style="width: 100%"
              >
                <el-option label="BTC/USDT:USDT" value="BTC/USDT:USDT" />
                <el-option label="ETH/USDT:USDT" value="ETH/USDT:USDT" />
                <el-option label="SOL/USDT:USDT" value="SOL/USDT:USDT" />
                <el-option label="XRP/USDT:USDT" value="XRP/USDT:USDT" />
                <el-option label="BNB/USDT:USDT" value="BNB/USDT:USDT" />
                <el-option label="DOGE/USDT:USDT" value="DOGE/USDT:USDT" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="投入资金 (USDT)">
              <el-input-number
                v-model="botBaseInfo.capital"
                :min="1"
                :step="100"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 第 2 行：Dry Run / 开仓金额 / 持仓杠杆 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="Dry Run">
              <el-switch
                v-model="botBaseInfo.dryRun"
                active-text="模拟"
                inactive-text="实盘"
                inline-prompt
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="开仓金额 (USDT)">
              <el-input-number
                v-model="botBaseInfo.stakeAmount"
                :min="1"
                :step="10"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="持仓杠杆">
              <el-input-number
                v-model="botBaseInfo.leverage"
                :min="1"
                :max="125"
                :step="1"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 第 3 行：启用方向 -->
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="启用多头">
              <el-switch v-model="botBaseInfo.enableLong" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="启用空头">
              <el-switch v-model="botBaseInfo.enableShort" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- 止盈止损 -->
    <el-card class="risk-config-card">
      <template #header>
        <span class="card-title">🎯 止盈止损</span>
      </template>

      <div class="risk-grid">
        <!-- 止盈 -->
        <div class="risk-item">
          <div class="risk-label">
            <span>启用止盈</span>
            <p>达到目标自动平仓并停止机器人</p>
          </div>
          <el-switch v-model="botRisk.tp_enabled" />
        </div>

        <div class="risk-item">
          <div class="risk-label"><span>止盈阈值</span></div>
          <div class="risk-input">
            <el-radio-group v-model="botRisk.tp_mode" size="small">
              <el-radio-button label="amount">金额</el-radio-button>
              <el-radio-button label="ratio">百分比</el-radio-button>
            </el-radio-group>

            <el-input-number
              v-if="botRisk.tp_mode === 'amount'"
              v-model="botRisk.tp_amount"
              :min="0" :step="1"
              :disabled="!botRisk.tp_enabled"
            />
            <el-input-number
              v-else
              v-model="botRisk.tp_ratio"
              :min="0" :step="0.1" :precision="2"
              suffix="%"
              :disabled="!botRisk.tp_enabled"
            />
          </div>
        </div>

        <!-- 止损 -->
        <div class="risk-item">
          <div class="risk-label">
            <span>启用止损</span>
            <p>达到亏损限制自动平仓并停止机器人</p>
          </div>
          <el-switch v-model="botRisk.sl_enabled" />
        </div>

        <div class="risk-item">
          <div class="risk-label"><span>止损阈值</span></div>
          <div class="risk-input">
            <el-radio-group v-model="botRisk.sl_mode" size="small">
              <el-radio-button label="amount">金额</el-radio-button>
              <el-radio-button label="ratio">百分比</el-radio-button>
            </el-radio-group>

            <el-input-number
              v-if="botRisk.sl_mode === 'amount'"
              v-model="botRisk.sl_amount"
              :min="0" :step="1"
              :disabled="!botRisk.sl_enabled"
            />
            <el-input-number
              v-else
              v-model="botRisk.sl_ratio"
              :min="0" :step="0.1" :precision="2"
              suffix="%"
              :disabled="!botRisk.sl_enabled"
            />
          </div>
        </div>

        <!-- 追踪止损 -->
        <div class="risk-item">
          <div class="risk-label">
            <span>启用追踪止损</span>
            <p>回撤/反弹到触发线自动平仓并停止机器人</p>
          </div>
          <el-switch v-model="botRisk.trail_enabled" />
        </div>

        <div class="risk-item">
          <div class="risk-label"><span>追踪参数</span></div>
          <div class="risk-input">
            <el-radio-group v-model="botRisk.trail_mode" size="small">
              <el-radio-button label="amount">金额</el-radio-button>
              <el-radio-button label="ratio">百分比</el-radio-button>
            </el-radio-group>

            <template v-if="botRisk.trail_mode === 'amount'">
              <el-input-number v-model="botRisk.trail_activate_amount"
                :step="1" :disabled="!botRisk.trail_enabled"
                placeholder="触发盈亏" />
              <el-input-number v-model="botRisk.trail_drawdown_amount"
                :min="0" :step="1" :disabled="!botRisk.trail_enabled"
                placeholder="追踪止损" />
            </template>
            <template v-else>
              <el-input-number v-model="botRisk.trail_activate_ratio"
                :step="0.1" :precision="2" :disabled="!botRisk.trail_enabled"
                placeholder="触发盈亏" />
              <el-input-number v-model="botRisk.trail_drawdown_ratio"
                :min="0" :step="0.1" :precision="2" :disabled="!botRisk.trail_enabled"
                placeholder="追踪止损" />
            </template>
          </div>
        </div>

        <!-- 触发后行为 -->
        <div class="risk-item risk-item--full">
          <div class="risk-label">
            <span>触发后自动停止机器人</span>
            <p>止盈/止损后不再入场（不会删除，可手动重启）</p>
          </div>
          <div style="display:flex; gap:12px;">
            <el-checkbox v-model="botRisk.auto_stop_on_tp">止盈后</el-checkbox>
            <el-checkbox v-model="botRisk.auto_stop_on_sl">止损后</el-checkbox>
            <el-checkbox v-model="botRisk.auto_stop_on_trail">追踪止损后</el-checkbox>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 策略配置区（多空卡片） -->
    <div class="strategy-columns">
      <!-- 多头 -->
      <div v-if="botBaseInfo.enableLong" class="strategy-column">
        <el-card class="title-card long">
          <h3>📈 多头策略</h3>
        </el-card>
        <StrategyPanel
          v-if="localConfig.long.entry"
          :config="localConfig.long"
          :trade-info="longTradeInfo"
          @save="handleSaveLong"
        />
      </div>

      <!-- 空头 -->
      <div v-if="botBaseInfo.enableShort" class="strategy-column">
        <el-card class="title-card short">
          <h3>📉 空头策略</h3>
        </el-card>
        <StrategyPanel
          v-if="localConfig.short.entry"
          :config="localConfig.short"
          :trade-info="shortTradeInfo"
          @save="handleSaveShort"
        />
      </div>
    </div>

    <!-- 都没有启用时的提示 -->
    <el-empty
      v-if="!botBaseInfo.enableLong && !botBaseInfo.enableShort"
      description="请至少启用一个方向（多头或空头）"
    />

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
import { ref, computed, onMounted } from 'vue'
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

// ============ 编辑模式 ============
const botId = computed(() => route.params.id)
const isEdit = computed(() => !!botId.value)

// ============ 基础信息 ============
const botBaseInfo = ref({
  name: '',
  pair: [],              // ← 从字符串改为数组
  capital: 100,
  stakeAmount: 30,       // ← 新增
  leverage: 10,          // ← 新增
  dryRun: true,          // ← 新增
  enableLong: true,
  enableShort: false
})

// ============ 本地策略配置（完全独立，不碰全局）============
const localConfig = ref({
  long: getDefaultLongConfig(),
  short: getDefaultShortConfig()
})

// tradeInfo 只是给 StrategyPanel 展示的摘要，本地简单处理
// 如果你希望它跟配置联动，需要重写 buildTradeInfo 或调用原逻辑
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

const parseCfg = (v) => {
  if (!v) return null
  if (typeof v === 'string') {
    try { return JSON.parse(v) } catch { return null }
  }
  return v
}

// ============ 加载数据 ============
const loadBotDetail = async () => {
  if (!isEdit.value) return
  try {
    const { data } = await axios.get(`${API}/bots/${botId.value}`)

    botBaseInfo.value = {
      name: data.name,
      pair: Array.isArray(data.pair)
        ? data.pair
        : (data.pair ? [data.pair] : []),     // 兼容旧数据
      capital: data.capital ?? 100,
      stakeAmount: data.stakeAmount ?? 30,    // 兜底
      leverage: data.leverage ?? 10,
      dryRun: data.dryRun !== undefined ? !!data.dryRun : true,
      enableLong: !!data.enableLong,
      enableShort: !!data.enableShort,
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

// ============ 保存 ============
const buildPayload = () => ({
  base: {
    name: botBaseInfo.value.name,
    pair: botBaseInfo.value.pair,         // 数组
    capital: botBaseInfo.value.capital,
    stakeAmount: botBaseInfo.value.stakeAmount,
    leverage: botBaseInfo.value.leverage,
    dryRun: botBaseInfo.value.dryRun,
    enableLong: botBaseInfo.value.enableLong,
    enableShort: botBaseInfo.value.enableShort,
  },
  risk: botRisk.value,
  longConfig: localConfig.value.long,
  shortConfig: localConfig.value.short,
})

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
  if (!botBaseInfo.value.enableLong && !botBaseInfo.value.enableShort) {
    ElMessage.warning('请至少启用一个方向')
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

    // 启动
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

// ============ 子策略保存 ============
const handleSaveLong = () => {
  // 已经是本地对象，不需要额外操作
  ElMessage.success('多头策略已更新')
}

const handleSaveShort = () => {
  ElMessage.success('空头策略已更新')
}

const goBack = () => {
  router.push({ name: 'BotList' })
}

onMounted(loadBotDetail)
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

.header-actions {
  display: flex;
  gap: 12px;
}

.base-info-card {
  border-radius: 12px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
}

/* 多空列 */
.strategy-columns {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.strategy-column {
  flex: 1;
  min-width: 0;
}

.title-card {
  margin-bottom: 20px;
}

.title-card h3 {
  margin: 0;
  font-size: 16px;
}

.long {
  border-left: 6px solid #67c23a;
}

.short {
  border-left: 6px solid #f56c6c;
}

.save-footer {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: flex-end;
  padding: 16px 24px;
  margin-top: 8px;
  background: var(--bg-dark);   /* 或 var(--el-bg-color) */
  border-top: 1px solid var(--border-color);
  z-index: 10;
}
</style>