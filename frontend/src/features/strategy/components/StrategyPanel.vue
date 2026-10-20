<template>
  <div v-if="config?.entry" class="strategy-panel">
    <!-- 指标配置 -->
    <ToggleSection
      v-model="panelOpen.indicator"
      mode="arrow"
      title="指标配置"
      desc="MACD / KDJ / EMA / RSI / BB"
    >
      <template #extra>
        <el-tooltip placement="top" effect="dark">
          <template #content>
            HTF 趋势过滤复用此处 EMA 的快 / 中 / 慢参数
          </template>
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
        </el-tooltip>
      </template>

      <!-- K 线周期 -->
      <el-form class="compact-form" label-width="100px" size="small">
        <el-form-item label="K 线周期">
          <el-select
            :model-value="config.timeframe"
            @update:model-value="onTimeframeChange"
            style="width: 220px"
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
          <span class="field-hint-inline">
            策略信号计算所用周期；变更后需重新下载数据
          </span>
        </el-form-item>
      </el-form>

      <el-divider content-position="left">MACD</el-divider>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="Fast">
            <el-input-number v-model="config.indicator.macd.fast" class="field-input"
              controls-position="right" :min="2" :max="200" :step="1" :precision="0" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="Slow">
            <el-input-number v-model="config.indicator.macd.slow" class="field-input"
              controls-position="right" :min="2" :max="200" :step="1" :precision="0" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="Signal">
            <el-input-number v-model="config.indicator.macd.signal" class="field-input"
              controls-position="right" :min="2" :max="200" :step="1" :precision="0" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">KDJ</el-divider>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="FastK">
            <el-input-number v-model="config.indicator.kdj.fastk" class="field-input"
              controls-position="right" :min="2" :max="200" :step="1" :precision="0" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="SlowK">
            <el-input-number v-model="config.indicator.kdj.slowk" class="field-input"
              controls-position="right" :min="2" :max="200" :step="1" :precision="0" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="SlowD">
            <el-input-number v-model="config.indicator.kdj.slowd" class="field-input"
              controls-position="right" :min="2" :max="200" :step="1" :precision="0" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">EMA</el-divider>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="快">
            <el-input-number v-model="config.indicator.ema.fast" class="field-input"
              controls-position="right" :min="2" :max="200" :step="1" :precision="0" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="中">
            <el-input-number v-model="config.indicator.ema.mid" class="field-input"
              controls-position="right" :min="2" :max="200" :step="1" :precision="0" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="慢">
            <el-input-number v-model="config.indicator.ema.slow" class="field-input"
              controls-position="right" :min="2" :max="200" :step="1" :precision="0" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">RSI / Bollinger</el-divider>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="RSI周期">
            <el-input-number v-model="config.indicator.rsi.period" class="field-input"
              controls-position="right" :min="2" :max="200" :step="1" :precision="0" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="BB周期">
            <el-input-number v-model="config.indicator.bb.period" class="field-input"
              controls-position="right" :min="2" :max="200" :step="1" :precision="0" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="BB STD">
            <el-input-number v-model="config.indicator.bb.std" class="field-input"
              controls-position="right" :min="0.5" :max="5" :step="0.1" :precision="2" />
          </el-form-item>
        </el-col>
      </el-row>
    </ToggleSection>

    <!-- ROI 止盈 -->
    <ToggleSection
      v-model="panelOpen.roi"
      mode="arrow"
      title="ROI 止盈规则"
      desc="按持仓时长匹配最近一档收益率目标"
    >
      <template #extra>
        <el-tooltip placement="top" effect="dark">
          <template #content>
            持仓达到指定时长后，收益率达到目标值触发 TP；<br />
            取「已满足时长」中 minutes 最大的一条作为当前目标
          </template>
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
        </el-tooltip>
      </template>

      <div class="roi-panel">
        <!-- 表头 -->
        <div class="roi-header">
          <span class="roi-col-idx">#</span>
          <span class="roi-col-time">持仓时长</span>
          <span class="roi-col-profit">目标收益率</span>
          <span class="roi-col-action"></span>
        </div>

        <!-- 列表 -->
        <div class="roi-list">
          <div v-for="(roi, index) in config.tp.roi_levels || []" :key="index" class="roi-row">
            <span class="roi-index">{{ index + 1 }}</span>

            <div class="roi-cell">
              <el-input-number
                v-model="roi.minutes"
                class="roi-input"
                controls-position="right"
                :min="0" :max="10080" :step="1" :precision="0"
                size="small"
              />
              <span class="roi-suffix">分钟</span>
            </div>

            <div class="roi-cell">
              <el-input-number
                v-model="roi.roi"
                class="roi-input"
                controls-position="right"
                :min="-100" :max="1000" :step="0.1" :precision="2"
                size="small"
              />
              <span class="roi-suffix">%</span>
            </div>

            <el-button
              class="roi-delete"
              type="danger"
              link
              size="small"
              :disabled="(config.tp.roi_levels || []).length <= 1"
              @click="removeRoi(index)"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>

        <!-- 底部操作区：改为靠右并统一按钮样式 -->
        <div class="roi-footer">
          <el-button
            class="add-btn"
            type="success"
            plain
            size="small"
            @click="addRoi"
          >
            + 新增一层
          </el-button>
        </div>
      </div>
    </ToggleSection>

    <!-- 开仓信号 -->
    <ToggleSection
      v-model="panelOpen.entry"
      mode="arrow"
      title="开仓信号"
      desc="RSI / MACD / Bollinger / Pump 保护"
    >
      <template #extra>
        <el-tooltip placement="top" effect="dark">
          <template #content>
            条件模式仅作用于 RSI / MACD / Bollinger；<br />
            Pump 保护为独立拦截，不受条件模式影响
          </template>
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
        </el-tooltip>
      </template>

      <el-form class="compact-form" label-width="100px" size="small">
        <el-form-item label="条件模式">
          <el-select v-model="config.entry.condition" class="field-input">
            <el-option label="全部满足 AND" value="and" />
            <el-option label="任意满足 OR"  value="or" />
          </el-select>
          <span class="field-hint-inline">仅作用于 RSI / MACD / Bollinger</span>
        </el-form-item>
      </el-form>

      <div class="entry-grid">
        <section class="signal-card">
          <div class="signal-head">
            <div>
              <div class="signal-name">RSI</div>
              <div class="signal-subtitle">
                {{ config.side === 'short' ? 'RSI 高于阈值允许入场' : 'RSI 低于阈值允许入场' }}
              </div>
            </div>
            <el-switch :model-value="config.entry.rsi.enable"
              @change="val => changeEntrySignal('rsi', val)" />
          </div>
          <el-form class="compact-form" label-width="54px" size="small">
            <el-input-number v-model="config.entry.rsi.value" class="field-input"
              controls-position="right" :disabled="!config.entry.rsi.enable"
              :min="1" :max="100" :step="1" :precision="0" />
          </el-form>
        </section>

        <section class="signal-card">
          <div class="signal-head">
            <div>
              <div class="signal-name">MACD</div>
              <div class="signal-subtitle">
                {{ config.side === 'short' ? 'MACD 死叉（快 < 慢）' : 'MACD 金叉（快 > 慢）' }}
              </div>
            </div>
            <el-switch :model-value="config.entry.macd.enable"
              @change="val => changeEntrySignal('macd', val)" />
          </div>
        </section>

        <section class="signal-card">
          <div class="signal-head">
            <div>
              <div class="signal-name">Bollinger</div>
              <div class="signal-subtitle">
                {{ config.side === 'short' ? '价格突破上轨' : '价格跌破下轨' }}
              </div>
            </div>
            <el-switch :model-value="config.entry.bb.enable"
              @change="val => changeEntrySignal('bb', val)" />
          </div>
        </section>
      </div>

      <section class="signal-card signal-card--standalone">
        <div class="signal-head">
          <div>
            <div class="signal-name">Pump 保护</div>
            <div class="signal-subtitle">
              {{ config.side === 'short'
                ? '3 根累计跌幅 ≥10% 且量比 ≥3 且 RSI ≤25 时，暂停开仓（防暴跌追空）'
                : '3 根累计涨幅 ≥10% 且量比 ≥3 且 RSI ≥75 时，暂停开仓（防暴涨追多）' }}
              （独立开关，不参与上方 AND/OR）
            </div>
          </div>
          <el-switch :model-value="config.entry.pump_protect.enable"
            @change="val => changeEntrySignal('pump_protect', val)" />
        </div>
      </section>
    </ToggleSection>

    <!-- TP 止盈 -->
    <ToggleSection
      v-model="panelOpen.tpReduce"
      mode="arrow"
      title="TP 止盈"
      :desc="config.tp.rebuy_enable
        ? '减仓后自动补回目标仓位'
        : '达到 ROI 后直接全平'"
    >
      <template #extra>
        <el-tooltip placement="top" effect="dark">
          <template #content>
            <template v-if="config.tp.rebuy_enable">
              达到 ROI 后按比例减仓，随后自动补回至「目标仓位」
            </template>
            <template v-else>
              达到 ROI 后直接全平（不保留仓位）
            </template>
          </template>
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
        </el-tooltip>
      </template>

      <el-form class="compact-form" label-width="140px" size="small">

        <!-- ★ 1. 自动补仓开关 -->
        <el-form-item :label="config.tp.rebuy_enable ? '自动补仓' : '全部平仓'">
          <el-switch v-model="config.tp.rebuy_enable" @change="onRebuyChange" />
        </el-form-item>

        <!-- ★ 2. 只有开启「自动补仓」时，才显示减仓参数和目标仓位 -->
        <template v-if="config.tp.rebuy_enable">

          <el-form-item :label="config.amount_mode === 'amount' ? '减仓金额(USDT)' : '减仓比例%'">
            <el-input-number v-if="config.amount_mode === 'amount'"
              v-model="config.tp.reduce_amount" class="field-input"
              controls-position="right" :min="1" :max="100000" :step="10" :precision="2" />
            <el-input-number v-else
              v-model="config.tp.reduce_percent" class="field-input"
              controls-position="right" :min="0" :max="100" :step="1" :precision="0" />
          </el-form-item>

          <el-form-item :label="config.amount_mode === 'amount' ? '调整仓位至(USDT)' : '调整仓位至总资金%'">
            <el-input-number v-if="config.amount_mode === 'amount'"
              v-model="config.tp.target_wallet_amount" class="field-input"
              controls-position="right" :min="1" :max="100000" :step="10" :precision="2" />
            <el-input-number v-else
              v-model="config.tp.target_wallet_percent" class="field-input"
              controls-position="right" :min="0" :max="100" :step="0.1" :precision="2" />
          </el-form-item>

        </template>
      </el-form>
    </ToggleSection>

    <!-- DCA -->
    <ToggleSection
      v-model="config.dca.enable"
      title="DCA 加仓"
      desc="回撤时分批补仓"
    >
      <template #extra>
        <el-tooltip placement="top" effect="dark">
          <template #content>
            触发价 = 持仓均价 × (1 ± 价格偏差 × 乘数^已加仓次数)；<br />
            首次加仓时「已加仓次数 = 0」，即倍率为 1（不放大）；<br />
            实际加仓需同时满足「价格触发」与「RSI / J 条件」
          </template>
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
        </el-tooltip>
      </template>

      <el-form class="compact-form" label-width="100px" size="small">
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="金额模式">
              <el-select v-model="config.dca.amount_mode" class="field-input">
                <el-option label="自动倍率" value="auto" />
                <el-option label="手动分层" value="manual" />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="8">
            <el-form-item label="条件模式">
              <el-select v-model="config.dca.condition" class="field-input">
                <el-option label="仅 RSI"   value="rsi" />
                <el-option label="仅 J"     value="j" />
                <el-option label="RSI 或 J" value="or" />
                <el-option label="RSI 且 J" value="and" />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="8">
            <el-form-item label="最大加仓次数">
              <el-input-number v-model="config.dca.max_count" class="field-input"
                controls-position="right" :min="1" :max="20" :step="1" :precision="0" />
            </el-form-item>
          </el-col>

          <el-col :span="8">
            <el-form-item label="冷却时间(分钟)">
              <el-input-number v-model="config.dca.cooldown_minutes" class="field-input"
                controls-position="right" :min="0" :max="1440" :step="5" :precision="0" />
            </el-form-item>
          </el-col>

          <el-col :span="8">
            <el-form-item label="价格偏差%">
              <el-input-number v-model="config.dca.price_offset" class="field-input"
                controls-position="right" :min="0.1" :max="20" :step="0.1" :precision="2" />
            </el-form-item>
          </el-col>

          <el-col :span="8">
            <el-form-item label="价格偏差乘数">
              <el-input-number v-model="config.dca.price_multiplier" class="field-input"
                controls-position="right" :min="0.1" :max="10" :step="0.1" :precision="2" />
            </el-form-item>
          </el-col>

          <template v-if="config.dca.amount_mode === 'auto'">
            <el-col :span="8">
              <el-form-item :label="config.amount_mode === 'amount'
                ? '加仓金额(USDT)' : '加仓比例%'">
                <el-input-number v-if="config.amount_mode === 'amount'"
                  v-model="config.dca.base_amount" class="field-input"
                  controls-position="right" :min="1" :max="100000" :step="10" :precision="2" />
                <el-input-number v-else
                  v-model="config.dca.base_percent" class="field-input"
                  controls-position="right" :min="0.1" :max="100" :step="0.1" :precision="2" />
              </el-form-item>
            </el-col>

            <el-col :span="8">
              <el-form-item label="订单规模乘数">
                <el-input-number v-model="config.dca.amount_multiplier" class="field-input"
                  controls-position="right" :min="0.1" :max="10" :step="0.1" :precision="2" />
              </el-form-item>
            </el-col>
          </template>
        </el-row>
      </el-form>

      <!-- manual levels -->
      <div class="dca-levels">
        <div v-for="(level, index) in config.dca.levels"
             :key="index" class="dca-level-row">
          <div class="dca-level-index">{{ index + 1 }}</div>
          <el-form class="dca-level-form" label-width="120px" size="small">
            <el-form-item v-if="config.dca.amount_mode === 'manual'"
              :label="config.amount_mode === 'amount'
                ? '加仓金额(USDT)' : '加仓比例%'">
              <el-input-number v-if="config.amount_mode === 'amount'"
                v-model="level.amount" class="field-input"
                controls-position="right" :min="1" :max="10000" :step="10" :precision="2" />
              <el-input-number v-else
                v-model="level.percent" class="field-input"
                controls-position="right" :min="0.1" :max="100" :step="0.1" :precision="2" />
            </el-form-item>
            <el-form-item :label="config.side === 'long' ? 'RSI <' : 'RSI >'">
              <el-input-number v-model="level.rsi_limit" class="field-input"
                controls-position="right" :min="0" :max="100" :step="1" :precision="0" />
            </el-form-item>
            <el-form-item :label="config.side === 'long' ? 'J <' : 'J >'">
              <el-input-number v-model="level.j_limit" class="field-input"
                controls-position="right" :min="-100" :max="200" :step="1" :precision="0" />
            </el-form-item>
          </el-form>
          <el-button class="dca-level-delete" type="danger" link size="small"
            :disabled="config.dca.levels.length <= 1"
            @click="removeDca(index)">✕</el-button>
        </div>

        <!-- 底部操作区 -->
        <div class="dca-footer">
          <el-button
            class="add-btn"
            type="success"
            plain
            size="small"
            @click="addDca"
          >
            + 新增一层
          </el-button>
        </div>
      </div>
    </ToggleSection>

    <!-- 浮亏止盈 -->
    <ToggleSection
      v-model="config.loss_tp.enable"
      title="浮亏止盈"
      desc="DCA 后达到目标自动减仓"
    >
      <template #extra>
        <el-tooltip placement="top" effect="dark">
          <template #content>
            仅在 DCA 后（dca_count &gt; 0）生效；<br />
            关闭「部分减仓」时直接全平；<br />
            开启「部分减仓」时按下方目标仓位减仓
          </template>
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
        </el-tooltip>
      </template>

      <!-- 浮亏止盈 -->
      <el-form class="compact-form" label-width="140px" size="small">

        <!-- ★ 修改点：将开关放上面，占满整行 -->
        <el-form-item :label="config.loss_tp.is_partial ? '部分减仓' : '全部平仓'">
          <el-switch v-model="config.loss_tp.is_partial" />
        </el-form-item>

        <!-- ★ 修改点：止盈收益率放到下面 -->
        <el-form-item label="止盈收益率%">
          <el-input-number v-model="config.loss_tp.dca_tp_profit" class="field-input"
            controls-position="right" :min="0" :max="100" :step="0.1" :precision="2" />
        </el-form-item>

        <!-- 只有部分减仓时才显示目标仓位输入 -->
        <el-form-item
          v-if="config.loss_tp.is_partial"
          :label="config.amount_mode === 'amount' ? '减仓至(USDT)' : '调整仓位至总资金%'"
        >
          <el-input-number v-if="config.amount_mode === 'amount'"
            v-model="config.loss_tp.target_wallet_amount" class="field-input"
            controls-position="right" :min="1" :max="100000" :step="10" :precision="2" />
          <el-input-number v-else
            v-model="config.loss_tp.target_wallet_percent" class="field-input"
            controls-position="right" :min="0" :max="100" :step="1" :precision="2" />
        </el-form-item>

      </el-form>
    </ToggleSection>

    <!-- 趋势加仓 -->

    <ToggleSection
    v-if="false"
      v-model="config.trend_add.enable"
      title="趋势加仓"
      desc="MACD / KDJ / EMA 趋势加仓"
    >
      <template #extra>
        <el-tooltip placement="top" effect="dark">
          <template #content>
            {{ config.side === 'long' ? '多头' : '空头' }}趋势成立时加仓一次；<br />
            条件模式为 {{ config.trend_add.condition === 'and' ? '全部满足' : '任意满足' }}
          </template>
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
        </el-tooltip>
      </template>

      <el-form class="compact-form" label-width="140px" size="small">
        <el-form-item :label="config.amount_mode === 'amount'
          ? '加仓金额(USDT)' : '加仓比例%'">
          <el-input-number v-if="config.amount_mode === 'amount'"
            v-model="config.trend_add.amount_amount"
            :min="1" :max="100000" :step="10" :precision="2" />
          <el-input-number v-else
            v-model="config.trend_add.amount_percent"
            :min="0" :max="100" :step="0.1" :precision="2" />
        </el-form-item>

        <el-form-item label="条件模式">
          <el-select v-model="config.trend_add.condition" class="field-input">
            <el-option label="全部满足 AND" value="and" />
            <el-option label="任意满足 OR"  value="or" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-divider>趋势指标</el-divider>

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="MACD">
            <el-switch v-model="config.trend_add.macd_enable" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="KDJ">
            <el-switch v-model="config.trend_add.kdj_enable" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="EMA">
            <el-switch v-model="config.trend_add.ema_enable" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">KDJ 减仓</el-divider>

      <el-form label-width="140px" size="small">
        <el-form-item label="启用 KDJ 减仓">
          <el-switch v-model="config.trend_add.kdj_reduce.enable"
            :disabled="!config.trend_add.enable" />
          <span class="field-hint-inline">仅在趋势加仓已触发（level &gt; 0）后生效</span>
        </el-form-item>

        <el-form-item :label="config.amount_mode === 'amount'
          ? '减仓金额(USDT)' : '减仓比例%'">
          <el-input-number v-if="config.amount_mode === 'amount'"
            v-model="config.trend_add.kdj_reduce.reduce_amount"
            :disabled="!config.trend_add.kdj_reduce.enable"
            :min="1" :max="100000" :step="10" :precision="2"
            controls-position="right" />
          <el-input-number v-else
            v-model="config.trend_add.kdj_reduce.reduce_percent"
            :disabled="!config.trend_add.kdj_reduce.enable"
            :min="0" :max="100" :step="1" :precision="0"
            controls-position="right" />
        </el-form-item>
      </el-form>
    </ToggleSection>

    <!-- 网格 -->
    <ToggleSection
      v-if="false"
      v-model="config.grid.enable"
      title="网格"
      desc="以锚点价为中心，上下沿触发加减仓"
    >
      <template #extra>
        <el-tooltip placement="top" effect="dark">
          <template #content>
            <template v-if="config.side === 'long'">
              跌至「锚点 × (1 + 下沿%)」加仓，涨至「锚点 × (1 + 上沿%)」减仓
            </template>
            <template v-else>
              涨至「锚点 × (1 + 上沿%)」加仓，跌至「锚点 × (1 + 下沿%)」减仓
            </template>
            <br />锚点：开仓时为开仓价，之后每次成交重置为成交价
          </template>
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
        </el-tooltip>
      </template>

      <el-form class="compact-form" label-width="140px" size="small">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="最大加仓次数">
              <el-input-number v-model="config.grid.max_count" class="field-input"
                controls-position="right" :min="1" :max="50" :step="1" :precision="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="冷却时间(分钟)">
              <el-input-number v-model="config.grid.cooldown_minutes" class="field-input"
                controls-position="right" :min="0" :max="1440" :step="5" :precision="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="网格下沿%">
              <el-input-number v-model="config.grid.grid_lower" class="field-input"
                controls-position="right" :min="-50" :max="0" :step="0.1" :precision="2" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="网格上沿%">
              <el-input-number v-model="config.grid.grid_upper" class="field-input"
                controls-position="right" :min="0" :max="50" :step="0.1" :precision="2" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="config.amount_mode === 'amount'
              ? '加仓金额(USDT)' : '加仓占比%'">
              <el-input-number v-if="config.amount_mode === 'amount'"
                v-model="config.grid.buy_amount" class="field-input"
                controls-position="right" :min="1" :max="100000" :step="10" :precision="2" />
              <el-input-number v-else
                v-model="config.grid.buy_percent" class="field-input"
                controls-position="right" :min="0" :max="100" :step="0.1" :precision="2" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="config.amount_mode === 'amount'
              ? '减仓金额(USDT)' : '减仓占比%'">
              <el-input-number v-if="config.amount_mode === 'amount'"
                v-model="config.grid.sell_amount" class="field-input"
                controls-position="right" :min="1" :max="100000" :step="10" :precision="2" />
              <el-input-number v-else
                v-model="config.grid.sell_percent" class="field-input"
                controls-position="right" :min="0" :max="100" :step="0.1" :precision="2" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="订单规模倍率">
              <el-input-number v-model="config.grid.order_scale" class="field-input"
                controls-position="right" :min="0.1" :max="10" :step="0.1" :precision="2" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </ToggleSection>

    <!-- 单交易对持仓限制 -->
    <ToggleSection
      v-model="config.pair_max_position.enable"
      title="单交易对持仓限制"
      desc="超限停止 DCA 与网格加仓"
    >
      <template #extra>
        <el-tooltip placement="top" effect="dark">
          <template #content>
            该交易对保证金占用 / 账户总 USDT 余额 ≥ 设定比例后，<br />
            停止 DCA 与网格加仓
          </template>
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
        </el-tooltip>
      </template>

      <el-form class="compact-form" label-width="140px" size="small">
        <el-form-item label="最大持仓占比%">
          <el-input-number v-model="config.pair_max_position.percent" class="field-input"
            controls-position="right" :min="1" :max="100" :step="1" :precision="2" />
        </el-form-item>
      </el-form>
    </ToggleSection>

    <!-- HTF 趋势过滤 -->
    <ToggleSection
      v-model="config.htf_trend_filter.enable"
      title="HTF 趋势过滤"
      desc="大周期趋势不利时暂停买入"
    >
      <template #extra>
        <el-tooltip placement="top" effect="dark">
          <template #content>
            {{ config.side === 'long'
              ? 'HTF 空头排列（快<中<慢）时暂停买入'
              : 'HTF 多头排列（快>中>慢）时暂停买入' }}
            <br />EMA 参数复用「指标配置」中的快/中/慢
            <br />需开启「启用」并至少勾选一项保护范围，HTF 数据才会加载
          </template>
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
        </el-tooltip>
      </template>

      <el-form class="compact-form" label-width="140px" size="small">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="HTF 周期">
              <el-select
                :model-value="config.htf_trend_filter.timeframe"
                @update:model-value="onHtfTimeframeChange"
                class="field-input"
              >
                <el-option label="4h"  value="4h" />
                <el-option label="12h" value="12h" />
                <el-option label="1d"  value="1d" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">保护范围</el-divider>

        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="开仓">
              <el-switch v-model="config.htf_trend_filter.protect_entry" />
              <el-tooltip placement="top" content="拦截 confirm_trade_entry 中的新开仓">
                <el-icon class="field-info"><InfoFilled /></el-icon>
              </el-tooltip>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="DCA 加仓">
              <el-switch v-model="config.htf_trend_filter.protect_dca" />
              <el-tooltip placement="top" content="跳过 adjust_trade_position 中的 dca_add">
                <el-icon class="field-info"><InfoFilled /></el-icon>
              </el-tooltip>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="网格加仓">
              <el-switch v-model="config.htf_trend_filter.protect_grid" />
              <el-tooltip placement="top" content="跳过 grid_single 的加仓分支">
                <el-icon class="field-info"><InfoFilled /></el-icon>
              </el-tooltip>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="浮盈回补">
              <el-switch v-model="config.htf_trend_filter.protect_rebuy" />
              <el-tooltip placement="top" content="跳过 profit_rebuy 浮盈回补">
                <el-icon class="field-info"><InfoFilled /></el-icon>
              </el-tooltip>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="趋势加仓" v-if="false">
              <el-switch v-model="config.htf_trend_filter.protect_trend" />
              <el-tooltip placement="top" content="跳过 trend_add 趋势加仓">
                <el-icon class="field-info"><InfoFilled /></el-icon>
              </el-tooltip>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </ToggleSection>

    <!-- 止损 -->
    <ToggleSection
      v-model="config.sl.enable"
      title="止损"
      desc="固定百分比 / 时间止损"
    >
      <template #extra>
        <el-tooltip placement="top" effect="dark">
          <template #content>
            固定止损：当前收益率 ≤ 设定值时平仓；<br />
            时间止损：距上次成交超过设定时长后累计收益低于阈值时平仓
          </template>
          <el-icon class="section-label__info"><InfoFilled /></el-icon>
        </el-tooltip>
      </template>

      <el-form class="compact-form" label-width="140px" size="small">
        <el-form-item label="止损百分比 (%)">
          <el-input-number v-model="config.sl.stoploss" class="field-input"
            controls-position="right" :min="-999" :max="0" :step="1" :precision="0" />
          <span class="field-hint-inline">例：-50 表示亏损 50% 平仓</span>
        </el-form-item>

        <el-divider content-position="left">时间止损</el-divider>

        <el-form-item label="启用时间止损">
          <el-switch v-model="config.sl.time_stop.enable" />
        </el-form-item>
        <el-form-item label="距上次成交时长(小时)">
          <el-input-number v-model="config.sl.time_stop.hours" class="field-input"
            controls-position="right" :min="0.1" :max="720" :step="0.5" :precision="1"
            :disabled="!config.sl.time_stop.enable" />
          <span class="field-hint-inline">从最近一次成交算起</span>
        </el-form-item>
        <el-form-item label="收益阈值模式">
          <el-select v-model="config.sl.time_stop.mode" class="field-input"
            :disabled="!config.sl.time_stop.enable">
            <el-option label="百分比 %" value="percent" />
            <el-option label="固定金额 USDT" value="amount" />
          </el-select>
        </el-form-item>
        <el-form-item :label="config.sl.time_stop.mode === 'amount'
          ? '收益阈值(USDT)' : '收益阈值(%)'">
          <el-input-number v-model="config.sl.time_stop.profit_threshold"
            class="field-input" controls-position="right"
            :min="-9999" :max="0"
            :step="config.sl.time_stop.mode === 'amount' ? 1 : 0.5"
            :precision="config.sl.time_stop.mode === 'amount' ? 2 : 1"
            :disabled="!config.sl.time_stop.enable" />
        </el-form-item>
      </el-form>
    </ToggleSection>
  </div>
