<template>
    <div
        v-if="config?.entry"
        class="strategy-panel">

        <!-- ==================== 策略概览 ==================== -->
        <el-card
            v-if="tradeInfo"
            class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">策略概览</span>
                    <span class="card-head__meta">
                        <el-text type="info" size="small">
                            当前策略运行参数与逻辑摘要
                        </el-text>
                    </span>
                </div>
            </template>

            <el-descriptions
                class="trade-descriptions"
                :column="3"
                border
                size="small">
                <el-descriptions-item label="方向">
                    <el-tag
                        :type="tradeInfo.side === 'long' ? 'success' : 'danger'"
                        size="small">
                        {{ tradeInfo.direction }}
                    </el-tag>
                </el-descriptions-item>

                <el-descriptions-item label="周期">
                    {{ tradeInfo.timeframe }}
                </el-descriptions-item>

                <el-descriptions-item label="杠杆">
                    {{ tradeInfo.leverage }}
                </el-descriptions-item>

                <el-descriptions-item label="止损">
                    {{ tradeInfo.stoploss }}
                </el-descriptions-item>

                <el-descriptions-item label="时间止损" :span="2">
                    <span v-if="tradeInfo.timeStopSignal">{{ tradeInfo.timeStopSignal }}</span>
                    <span v-else class="empty-placeholder"></span>
                </el-descriptions-item>

                <el-descriptions-item
                    v-if="tradeInfo.entrySignal"
                    label="开仓信号"
                    :span="2">
                    {{ tradeInfo.entrySignal }}
                </el-descriptions-item>

                <el-descriptions-item
                    v-if="tradeInfo.pumpProtectSignal"
                    label="Pump 保护"
                    :span="2">
                    {{ tradeInfo.pumpProtectSignal }}
                </el-descriptions-item>

                <el-descriptions-item label="TP减仓" :span="2">
                    <span v-if="tradeInfo.tpSignal">{{ tradeInfo.tpSignal }}</span>
                    <span v-else class="empty-placeholder"></span>
                </el-descriptions-item>

                <el-descriptions-item label="DCA止盈" :span="2">
                    <span v-if="tradeInfo.lossTpSignal">{{ tradeInfo.lossTpSignal }}</span>
                    <span v-else class="empty-placeholder"></span>
                </el-descriptions-item>

                <el-descriptions-item label="趋势加仓" :span="2">
                    <span v-if="tradeInfo.trendSignal">{{ tradeInfo.trendSignal }}</span>
                    <span v-else class="empty-placeholder"></span>
                </el-descriptions-item>

                <el-descriptions-item label="DCA规则" :span="2">
                    <span v-if="tradeInfo.dcaSignal">{{ tradeInfo.dcaSignal }}</span>
                    <span v-else class="empty-placeholder"></span>
                </el-descriptions-item>

                <el-descriptions-item label="网格规则" :span="2">
                    <span v-if="tradeInfo.gridSignal">{{ tradeInfo.gridSignal }}</span>
                    <span v-else class="empty-placeholder"></span>
                </el-descriptions-item>

                <el-descriptions-item label="单对持仓上限" :span="2">
                    <span v-if="tradeInfo.pairMaxPositionSignal">
                        {{ tradeInfo.pairMaxPositionSignal }}
                    </span>
                    <span v-else class="empty-placeholder"></span>
                </el-descriptions-item>

                <el-descriptions-item label="HTF 趋势过滤" :span="2">
                    <span v-if="tradeInfo.htfTrendSignal">{{ tradeInfo.htfTrendSignal }}</span>
                    <span v-else class="empty-placeholder"></span>
                </el-descriptions-item>

                <el-descriptions-item
                    v-if="tradeInfo.roiLevels.length"
                    label="ROI阶梯"
                    :span="2">
                    <el-scrollbar max-height="100px">
                        <div class="roi-chip-wrap">
                            <el-tag
                                v-for="tier in tradeInfo.roiLevels"
                                :key="tier.label"
                                size="small"
                                effect="plain">
                                {{ tier.label }}
                            </el-tag>
                        </div>
                    </el-scrollbar>
                </el-descriptions-item>

                <el-descriptions-item label="交易开关">
                    {{ tradeInfo.positionAdjustment }} / {{ tradeInfo.trailingStop }}
                </el-descriptions-item>
            </el-descriptions>

            <el-alert
                class="section-alert"
                type="info"
                :closable="false">
                <div class="note-list">
                    <div
                        v-for="note in tradeInfo.notes"
                        :key="note">
                        {{ note }}
                    </div>
                </div>
            </el-alert>
        </el-card>

        <!-- ==================== 时间周期 ==================== -->
        <el-card class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">K 线时间周期</span>
                    <span class="card-head__meta">
                        <el-text type="info" size="small">
                            修改后需重启策略生效
                        </el-text>
                    </span>
                </div>
            </template>

            <el-alert
                class="section-alert"
                type="warning"
                :closable="false"
                show-icon>
                切换时间周期会改变指标计算和交易频率，保存后需要重启对应 bot 才能生效
            </el-alert>

            <el-form class="compact-form" label-width="120px" size="small">
                <el-form-item label="时间周期">
                    <el-select
                        v-model="config.timeframe"
                        class="field-input">
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
                </el-form-item>
            </el-form>
        </el-card>

        <!-- ==================== 金额模式 ==================== -->
        <el-card class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">金额模式</span>
                    <span class="card-head__meta">
                        <el-text type="info" size="small">
                            百分比按总资金缩放，固定金额每层固定
                        </el-text>
                    </span>
                </div>
            </template>

            <el-radio-group v-model="config.amount_mode">
                <el-radio-button value="percent">
                    百分比
                </el-radio-button>
                <el-radio-button value="amount">
                    固定金额（保证金 USDT）
                </el-radio-button>
            </el-radio-group>
        </el-card>

        <!-- ==================== 指标配置 ==================== -->
        <el-card class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">指标配置</span>
                </div>
            </template>

            <el-divider content-position="left">MACD</el-divider>

            <el-row :gutter="12">
                <el-col :span="8">
                    <el-form-item label="Fast">
                        <el-input-number
                            v-model="config.indicator.macd.fast"
                            class="field-input"
                            controls-position="right"
                            :min="2"
                            :max="200"
                            :step="1"
                            :precision="0"
                        />
                    </el-form-item>
                </el-col>
                <el-col :span="8">
                    <el-form-item label="Slow">
                        <el-input-number
                            v-model="config.indicator.macd.slow"
                            class="field-input"
                            controls-position="right"
                            :min="2"
                            :max="200"
                            :step="1"
                            :precision="0"
                        />
                    </el-form-item>
                </el-col>
                <el-col :span="8">
                    <el-form-item label="Signal">
                        <el-input-number
                            v-model="config.indicator.macd.signal"
                            class="field-input"
                            controls-position="right"
                            :min="2"
                            :max="200"
                            :step="1"
                            :precision="0"
                        />
                    </el-form-item>
                </el-col>
            </el-row>

            <el-divider content-position="left">KDJ</el-divider>

            <el-row :gutter="12">
                <el-col :span="8">
                    <el-form-item label="FastK">
                        <el-input-number
                            v-model="config.indicator.kdj.fastk"
                            class="field-input"
                            controls-position="right"
                            :min="2"
                            :max="200"
                            :step="1"
                            :precision="0"
                        />
                    </el-form-item>
                </el-col>
                <el-col :span="8">
                    <el-form-item label="SlowK">
                        <el-input-number
                            v-model="config.indicator.kdj.slowk"
                            class="field-input"
                            controls-position="right"
                            :min="2"
                            :max="200"
                            :step="1"
                            :precision="0"
                        />
                    </el-form-item>
                </el-col>
                <el-col :span="8">
                    <el-form-item label="SlowD">
                        <el-input-number
                            v-model="config.indicator.kdj.slowd"
                            class="field-input"
                            controls-position="right"
                            :min="2"
                            :max="200"
                            :step="1"
                            :precision="0"
                        />
                    </el-form-item>
                </el-col>
            </el-row>

            <el-divider content-position="left">EMA</el-divider>

            <el-row :gutter="12">
                <el-col :span="8">
                    <el-form-item label="快">
                        <el-input-number
                            v-model="config.indicator.ema.fast"
                            class="field-input"
                            controls-position="right"
                            :min="2"
                            :max="200"
                            :step="1"
                            :precision="0"
                        />
                    </el-form-item>
                </el-col>
                <el-col :span="8">
                    <el-form-item label="中">
                        <el-input-number
                            v-model="config.indicator.ema.mid"
                            class="field-input"
                            controls-position="right"
                            :min="2"
                            :max="200"
                            :step="1"
                            :precision="0"
                        />
                    </el-form-item>
                </el-col>
                <el-col :span="8">
                    <el-form-item label="慢">
                        <el-input-number
                            v-model="config.indicator.ema.slow"
                            class="field-input"
                            controls-position="right"
                            :min="2"
                            :max="200"
                            :step="1"
                            :precision="0"
                        />
                    </el-form-item>
                </el-col>
            </el-row>

            <el-divider content-position="left">RSI / Bollinger</el-divider>

            <el-row :gutter="12">
                <el-col :span="8">
                    <el-form-item label="RSI周期">
                        <el-input-number
                            v-model="config.indicator.rsi.period"
                            class="field-input"
                            controls-position="right"
                            :min="2"
                            :max="200"
                            :step="1"
                            :precision="0"
                        />
                    </el-form-item>
                </el-col>
                <el-col :span="8">
                    <el-form-item label="BB周期">
                        <el-input-number
                            v-model="config.indicator.bb.period"
                            class="field-input"
                            controls-position="right"
                            :min="2"
                            :max="200"
                            :step="1"
                            :precision="0"
                        />
                    </el-form-item>
                </el-col>
                <el-col :span="8">
                    <el-form-item label="BB STD">
                        <el-input-number
                            v-model="config.indicator.bb.std"
                            class="field-input"
                            controls-position="right"
                            :min="0.5"
                            :max="5"
                            :step="0.1"
                            :precision="2"
                        />
                    </el-form-item>
                </el-col>
            </el-row>
        </el-card>

        <!-- ==================== ROI止盈规则 ==================== -->
        <el-card class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">ROI止盈规则</span>
                    <span class="card-head__meta">
                        <el-text type="info" size="small">
                            达到目标收益后分批止盈
                        </el-text>
                        <el-button
                            size="small"
                            type="success"
                            plain
                            @click="addRoi">
                            新增规则
                        </el-button>
                    </span>
                </div>
            </template>

            <el-alert
                class="section-alert"
                type="success"
                :closable="false"
                show-icon>
                持仓达到指定时间后，收益率达到目标值触发 TP
            </el-alert>

            <div class="roi-list">
                <div
                    v-for="(roi, index) in config.tp.roi_levels || []"
                    :key="index"
                    class="roi-row">
                    <span class="roi-index">{{ index + 1 }}</span>

                    <el-input-number
                        v-model="roi.minutes"
                        class="roi-input"
                        controls-position="right"
                        :min="0"
                        :max="10080"
                        :step="1"
                        :precision="0"
                        size="small"
                        placeholder="分钟"/>

                    <el-input-number
                        v-model="roi.roi"
                        class="roi-input"
                        controls-position="right"
                        :min="-100"
                        :max="100"
                        :step="0.1"
                        :precision="2"
                        size="small"
                        placeholder="收益%"/>

                    <el-button
                        class="roi-delete"
                        type="danger"
                        link
                        size="small"
                        @click="removeRoi(index)">
                        ✕
                    </el-button>
                </div>
            </div>
        </el-card>

        <!-- ==================== 开仓信号 ==================== -->
        <el-card class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">开仓信号</span>
                    <span class="card-head__meta">
                        <el-text type="info" size="small">
                            选择满足方式与信号条件
                        </el-text>
                    </span>
                </div>
            </template>

            <!-- 条件模式 -->
            <el-form class="compact-form" label-width="100px" size="small">
                <el-form-item label="条件模式">
                    <el-select
                        v-model="config.entry.condition"
                        class="field-input"
                    >
                        <el-option label="全部满足 AND" value="and" />
                        <el-option label="任意满足 OR" value="or" />
                    </el-select>
                </el-form-item>
            </el-form>

            <div class="entry-grid">
                <section class="signal-card">
                    <div class="signal-head">
                        <div>
                            <div class="signal-name">RSI</div>
                            <div class="signal-subtitle">RSI低位允许入场</div>
                        </div>
                        <el-switch
                            :model-value="config.entry.rsi.enable"
                            @change="val => changeEntrySignal('rsi', val)"
                        />
                    </div>
                    <el-form class="compact-form" label-width="54px" size="small">
                        <el-input-number
                            v-model="config.entry.rsi.value"
                            class="field-input"
                            controls-position="right"
                            :disabled="!config.entry.rsi.enable"
                            :min="1"
                            :max="100"
                            :step="1"
                            :precision="0"
                        />
                    </el-form>
                </section>

                <section class="signal-card">
                    <div class="signal-head">
                        <div>
                            <div class="signal-name">MACD</div>
                            <div class="signal-subtitle">趋势与动能共振确认</div>
                        </div>
                        <el-switch
                            :model-value="config.entry.macd.enable"
                            @change="val => changeEntrySignal('macd', val)"
                        />
                    </div>
                </section>

                <section class="signal-card">
                    <div class="signal-head">
                        <div>
                            <div class="signal-name">Bollinger</div>
                            <div class="signal-subtitle">价格触及下轨时允许入场</div>
                        </div>
                        <el-switch
                            :model-value="config.entry.bb.enable"
                            @change="val => changeEntrySignal('bb', val)"
                        />
                    </div>
                </section>

                <section class="signal-card">
                    <div class="signal-head">
                        <div>
                            <div class="signal-name">Pump 保护</div>
                            <div class="signal-subtitle">
                                开启后，检测到 Pump 行情时暂停开仓
                            </div>
                        </div>
                        <el-switch
                            :model-value="config.entry.pump_protect.enable"
                            @change="val => changeEntrySignal('pump_protect', val)"
                        />
                    </div>
                </section>
            </div>
        </el-card>

        <!-- ==================== TP止盈 + 止损 ==================== -->
        <el-row class="panel-grid" :gutter="12">
            <el-col :span="12">
                <el-card class="section-card">
                    <template #header>
                        <div class="card-head">
                            <span class="card-head__title">TP止盈</span>
                            <span class="card-head__meta">
                                <el-text type="info" size="small">
                                    减仓后自动补回目标仓位
                                </el-text>
                            </span>
                        </div>
                    </template>

                    <el-alert
                        class="section-alert"
                        type="info"
                        :closable="false">
                        达到 ROI 后减仓，并自动补回目标仓位
                    </el-alert>

                    <el-form class="compact-form" label-width="120px" size="small">
                        <el-form-item label="自动补仓">
                            <el-switch
                                v-model="config.tp.rebuy_enable"
                                @change="onRebuyChange"
                            />
                        </el-form-item>
                        <el-form-item
                            :label="
                                !config.tp.rebuy_enable
                                    ? '减仓比例%'
                                    : (config.amount_mode === 'amount' ? '减仓金额(USDT)' : '减仓比例%')
                            "
                        >
                            <!-- 不补仓：一律显示 100% 且禁用 -->
                            <el-input-number
                                v-if="!config.tp.rebuy_enable"
                                :model-value="100"
                                class="field-input"
                                controls-position="right"
                                :min="100"
                                :max="100"
                                :step="1"
                                :precision="0"
                                disabled
                            />

                            <!-- 补仓 + 金额模式 -->
                            <el-input-number
                                v-else-if="config.amount_mode === 'amount'"
                                v-model="config.tp.reduce_amount"
                                class="field-input"
                                controls-position="right"
                                :min="1"
                                :max="100000"
                                :step="10"
                                :precision="2"
                            />

                            <!-- 补仓 + 百分比模式 -->
                            <el-input-number
                                v-else
                                v-model="config.tp.reduce_percent"
                                class="field-input"
                                controls-position="right"
                                :min="0"
                                :max="100"
                                :step="1"
                                :precision="0"
                            />
                        </el-form-item>

                        <el-form-item
                            :label="config.amount_mode === 'amount' ? '加仓至(USDT)' : '目标仓位占比%'"
                        >
                            <el-input-number
                                v-if="config.amount_mode === 'amount'"
                                v-model="config.tp.target_wallet_amount"
                                class="field-input"
                                controls-position="right"
                                :min="1"
                                :max="100000"
                                :step="10"
                                :precision="2"
                            />
                            <el-input-number
                                v-else
                                v-model="config.tp.target_wallet_percent"
                                class="field-input"
                                controls-position="right"
                                :min="0"
                                :max="100"
                                :step="0.1"
                                :precision="2"
                            />
                        </el-form-item>
                    </el-form>
                </el-card>
            </el-col>

            <el-col :span="12">
                <el-card class="section-card">
                    <template #header>
                        <div class="card-head">
                            <span class="card-head__title">止损配置</span>
                            <span class="card-head__meta">
                                <el-text type="info" size="small">
                                    达到设定亏损后强制平仓
                                </el-text>
                            </span>
                        </div>
                    </template>

                    <el-alert
                        class="section-alert"
                        type="warning"
                        :closable="false">
                        达到设定亏损比例后强制平仓
                    </el-alert>

                    <el-form class="compact-form" label-width="120px" size="small">
                        <el-form-item label="启用止损">
                            <el-switch v-model="config.sl.enable" />
                        </el-form-item>
                        <el-form-item label="止损百分比">
                            <el-input-number
                                v-model="config.sl.stoploss"
                                class="field-input"
                                controls-position="right"
                                :min="-999"
                                :max="0"
                                :step="1"
                                :precision="0"
                            />
                        </el-form-item>

                        <!-- ⬇️ 新增：时间止损 -->
                        <el-divider content-position="left">时间止损</el-divider>

                        <el-form-item label="启用时间止损">
                            <el-switch v-model="config.sl.time_stop.enable" />
                        </el-form-item>

                        <el-form-item label="未成交时长(小时)">
                            <el-input-number
                                v-model="config.sl.time_stop.hours"
                                class="field-input"
                                controls-position="right"
                                :min="0.1"
                                :max="720"
                                :step="0.5"
                                :precision="1"
                                :disabled="!config.sl.time_stop.enable"
                            />
                        </el-form-item>

                        <el-form-item label="收益阈值模式">
                            <el-select
                                v-model="config.sl.time_stop.mode"
                                class="field-input"
                                :disabled="!config.sl.time_stop.enable">
                                <el-option label="百分比 %" value="percent" />
                                <el-option label="固定金额 USDT" value="amount" />
                            </el-select>
                        </el-form-item>

                        <el-form-item
                            :label="config.sl.time_stop.mode === 'amount' ? '收益阈值(USDT)' : '收益阈值(%)'">
                            <el-input-number
                                v-model="config.sl.time_stop.profit_threshold"
                                class="field-input"
                                controls-position="right"
                                :min="-9999"
                                :max="0"
                                :step="config.sl.time_stop.mode === 'amount' ? 1 : 0.5"
                                :precision="config.sl.time_stop.mode === 'amount' ? 2 : 1"
                                :disabled="!config.sl.time_stop.enable"
                            />
                        </el-form-item>
                    </el-form>
                </el-card>
            </el-col>
        </el-row>

        <!-- ==================== DCA配置 ==================== -->
        <el-card class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">DCA配置</span>
                    <span class="card-head__meta">
                        <el-text type="info" size="small">
                            回撤满足条件时分层补仓
                        </el-text>
                    </span>
                </div>
            </template>

            <el-alert
                class="section-alert"
                type="warning"
                :closable="false"
                show-icon>
                回撤达到阈值且满足 RSI 或 KDJ 条件时加仓
            </el-alert>

            <el-form class="compact-form" label-width="100px" size="small">
                <el-row :gutter="12">
                    <el-col :span="8">
                        <el-form-item label="启用DCA">
                            <el-switch v-model="config.dca.enable" />
                        </el-form-item>
                    </el-col>

                    <el-col :span="8">
                        <el-form-item label="金额模式">
                            <el-select
                                v-model="config.dca.amount_mode"
                                class="field-input">
                                <el-option label="自动倍率" value="auto" />
                                <el-option label="手动分层" value="manual" />
                            </el-select>
                        </el-form-item>
                    </el-col>

                    <el-col :span="8">
                        <el-form-item label="条件模式">
                            <el-select
                                v-model="config.dca.condition"
                                class="field-input">
                                <el-option label="仅 RSI" value="rsi" />
                                <el-option label="仅 J" value="j" />
                                <el-option label="RSI 或 J" value="or" />
                                <el-option label="RSI 且 J" value="and" />
                            </el-select>
                        </el-form-item>
                    </el-col>

                    <el-col :span="8">
                        <el-form-item label="最大加仓次数">
                            <el-input-number
                                v-model="config.dca.max_count"
                                class="field-input"
                                controls-position="right"
                                :min="1"
                                :max="20"
                                :step="1"
                                :precision="0"
                            />
                        </el-form-item>
                    </el-col>

                    <el-col :span="8">
                        <el-form-item label="冷却时间">
                            <el-input-number
                                v-model="config.dca.cooldown_minutes"
                                class="field-input"
                                controls-position="right"
                                :min="0"
                                :max="1440"
                                :step="5"
                                :precision="0"
                            />
                        </el-form-item>
                    </el-col>

                    <el-col :span="8">
                        <el-form-item label="价格偏差">
                            <el-input-number
                                v-model="config.dca.price_offset"
                                class="field-input"
                                controls-position="right"
                                :min="0.1"
                                :max="20"
                                :step="0.1"
                                :precision="2"
                            />
                        </el-form-item>
                    </el-col>

                    <el-col :span="8">
                        <el-form-item label="价格偏差乘数">
                            <el-input-number
                                v-model="config.dca.price_multiplier"
                                class="field-input"
                                controls-position="right"
                                :min="0.1"
                                :max="10"
                                :step="0.1"
                                :precision="2"
                            />
                        </el-form-item>
                    </el-col>

                    <template v-if="config.dca.amount_mode === 'auto'">
                        <el-col :span="8">
                            <el-form-item
                                :label="config.amount_mode === 'amount' ? '加仓金额(USDT)' : '加仓比例%'"
                            >
                                <!-- 固定金额：用 base_amount -->
                                <el-input-number
                                    v-if="config.amount_mode === 'amount'"
                                    v-model="config.dca.base_amount"
                                    class="field-input"
                                    controls-position="right"
                                    :min="1"
                                    :max="100000"
                                    :step="10"
                                    :precision="2"
                                />
                                <!-- 百分比：用 base_percent -->
                                <el-input-number
                                    v-else
                                    v-model="config.dca.base_percent"
                                    class="field-input"
                                    controls-position="right"
                                    :min="0.1"
                                    :max="100"
                                    :step="0.1"
                                    :precision="2"
                                />
                            </el-form-item>
                        </el-col>

                        <el-col :span="8">
                            <el-form-item label="订单规模乘数">
                                <el-input-number
                                    v-model="config.dca.amount_multiplier"
                                    class="field-input"
                                    controls-position="right"
                                    :min="0.1"
                                    :max="10"
                                    :step="0.1"
                                    :precision="2"
                                />
                            </el-form-item>
                        </el-col>
                    </template>
                </el-row>
            </el-form>

            <!-- 手动模式：levels -->
            <div class="dca-levels">
                <div
                    v-for="(level, index) in config.dca.levels"
                    :key="index"
                    class="dca-level-row">
                    <div class="dca-level-index">{{ index + 1 }}</div>

                    <el-form class="dca-level-form" label-width="120px" size="small">
                        <el-form-item
                            v-if="config.dca.amount_mode === 'manual'"
                            :label="config.amount_mode === 'amount' ? '加仓金额(USDT)' : '加仓比例%'"
                        >
                            <!-- 固定金额：用 level.amount -->
                            <el-input-number
                                v-if="config.amount_mode === 'amount'"
                                v-model="level.amount"
                                class="field-input"
                                controls-position="right"
                                :min="1"
                                :max="10000"
                                :step="10"
                                :precision="2"
                            />
                            <!-- 百分比：用 level.percent -->
                            <el-input-number
                                v-else
                                v-model="level.percent"
                                class="field-input"
                                controls-position="right"
                                :min="0.1"
                                :max="100"
                                :step="0.1"
                                :precision="2"
                            />
                        </el-form-item>

                        <el-form-item :label="config.side === 'long' ? 'RSI <' : 'RSI >'">
                            <el-input-number
                                v-model="level.rsi_limit"
                                class="field-input"
                                controls-position="right"
                                :min="0"
                                :max="100"
                                :step="1"
                                :precision="0"
                            />
                        </el-form-item>

                        <el-form-item label="J值">
                            <el-input-number
                                v-model="level.j_limit"
                                class="field-input"
                                controls-position="right"
                                :min="-100"
                                :max="200"
                                :step="1"
                                :precision="0"
                            />
                        </el-form-item>
                    </el-form>

                    <el-button
                        class="dca-level-delete"
                        type="danger"
                        link
                        size="small"
                        :disabled="config.dca.levels.length <= 1"
                        @click="removeDca(index)">
                        ✕
                    </el-button>
                </div>

                <el-button
                    class="dca-add-btn"
                    type="success"
                    plain
                    size="small"
                    @click="addDca">
                    + 新增一层
                </el-button>
            </div>
        </el-card>

        <!-- ==================== 浮亏止盈 ==================== -->
        <el-card class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">浮亏止盈</span>
                    <span class="card-head__meta">
                        <el-text type="info" size="small">
                            DCA后达到收益目标，自动减仓保留仓位
                        </el-text>
                    </span>
                </div>
            </template>

            <el-form class="compact-form" label-width="110px" size="small">
                <el-row :gutter="12">
                    <el-col :span="8">
                        <el-form-item label="启用">
                            <el-switch v-model="config.loss_tp.enable" />
                        </el-form-item>
                    </el-col>

                    <el-col :span="8">
                        <el-form-item label="止盈收益率%">
                            <el-input-number
                                v-model="config.loss_tp.dca_tp_profit"
                                class="field-input"
                                controls-position="right"
                                :min="0"
                                :max="100"
                                :step="0.1"
                                :precision="2"
                            />
                        </el-form-item>
                    </el-col>

                    <!-- 全平开关 -->
                    <el-col :span="8">
                        <el-form-item label="全平仓位">
                            <el-switch
                                v-model="config.loss_tp.close_all"
                            />
                        </el-form-item>
                    </el-col>
                </el-row>

                <!-- 非全平时显示目标仓位 -->
                <el-row :gutter="12" v-if="!config.loss_tp.close_all">
                    <el-col :span="8">
                        <el-form-item
                            :label="config.amount_mode === 'amount' ? '减仓至(USDT)' : '减仓至目标仓位%'"
                        >
                            <el-input-number
                                v-if="config.amount_mode === 'amount'"
                                v-model="config.loss_tp.target_wallet_amount"
                                class="field-input"
                                controls-position="right"
                                :min="1"
                                :max="100000"
                                :step="10"
                                :precision="2"
                            />
                            <el-input-number
                                v-else
                                v-model="config.loss_tp.target_wallet_percent"
                                class="field-input"
                                controls-position="right"
                                :min="0"
                                :max="100"
                                :step="1"
                                :precision="2"
                            />
                        </el-form-item>
                    </el-col>
                </el-row>
            </el-form>
        </el-card>

        <!-- ==================== 趋势加仓 + 网格 ==================== -->
        <el-row class="panel-grid" :gutter="12">
            <el-col :span="12">
                <el-card class="section-card">
                    <template #header>
                        <div class="card-head">
                            <span class="card-head__title">
                                趋势加仓
                            </span>

                            <span class="card-head__meta">
                                <el-text type="info" size="small">
                                    盈利趋势中扩大仓位
                                </el-text>
                            </span>
                        </div>
                    </template>

                    <el-alert
                        class="section-alert"
                        type="success"
                        :closable="false"
                        show-icon
                    >
                        {{config.side==="long"
                            ?"MACD+KDJ+EMA多头趋势加仓"
                            :"MACD+KDJ+EMA空头趋势加仓"}}
                    </el-alert>

                    <el-form class="compact-form" label-width="120px" size="small">
                        <el-row :gutter="12">
                            <el-col :span="24">
                                <el-form-item label="启用趋势加仓">
                                    <el-switch v-model="config.trend_add.enable" />
                                </el-form-item>
                            </el-col>

                            <el-col :span="24">
                                <el-form-item
                                    :label="config.amount_mode === 'amount' ? '加仓金额(USDT)' : '加仓比例%'"
                                >
                                    <el-input-number
                                        v-if="config.amount_mode === 'amount'"
                                        v-model="config.trend_add.amount_amount"
                                        :min="1"
                                        :max="100000"
                                        :step="10"
                                        :precision="2"
                                    />
                                    <el-input-number
                                        v-else
                                        v-model="config.trend_add.amount_percent"
                                        :min="0"
                                        :max="100"
                                        :step="0.1"
                                        :precision="2"
                                    />
                                </el-form-item>
                            </el-col>

                            <el-col :span="20">
                                <el-form-item label="条件模式">
                                    <el-select v-model="config.trend_add.condition">
                                        <el-option label="全部满足 AND" value="and" />
                                        <el-option label="任意满足 OR" value="or" />
                                    </el-select>
                                </el-form-item>
                            </el-col>
                        </el-row>
                    </el-form>

                    <el-divider>
                        趋势指标
                    </el-divider>

                    <el-row :gutter="12">
                        <el-col :span="8">
                            <el-form-item label="MACD">
                                <el-switch
                                    v-model="config.trend_add.macd_enable"
                                />
                            </el-form-item>
                        </el-col>

                        <el-col :span="8">
                            <el-form-item label="KDJ">
                                <el-switch
                                    v-model="config.trend_add.kdj_enable"
                                />
                            </el-form-item>
                        </el-col>

                        <el-col :span="8">
                            <el-form-item label="EMA">
                                <el-switch
                                    v-model="config.trend_add.ema_enable"
                                />
                            </el-form-item>
                        </el-col>
                    </el-row>

                    <el-card class="section-card">
                        <template #header>
                            <div class="card-head">
                                <span class="card-head__title">
                                    KDJ减仓
                                </span>
                            </div>
                        </template>

                        <el-alert
                            class="section-alert"
                            type="warning"
                            :closable="false"
                        >
                            趋势加仓后，KDJ转弱退出趋势仓位
                        </el-alert>

                        <el-form label-width="120px" size="small">
                            <el-row :gutter="12">
                                <el-col :span="24">
                                    <el-form-item label="启用KDJ减仓">
                                        <el-switch
                                            v-model="config.trend_add.kdj_reduce.enable"
                                            :disabled="!config.trend_add.enable"
                                        />
                                    </el-form-item>
                                </el-col>

                                <el-col :span="24">
                                    <el-form-item
                                        :label="config.amount_mode === 'amount' ? '减仓金额(USDT)' : '减仓比例%'"
                                    >
                                        <el-input-number
                                            v-if="config.amount_mode === 'amount'"
                                            v-model="config.trend_add.kdj_reduce.reduce_amount"
                                            :disabled="
                                                !config.trend_add.enable ||
                                                !config.trend_add.kdj_reduce.enable
                                            "
                                            :min="1"
                                            :max="100000"
                                            :step="10"
                                            :precision="2"
                                            controls-position="right"
                                        />
                                        <el-input-number
                                            v-else
                                            v-model="config.trend_add.kdj_reduce.reduce_percent"
                                            :disabled="
                                                !config.trend_add.enable ||
                                                !config.trend_add.kdj_reduce.enable
                                            "
                                            :min="0"
                                            :max="100"
                                            :step="1"
                                            :precision="0"
                                            controls-position="right"
                                        />
                                    </el-form-item>
                                </el-col>
                            </el-row>
                        </el-form>
                    </el-card>
                </el-card>
            </el-col>

            <el-col :span="12">
                <el-card class="section-card">
                    <template #header>
                        <div class="card-head">
                            <span class="card-head__title">网格配置</span>
                            <span class="card-head__meta">
                                <el-text type="info" size="small">
                                    价格区间内自动分层挂单
                                </el-text>
                            </span>
                        </div>
                    </template>

                    <el-alert
                        class="section-alert"
                        type="warning"
                        :closable="false">
                        启用后将在当前仓位下方自动挂网格单
                    </el-alert>

                    <el-form class="compact-form" label-width="120px" size="small">
                        <el-row :gutter="12">
                            <el-col :span="24">
                                <el-form-item label="启用网格">
                                    <el-switch v-model="config.grid.enable" />
                                </el-form-item>
                            </el-col>

                            <el-col :span="24">
                                <el-form-item label="最大加仓次数">
                                    <el-input-number
                                        v-model="config.grid.max_count"
                                        class="field-input"
                                        controls-position="right"
                                        :min="1"
                                        :max="50"
                                        :step="1"
                                        :precision="0"
                                    />
                                </el-form-item>
                            </el-col>

                            <el-col :span="24">
                                <el-form-item label="冷却时间">
                                    <el-input-number
                                        v-model="config.grid.cooldown_minutes"
                                        class="field-input"
                                        controls-position="right"
                                        :min="0"
                                        :max="1440"
                                        :step="5"
                                        :precision="0"
                                    />
                                </el-form-item>
                            </el-col>

                            <el-col :span="24">
                                <el-form-item label="网格下沿%">
                                    <el-input-number
                                        v-model="config.grid.grid_lower"
                                        class="field-input"
                                        controls-position="right"
                                        :min="-50"
                                        :max="0"
                                        :step="0.1"
                                        :precision="2"
                                    />
                                </el-form-item>
                            </el-col>

                            <el-col :span="24">
                                <el-form-item label="网格上沿%">
                                    <el-input-number
                                        v-model="config.grid.grid_upper"
                                        class="field-input"
                                        controls-position="right"
                                        :min="0"
                                        :max="50"
                                        :step="0.1"
                                        :precision="2"
                                    />
                                </el-form-item>
                            </el-col>

                            <el-col :span="24">
                                <el-form-item
                                    :label="config.amount_mode === 'amount' ? '加仓金额(USDT)' : '加仓占比%'"
                                >
                                    <el-input-number
                                        v-if="config.amount_mode === 'amount'"
                                        v-model="config.grid.buy_amount"
                                        class="field-input"
                                        controls-position="right"
                                        :min="1"
                                        :max="100000"
                                        :step="10"
                                        :precision="2"
                                    />
                                    <el-input-number
                                        v-else
                                        v-model="config.grid.buy_percent"
                                        class="field-input"
                                        controls-position="right"
                                        :min="0"
                                        :max="100"
                                        :step="0.1"
                                        :precision="2"
                                    />
                                </el-form-item>
                            </el-col>

                            <el-col :span="24">
                                <el-form-item
                                    :label="config.amount_mode === 'amount' ? '减仓金额(USDT)' : '减仓占比%'"
                                >
                                    <el-input-number
                                        v-if="config.amount_mode === 'amount'"
                                        v-model="config.grid.sell_amount"
                                        class="field-input"
                                        controls-position="right"
                                        :min="1"
                                        :max="100000"
                                        :step="10"
                                        :precision="2"
                                    />
                                    <el-input-number
                                        v-else
                                        v-model="config.grid.sell_percent"
                                        class="field-input"
                                        controls-position="right"
                                        :min="0"
                                        :max="100"
                                        :step="0.1"
                                        :precision="2"
                                    />
                                </el-form-item>
                            </el-col>

                            <el-col :span="24">
                                <el-form-item label="订单规模倍率">
                                    <el-input-number
                                        v-model="config.grid.order_scale"
                                        class="field-input"
                                        controls-position="right"
                                        :min="0.1"
                                        :max="10"
                                        :step="0.1"
                                        :precision="2"
                                    />
                                </el-form-item>
                            </el-col>
                        </el-row>
                    </el-form>
                </el-card>
            </el-col>
        </el-row>
        <!-- ==================== 单交易对持仓限制 ==================== -->
        <el-card class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">单交易对持仓限制</span>
                    <span class="card-head__meta">
                        <el-text type="info" size="small">
                            超限后仅停止该交易对的 DCA 与网格加仓
                        </el-text>
                    </span>
                </div>
            </template>

            <el-alert
                class="section-alert"
                type="warning"
                :closable="false"
                show-icon>
                该交易对保证金占用超过总资金比例后，停止 DCA 与网格加仓；止盈、止损、趋势加仓等逻辑不受影响
            </el-alert>

            <el-form class="compact-form" label-width="140px" size="small">
                <el-row :gutter="12">
                    <el-col :span="8">
                        <el-form-item label="启用限制">
                            <el-switch v-model="config.pair_max_position.enable" />
                        </el-form-item>
                    </el-col>
                    <el-col :span="8">
                        <el-form-item label="最大持仓占比%">
                            <el-input-number
                                v-model="config.pair_max_position.percent"
                                class="field-input"
                                controls-position="right"
                                :min="1"
                                :max="100"
                                :step="1"
                                :precision="2"
                                :disabled="!config.pair_max_position.enable"
                            />
                        </el-form-item>
                    </el-col>
                </el-row>
            </el-form>
        </el-card>

        <!-- ==================== HTF 趋势过滤 ==================== -->
        <el-card class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">HTF 趋势过滤</span>
                    <span class="card-head__meta">
                        <el-text type="info" size="small">
                            大周期趋势不利时暂停买入
                        </el-text>
                    </span>
                </div>
            </template>

            <el-alert
                class="section-alert"
                type="warning"
                :closable="false"
                show-icon>
                {{ config.side === 'long'
                    ? 'HTF 空头排列（快<中<慢）时暂停买入；减仓、止损不受影响'
                    : 'HTF 多头排列（快>中>慢）时暂停买入；减仓、止损不受影响' }}
                （EMA 参数复用「指标配置」中的快/中/慢）
            </el-alert>

            <el-form class="compact-form" label-width="140px" size="small">
                <el-row :gutter="12">
                    <el-col :span="8">
                        <el-form-item label="启用">
                            <el-switch v-model="config.htf_trend_filter.enable" />
                        </el-form-item>
                    </el-col>

                    <el-col :span="8">
                        <el-form-item label="HTF 周期">
                            <el-select
                                v-model="config.htf_trend_filter.timeframe"
                                class="field-input"
                                :disabled="!config.htf_trend_filter.enable">
                                <el-option label="4h" value="4h" />
                                <el-option label="12h" value="12h" />
                                <el-option label="1d" value="1d" />
                            </el-select>
                        </el-form-item>
                    </el-col>
                </el-row>

                <el-divider content-position="left">保护范围</el-divider>

                <el-row :gutter="12">
                    <el-col :span="8">
                        <el-form-item label="开仓">
                            <el-switch
                                v-model="config.htf_trend_filter.protect_entry"
                                :disabled="!config.htf_trend_filter.enable" />
                        </el-form-item>
                    </el-col>

                    <el-col :span="8">
                        <el-form-item label="DCA 加仓">
                            <el-switch
                                v-model="config.htf_trend_filter.protect_dca"
                                :disabled="!config.htf_trend_filter.enable" />
                        </el-form-item>
                    </el-col>

                    <el-col :span="8">
                        <el-form-item label="网格加仓">
                            <el-switch
                                v-model="config.htf_trend_filter.protect_grid"
                                :disabled="!config.htf_trend_filter.enable" />
                        </el-form-item>
                    </el-col>
                </el-row>

                <el-row :gutter="12">
                    <el-col :span="8">
                        <el-form-item label="浮盈回补">
                            <el-switch
                                v-model="config.htf_trend_filter.protect_rebuy"
                                :disabled="!config.htf_trend_filter.enable" />
                        </el-form-item>
                    </el-col>

                    <el-col :span="8">
                        <el-form-item label="趋势加仓">
                            <el-switch
                                v-model="config.htf_trend_filter.protect_trend"
                                :disabled="!config.htf_trend_filter.enable" />
                        </el-form-item>
                    </el-col>
                </el-row>
            </el-form>
        </el-card>
    </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'

