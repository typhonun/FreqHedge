<template>
  <div class="bot-config-page">
    <!-- 顶部返回栏 -->
    <div class="config-header">
      <el-button :icon="ArrowLeft" text @click="goBack">返回列表</el-button>
      <h2 class="config-title">{{ pageTitle }}</h2>
    </div>

    <div class="config-layout">
      <!-- ============ 左列 ============ -->
      <div class="config-left">
        <el-card class="unified-card" shadow="never">
          <template #header>
            <div class="card-head">
              <span class="card-head__title">基础配置</span>
              <el-text type="info" size="small">
                机器人信息 · 交易参数 · 机器人风控
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
                      style="width: 100%"
                    />
                  </div>
                </div>

                <div class="field-row">
                  <div class="field-label">交易所账户</div>
                  <div class="field-value">
                    <el-select
                      v-model="botBaseInfo.exchangeAccountId"
                      placeholder="Demo"
                      style="width: 100%"
                      clearable
                    >
                      <el-option-group>
                        <el-option
                          label="Demo"
                          :value="DRY_RUN_VALUE"
                        />
                      </el-option-group>

                      <el-option-group
                        v-if="exchangeAccounts.length"
                      >
                        <el-option
                          v-for="acc in exchangeAccounts"
                          :key="acc.id"
                          :label="`${exchangeLabel(acc.exchange)} · ${acc.alias || '未命名'}${acc.isDefault ? ' (默认)' : ''}`"
                          :value="acc.id"
                        />
                      </el-option-group>
                    </el-select>

                    <span class="inline-field__hint" style="margin-top: 4px">
                      <template v-if="isDryRun">
                        Dry Run 使用实时行情模拟撮合，不产生真实订单
                      </template>
                      <template v-else>
                        实盘模式，将使用所选账户的 API 密钥下单
                      </template>
                    </span>

                    <el-text
                      v-if="!exchangeAccounts.length"
                      type="warning"
                      size="small"
                      style="margin-top: 4px"
                    >
                      还没有配置真实账户，去
                      <el-link type="primary" @click="goExchangeSettings">
                        设置 → 交易所 API
                      </el-link>
                      添加
                    </el-text>
                  </div>
                </div>

                <div class="field-row">
                  <div class="field-label">交易对</div>
                  <div class="field-value">
                    <el-select
                      v-model="botBaseInfo.pair"
                      multiple
                      filterable
                      :multiple-limit="isSinglePair ? 1 : 0"
                      collapse-tags
                      collapse-tags-tooltip
                      :placeholder="isSinglePair ? '选择交易对（仅支持单个）' : '选择交易对（可多选）'"
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
              </div>
            </div>

            <!-- ── 第 2 节：交易参数 ── -->
            <div class="config-section">
              <div class="section-label">交易参数</div>
              <div class="field-list">
                <!-- 交易模式 / 持仓模式 / 方向 -->
                <div class="field-row">
                  <div class="field-label">交易模式</div>
                  <div class="field-value">
                    <div class="inline-group inline-group--triple">
                      <div class="inline-field">
                        <span class="inline-field__label">模式</span>
                        <el-radio-group v-model="botBaseInfo.tradingMode" :disabled="isLocked">
                          <el-radio-button value="futures">合约</el-radio-button>
                          <el-radio-button value="spot">现货</el-radio-button>
                        </el-radio-group>
                      </div>

                      <div
                        v-if="botBaseInfo.tradingMode === 'futures'"
                        class="inline-field"
                      >
                        <span class="inline-field__label">持仓</span>
                        <el-radio-group v-model="botBaseInfo.marginMode" :disabled="isLocked">
                          <el-radio-button value="cross">全仓</el-radio-button>
                          <el-radio-button value="isolated">逐仓</el-radio-button>
                        </el-radio-group>
                      </div>

                      <div class="inline-field">
                        <span class="inline-field__label">方向</span>
                        <el-radio-group v-model="botBaseInfo.direction" :disabled="isLocked">
                          <el-radio-button value="long">做多</el-radio-button>
                          <el-radio-button
                            value="short"
                            :disabled="botBaseInfo.tradingMode === 'spot' || isLocked"
                          >
                            做空
                          </el-radio-button>
                        </el-radio-group>
                        <span
                          v-if="botBaseInfo.tradingMode === 'spot'"
                          class="inline-field__hint"
                        >
                          现货不支持做空
                        </span>
                        <!-- ★ 新增：被锁定时的提示 -->
                        <span v-if="isLocked" class="inline-field__hint text-warning">
                          持仓中，不可修改模式/方向
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 机器人可用资金 / 单笔保证金 -->
                <div class="field-row">
                  <div class="field-label">资金</div>
                  <div class="field-value">
                    <div class="inline-group inline-group--inputs">
                      <div class="inline-field" style="position: relative;">
                        <span class="inline-field__label">机器人可用资金 (USDT)</span>
                        <el-input-number
                          v-model="botBaseInfo.capital"
                          :min="1" :step="10"
                          controls-position="right"
                          style="width: 100%"
                        />
                      </div>
                      <!-- ★ 网格模式：单笔保证金显示为只读「每格金额」 -->
                      <div class="inline-field" style="position: relative;">
                        <template v-if="strategyType === 'grid'">
                          <span class="inline-field__label">每格金额 (USDT)</span>
                          <el-input :model-value="gridPerGridText" readonly style="width: 100%" />
                        </template>
                        <template v-else>
                          <span class="inline-field__label">单笔保证金 (USDT)</span>
                          <el-input-number
                            v-model="botBaseInfo.stakeAmount"
                            :min="1" :step="10"
                            controls-position="right"
                            style="width: 100%"
                          />
                        </template>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 持仓杠杆 / 最大持仓数 -->
                <div class="field-row">
                  <div class="field-label">持仓</div>
                  <div class="field-value">
                    <div class="inline-group inline-group--inputs">

                      <!-- ★ 修改点 1：去掉 position: relative 和 padding-bottom，让内容自动撑开 -->
                      <div class="inline-field">
                        <span class="inline-field__label">杠杆</span>
                        <el-input-number
                          v-model="botBaseInfo.leverage"
                          :min="1"
                          :max="botBaseInfo.tradingMode === 'spot' ? 1 : 125"
                          :disabled="botBaseInfo.tradingMode === 'spot' || isLocked"
                          :step="1"
                          controls-position="right"
                          style="width: 100%"
                        />
                        <span
                          v-if="botBaseInfo.tradingMode === 'spot'"
                          class="inline-field__hint"
                        >
                          现货固定 1x
                        </span>
                        <!-- ★ 修改点 2：去掉 absolute-hint 类，使用 inline-field__hint 统一风格 -->
                        <span v-if="isLocked" class="inline-field__hint text-warning" style="margin-top: 4px;">
                          持仓中，不可修改杠杆
                        </span>
                      </div>

                      <!-- ★ 同样去掉 position: relative 和 padding-bottom -->
                      <div class="inline-field">
                        <span class="inline-field__label">最大持仓数</span>
                        <el-input-number
                          v-model="botBaseInfo.maxOpenTrades"
                          :min="1" :max="100" :step="1"
                          :disabled="strategyType === 'grid'"
                          controls-position="right"
                          style="width: 100%"
                        />
                      </div>

                    </div>
                  </div>
                </div>

                <!-- ★ 新增：订单类型展示 -->
                <div class="field-row" style="border-top: 1px dashed var(--el-border-color-lighter); padding-top: 12px;">
                  <div class="field-label">订单类型</div>
                  <div class="field-value">
                    <el-radio-group :model-value="strategyType === 'grid' ? 'market' : 'limit'" disabled>
                      <el-radio-button value="limit">限价单 (Limit)</el-radio-button>
                      <el-radio-button value="market">市价单 (Market)</el-radio-button>
                    </el-radio-group>
                    <span class="inline-field__hint">
                      {{ strategyType === 'grid'
                        ? '网格策略需高频触发，系统强制使用市价单'
                        : '当前策略使用限价单，降低滑点' }}
                    </span>
                  </div>
                </div>
                
                <!-- 金额模式 (网格不显示) -->
                <div class="field-row" v-if="strategyType !== 'grid'">
                  <div class="field-label">
                    <span>
                      金额模式
                      <el-tooltip placement="top" effect="dark">
                        <template #content>
                          影响 DCA、网格、趋势加仓、TP 减仓、浮盈回补 的金额单位
                        </template>
                        <el-icon class="section-label__info"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </span>
                  </div>
                  <div class="field-value">
                    <el-radio-group
                      :model-value="currentStrategy.amount_mode"
                      @update:model-value="val => currentStrategy.amount_mode = val"
                    >
                      <el-radio-button value="amount">固定金额</el-radio-button>
                      <el-radio-button value="percent">百分比</el-radio-button>
                    </el-radio-group>
                  </div>
                </div>
              </div>
            </div>

            <!-- ── 第 3 节：机器人风控 ── -->
            <div class="config-section">
              <div class="section-label">机器人风控</div>
              <div class="field-list">

                <!-- 止盈 -->
                <div class="field-row field-row--switch">
                  <div class="field-label">
                    <span>
                      启用止盈
                      <el-tooltip placement="top" effect="dark">
                        <template #content>
                          账户总盈亏达到阈值时平掉全部仓位并停止机器人
                        </template>
                        <el-icon class="section-label__info"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </span>
                  </div>
                  <div class="field-value field-value--right">
                    <el-switch v-model="botRisk.tp_enabled" />
                  </div>
                </div>

                <div v-if="botRisk.tp_enabled" class="field-row field-row--sub">
                  <div class="field-label">止盈设置</div>
                  <div class="field-value">
                    <div class="inline-group inline-group--risk">
                      <el-radio-group v-model="botRisk.tp_mode" size="small">
                        <el-radio-button value="amount">金额</el-radio-button>
                        <el-radio-button value="ratio">百分比</el-radio-button>
                      </el-radio-group>

                      <div class="inline-field inline-field--compact">
                        <span class="inline-field__label">
                          {{ botRisk.tp_mode === 'amount' ? '阈值 (USDT)' : '阈值 (%)' }}
                        </span>
                        <el-input-number
                          v-if="botRisk.tp_mode === 'amount'"
                          v-model="botRisk.tp_amount"
                          :min="0" :step="1"
                          controls-position="right"
                          style="width: 140px"
                        />
                        <el-input-number
                          v-else
                          v-model="botRisk.tp_ratio"
                          :min="0" :step="0.1" :precision="2"
                          controls-position="right"
                          style="width: 140px"
                        />
                      </div>

                      <el-checkbox
                        v-model="botRisk.auto_stop_on_tp"
                        class="inline-check"
                      >
                        触发后停止机器人
                      </el-checkbox>
                    </div>
                  </div>
                </div>

                <!-- 止损 -->
                <div class="field-row field-row--switch">
                  <div class="field-label">
                    <span>
                      启用止损
                      <el-tooltip placement="top" effect="dark">
                        <template #content>
                          账户总亏损达到阈值时平掉全部仓位并停止机器人
                        </template>
                        <el-icon class="section-label__info"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </span>
                  </div>
                  <div class="field-value field-value--right">
                    <el-switch v-model="botRisk.sl_enabled" />
                  </div>
                </div>

                <div v-if="botRisk.sl_enabled" class="field-row field-row--sub">
                  <div class="field-label">止损设置</div>
                  <div class="field-value">
                    <div class="inline-group inline-group--risk">
                      <el-radio-group v-model="botRisk.sl_mode" size="small">
                        <el-radio-button value="amount">金额</el-radio-button>
                        <el-radio-button value="ratio">百分比</el-radio-button>
                      </el-radio-group>

                      <div class="inline-field inline-field--compact">
                        <span class="inline-field__label">
                          {{ botRisk.sl_mode === 'amount' ? '阈值 (USDT)' : '阈值 (%)' }}
                        </span>
                        <el-input-number
                          v-if="botRisk.sl_mode === 'amount'"
                          v-model="botRisk.sl_amount"
                          :min="0" :step="1"
                          controls-position="right"
                          style="width: 140px"
                        />
                        <el-input-number
                          v-else
                          v-model="botRisk.sl_ratio"
                          :min="0" :step="0.1" :precision="2"
                          controls-position="right"
                          style="width: 140px"
                        />
                      </div>

                      <el-checkbox
                        v-model="botRisk.auto_stop_on_sl"
                        class="inline-check"
                      >
                        触发后停止机器人
                      </el-checkbox>
                    </div>
                  </div>
                </div>

                <!-- 追踪止损 -->
                <div class="field-row field-row--switch">
                  <div class="field-label">
                    <span>
                      启用追踪止损
                      <el-tooltip placement="top" effect="dark">
                        <template #content>
                          浮盈达到激活线后，从最高点回撤超过阈值即平仓并停止机器人
                        </template>
                        <el-icon class="section-label__info"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </span>
                  </div>
                  <div class="field-value field-value--right">
                    <el-switch v-model="botRisk.trail_enabled" />
                  </div>
                </div>

                <div v-if="botRisk.trail_enabled" class="field-row field-row--sub">
                  <div class="field-label">追踪设置</div>
                  <div class="field-value">
                    <div class="inline-group inline-group--risk">
                      <el-radio-group v-model="botRisk.trail_mode" size="small">
                        <el-radio-button value="amount">金额</el-radio-button>
                        <el-radio-button value="ratio">百分比</el-radio-button>
                      </el-radio-group>

                      <div class="inline-field inline-field--compact">
                        <span class="inline-field__label">
                          {{ botRisk.trail_mode === 'amount' ? '触发盈亏 (USDT)' : '触发盈亏 (%)' }}
                        </span>
                        <el-input-number
                          v-if="botRisk.trail_mode === 'amount'"
                          v-model="botRisk.trail_activate_amount"
                          :step="1"
                          controls-position="right"
                          style="width: 140px"
                        />
                        <el-input-number
                          v-else
                          v-model="botRisk.trail_activate_ratio"
                          :step="0.1" :precision="2"
                          controls-position="right"
                          style="width: 140px"
                        />
                      </div>

                      <div class="inline-field inline-field--compact">
                        <span class="inline-field__label">
                          {{ botRisk.trail_mode === 'amount' ? '追踪止损 (USDT)' : '追踪止损 (%)' }}
                        </span>
                        <el-input-number
                          v-if="botRisk.trail_mode === 'amount'"
                          v-model="botRisk.trail_drawdown_amount"
                          :min="0" :step="1"
                          controls-position="right"
                          style="width: 140px"
                        />
                        <el-input-number
                          v-else
                          v-model="botRisk.trail_drawdown_ratio"
                          :min="0" :step="0.1" :precision="2"
                          controls-position="right"
                          style="width: 140px"
                        />
                      </div>

                      <el-checkbox
                        v-model="botRisk.auto_stop_on_trail"
                        class="inline-check"
                      >
                        触发后停止机器人
                      </el-checkbox>
                    </div>

                    <div class="field-hint" style="margin-top: 6px">
                      先达到「触发盈亏」激活追踪，随后从浮盈最高点回撤「追踪止损」值时平仓
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </div>
        </el-card>

        <!-- ★ 策略配置区 -->
        <el-card class="strategy-card" shadow="never">
          <template #header>
            <div class="card-head">
              <span class="card-head__title">
                {{ strategyDef.label }} 配置
              </span>
              <el-text type="info" size="small">
                {{ botBaseInfo.direction === 'short' ? '空头策略' : '多头策略' }}
              </el-text>
            </div>
          </template>

          <component
            :is="strategyDef.panel"
            :config="strategyConfig"
            :capital="botBaseInfo.capital"
            :pair="botBaseInfo.pair?.[0]"
            :direction="botBaseInfo.direction"
            :leverage="botBaseInfo.leverage"
            @save="handleSaveStrategy"
            @timeframe-change="onTimeframeChange"
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
                <el-radio-group
                  v-model="rangePreset"
                  size="small"
                  @change="onPresetChange"
                >
                  <el-radio-button value="7">7天</el-radio-button>
                  <el-radio-button value="30">30天</el-radio-button>
                  <el-radio-button value="60">60天</el-radio-button>
                  <el-radio-button value="90">90天</el-radio-button>
                  <el-radio-button value="180">半年</el-radio-button>
                  <el-radio-button value="365">一年</el-radio-button>
                  <el-radio-button value="custom">自定义</el-radio-button>
                </el-radio-group>

                <div v-if="rangePreset === 'custom'" class="bt-date-row">
                  <el-date-picker
                    v-model="customStart"
                    type="date"
                    placeholder="开始日期"
                    value-format="YYYYMMDD"
                    format="YYYY-MM-DD"
                    :disabled-date="disabledStartDate"
                    :disabled="backtesting"
                    size="small"
                    class="bt-date-single"
                    @change="onCustomDateChange"
                  />

                  <span class="bt-range-sep">至</span>

                  <el-date-picker
                    v-model="customEnd"
                    type="date"
                    placeholder="结束日期"
                    value-format="YYYYMMDD"
                    format="YYYY-MM-DD"
                    :disabled-date="disabledEndDate"
                    :disabled="backtesting"
                    size="small"
                    class="bt-date-single"
                    @change="onCustomDateChange"
                  />
                </div>

                <div class="bt-range-display">
                  <span class="bt-range-display__label">当前区间（滚动窗口）：</span>
                  <span class="bt-range-display__value">{{ displayRange }}</span>
                </div>
              </div>
            </div>
          </template>

          <div v-if="downloading" class="bt-progress">
            <el-progress
              :percentage="Math.min(100, Math.round(downloadPercent))"
              :stroke-width="10"
              :status="downloadPercent >= 100 ? 'success' : undefined"
              striped
              striped-flow
            >
              <span class="bt-progress__pct">
                {{ Math.round(downloadPercent) }}%
              </span>
            </el-progress>

            <div class="bt-progress__row">
              <span class="bt-progress__stage">
                <el-icon class="is-loading"><Loading /></el-icon>
                {{ downloadStage || '下载中…' }}
              </span>
              <span class="bt-progress__elapsed">
                ⏱ {{ formatElapsed(downloadElapsed) }}
              </span>
            </div>

            <div class="bt-progress__tip">
              正在下载 K 线数据，耗时可能几分钟；下载期间可继续调整左侧参数
            </div>

            <div class="bt-progress__actions">
              <el-button size="small" @click="handleCancelDownload">
                取消下载
              </el-button>
            </div>
          </div>

          <div v-else-if="backtesting" class="bt-progress">
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

          <el-empty
            v-else-if="!backtestResult"
            description="选择时间区间后，点击下方「回测」按钮查看结果"
          />

          <div v-else class="backtest-result">
            <!-- ★ 新增：回测时间范围展示 -->
            <div class="bt-range-header" v-if="backtestResult.summary.backtest_start">
              <el-icon><Calendar /></el-icon>
              回测范围：{{ backtestResult.summary.backtest_start }} ~ {{ backtestResult.summary.backtest_end }}
            </div>

            <div class="bt-summary">
              <!-- ★ 新增：初始资金 -->
              <div class="bt-metric">
                <div class="bt-metric__label">初始资金 (USDT)</div>
                <div class="bt-metric__value bt-metric__value--neutral">
                  {{ backtestResult.summary.starting_balance?.toFixed(2) }}
                </div>
              </div>

              <!-- ★ 新增：结束资金 -->
              <div class="bt-metric">
                <div class="bt-metric__label">结束资金 (USDT)</div>
                <div class="bt-metric__value" :class="profitClass(backtestResult.summary.final_balance - backtestResult.summary.starting_balance)">
                  {{ backtestResult.summary.final_balance?.toFixed(2) }}
                </div>
              </div>

              <div class="bt-metric">
                <div class="bt-metric__label">
                  总收益 (%)
                  <el-tooltip placement="top" content="回测区间内累计收益率">
                    <el-icon class="bt-metric__info"><InfoFilled /></el-icon>
                  </el-tooltip>
                </div>
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

              <!-- 把年化移到这里，比较显眼 -->
              <div class="bt-metric">
                <div class="bt-metric__label">
                  年化收益 CAGR (%)
                  <el-tooltip placement="top" content="年化复合增长率">
                    <el-icon class="bt-metric__info"><InfoFilled /></el-icon>
                  </el-tooltip>
                </div>
                <div class="bt-metric__value" :class="profitClass(backtestResult.summary.cagr)">
                  {{ backtestResult.summary.cagr?.toFixed(2) }}%
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
                <div class="bt-metric__label">
                  最大回撤 (%)
                  <el-tooltip placement="top" content="权益曲线从峰值的最大回落">
                    <el-icon class="bt-metric__info"><InfoFilled /></el-icon>
                  </el-tooltip>
                </div>
                <div class="bt-metric__value bt-metric__value--neutral">
                  {{ backtestResult.summary.max_drawdown?.toFixed(2) }}%
                </div>
              </div>
              <div class="bt-metric">
                <div class="bt-metric__label">
                  Sharpe
                  <el-tooltip placement="top" content="风险调整后收益；越高越好">
                    <el-icon class="bt-metric__info"><InfoFilled /></el-icon>
                  </el-tooltip>
                </div>
                <div class="bt-metric__value">{{ backtestResult.summary.sharpe?.toFixed(2) }}</div>
              </div>
              <div class="bt-metric">
                <div class="bt-metric__label">
                  Profit Factor
                  <el-tooltip placement="top" content="总盈利 / 总亏损">
                    <el-icon class="bt-metric__info"><InfoFilled /></el-icon>
                  </el-tooltip>
                </div>
                <div class="bt-metric__value">{{ backtestResult.summary.profit_factor?.toFixed(2) }}</div>
              </div>
              <div class="bt-metric">
                <div class="bt-metric__label">
                  Sortino
                  <el-tooltip placement="top" content="仅考虑下行波动的风险调整收益">
                    <el-icon class="bt-metric__info"><InfoFilled /></el-icon>
                  </el-tooltip>
                </div>
                <div class="bt-metric__value">{{ backtestResult.summary.sortino?.toFixed(2) }}</div>
              </div>
            </div>

            <div class="bt-section">
              <div class="bt-section__title">交易对</div>
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
                <el-table-column label="退出原因" min-width="140">
                  <template #default="{ row }">
                    {{ exitReasonLabel(row.reason) }}
                  </template>
                </el-table-column>
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
        {{ downloading ? '下载中…' : '下载数据' }}
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
/* ══════════════════════════════════════════════════════════════════
 * 1. Imports
 * ══════════════════════════════════════════════════════════════════ */
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ArrowLeft, DataAnalysis, Download, Loading, InfoFilled, Calendar } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useExchangeAccounts } from '@/composables/useExchangeAccounts'
import { BOT_DEFAULTS, RISK_DEFAULTS, getDirectionalDefaults } from '@/config/botDefaults.js'
import { getStrategyDef } from '@/config/strategyRegistry.js'
import {
  startBacktest,
  getBacktestProgress,
  cancelBacktest,
  startDownload,
  getDownloadProgress,
  cancelDownload,
  downloadData
} from '@/api/backtest.js'
import { useBotStore } from '@/stores/botStore.js'
import axios from 'axios'