</template>


<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { InfoFilled, Close, Plus } from '@element-plus/icons-vue'
import ToggleSection from './ToggleSection.vue'
import { reactive } from 'vue'

const panelOpen = reactive({
  indicator: false,   // 指标配置：默认收起
  roi: false,         // ROI 止盈：默认收起
  entry: true,        // 开仓信号：默认展开
  tpReduce: false,    // TP 减仓：默认收起
})

const props = defineProps({
    config: Object,
    tradeInfo: Object
})

const emit = defineEmits(['save', 'timeframe-change'])

const onTimeframeChange = (val) => {
  emit('timeframe-change', val)
}

const changeEntrySignal = (type, val) => {
    const entry = props.config.entry

    if (type === "pump_protect") {
        if (!entry.pump_protect) {
            entry.pump_protect = { enable: false }
        }
        entry.pump_protect.enable = val
        return
    }

    if (!val) {
        const remain = ["rsi", "macd", "bb"]
            .filter(key => key !== type)
            .some(key => entry[key]?.enable)

        if (!remain) {
            ElMessage.warning('开仓信号至少需要保留一个')
            return
        }
    }

    entry[type].enable = val
}

const addRoi = () => {
    if (!props.config.tp) return
    if (!props.config.tp.roi_levels) {
        props.config.tp.roi_levels = []
    }
    props.config.tp.roi_levels.push({
        minutes: 0,
        roi: 30
    })
}