const props = defineProps({
    config: Object,
    tradeInfo: Object
})

if (props.config && !props.config.amount_mode) {
    props.config.amount_mode = "percent"
}

const emit = defineEmits(['save'])

const changeEntrySignal = (type, val) => {
    const entry = props.config.entry

    // Pump 保护是独立开关，不参与“至少保留一个”校验
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
        // 补仓：按模式初始化
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
        // 不补仓：统一 100%，跟金额模式无关
        props.config.tp.reduce_percent = 100
    }
}

</script>

<style scoped>
/* ==================== 整体布局 ==================== */
.strategy-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.section-card {
    border-radius: 12px;
}

.section-card :deep(.el-card__header) {
    padding: 10px 14px;
}

.section-card :deep(.el-card__body) {
    padding: 14px;
    overflow-x: hidden;
}

.section-card :deep(.el-row) {
    margin-left: 0 !important;
    margin-right: 0 !important;
}

.section-card :deep(.el-col) {
    min-width: 0;
}

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
    justify-content: flex-end;
    gap: 8px;
    flex-wrap: wrap;
    text-align: right;
}

/* ==================== 表单通用 ==================== */
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

.dca-level-form :deep(.el-form-item__label) {
    line-height: 28px;
    font-size: 13px;
    white-space: nowrap;
}

