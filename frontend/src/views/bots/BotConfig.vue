<template>
  <div class="bot-config-page">
    <!-- 顶部返回栏 -->
    <div class="config-header">
      <el-button :icon="ArrowLeft" text @click="goBack">返回列表</el-button>
      <h2 class="config-title">{{ isEdit ? '编辑机器人' : '新建机器人' }}</h2>
    </div>

    <div class="config-layout">
      <!-- ============ 左列 ============ -->
      <div class="config-left">
        <el-card class="unified-card" shadow="never">
          <template #header>
            <div class="card-head">
              <span class="card-head__title">基础配置</span>
              <el-text type="info" size="small">
                机器人信息 · 策略参数 · 止盈止损
              </el-text>
            </div>
          </template>

          <div class="base-single">
            <!-- ── 第 1 节：机器人信息 ── -->
            <div class="config-section">
              <div class="section-label">机器人信息</div>
              <div class="field-list">
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
                  <div class="field-row field-row--sub">
                    <div class="field-label">止盈模式</div>
                    <div class="field-value">
                      <el-radio-group v-model="botRisk.tp_mode" size="small">
                        <el-radio-button label="amount">金额</el-radio-button>
                        <el-radio-button label="ratio">百分比</el-radio-button>
                      </el-radio-group>
                    </div>
                  </div>

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
        </el-card>

        <!-- 策略配置区 -->
        <el-card class="strategy-card" shadow="never">
          <template #header>
            <div class="card-head">
              <span class="card-head__title">策略配置</span>
              <el-text type="info" size="small">
                {{ botBaseInfo.direction === 'short' ? '空头策略' : '多头策略' }}
              </el-text>
            </div>
          </template>

          <StrategyPanel
            v-if="localConfig.long.entry"
            :config="localConfig.long"
            :trade-info="longTradeInfo"
            @save="handleSaveLong"
          />
        </el-card>
      </div>

      <!-- ============ 右列：回测区域 ============ -->
      <div class="config-right">
        <el-card class="backtest-card" shadow="never">
          <template #header>
            <div class="bt-header">
              <span class="bt-header__title">回测</span>
              <div class="bt-date-picker">
                <el-date-picker
                  v-model="backtestRange"
                  type="daterange"
                  range-separator="至"
                  start-placeholder="开始日期"
                  end-placeholder="结束日期"
                  value-format="YYYYMMDD"
                  :disabled-date="disableFutureDate"
                  :disabled="backtesting"
                  size="default"
                  :clearable="false"
                  @change="onBacktestRangeChange"
                />
              </div>
            </div>
          </template>

          <!-- ★ 进度视图 -->
          <div v-if="backtesting" class="bt-progress">
            <el-progress
              :percentage="Math.min(100, Math.round(backtestPercent))"
              :stroke-width="10"
              :status="backtestPercent >= 100 ? 'success' : undefined"
              striped
              striped-flow
            >
              <span class="bt-progress__pct">
                {{ Math.round(backtestPercent) }}%
              </span>
            </el-progress>

            <div class="bt-progress__row">
              <span class="bt-progress__stage">
                <el-icon class="is-loading"><Loading /></el-icon>
                {{ backtestStage || '准备中…' }}
              </span>
              <span class="bt-progress__elapsed">
                ⏱ {{ formatElapsed(backtestElapsed) }}
              </span>
            </div>

            <div class="bt-progress__tip">
              回测运行中，可继续调整左侧参数；本次结果使用点「回测」瞬间的参数快照
            </div>

            <div class="bt-progress__actions">
              <el-button size="small" @click="handleCancelBacktest">
                取消回测
              </el-button>
            </div>
          </div>

          <!-- 空状态 -->
          <el-empty
            v-else-if="!backtestResult"
            description="选择时间区间后，点击下方「回测」按钮查看结果"
          />

          <!-- 回测结果 -->
          <div v-else class="backtest-result">
            <div class="bt-summary">
              <div class="bt-metric">
                <div class="bt-metric__label">总收益</div>
                <div class="bt-metric__value" :class="profitClass(backtestResult.summary.total_profit_pct)">
                  {{ backtestResult.summary.total_profit_pct?.toFixed(2) }}%
                </div>
              </div>
              <div class="bt-metric">
                <div class="bt-metric__label">绝对收益 (USDT)</div>
                <div class="bt-metric__value" :class="profitClass(backtestResult.summary.absolute_profit)">
                  {{ backtestResult.summary.absolute_profit?.toFixed(2) }}
                </div>
              </div>
              <div class="bt-metric">
                <div class="bt-metric__label">交易次数</div>
                <div class="bt-metric__value">{{ backtestResult.summary.total_trades }}</div>
              </div>
              <div class="bt-metric">
                <div class="bt-metric__label">胜率</div>
                <div class="bt-metric__value">{{ backtestResult.summary.win_rate?.toFixed(1) }}%</div>
              </div>
              <div class="bt-metric">
                <div class="bt-metric__label">最大回撤</div>
                <div class="bt-metric__value bt-metric__value--danger">
                  {{ backtestResult.summary.max_drawdown?.toFixed(2) }}%
                </div>
              </div>
              <div class="bt-metric">
                <div class="bt-metric__label">Sharpe</div>
                <div class="bt-metric__value">{{ backtestResult.summary.sharpe?.toFixed(2) }}</div>
              </div>
              <div class="bt-metric">
                <div class="bt-metric__label">Profit Factor</div>
                <div class="bt-metric__value">{{ backtestResult.summary.profit_factor?.toFixed(2) }}</div>
              </div>
              <div class="bt-metric">
                <div class="bt-metric__label">CAGR</div>
                <div class="bt-metric__value" :class="profitClass(backtestResult.summary.cagr)">
                  {{ backtestResult.summary.cagr?.toFixed(2) }}%
                </div>
              </div>
              <div class="bt-metric">
                <div class="bt-metric__label">Sortino</div>
                <div class="bt-metric__value">{{ backtestResult.summary.sortino?.toFixed(2) }}</div>
              </div>
            </div>

            <div v-if="equityCurve.length" class="bt-chart">
              <div class="bt-chart__title">资金曲线</div>
              <svg :viewBox="`0 0 ${chartWidth} ${chartHeight}`" class="bt-chart__svg">
                <polyline
                  :points="equityCurvePoints"
                  fill="none"
                  stroke="var(--el-color-primary)"
                  stroke-width="2"
                />
              </svg>
            </div>

            <div class="bt-section">
              <div class="bt-section__title">按交易对</div>
              <el-table
                :data="backtestResult.pairs"
                size="small"
                class="bt-table"
                :header-cell-style="{ background: 'var(--el-fill-color-light)' }"
              >
                <el-table-column prop="pair" label="交易对" min-width="130" />
                <el-table-column prop="trades" label="笔数" width="60" align="center" />
                <el-table-column label="平均收益%" width="100" align="right">
                  <template #default="{ row }">
                    <span :class="profitClass(row.avg_profit_pct)">
                      {{ row.avg_profit_pct?.toFixed(2) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column label="总收益 USDT" width="110" align="right">
                  <template #default="{ row }">
                    <span :class="profitClass(row.total_profit_usdt)">
                      {{ row.total_profit_usdt?.toFixed(2) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="avg_duration" label="平均持仓" width="130" />
                <el-table-column label="胜率" width="80" align="right">
                  <template #default="{ row }">
                    {{ row.win_rate?.toFixed(1) }}%
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div class="bt-section">
              <div class="bt-section__title">退出原因</div>
              <el-table
                :data="backtestResult.exit_reasons"
                size="small"
                class="bt-table"
                :header-cell-style="{ background: 'var(--el-fill-color-light)' }"
              >
                <el-table-column prop="reason" label="退出原因" min-width="140" />
                <el-table-column prop="exits" label="笔数" width="60" align="center" />
                <el-table-column label="平均收益%" width="100" align="right">
                  <template #default="{ row }">
                    <span :class="profitClass(row.avg_profit_pct)">
                      {{ row.avg_profit_pct?.toFixed(2) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column label="总收益 USDT" width="110" align="right">
                  <template #default="{ row }">
                    <span :class="profitClass(row.total_profit_usdt)">
                      {{ row.total_profit_usdt?.toFixed(2) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="avg_duration" label="平均持仓" width="130" />
                <el-table-column label="胜率" width="80" align="right">
                  <template #default="{ row }">
                    {{ row.win_rate?.toFixed(1) }}%
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 底部保存栏 -->
    <div class="save-footer">
      <el-button
        size="large"
        :loading="downloading"
        :disabled="backtesting"
        @click="handleDownloadData"
      >
        <el-icon class="el-icon--left"><Download /></el-icon>
        下载数据
      </el-button>

      <el-button
        size="large"
        :loading="backtesting"
        @click="handleBacktest"
      >
        <el-icon class="el-icon--left"><DataAnalysis /></el-icon>
        {{ backtesting ? '回测中…' : '回测' }}
      </el-button>

      <el-button
        type="primary"
        size="large"
        :loading="saving"
        @click="handleSaveAndStart"
      >
        {{ submitButtonText }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ArrowLeft, DataAnalysis, Download, Loading } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  startBacktest,
  getBacktestProgress,
  cancelBacktest,
  downloadData
} from '@/api/backtest.js'
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

const botId = computed(() => route.params.id)
const isEdit = computed(() => !!botId.value)
const submitButtonText = computed(() =>
  isEdit.value ? '保存配置' : '创建机器人'
)

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

const localConfig = reactive({
  long: getDefaultLongConfig(),
  short: getDefaultShortConfig(),
})

const currentStrategy = computed(() => localConfig.long)

const longTradeInfo = computed(() => ({
  side: 'long',
  direction: '仅做多',
  timeframe: localConfig.long?.timeframe || '30m',
  leverage: `${localConfig.long?.leverage || 10}x`,
  stoploss: localConfig.long?.sl?.enable
    ? `${localConfig.long.sl.stoploss}%`
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

function debounce(fn, wait = 600) {
  let t = null
  return (...args) => {
    if (t) clearTimeout(t)
    t = setTimeout(() => fn(...args), wait)
  }
}

const parseCfg = (v) => {
  if (!v) return null
  if (typeof v === 'string') {
    try { return JSON.parse(v) } catch { return null }
  }
  return v
}

const onBacktestRangeChange = (val) => {
  const next = val || defaultRange()
  backtestRange.value = next
  saveRange(currentBotIdForStorage.value, next)
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

    if (longCfg && longCfg.entry) deepMerge(localConfig.long, longCfg)
    if (shortCfg && shortCfg.entry) deepMerge(localConfig.short, shortCfg)

  } catch (e) {
    console.error(e)
    ElMessage.error('加载机器人详情失败')
    router.push({ name: 'BotList' })
  }
}

const deepMerge = (target, source) => {
  if (!source || typeof source !== 'object') return target
  for (const key of Object.keys(source)) {
    const sv = source[key]
    const tv = target[key]
    if (sv && typeof sv === 'object' && !Array.isArray(sv) &&
        tv && typeof tv === 'object' && !Array.isArray(tv)) {
      deepMerge(tv, sv)
    } else {
      target[key] = sv
    }
  }
  return target
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
    longConfig: localConfig.long,
    shortConfig: localConfig.short,
  }
}

/* ============================================================
 * 参数实时同步
 * ★ 回测期间暂停自动同步，避免和回测抢 DB / 造成前端请求堆积
 * ============================================================ */
const syncing = ref(false)

const syncConfig = async () => {
  if (!botId.value) return
  try {
    syncing.value = true
    await axios.put(`${API}/bots/${botId.value}`, buildPayload())
  } catch (e) {
    console.error('[syncConfig] failed', e)
  } finally {
    syncing.value = false
  }
}

const syncConfigDebounced = debounce(syncConfig, 600)

watch(
  () => [botBaseInfo.value, botRisk.value, localConfig.long, localConfig.short],
  () => {
    if (!loaded.value) return
    // ★ 回测期间不自动同步
    if (backtesting.value) return
    syncConfigDebounced()
  },
  { deep: true }
)

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
  if (!botBaseInfo.value.name) { ElMessage.warning('请输入机器人名称'); return false }
  if (!botBaseInfo.value.pair?.length) { ElMessage.warning('请至少选择一个交易对'); return false }
  if (!botBaseInfo.value.capital || botBaseInfo.value.capital <= 0) { ElMessage.warning('投入资金必须大于 0'); return false }
  if (!botBaseInfo.value.stakeAmount || botBaseInfo.value.stakeAmount <= 0) { ElMessage.warning('开仓金额必须大于 0'); return false }
  if (!botBaseInfo.value.leverage || botBaseInfo.value.leverage < 1) { ElMessage.warning('持仓杠杆至少为 1'); return false }
  if (!botBaseInfo.value.maxOpenTrades || botBaseInfo.value.maxOpenTrades < 1) { ElMessage.warning('最大持仓数至少为 1'); return false }
  if (!['long', 'short', 'both'].includes(botBaseInfo.value.direction)) { ElMessage.warning('请选择方向'); return false }
  return true
}

const saving = ref(false)
const saved = ref(false)

onBeforeRouteLeave(async (to, from, next) => {
  // 回测进行中：提示
  if (backtesting.value) {
    try {
      await ElMessageBox.confirm(
        '回测正在进行中，离开会丢失进度。确定离开吗？',
        '提示',
        { type: 'warning' }
      )
    } catch {
      next(false)
      return
    }
    // 主动取消
    if (backtestJobId.value && botId.value) {
      try { await cancelBacktest(botId.value, backtestJobId.value) } catch {}
    }
    clearBacktestTimers()
  }

  if (!isEdit.value) { next(); return }
  if (saved.value) { next(); return }

  try {
    const { data } = await axios.get(`${API}/bots/${botId.value}`)
    if (data?.status === 'draft') {
      await axios.delete(`${API}/bots/${botId.value}`)
      console.log('[BotConfig] draft deleted on leave')
    }
  } catch (e) {
    console.warn('[BotConfig] cleanup draft failed', e)
  }
  next()
})

const handleSaveAndStart = async () => {
  if (!validate()) return

  // ★ 回测期间保存提醒
  if (backtesting.value) {
    try {
      await ElMessageBox.confirm(
        '回测正在进行中。保存会更新机器人参数，但不影响正在跑的回测（回测用的是启动瞬间的快照）。是否继续？',
        '提示',
        { type: 'warning' }
      )
    } catch {
      return
    }
  }

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

    saved.value = true

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

/* ============================================================
 * 下载数据
 * ============================================================ */
const downloading = ref(false)

const handleDownloadData = async () => {
  if (!botBaseInfo.value.pair?.length) {
    ElMessage.warning('请先选择交易对')
    return
  }
  if (!currentStrategy.value.timeframe) {
    ElMessage.warning('请先选择 K 线周期')
    return
  }
  if (!backtestRange.value || backtestRange.value.length !== 2) {
    backtestRange.value = defaultRange()
  }

  const [startStr, endStr] = backtestRange.value
  const timerange = `${startStr}-${endStr}`

  try { await syncConfig() } catch (e) { console.error(e) }

  downloading.value = true
  try {
    const res = await downloadData(botId.value, {
      side: botBaseInfo.value.direction === 'short' ? 'short' : 'long',
      timeframe: currentStrategy.value.timeframe || '30m',
      timerange,
    })
    if (res?.success) ElMessage.success('数据下载完成')
    else ElMessage.error('下载失败，请查看后端日志')
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || '下载失败')
  } finally {
    downloading.value = false
  }
}

/* ============================================================
 * 回测
 * ============================================================ */
const backtesting = ref(false)
const backtestResult = ref(null)
const backtestJobId = ref(null)
const backtestStage = ref('')
const backtestPercent = ref(0)
const backtestElapsed = ref(0)
let pollTimer = null
let elapsedTimer = null

const clearBacktestTimers = () => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null }
}

const formatElapsed = (sec) => {
  const s = Number(sec) || 0
  if (s < 60) return `${s.toFixed(1)}s`
  const m = Math.floor(s / 60)
  const r = (s % 60).toFixed(0)
  return `${m}m ${r}s`
}

const currentBotIdForStorage = computed(() => botId.value || null)
const backtestRange = ref(
  loadSavedRange(currentBotIdForStorage.value) || defaultRange()
)

function defaultRange() {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 60)
  const fmt = (d) => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}${m}${day}`
  }
  return [fmt(start), fmt(end)]
}

const STORAGE_KEY = 'backtest_range_v1'
const STORAGE_KEY_NEW = 'backtest_range_new_v1'

function loadSavedRange(botId) {
  try {
    const key = botId ? `${STORAGE_KEY}_${botId}` : STORAGE_KEY_NEW
    const raw = localStorage.getItem(key)
    if (!raw) return null
    const arr = JSON.parse(raw)
    if (Array.isArray(arr) && arr.length === 2 &&
        typeof arr[0] === 'string' && typeof arr[1] === 'string') {
      return arr
    }
  } catch (e) {
    console.warn('[backtest] load saved range failed:', e)
  }
  return null
}

function saveRange(botId, range) {
  if (!Array.isArray(range) || range.length !== 2) return
  try {
    const key = botId ? `${STORAGE_KEY}_${botId}` : STORAGE_KEY_NEW
    localStorage.setItem(key, JSON.stringify(range))
  } catch (e) {
    console.warn('[backtest] save range failed:', e)
  }
}

const disableFutureDate = (date) => date.getTime() > Date.now()

const profitClass = (val) => {
  if (val > 0) return 'is-profit'
  if (val < 0) return 'is-loss'
  return ''
}

const equityCurve = computed(() => {
  const trades = backtestResult.value?.trades || []
  if (!trades.length) return []
  let balance = backtestResult.value?.summary?.starting_balance || 100
  const points = [{ x: 0, y: balance }]
  trades.forEach((t, i) => {
    balance += t.profit_abs || 0
    points.push({ x: i + 1, y: balance })
  })
  return points
})

const chartWidth = 400
const chartHeight = 160

const equityCurvePoints = computed(() => {
  const pts = equityCurve.value
  if (pts.length < 2) return ''
  const xs = pts.map(p => p.x)
  const ys = pts.map(p => p.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const padX = 10
  const padY = 10
  return pts.map(p => {
    const x = padX + ((p.x - minX) / (maxX - minX || 1)) * (chartWidth - padX * 2)
    const y = chartHeight - padY - ((p.y - minY) / (maxY - minY || 1)) * (chartHeight - padY * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})

const startPolling = (botId, jobId) => {
  clearBacktestTimers()

  // 计时器：每 800ms 加一次（和轮询同频；会被后端返回的 elapsed 覆盖）
  elapsedTimer = setInterval(() => {
    backtestElapsed.value += 0.8
  }, 800)

  pollTimer = setInterval(async () => {
    try {
      const data = await getBacktestProgress(botId, jobId)
      backtestStage.value = data.stage || ''
      backtestPercent.value = data.percent || 0
      if (typeof data.elapsed === 'number') {
        backtestElapsed.value = data.elapsed
      }

      if (['success', 'failed', 'cancelled'].includes(data.status)) {
        clearBacktestTimers()
        backtesting.value = false

        if (data.status === 'success') {
          backtestResult.value = data.result
          ElMessage.success(`回测完成，耗时 ${formatElapsed(data.elapsed)}`)
        } else if (data.status === 'cancelled') {
          ElMessage.info('回测已取消')
        } else {
          const err = data.error || '回测失败'
          if (
            err.includes('No data') || err.includes('no data') ||
            err.includes('missing') || err.includes('not found')
          ) {
            ElMessage.warning({
              message: '该时间区间数据缺失，请先点「下载数据」',
              duration: 5000,
            })
          } else {
            ElMessage.error(err)
          }
        }
      }
    } catch (e) {
      console.error('[backtest polling] failed', e)
    }
  }, 800)
}

const handleBacktest = async () => {
  if (backtesting.value) return

  if (!botBaseInfo.value.pair?.length) {
    ElMessage.warning('请先选择交易对')
    return
  }
  if (!currentStrategy.value.timeframe) {
    ElMessage.warning('请先选择 K 线周期')
    return
  }
  if (!botId.value) {
    ElMessage.warning('请先保存机器人')
    return
  }

  if (!backtestRange.value || backtestRange.value.length !== 2) {
    backtestRange.value = defaultRange()
  }

  const [startStr, endStr] = backtestRange.value
  const timerange = `${startStr}-${endStr}`

  // 1. 冻结当前参数到 config
  try {
    await syncConfig()
  } catch (e) {
    console.error(e)
  }

  saveRange(botId.value, backtestRange.value)

  // 2. 重置 UI 状态
  backtesting.value = true
  backtestResult.value = null
  backtestStage.value = '提交任务'
  backtestPercent.value = 0
  backtestElapsed.value = 0

  try {
    const res = await startBacktest(botId.value, {
      side: botBaseInfo.value.direction === 'short' ? 'short' : 'long',
      timeframe: currentStrategy.value.timeframe || '30m',
      timerange,
      auto_download: false,
    })
    backtestJobId.value = res.job_id
    startPolling(botId.value, res.job_id)
  } catch (e) {
    backtesting.value = false
    clearBacktestTimers()
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || '回测启动失败')
  }
}

const handleCancelBacktest = async () => {
  if (!backtestJobId.value || !botId.value) return
  try {
    await cancelBacktest(botId.value, backtestJobId.value)
    ElMessage.info('已请求取消回测')
  } catch (e) {
    console.error(e)
  }
}

const handleSaveLong = () => {
  ElMessage.success('策略已更新')
}

const goBack = () => {
  router.push({ name: 'BotList' })
}

const loaded = ref(false)

onMounted(async () => {
  await loadPairs()
  await loadBotDetail()
  loaded.value = true
})

onUnmounted(() => {
  clearBacktestTimers()
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

.config-layout {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
  gap: 16px;
  align-items: start;
}

.config-left {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-right {
  min-width: 0;
  position: sticky;
  top: 16px;
}

.unified-card,
.strategy-card,
.backtest-card {
  border-radius: 12px;
}

.unified-card :deep(.el-card__header),
.strategy-card :deep(.el-card__header),
.backtest-card :deep(.el-card__header) {
  padding: 12px 16px;
  background: var(--el-fill-color-light);
}

.unified-card :deep(.el-card__body) {
  padding: 0;
}

.strategy-card :deep(.el-card__body) {
  padding: 12px;
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

.base-single { display: block; }

.config-section {
  padding: 16px 20px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.config-section:last-child { border-bottom: none; }

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin-bottom: 12px;
  padding-left: 8px;
  border-left: 3px solid var(--el-color-primary);
}

.field-list { display: flex; flex-direction: column; gap: 0; }

.field-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed var(--el-border-color-lighter);
  min-height: 40px;
}
.field-row:last-child { border-bottom: none; }

.field-row--switch {
  align-items: flex-start;
  padding: 12px 0;
}

.field-row--sub {
  background: var(--el-fill-color-extra-light);
  padding: 10px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.field-row--sub:last-child { border-bottom: none; }

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

.field-value {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
}
.field-value--right { justify-content: flex-end; }

.checkbox-stack {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.checkbox-stack :deep(.el-checkbox) { margin-right: 0; }

/* ============================================================ */
/* 回测卡片                                                      */
/* ============================================================ */
.backtest-card {
  min-height: calc(100vh - 200px);
  display: flex;
  flex-direction: column;
}
.backtest-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bt-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 4px 0;
}

.bt-header__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.bt-date-picker {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}
.bt-date-picker :deep(.el-date-editor) {
  width: 320px;
  --el-date-editor-width: 320px;
}
.bt-date-picker :deep(.el-range-input) {
  font-size: 14px;
  color: var(--el-text-color-primary);
}
.bt-date-picker :deep(.el-range-separator) {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}
.bt-date-picker :deep(.el-input__wrapper) {
  padding: 6px 12px;
  height: 36px;
}

/* ★ 进度视图 */
.bt-progress {
  width: 100%;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.bt-progress__pct {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.bt-progress__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.bt-progress__stage {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.bt-progress__elapsed {
  font-variant-numeric: tabular-nums;
  color: var(--el-text-color-secondary);
}
.bt-progress__tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  padding: 6px 10px;
  border-radius: 6px;
  line-height: 1.5;
}
.bt-progress__actions {
  display: flex;
  justify-content: flex-end;
}

/* 回测结果 */
.backtest-result {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px;
}

.bt-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.bt-metric {
  background: var(--el-fill-color-extra-light);
  border-radius: 8px;
  padding: 10px 12px;
}
.bt-metric__label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}
.bt-metric__value {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.bt-metric__value.is-profit { color: var(--el-color-success); }
.bt-metric__value.is-loss   { color: var(--el-color-danger); }

.bt-chart {
  background: var(--el-fill-color-extra-light);
  border-radius: 8px;
  padding: 12px;
}
.bt-chart__title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}
.bt-chart__svg {
  width: 100%;
  height: 160px;
}

.bt-table { width: 100%; }
.bt-table .is-profit { color: var(--el-color-success); }
.bt-table .is-loss   { color: var(--el-color-danger); }

.bt-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.bt-section__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

/* 底部保存栏 */
.save-footer {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  margin-top: 8px;
  background: var(--el-bg-color);
  border-top: 1px solid var(--el-border-color);
  z-index: 10;
}

@media (max-width: 1200px) {
  .config-layout { grid-template-columns: minmax(0, 1fr); }
  .config-right { position: static; }
  .backtest-card { min-height: 400px; }
}
</style>