const removeRoi = (index) => {
    const roiLevels = props.config.tp.roi_levels

    if (roiLevels.length <= 1) {
        ElMessage.warning({
            message: 'ROI止盈规则至少需要保留一条',
            duration: 2000
        })
        return
    }

    roiLevels.splice(index, 1)
}

const addDca = () => {
    if (props.config.side === 'long') {
        props.config.dca.levels.push({
            drawdown: -5,
            rsi_limit: 20,
            j_limit: 0,
            amount: 10,
            percent: 2.0
        })
    } else {
        props.config.dca.levels.push({
            drawdown: -5,
            rsi_limit: 80,
            j_limit: 100,
            amount: 10,
            percent: 2.0
        })
    }
}

const removeDca = (index) => {
    props.config.dca.levels.splice(index, 1)
}

const addTrendAdd = () => {
    props.config.trend_add.levels.push({
        profit: 2,
        rsi: props.config.side === 'long' ? 60 : 40,
        amount: 0.5
    })
}

const removeTrendAdd = (index) => {
    props.config.trend_add.levels.splice(index, 1)
}

const syncKdjReduce = () => {
    if (!props.config.trend_add.enable) {
        props.config.trend_add.kdj_reduce.enable = false
    }
}

const onRebuyChange = (val) => {
    if (!props.config?.tp) return

    if (val) {
        // 开启自动补仓：初始化合理的减仓参数
        if (props.config.amount_mode === "amount") {
            if (!props.config.tp.reduce_amount || props.config.tp.reduce_amount <= 0) {
                props.config.tp.reduce_amount = 10.0
            }
        } else {
            if (!props.config.tp.reduce_percent || props.config.tp.reduce_percent === 100) {
                props.config.tp.reduce_percent = 30
            }
        }
    } else {
        // 关闭自动补仓：全平模式，强行把减仓比例设为 100%
        props.config.tp.reduce_percent = 100
        // 如果金额模式下，不需要减仓金额，因为直接全平
    }
}