/* 输入控件：固定 140px，不撑满 */
.field-input {
    width: 140px;
    max-width: 100%;
}

/* el-select 也用同样宽度 */
.compact-form :deep(.el-select.field-input) {
    width: 140px;
}

/* el-input-number 内部数字区允许收缩 */
.field-input :deep(.el-input__wrapper) {
    padding-left: 6px;
    padding-right: 30px;
}

/* ==================== 分隔线 ==================== */
.section-card :deep(.el-divider) {
    margin: 12px 0 10px;
}

.section-card :deep(.el-divider__text) {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    background: var(--el-bg-color);
    padding: 0 8px;
}

/* ==================== 开仓信号 ==================== */
.entry-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
}

.signal-card {
    background: var(--el-fill-color-extra-light);
    border: 1px solid var(--el-border-color-light);
    border-radius: 10px;
    padding: 12px;
    min-width: 0;
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

/* ==================== ROI 列表 ==================== */
.roi-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
    gap: 8px;
}

.roi-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    border: 1px solid var(--el-border-color-light);
    border-radius: 6px;
    background: var(--el-fill-color-extra-light);
    min-width: 0;
}

.roi-index {
    width: 20px;
    text-align: center;
    font-weight: 700;
    font-size: 12px;
    color: var(--el-text-color-secondary);
    flex: none;
}

.roi-input {
    flex: 1;
    min-width: 0;
}

.roi-input :deep(.el-input__wrapper) {
    padding-left: 4px;
    padding-right: 24px;
}

.roi-input :deep(.el-input__inner) {
    font-size: 12px;
    text-align: left;
}

.roi-input :deep(.el-input-number__increase),
.roi-input :deep(.el-input-number__decrease) {
    width: 20px;
}

.roi-delete {
    width: 20px;
    padding: 0;
    flex: none;
    font-size: 12px;
}

/* ==================== 概览描述 ==================== */
.trade-descriptions :deep(.el-descriptions__label) {
    width: 96px;
    white-space: nowrap;
}

.trade-descriptions :deep(.el-descriptions__content) {
    word-break: break-word;
}

.roi-chip-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.note-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.empty-placeholder {
    display: inline-block;
    width: 100%;
    height: 20px;
}

/* ==================== 提示框 ==================== */
.section-alert {
    margin-bottom: 12px;
}

/* ==================== 面板网格 ==================== */
.panel-grid {
    margin: 0 !important;
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

</style>