/* ══════════════════════════════════════════════════════════════════
 * 2. 常量 / 路由 / Store
 * ══════════════════════════════════════════════════════════════════ */
const API = 'http://localhost:9000'

const route = useRoute()
const router = useRouter()
const { createBot, updateBot } = useBotStore()
const { accounts: exchangeAccounts, defaultAccount, getById: getExchangeAccount } = useExchangeAccounts()
const exchangeLabel = (v) => ({
  binance: 'Binance',
  okx: 'OKX',
  bybit: 'Bybit',
  kucoin: 'KuCoin',
  gate: 'Gate.io',
  huobi: 'HTX',
}[v] || v)

const DRY_RUN_VALUE = '__dry_run__'

const goExchangeSettings = () => {
  router.push('/settings/exchanges')
}

/* ══════════════════════════════════════════════════════════════════
 * 3. 派生状态
 * ══════════════════════════════════════════════════════════════════ */
const botId = computed(() => route.params.id)
// ★ 新增：判断当前是什么策略类型
const strategyType = computed(() => route.query.strategyType || 'dca')
const strategyDef = computed(() => getStrategyDef(strategyType.value))
const isSinglePair = computed(() => !!strategyDef.value.singlePair)

const copyFromId = computed(() => route.query.copyFrom)
const isCopy = computed(() => !!copyFromId.value)
const isEdit = computed(() => !!botId.value && !isCopy.value)