const onHtfTimeframeChange = async (newTf) => {
  if (!props.config?.htf_trend_filter) return

  const oldTf = props.config.htf_trend_filter.timeframe

  if (oldTf === newTf) return

  try {
    await ElMessageBox.confirm(
      `HTF 周期已切换到 ${newTf}。\n\n` +
      `策略只会加载该周期（不再同时计算 4h/12h/1d），因此必须重新下载 ${newTf} 数据后回测才能生效。\n\n` +
      `是否确认切换？`,
      '请重新下载数据',
      {
        type: 'warning',
        confirmButtonText: '确认切换',
        cancelButtonText: '取消',
        dangerouslyUseHTMLString: false,
        customClass: 'htf-switch-confirm'
      }
    )
  } catch {
    return
  }

  props.config.htf_trend_filter.timeframe = newTf

  ElMessage.warning({
    message: `请点击「下载数据」按钮下载 ${newTf} 数据后再回测`,
    duration: 5000,
    showClose: true
  })
}
</script>

<style scoped>
/* ==================== 整体 ==================== */
.strategy-panel {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* ==================== 卡片通用 ==================== */
.section-card {
  border-radius: 8px;
  margin: 0;
  border: 1px solid var(--el-border-color-lighter);
}

.section-card :deep(.el-card__header) {
  padding: 8px 12px;
  background: var(--el-fill-color-light);
}

.section-card :deep(.el-card__body) {
  padding: 12px;
  overflow-x: hidden;
}

.section-card :deep(.el-row) {
  margin-left: 0 !important;
  margin-right: 0 !important;
}

.section-card :deep(.el-col) {
  min-width: 0;
}

/* ==================== 卡片头 ==================== */
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}

.card-head__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.card-head__meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ==================== 表头右侧信息图标 ==================== */
.section-label__info {
  margin-left: 4px;
  color: var(--el-color-info);
  cursor: help;
  font-size: 14px;
  vertical-align: middle;
  transition: color 0.2s;
}

.section-label__info:hover {
  color: var(--el-color-primary);
}

/* ==================== 表单紧凑 ==================== */
.compact-form :deep(.el-form-item) {
  margin-bottom: 8px;
}

.compact-form :deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

.compact-form :deep(.el-form-item__label) {
  line-height: 28px;
  font-size: 13px;
  white-space: nowrap;
}

.field-input {
  width: 140px;
  max-width: 100%;
}

.compact-form :deep(.el-select.field-input) {
  width: 140px;
}

.field-input :deep(.el-input__wrapper) {
  padding-left: 6px;
  padding-right: 30px;
}

/* 表单内联 hint */
.field-hint-inline {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  line-height: 1.4;
  margin-left: 6px;
  display: inline-block;
}

/* 表单项旁的小图标 */
.field-info {
  margin-left: 4px;
  color: var(--el-text-color-placeholder);
  cursor: help;
  font-size: 13px;
  vertical-align: middle;
}

/* 分隔线旁的小图标 */
.divider-info {
  margin-left: 4px;
  color: var(--el-text-color-placeholder);
  cursor: help;
  font-size: 13px;
  vertical-align: middle;
}