const submitButtonText = computed(() => {
  if (isEdit.value) return '保存配置'
  return '创建机器人'
})

const pageTitle = computed(() => {
  if (isEdit.value) return '编辑机器人'
  if (isCopy.value) return '复制机器人'
  return '新建机器人'
})

const gridPerGridText = computed(() => {
  if (strategyType.value !== 'grid') return ''
  const grid = strategyConfig.grid || {}
  const gridCount = Math.max(1, Number(grid.grid_count || 20))
  const capital = Number(botBaseInfo.value.capital || 0)
  const v = capital / gridCount
  if (!Number.isFinite(v) || v <= 0) return '—'
  return `${v.toFixed(2)} USDT`
})

// 1. 增加状态
const botStatus = ref('stopped') // 记录机器人运行状态
const hasOpenPositions = ref(false) // 记录是否有持仓

// 2. 增加判断计算属性
const isLocked = computed(() => {
  // 如果是编辑模式，且机器人运行中，且有持仓，则锁定
  return isEdit.value && botStatus.value === 'running' && hasOpenPositions.value
})

// 3. 修改 loadBotDetail 方法，获取持仓状态
const loadBotDetail = async () => {
  const sourceId = isCopy.value ? copyFromId.value : botId.value
  if (!sourceId) return

  try {
    const { data } = await axios.get(`${API}/bots/${sourceId}`)

    // ★ 1. 记录当前机器人运行状态
    botStatus.value = data.status || 'stopped'

    /* ════════════════════════════════════════════════════════
     * ★ 以 DB 为准，校正 URL 的 strategyType
     * ════════════════════════════════════════════════════════ */
    if (!isCopy.value) {
      const realType = data.strategyType || 'dca'
      if (realType !== strategyType.value) {
        console.warn(
          `[loadBotDetail] strategyType 不一致：URL=${strategyType.value}, DB=${realType}，强制刷新`
        )
        router.replace({
          name: route.name,
          params: route.params,
          query: { ...route.query, strategyType: realType },
        }).finally(() => {
          window.location.reload()
        })
        return
      }
    }

    if (isCopy.value) {
      try {
        const { data: cur } = await axios.get(`${API}/bots/${botId.value}`)
        isDraft.value = cur.status === 'draft'
      } catch {
        isDraft.value = true
      }
    } else {
      isDraft.value = data.status === 'draft'
    }

    // ★ 2. 查询是否有持仓（仅在编辑且运行中时查询）
    if (isEdit.value && botStatus.value === 'running') {
      try {
        const posRes = await axios.get(`${API}/chart/bot-positions/${sourceId}`)
        const positions = posRes.data || []
        // 只要返回的数组长度大于 0，说明有持仓
        hasOpenPositions.value = positions.length > 0
      } catch (e) {
        console.warn('获取持仓状态失败', e)
        hasOpenPositions.value = false
      }
    }

    const dir = (() => {
      const l = !!data.enableLong
      const s = !!data.enableShort
      if (s) return 'short'
      return 'long'
    })()

    /* ★ 关键改动：Dry Run 时强制清空 exchangeAccountId，
       避免旧数据「dryRun=true 但有 accountId」的歧义 */
    const isDryRunFromData = data.dryRun !== undefined
      ? !!data.dryRun
      : !data.exchangeAccountId

    const accountId = isDryRunFromData
      ? DRY_RUN_VALUE
      : (data.exchangeAccountId ?? DRY_RUN_VALUE)

    botBaseInfo.value = {
      name: isCopy.value ? '' : data.name,
      pair: Array.isArray(data.pair) ? data.pair : (data.pair ? [data.pair] : []),
      capital: data.capital ?? BOT_DEFAULTS.capital,
      stakeAmount: data.stakeAmount ?? BOT_DEFAULTS.stakeAmount,
      leverage: data.leverage ?? BOT_DEFAULTS.leverage,
      // ★ 如果是网格策略，强制 maxOpenTrades 为 1
      maxOpenTrades: strategyType.value === 'grid' ? 1 : (data.maxOpenTrades ?? BOT_DEFAULTS.maxOpenTrades),
      direction: dir,
      exchangeAccountId: accountId,
      tradingMode: data.tradingMode ?? BOT_DEFAULTS.tradingMode,
      marginMode: data.marginMode ?? BOT_DEFAULTS.marginMode,
    }

    botRisk.value = Object.fromEntries(
      Object.keys(RISK_DEFAULTS).map((key) => [
        key,
        data[key] ?? RISK_DEFAULTS[key],
      ])
    )

    /* ════════════════════════════════════════════════════════
     * ★ 网格机器人与 DCA 机器人的加载路径分叉
     * ════════════════════════════════════════════════════════ */
    const raw = strategyDef.value.unwrap(data, dir)
    if (raw) {
      deepMerge(strategyConfig, raw)
    }

    // ★ DCA 特有：维护 sideFields（entryRsiValue / dcaLevels）
    if (strategyType.value === 'dca') {
      const longCfg = parseCfg(data.longConfig)
      const shortCfg = parseCfg(data.shortConfig)

      let cfgToLoad = null
      if (dir === 'short' && shortCfg && shortCfg.entry) cfgToLoad = shortCfg
      else if (dir === 'long' && longCfg && longCfg.entry) cfgToLoad = longCfg
      else if (longCfg && longCfg.entry) cfgToLoad = longCfg

      const dcaLevelCount = (strategyConfig.dca?.levels || []).length

      if (cfgToLoad && cfgToLoad.entry) {
        sideFields[dir].entryRsiValue =
          cfgToLoad.entry?.rsi?.value ?? defaultEntryRsi(dir)

        const cfgLevels = cfgToLoad.dca?.levels || []
        sideFields[dir].dcaLevels = Array.from({ length: dcaLevelCount }, (_, i) => ({
          rsi_limit: cfgLevels[i]?.rsi_limit ?? defaultRsiLimit(dir),
          j_limit: cfgLevels[i]?.j_limit ?? defaultJLimit(dir),
        }))
      } else {
        sideFields[dir].entryRsiValue = defaultEntryRsi(dir)
        sideFields[dir].dcaLevels = Array.from({ length: dcaLevelCount }, () => ({
          rsi_limit: defaultRsiLimit(dir),
          j_limit: defaultJLimit(dir),
        }))
      }

      const otherDir = dir === 'long' ? 'short' : 'long'
      sideFields[otherDir].entryRsiValue = defaultEntryRsi(otherDir)
      sideFields[otherDir].dcaLevels = Array.from({ length: dcaLevelCount }, () => ({
        rsi_limit: defaultRsiLimit(otherDir),
        j_limit: defaultJLimit(otherDir),
      }))

      strategyConfig.side = dir
    }

    if (!isCopy.value) {
      updateSnapshot()
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载机器人配置失败')
    router.push({ name: 'BotList' })
  }
}

/* ══════════════════════════════════════════════════════════════════
 * 4. 回测区间：纯函数 + 常量
 * ══════════════════════════════════════════════════════════════════ */
const STORAGE_KEY = 'backtest_range_v1'
const STORAGE_KEY_NEW = 'backtest_range_new_v1'

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

function loadSavedRange(id) {
  try {
    const key = id ? `${STORAGE_KEY}_${id}` : STORAGE_KEY_NEW
    const raw = localStorage.getItem(key)
    if (!raw) return null
    const arr = JSON.parse(raw)
    if (
      Array.isArray(arr) &&
      arr.length === 2 &&
      typeof arr[0] === 'string' &&
      typeof arr[1] === 'string'
    ) {
      return arr
    }
  } catch (e) {
    console.warn('[backtest] load saved range failed:', e)
  }
  return null
}

function saveRange(id, range) {
  if (!Array.isArray(range) || range.length !== 2) return
  try {
    const key = id ? `${STORAGE_KEY}_${id}` : STORAGE_KEY_NEW
    localStorage.setItem(key, JSON.stringify(range))
  } catch (e) {
    console.warn('[backtest] save range failed:', e)
  }
}

function parseYYYYMMDD(s) {
  if (typeof s !== 'string' || s.length !== 8) return null
  const y = Number(s.slice(0, 4))
  const m = Number(s.slice(4, 6)) - 1
  const d = Number(s.slice(6, 8))
  return new Date(y, m, d)
}

/* ══════════════════════════════════════════════════════════════════
 * 5. 回测区间 refs
 * ══════════════════════════════════════════════════════════════════ */
const rangePreset = ref('60')
const currentBotIdForStorage = computed(() => botId.value || null)

const backtestRange = ref(
  loadSavedRange(currentBotIdForStorage.value) || defaultRange()
)

const customStart = ref('')
const customEnd = ref('')

/* ══════════════════════════════════════════════════════════════════
 * 6. 回测区间 computed / watch / 事件
 * ══════════════════════════════════════════════════════════════════ */
const displayRange = computed(() => {
  const r = backtestRange.value
  if (!Array.isArray(r) || r.length !== 2) return '未选择'

  const fmt = (s) => {
    if (typeof s === 'string' && s.length === 8) {
      return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`
    }
    try {
      const d = new Date(s)
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    } catch {
      return String(s)
    }
  }
  return `${fmt(r[0])} ~ ${fmt(r[1])}`
})

watch(
  backtestRange,
  (val) => {
    if (Array.isArray(val) && val.length === 2) {
      customStart.value = val[0]
      customEnd.value = val[1]
    }
  },
  { immediate: true }
)

const onBacktestRangeChange = (val) => {
  const next = val || defaultRange()
  backtestRange.value = next
  saveRange(currentBotIdForStorage.value, next)
}

const onCustomDateChange = () => {
  if (!customStart.value || !customEnd.value) return

  if (Number(customStart.value) > Number(customEnd.value)) {
    const tmp = customStart.value
    customStart.value = customEnd.value
    customEnd.value = tmp
  }

  backtestRange.value = [customStart.value, customEnd.value]
  onBacktestRangeChange(backtestRange.value)
}

const onPresetChange = (val) => {
  if (val === 'custom') {
    if (!customStart.value || !customEnd.value) {
      customStart.value = backtestRange.value?.[0] || ''
      customEnd.value = backtestRange.value?.[1] || ''
    }
    return
  }

  const days = Number(val)
  if (!Number.isFinite(days) || days <= 0) return

  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - days)

  const fmt = (d) => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}${m}${day}`
  }

  const range = [fmt(start), fmt(end)]
  backtestRange.value = range
  onBacktestRangeChange(range)
}

const disabledStartDate = (date) => {
  if (date.getTime() > Date.now()) return true

  if (customEnd.value) {
    const end = parseYYYYMMDD(customEnd.value)
    if (end) {
      const d = new Date(date.getFullYear(), date.getMonth(), date.getDate())
      return d.getTime() > end.getTime()
    }
  }
  return false
}

const disabledEndDate = (date) => {
  if (date.getTime() > Date.now()) return true

  if (customStart.value) {
    const start = parseYYYYMMDD(customStart.value)
    if (start) {
      const d = new Date(date.getFullYear(), date.getMonth(), date.getDate())
      return d.getTime() < start.getTime()
    }
  }
  return false
}

const inferPresetFromRange = () => {
  const r = backtestRange.value
  if (!Array.isArray(r) || r.length !== 2) {
    rangePreset.value = '60'
    return
  }

  const [startStr, endStr] = r
  const end = new Date()
  const today = `${end.getFullYear()}${String(end.getMonth() + 1).padStart(2, '0')}${String(end.getDate()).padStart(2, '0')}`

  if (endStr !== today) {
    rangePreset.value = 'custom'
    return
  }

  const startDate = parseYYYYMMDD(startStr)
  const endDate = parseYYYYMMDD(endStr)
  if (!startDate || !endDate) {
    rangePreset.value = 'custom'
    return
  }

  const days = Math.round((endDate - startDate) / (1000 * 60 * 60 * 24))
  const presets = [7, 30, 60, 90, 180, 365]
  rangePreset.value = presets.includes(days) ? String(days) : 'custom'
}

/* ══════════════════════════════════════════════════════════════════
 * 7. 基础业务状态
 * ══════════════════════════════════════════════════════════════════ */
const botBaseInfo = ref({
  name: '',
  pair: [],
  ...BOT_DEFAULTS,
  direction: 'long',
  exchangeAccountId: DRY_RUN_VALUE,
})

/* ★ Dry Run 判定：显式字符串 or 空值（clearable 后）都算 Dry Run */
const isDryRun = computed(() => {
  const v = botBaseInfo.value.exchangeAccountId
  return v === DRY_RUN_VALUE || v === null || v === undefined || v === ''
})

const isDraft = ref(false)

const botRisk = ref({
  ...RISK_DEFAULTS,
})

// ★ 单一配置对象（网格/DCA/未来类型共用）
const strategyConfig = reactive(strategyDef.value.defaultConfig('long'))

// ★ 兼容旧命名（DCA 特有的 amount_mode、currentConfig.entry 等仍在用）
const currentConfig = computed(() => strategyConfig)
const currentStrategy = computed(() => strategyConfig)

const pairOptions = ref([])
const pairLoading = ref(false)

const saving = ref(false)
const saved = ref(false)
const downloading = ref(false)

const downloadJobId = ref(null)
const downloadStage = ref('')
const downloadPercent = ref(0)
const downloadElapsed = ref(0)
let downloadPollTimer = null
let downloadElapsedTimer = null

const clearDownloadTimers = () => {
  if (downloadPollTimer) {
    clearInterval(downloadPollTimer)
    downloadPollTimer = null
  }
  if (downloadElapsedTimer) {
    clearInterval(downloadElapsedTimer)
    downloadElapsedTimer = null
  }
}

const startDownloadPolling = (id, jobId) => {
  clearDownloadTimers()

  downloadPollTimer = setInterval(async () => {
    try {
      const res = await getDownloadProgress(id, jobId)
      const data = res?.data || res

      downloadStage.value = data.stage || ''
      if (typeof data.percent === 'number') {
        downloadPercent.value = data.percent
      }
      if (typeof data.elapsed === 'number') {
        downloadElapsed.value = data.elapsed
      }

      if (['success', 'failed', 'cancelled'].includes(data.status)) {
        clearDownloadTimers()
        downloading.value = false

        if (data.status === 'success') {
          downloadPercent.value = 100
          const r = data.result || {}
          if (r.skipped) {
            ElMessage.success(r.message || '数据已下载')
          } else {
            // ★ 修改点：展示后端返回的具体时间范围
            if (r.message && r.message.includes('实际可用数据区间')) {
                ElMessage.warning({
                    message: r.message,
                    duration: 8000,
                    showClose: true
                })
            } else {
                ElMessage.success(`数据下载完成，耗时 ${formatElapsed(downloadElapsed.value)}`)
            }
          }
        }
      }
    } catch (e) {
      console.error('[download polling] failed', e)
    }
  }, 800)
}

const loaded = ref(false)

/* ══════════════════════════════════════════════════════════════════
 * 8. 方向相关字段
 * ══════════════════════════════════════════════════════════════════ */
const sideFields = reactive({
  long: { entryRsiValue: getDirectionalDefaults('long').entryRsiValue, dcaLevels: [] },
  short: { entryRsiValue: getDirectionalDefaults('short').entryRsiValue, dcaLevels: [] },
})

const defaultRsiLimit = (dir) => getDirectionalDefaults(dir).rsiLimit
const defaultJLimit = (dir) => getDirectionalDefaults(dir).jLimit
const defaultEntryRsi = (dir) => getDirectionalDefaults(dir).entryRsiValue

/* ══════════════════════════════════════════════════════════════════
 * 9. 工具函数
 * ══════════════════════════════════════════════════════════════════ */
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
    try {
      return JSON.parse(v)
    } catch {
      return null
    }
  }
  return v
}

const deepMerge = (target, source) => {
  if (!source || typeof source !== 'object') return target
  for (const key of Object.keys(source)) {
    const sv = source[key]
    const tv = target[key]
    if (
      sv &&
      typeof sv === 'object' &&
      !Array.isArray(sv) &&
      tv &&
      typeof tv === 'object' &&
      !Array.isArray(tv)
    ) {
      deepMerge(tv, sv)
    } else {
      target[key] = sv
    }
  }
  return target
}

const stableStringify = (obj) => {
  if (obj === null || typeof obj !== 'object') return JSON.stringify(obj)
  if (Array.isArray(obj)) {
    return '[' + obj.map(stableStringify).join(',') + ']'
  }
  const keys = Object.keys(obj).sort()
  return '{' + keys.map(k => JSON.stringify(k) + ':' + stableStringify(obj[k])).join(',') + '}'
}

const profitClass = (val) => {
  if (val > 0) return 'is-profit'
  if (val < 0) return 'is-loss'
  return ''
}

const formatElapsed = (sec) => {
  const s = Number(sec) || 0
  if (s < 60) return `${s.toFixed(1)}s`
  const m = Math.floor(s / 60)
  const r = (s % 60).toFixed(0)
  return `${m}m ${r}s`
}

/**
 * 退出原因枚举 → 中文标签
 * 对应后端 DcaTpBotBase 里 order_filled / custom_exit 写入的 tag
 */
const exitReasonLabel = (reason) => {
  if (!reason) return '-'
  const s = String(reason)

  if (s === 'stop_loss') return 'ROI 止损'
  if (s === 'time_stop') return '时间止损'

  // ★ 新增：网格相关
  if (s === 'grid_stop_lower') return '网格跌破下沿'
  if (s === 'grid_stop_upper') return '网格涨破上沿'
  if (s.startsWith('grid_reduce_lv')) return `网格减仓 格${s.slice(14)}`
  if (s.startsWith('grid_add_lv')) return `网格加仓 格${s.slice(11)}`
  if (s.startsWith('grid_tp_lv')) return `网格止盈 格${s.slice(10)}`

  if (s.startsWith('tp_afterDCA')) return 'DCA 后止盈'
  if (s.startsWith('tp_')) return 'ROI 止盈'
  if (s.startsWith('dca_u=')) return `DCA 第 ${s.slice(6)} 层`
  if (s.startsWith('dca')) return 'DCA 加仓'
  if (s.startsWith('trend_add')) return '趋势加仓'
  if (s.startsWith('kdj_reduce')) return 'KDJ 减仓'
  if (s.startsWith('rebuy_')) return '浮盈回补'
  return s
}

/* ══════════════════════════════════════════════════════════════════
 * 10. Payload 构造 / 快照
 * ══════════════════════════════════════════════════════════════════ */
const buildPayload = () => {
  const dir = botBaseInfo.value.direction
  const acct = isDryRun.value ? null : getExchangeAccount(botBaseInfo.value.exchangeAccountId)
  const dryRun = isDryRun.value

  // ★ 计算 stakeAmount
  let stakeAmount = botBaseInfo.value.stakeAmount
  if (strategyType.value === 'grid') {
    const grid = strategyConfig.grid || {}
    const gridCount = Math.max(1, Number(grid.grid_count || 20))
    const capital = Number(botBaseInfo.value.capital || 0)
    // ★ 每格金额 = 投入资金 / 网格数量
    stakeAmount = capital / gridCount
  }

  const common = {
    name: botBaseInfo.value.name,
    pair: botBaseInfo.value.pair,
    capital: botBaseInfo.value.capital,
    stakeAmount: stakeAmount,        // ★ 用算好的
    leverage: botBaseInfo.value.leverage,
    maxOpenTrades: botBaseInfo.value.maxOpenTrades,
    dryRun,
    enableLong: dir === 'long',
    enableShort: dir === 'short',
    exchangeAccountId: botBaseInfo.value.exchangeAccountId || null,
    exchangeAccount: dryRun ? null : (acct ? {
      exchange: acct.exchange,
      apiKey: acct.apiKey,
      apiSecret: acct.apiSecret,
      passphrase: acct.passphrase || '',
    } : null),
    tradingMode: botBaseInfo.value.tradingMode,
    marginMode: botBaseInfo.value.marginMode,
    strategyType: strategyType.value,
  }

  return {
    base: common,
    risk: botRisk.value,
    [strategyDef.value.configKey]: strategyConfig,
  }
}

const savedPayload = ref(null)

const updateSnapshot = () => {
  try {
    savedPayload.value = JSON.parse(JSON.stringify(buildPayload()))
  } catch (e) {
    console.warn('[updateSnapshot] failed', e)
    savedPayload.value = null
  }
}

const hasChanges = () => {
  if (!savedPayload.value) return true
  try {
    return stableStringify(buildPayload()) !== stableStringify(savedPayload.value)
  } catch (e) {
    console.warn('[hasChanges] failed', e)
    return true
  }
}

/* ══════════════════════════════════════════════════════════════════
 * 11. 校验 / 保存 / 回滚
 * ══════════════════════════════════════════════════════════════════ */
const validate = () => {
  if (!botBaseInfo.value.name) {
    ElMessage.warning('请输入机器人名称')
    return false
  }
  if (!botBaseInfo.value.pair?.length) {
    ElMessage.warning('请至少选择一个交易对')
    return false
  }
  if (isSinglePair.value && botBaseInfo.value.pair.length !== 1) {
    ElMessage.warning(`${strategyDef.value.label} 只能选择 1 个交易对`)
    return false
  }
  if (!botBaseInfo.value.capital || botBaseInfo.value.capital <= 0) {
    ElMessage.warning('机器人可用资金必须大于 0')
    return false
  }
  if (!botBaseInfo.value.stakeAmount || botBaseInfo.value.stakeAmount <= 0) {
    ElMessage.warning('单笔保证金必须大于 0')
    return false
  }
  if (!['spot', 'futures'].includes(botBaseInfo.value.tradingMode)) {
    ElMessage.warning('请选择交易模式')
    return false
  }
  if (botBaseInfo.value.tradingMode === 'futures'
      && !['cross', 'isolated'].includes(botBaseInfo.value.marginMode)) {
    ElMessage.warning('请选择持仓模式')
    return false
  }
  if (botBaseInfo.value.tradingMode === 'spot'
      && botBaseInfo.value.direction === 'short') {
    ElMessage.warning('现货模式不支持做空')
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
  if (!['long', 'short'].includes(botBaseInfo.value.direction)) {
    ElMessage.warning('请选择方向')
    return false
  }
  return true
}

const revertToSnapshot = async () => {
  if (isDraft.value) return
  if (!isEdit.value) return
  if (!savedPayload.value) return
  if (!hasChanges()) return
  try {
    await axios.put(`${API}/bots/${botId.value}`, savedPayload.value)
    console.log('[leave] 已恢复到上次保存状态')
  } catch (e) {
    console.warn('[leave] 恢复失败', e)
  }
}

const saveAndRestart = async () => {
  if (!validate()) return false
  if (!hasChanges()) return true

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

    isDraft.value = false

    axios.post(`${API}/bots/${id}/start`).catch((e) => {
      console.warn('[saveAndRestart] start 失败', e)
      ElMessage.warning({
        message: '后台启动机器人失败，请在列表页手动启动',
        duration: 5000,
      })
    })

    updateSnapshot()
    saved.value = true
    return true
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存失败')
    return false
  } finally {
    saving.value = false
  }
}

/* ══════════════════════════════════════════════════════════════════
 * 12. 加载交易对 / Bot 详情
 * ══════════════════════════════════════════════════════════════════ */
const loadPairs = async () => {
  pairLoading.value = true
  try {
    const { data } = await axios.get(`${API}/exchange/pairs`, {
      params: { exchange: 'binance', market: 'futures' },
    })
    pairOptions.value = data || []
  } catch (e) {
    console.error('load pairs failed', e)
    ElMessage.error('加载交易对失败')
  } finally {
    pairLoading.value = false
  }
}

/* ══════════════════════════════════════════════════════════════════
 * 13. K 线周期切换
 * ══════════════════════════════════════════════════════════════════ */
const onTimeframeChange = async (newTf) => {
  const oldTf = currentStrategy.value?.timeframe
  if (!newTf || oldTf === newTf) return

  try {
    await ElMessageBox.confirm(
      `K 线周期将从 ${oldTf} 切换到 ${newTf}。\n\n` +
        `主周期变化后必须重新下载 ${newTf} 数据，回测才能正常运行。\n\n` +
        `是否确认切换？`,
      '请重新下载数据',
      {
        type: 'warning',
        confirmButtonText: '确认切换',
        cancelButtonText: '取消',
      }
    )
  } catch {
    return
  }

  currentStrategy.value.timeframe = newTf

  ElMessage.warning({
    message: `请点击「下载数据」按钮下载 ${newTf} 数据后再回测`,
    duration: 5000,
    showClose: true,
  })
}

/* ══════════════════════════════════════════════════════════════════
 * 14. 参数实时同步
 * ══════════════════════════════════════════════════════════════════ */
const syncing = ref(false)
const configDirtyDuringBacktest = ref(false)

const syncConfig = async () => {
  if (!botId.value) return
  if (!loaded.value) return   // ★ 新增：没加载完不准同步

  // ★ 新增：如果是网格，确保 core 参数有效再提交
  if (strategyType.value === 'grid') {
    const grid = strategyConfig.grid || {}
    if (!grid.lower_price || !grid.upper_price || !grid.grid_count) {
      return // 数据还没填全，不触发自动同步
    }
  }

  try {
    syncing.value = true
    const payload = buildPayload()

    // 如果 stakeAmount 是非法的（比如 NaN/0），也不发
    if (payload.base.stakeAmount <= 0) {
      return
    }

    await axios.put(`${API}/bots/${botId.value}`, payload)
  } catch (e) {
    console.error('[syncConfig] failed', e)
  } finally {
    syncing.value = false
  }
}

const syncConfigDebounced = debounce(syncConfig, 600)

watch(
  () => [botBaseInfo.value, botRisk.value, strategyConfig],
  () => {
    if (!loaded.value) return

    if (backtesting.value) {
      configDirtyDuringBacktest.value = true
      console.log('[backtest] 回测中，配置改动已记录待同步')
      return
    }

    syncConfigDebounced()
  },
  { deep: true }
)

watch(
  () => strategyConfig.entry?.rsi?.value,
  (val) => {
    if (strategyType.value !== 'dca') return   // ★ 新增
    if (!loaded.value) return
    if (val == null) return
    const dir = botBaseInfo.value.direction
    if (sideFields[dir].entryRsiValue === val) return
    sideFields[dir].entryRsiValue = val
  }
)

watch(
  () => (strategyConfig.dca?.levels || []).map((lv) => ({
    rsi_limit: lv.rsi_limit,
    j_limit: lv.j_limit,
  })),
  (newArr) => {
    if (strategyType.value !== 'dca') return   // ★ 新增
    if (!loaded.value) return
    if (!newArr) return
    const dir = botBaseInfo.value.direction

    if (sideFields[dir].dcaLevels.length !== newArr.length) {
      sideFields[dir].dcaLevels = newArr.map((x) => ({ ...x }))
      return
    }
    const same = newArr.every((x, i) => {
      const y = sideFields[dir].dcaLevels[i]
      return y && y.rsi_limit === x.rsi_limit && y.j_limit === x.j_limit
    })
    if (same) return
    sideFields[dir].dcaLevels = newArr.map((x) => ({ ...x }))
  },
  { deep: true }
)

watch(
  () => botBaseInfo.value.tradingMode,
  (mode) => {
    if (mode === 'spot') {
      if (botBaseInfo.value.direction === 'short') {
        botBaseInfo.value.direction = 'long'
        ElMessage.info('现货模式不支持做空，已切换为做多')
      }
      botBaseInfo.value.leverage = 1
      botBaseInfo.value.marginMode = 'cross'
    } else {
      if (!botBaseInfo.value.leverage || botBaseInfo.value.leverage < 2) {
        botBaseInfo.value.leverage = 5
      }
    }
  }
)

watch(
  () => botBaseInfo.value.direction,
  (dir, oldDir) => {
    if (strategyType.value !== 'dca') return   // ★ 新增
    if (!loaded.value) return
    if (dir === oldDir) return

    const newFields = sideFields[dir]

    if (strategyConfig.entry?.rsi) {           // ★ localConfig → strategyConfig
      strategyConfig.entry.rsi.value = newFields.entryRsiValue
    }

    const curLevels = strategyConfig.dca?.levels || []   // ★ localConfig → strategyConfig
    if (curLevels.length > 0) {
      if (newFields.dcaLevels.length !== curLevels.length) {
        newFields.dcaLevels = curLevels.map(() => ({
          rsi_limit: defaultRsiLimit(dir),
          j_limit: defaultJLimit(dir),
        }))
      }
      curLevels.forEach((lv, i) => {
        const src = newFields.dcaLevels[i] || {}
        lv.rsi_limit = src.rsi_limit ?? defaultRsiLimit(dir)
        lv.j_limit = src.j_limit ?? defaultJLimit(dir)
      })
    }

    strategyConfig.side = dir                  // ★ localConfig → strategyConfig
    console.log(`[direction] 切换到 ${dir}，已换入方向相关字段`)
  }
)

/* ══════════════════════════════════════════════════════════════════
 * 15. 回测
 * ══════════════════════════════════════════════════════════════════ */
const backtesting = ref(false)
const backtestResult = ref(null)
const backtestJobId = ref(null)
const backtestStage = ref('')
const backtestPercent = ref(0)
const backtestElapsed = ref(0)
let pollTimer = null
let elapsedTimer = null

const clearBacktestTimers = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  if (elapsedTimer) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
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
  const xs = pts.map((p) => p.x)
  const ys = pts.map((p) => p.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const padX = 10
  const padY = 10
  return pts
    .map((p) => {
      const x = padX + ((p.x - minX) / (maxX - minX || 1)) * (chartWidth - padX * 2)
      const y = chartHeight - padY - ((p.y - minY) / (maxY - minY || 1)) * (chartHeight - padY * 2)
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})

const startPolling = (id, jobId) => {
  clearBacktestTimers()

  elapsedTimer = setInterval(() => {
    backtestElapsed.value += 0.8
  }, 800)

  pollTimer = setInterval(async () => {
    try {
      const res = await getBacktestProgress(id, jobId)
      const data = res?.data || res

      backtestStage.value = data.stage || ''
      backtestPercent.value = data.percent || 0
      if (typeof data.elapsed === 'number') {
        backtestElapsed.value = data.elapsed
      }

      if (['success', 'failed', 'cancelled'].includes(data.status)) {
        clearBacktestTimers()
        backtesting.value = false

        if (configDirtyDuringBacktest.value) {
          configDirtyDuringBacktest.value = false
          try {
            await syncConfig()
            console.log('[backtest] 回测结束，已补同步 config')
          } catch (e) {
            console.warn('[backtest] 回测结束补同步失败', e)
          }
        }

        if (data.status === 'success') {
          backtestResult.value = data.result
          ElMessage.success(`回测完成，耗时 ${formatElapsed(data.elapsed)}`)
        } else if (data.status === 'cancelled') {
          ElMessage.info('回测已取消')
        } else {
          const err = data.error || '回测失败'
          if (
            err.includes('No data') ||
            err.includes('no data') ||
            err.includes('missing') ||
            err.includes('not found')
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

  try {
    await syncConfig()
  } catch (e) {
    console.error(e)
  }

  saveRange(botId.value, backtestRange.value)

  backtesting.value = true
  backtestResult.value = null
  backtestStage.value = '提交任务'
  backtestPercent.value = 0
  backtestElapsed.value = 0

  try {
    const res = await startBacktest(botId.value, {
      side: botBaseInfo.value.direction,
      timeframe: currentStrategy.value.timeframe || '30m',
      timerange,
      auto_download: false,
    })
    const data = res?.data || res
    backtestJobId.value = data.job_id
    startPolling(botId.value, data.job_id)
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

/* ══════════════════════════════════════════════════════════════════
 * 16. 下载数据 / 保存策略 / 保存并启动 / 返回
 * ══════════════════════════════════════════════════════════════════ */
const handleDownloadData = async () => {
  if (downloading.value) return

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
  if (!botId.value) {
    ElMessage.warning('请先保存机器人')
    return
  }

  const [startStr, endStr] = backtestRange.value
  const timerange = `${startStr}-${endStr}`

  try {
    await syncConfig()
  } catch (e) {
    console.error(e)
  }

  saveRange(botId.value, backtestRange.value)

  downloading.value = true
  downloadPercent.value = 0
  downloadElapsed.value = 0
  downloadStage.value = '提交任务'

  try {
    const res = await startDownload(botId.value, {
      side: botBaseInfo.value.direction,
      timeframe: currentStrategy.value.timeframe || '30m',
      timerange,
    })
    const data = res?.data || res

    if (data.skipped) {
      downloading.value = false
      downloadPercent.value = 100
      ElMessage.success('数据已下载')
      return
    }

    downloadJobId.value = data.job_id
    startDownloadPolling(botId.value, data.job_id)
  } catch (e) {
    downloading.value = false
    clearDownloadTimers()
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || '下载启动失败')
  }
}

const handleCancelDownload = async () => {
  if (!downloadJobId.value || !botId.value) return
  try {
    await cancelDownload(botId.value, downloadJobId.value)
    ElMessage.info('已请求取消下载')
  } catch (e) {
    console.error(e)
  }
}

const handleSaveStrategy = () => {
  ElMessage.success('策略已更新')
}

const handleSaveAndStart = async () => {
  if (!validate()) return

  if (isCopy.value) {
    saving.value = true
    try {
      const payload = buildPayload()
      await updateBot(botId.value, payload)
      isDraft.value = false
      axios.post(`${API}/bots/${botId.value}/start`).catch((e) => {
        console.warn('[copy] start 失败', e)
      })
      ElMessage.success('复制成功')
      router.push({ name: 'BotList' })
    } catch (e) {
      console.error(e)
      ElMessage.error(e?.response?.data?.detail || e?.message || '复制失败')
    } finally {
      saving.value = false
    }
    return
  }

  if (!hasChanges()) {
    ElMessage.info({
      message: '配置无变更，无需重启',
      duration: 3000,
      showClose: true,
    })
    return
  }

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

  const success = await saveAndRestart()
  if (!success) return

  ElMessage.success(isEdit.value ? '已保存并重启' : '已保存并启动')
  router.push({ name: 'BotList' })
}

const discardDraftIfNeeded = async () => {
  if (!isDraft.value) return
  if (!botId.value) return
  try {
    await axios.delete(`${API}/bots/${botId.value}/draft`)
    console.log('[leave] 已清理草稿', botId.value)
  } catch (e) {
    console.warn('[leave] 清理草稿失败', e)
  }
}

const goBack = () => {
  router.push({ name: 'BotList' })
}

/* ══════════════════════════════════════════════════════════════════
 * 17. 路由离开守卫
 * ══════════════════════════════════════════════════════════════════ */
onBeforeRouteLeave(async (to, from) => {
  if (downloading.value) {
    try {
      await ElMessageBox.confirm(
        '数据下载正在进行中，离开会丢失进度。确定离开吗？',
        '提示',
        { type: 'warning' }
      )
    } catch {
      return false
    }

    if (downloadJobId.value && botId.value) {
      try { await cancelDownload(botId.value, downloadJobId.value) } catch {}
    }
    clearDownloadTimers()
    downloading.value = false
  }

  if (backtesting.value) {
    try {
      await ElMessageBox.confirm(
        '回测正在进行中，离开会丢失进度。确定离开吗？',
        '提示',
        { type: 'warning' }
      )
    } catch {
      return false
    }

    if (configDirtyDuringBacktest.value) {
      configDirtyDuringBacktest.value = false
      try { await syncConfig() } catch {}
    }
    if (backtestJobId.value && botId.value) {
      try { await cancelBacktest(botId.value, backtestJobId.value) } catch {}
    }
    clearBacktestTimers()
    backtesting.value = false
  }

  if (!isEdit.value) {
    await discardDraftIfNeeded()
    return true
  }
  if (!hasChanges()) {
    await discardDraftIfNeeded()
    return true
  }

  let action = 'confirm'
  try {
    await ElMessageBox.confirm(
      '当前配置有未保存的修改，直接离开将不会生效。\n\n是否保存配置并重启机器人？',
      '有未保存的修改',
      {
        type: 'warning',
        confirmButtonText: '保存并退出',
        cancelButtonText: '直接退出',
        distinguishCancelAndClose: true,
        closeOnClickModal: false,
        closeOnPressEscape: true,
        showClose: true,
      }
    )
  } catch (e) {
    action = typeof e === 'string' ? e : 'close'
  }

  if (action === 'cancel') {
    try { await revertToSnapshot() } catch (e) {
      console.warn('[leave] revert failed', e)
    }
    await discardDraftIfNeeded()
    return true
  }

  if (action === 'close') {
    return false
  }

  const success = await saveAndRestart()
  if (!success) return false

  await discardDraftIfNeeded()
  return true
})

/* ══════════════════════════════════════════════════════════════════
 * 18. 生命周期
 * ══════════════════════════════════════════════════════════════════ */
onMounted(async () => {
  await loadPairs()
  await loadBotDetail()
  loaded.value = true
  inferPresetFromRange()
})

onUnmounted(() => {
  clearBacktestTimers()
  clearDownloadTimers()
})
</script>

<style scoped>
/* ══════════════════════════════════════════════════════════════════
 * 页面骨架
 * ══════════════════════════════════════════════════════════════════ */
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
  font-size: 22px;
  font-weight: 600;
  color: var(--text-main);
  flex: 1;
}

.config-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
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

/* ══════════════════════════════════════════════════════════════════
 * 卡片通用
 * ══════════════════════════════════════════════════════════════════ */
.unified-card,
.strategy-card,
.backtest-card {
  border-radius: 12px;
}

.unified-card :deep(.el-card__header),
.strategy-card :deep(.el-card__header),
.backtest-card :deep(.el-card__header) {
  padding: 10px 16px 12px;
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
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.base-single {
  display: block;
}

.config-section {
  padding: 14px 20px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.config-section:last-child {
  border-bottom: none;
}

.section-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin-bottom: 10px;
  padding-left: 8px;
  border-left: 3px solid var(--el-color-primary);
  display: inline-flex;
  align-items: center;
}

/* 提示图标：金额模式 / 机器人风控 复用 */
.section-label__info {
  margin-left: 4px;
  color: var(--el-color-info);
  cursor: help;
  font-size: 13px;
  vertical-align: middle;
  transition: color 0.2s;
}

.section-label__info:hover {
  color: var(--el-color-primary);
}

/* ══════════════════════════════════════════════════════════════════
 * 字段列表
 * ══════════════════════════════════════════════════════════════════ */
.field-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--el-border-color-lighter);
  min-height: 38px;
}
.field-row:last-child {
  border-bottom: none;
}

.field-row--switch {
  align-items: center;
  padding: 10px 0;
}

.field-row--sub {
  background: var(--el-fill-color-extra-light);
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 6px;
}

.field-label {
  flex: 0 0 120px;
  font-size: 14px;
  color: var(--el-text-color-regular);
  line-height: 1.4;
}

.field-label > span {
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 14px;
  display: inline-flex;
  align-items: center;
}

.field-hint {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  font-weight: normal;
  line-height: 1.4;
}

.field-value {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.field-value--right {
  flex-direction: row;
  justify-content: flex-end;
  align-items: center;
}

/* ══════════════════════════════════════════════════════════════════
 * 内联分组
 * ══════════════════════════════════════════════════════════════════ */
.inline-group {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.inline-group--inputs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
  align-items: start;
}

.inline-group--triple {
  display: flex;
  align-items: flex-start;
  gap: 24px;
  flex-wrap: wrap;
  width: 100%;
}

.inline-group--risk {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  width: 100%;
}

.inline-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.inline-field--compact {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.inline-field__label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.inline-field__hint {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  line-height: 1.3;
  margin-top: 2px;
  display: block;
}

.inline-check {
  margin-left: 4px;
}

.form-item-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
  margin-top: 4px;
}

/* ══════════════════════════════════════════════════════════════════
 * 基础配置卡片：Element Plus 组件字号放大
 * ══════════════════════════════════════════════════════════════════ */
.unified-card :deep(.el-input__inner),
.unified-card :deep(.el-select__placeholder),
.unified-card :deep(.el-radio-button__inner),
.unified-card :deep(.el-input-number__decrease),
.unified-card :deep(.el-input-number__increase),
.unified-card :deep(.el-text) {
  font-size: 14px;
}

.unified-card :deep(.el-radio-button__inner) {
  font-size: 14px !important;
}

.unified-card :deep(.el-input-number .el-input__inner) {
  font-size: 14px;
}

.unified-card :deep(.el-input__wrapper),
.unified-card :deep(.el-select__wrapper),
.unified-card :deep(.el-input-number .el-input__wrapper) {
  min-height: 34px;
}

.unified-card :deep(.el-input-number .el-input__inner) {
  height: 34px;
  line-height: 34px;
}

/* ══════════════════════════════════════════════════════════════════
 * 策略配置卡片
 * ══════════════════════════════════════════════════════════════════ */
.strategy-card .card-head__title {
  font-size: 16px;
}

.strategy-card :deep(.compact-form .el-form-item__label) {
  font-size: 14px;
  line-height: 32px;
}

.strategy-card :deep(.compact-form .el-input__inner),
.strategy-card :deep(.compact-form .el-select__placeholder) {
  font-size: 14px;
}

/* ══════════════════════════════════════════════════════════════════
 * 回测卡片
 * ══════════════════════════════════════════════════════════════════ */
.backtest-card .bt-header__title {
  font-size: 16px;
}

.backtest-card :deep(.el-radio-button__inner) {
  font-size: 14px !important;
  padding: 6px 12px;
}

.backtest-card :deep(.bt-date-single .el-input__inner) {
  font-size: 13px;
}
.backtest-card .bt-range-sep {
  font-size: 13px;
}
.backtest-card .bt-range-display,
.backtest-card .bt-range-display__label,
.backtest-card .bt-range-display__value {
  font-size: 13px;
}

.backtest-card .bt-metric__label {
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.backtest-card .bt-metric__value {
  font-size: 18px;
}

.bt-metric__info {
  color: var(--el-text-color-placeholder);
  cursor: help;
  font-size: 13px;
}

.backtest-card .bt-section__title {
  font-size: 14px;
}

.backtest-card :deep(.el-table) {
  font-size: 13px;
}
.backtest-card :deep(.el-table th.el-table__cell) {
  font-size: 13px;
}

.backtest-card .bt-progress__pct,
.backtest-card .bt-progress__row,
.backtest-card .bt-progress__tip,
.backtest-card .bt-progress__stage,
.backtest-card .bt-progress__elapsed {
  font-size: 14px;
}

.backtest-card :deep(.el-empty__description p) {
  font-size: 14px;
}

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
  align-items: stretch;
  gap: 4px;
  width: 100%;
  padding: 0;
}

.bt-header__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
  align-self: flex-start;
  line-height: 1.2;
  margin: 0;
}

.bt-date-picker {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 100%;
}

.bt-date-picker :deep(.el-radio-group) {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 4px;
}

.bt-date-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
}

.bt-date-single {
  width: 152px;
  flex: none;
}

.bt-date-single :deep(.el-input__wrapper) {
  padding: 0 8px;
  height: 30px;
}

.bt-date-single :deep(.el-input__inner) {
  font-size: 13px;
  color: var(--el-text-color-primary);
}

.bt-range-sep {
  flex: none;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.bt-range-display {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  font-variant-numeric: tabular-nums;
  display: flex;
  gap: 4px;
  align-items: center;
}

.bt-range-display__label {
  color: var(--el-text-color-placeholder);
}

.bt-range-display__value {
  color: var(--el-text-color-primary);
  font-weight: 500;
}

/* ══════════════════════════════════════════════════════════════════
 * 回测进度视图
 * ══════════════════════════════════════════════════════════════════ */
.bt-progress {
  width: 100%;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.bt-progress__pct {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.bt-progress__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
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
  font-size: 14px;
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

/* ══════════════════════════════════════════════════════════════════
 * 回测结果
 * ══════════════════════════════════════════════════════════════════ */
.backtest-result {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px;
}

/* 加在 .backtest-result 下面 */
.bt-range-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 4px;
}

/* 原先的网格是 3 列，现在增加了两个指标（11个），改为 4 列更紧凑好看 */
.bt-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

/* 针对小屏幕响应式调整为 3 列或 2 列 */
@media (max-width: 1400px) {
  .bt-summary {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 992px) {
  .bt-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
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
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}
.bt-metric__value {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.bt-metric__value.is-profit {
  color: var(--el-color-success);
}
.bt-metric__value.is-loss {
  color: var(--el-color-danger);
}
.bt-metric__value--neutral {
  color: var(--el-color-warning);
}

.bt-chart {
  background: var(--el-fill-color-extra-light);
  border-radius: 8px;
  padding: 12px;
}
.bt-chart__title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}
.bt-chart__svg {
  width: 100%;
  height: 160px;
}

.bt-table {
  width: 100%;
}
.bt-table .is-profit {
  color: var(--el-color-success);
}
.bt-table .is-loss {
  color: var(--el-color-danger);
}

.bt-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.bt-section__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

/* ══════════════════════════════════════════════════════════════════
 * 底部保存栏
 * ══════════════════════════════════════════════════════════════════ */
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

/* ══════════════════════════════════════════════════════════════════
 * 响应式
 * ══════════════════════════════════════════════════════════════════ */
@media (max-width: 1200px) {
  .config-layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .config-right {
    position: static;
  }
  .backtest-card {
    min-height: 400px;
  }
  .inline-group--triple {
    gap: 16px;
  }
}

.text-warning {
  color: var(--el-color-warning);
  font-weight: 500;
}
</style>