/* ==================== 开仓信号 ==================== */
.entry-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.signal-card {
  background: var(--el-fill-color-extra-light);
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  padding: 12px;
  min-width: 0;
}

.signal-card--standalone {
  background: var(--el-fill-color-light);
  border-style: dashed;
}

.signal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.signal-name {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.2;
}

.signal-subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}

/* ==================== ROI 止盈卡片 ==================== */
.roi-panel {
  background: var(--el-fill-color-extra-light);
  border-radius: 8px;
  border: 1px solid var(--el-border-color-light);
  padding: 12px;
}

.roi-header {
  display: grid;
  grid-template-columns: 28px 1fr 1fr 32px;
  gap: 12px;
  padding: 0 8px 8px 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  border-bottom: 1px dashed var(--el-border-color);
  margin-bottom: 8px;
}

.roi-col-time,
.roi-col-profit {
  padding-left: 8px;
}

.roi-col-idx {
  text-align: center;
}

.roi-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.roi-row {
  display: grid;
  grid-template-columns: 28px 1fr 1fr 32px;
  gap: 12px;
  align-items: center;
  background: var(--el-bg-color);
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px solid var(--el-border-color-lighter);
  transition: all 0.2s;
}

.roi-row:hover {
  border-color: var(--el-color-primary-light-5);
}

.roi-index {
  text-align: center;
  font-weight: 600;
  font-size: 13px;
  color: var(--el-text-color-regular);
}

/* 输入框与单位容器 */
.roi-cell {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 0;
}

/* 覆盖 Element 的输入框样式，让出右侧单位空间 */
.roi-input {
  width: 100%;
}
.roi-input :deep(.el-input__wrapper) {
  padding-right: 40px; /* 留出空间给后缀 */
}
.roi-input :deep(.el-input__inner) {
  text-align: left;
  font-family: var(--el-font-family-monospace, monospace);
  font-size: 13px;
}

/* 自定义后缀单位 */
.roi-suffix {
  position: absolute;
  right: 32px; /* 避开 Element 的上下加减按钮 */
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  pointer-events: none;
  z-index: 2;
}

.roi-delete {
  padding: 0;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  font-size: 16px;
}

/* ==================== 统一的新增按钮底部样式 ==================== */
.roi-footer,
.dca-footer {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end; /* 居右对齐 */
}

.add-btn {
  /* 已经通过 element 的 type="success" 确定了颜色，这里控制大小 */
  border-style: solid;
  transition: all 0.2s;
}


/* ==================== 提示框（保留兼容） ==================== */
.section-alert {
  margin-bottom: 12px;
}

/* ==================== DCA levels ==================== */
.dca-levels {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.dca-level-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-fill-color-extra-light);
}

.dca-level-index {
  width: 22px;
  text-align: center;
  font-weight: 700;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  flex: none;
}

.dca-level-form {
  flex: 1;
  display: flex;
  gap: 12px;
  min-width: 0;
}

.dca-level-form :deep(.el-form-item) {
  margin-bottom: 0;
  flex: 1;
  min-width: 0;
}

.dca-level-form :deep(.el-form-item__label) {
  line-height: 28px;
  font-size: 13px;
}

.dca-level-form :deep(.el-form-item__content) {
  line-height: 28px;
  min-width: 0;
}

.dca-level-form .field-input {
  width: 100%;
}

.dca-level-delete {
  width: 20px;
  padding: 0;
  flex: none;
}

.dca-add-btn {
  align-self: flex-start;
  margin-top: 4px;
}

/* ==================== 单列输入框（网格配置） ==================== */
.field-input-block {
  width: 100%;
  max-width: 320px;
}

.field-input-block :deep(.el-input__wrapper) {
  padding-left: 8px;
  padding-right: 32px;
}

.field-input-block :deep(.el-input__inner) {
  text-align: left;
  padding-right: 0;
  font-size: 13px;
}

.field-input-block :deep(.el-input-number__increase),
.field-input-block :deep(.el-input-number__decrease) {
  width: 24px;
}

/* ==================== 保存 ==================== */
.save-bar {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
}

/* ==================== 响应式 ==================== */
@media (max-width: 1400px) {
  .entry-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .roi-list {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }
}
</style>