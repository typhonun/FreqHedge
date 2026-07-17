<template>
    <div
        v-if="config?.entry"
        class="strategy-panel"
    >
        <el-card
            v-if="tradeInfo"
            class="section-card"
        >
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">交易信息</span>
                    <span class="card-head__meta">
                        <el-text
                            type="info"
                            size="small"
                        >
                            源码逻辑 + SQLite / JSON 配置
                        </el-text>
                    </span>
                </div>
            </template>

            <el-descriptions
                class="trade-descriptions"
                :column="2"
                border
                size="small"
            >
                <el-descriptions-item label="方向">
                    <el-tag
                        :type="config.side === 'long' ? 'success' : 'danger'"
                        size="small"
                    >
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

                <el-descriptions-item label="开仓信号" :span="2">
                    {{ tradeInfo.entrySignal }}
                </el-descriptions-item>

                <el-descriptions-item label="趋势加仓" :span="2">
                    {{ tradeInfo.trendSignal }}
                </el-descriptions-item>

                <el-descriptions-item label="DCA规则" :span="2">
                    {{ tradeInfo.dcaSignal }}
                </el-descriptions-item>

                <el-descriptions-item label="止盈/回补" :span="2">
                    {{ tradeInfo.tpSignal }}
                </el-descriptions-item>

                <el-descriptions-item label="网格规则" :span="2">
                    {{ tradeInfo.gridSignal }}
                </el-descriptions-item>

                <el-descriptions-item label="ROI阶梯":span="2">
                    <div class="roi-chip-wrap">
                        <el-tag
                            v-for="tier in tradeInfo.roiLevels"
                            :key="tier.label"
                            size="small"
                            type="info"
                            effect="plain"
                        >
                            {{ tier.label }}
                        </el-tag>
                    </div>
                </el-descriptions-item>

                <el-descriptions-item label="交易开关">
                    {{ tradeInfo.positionAdjustment }} / {{ tradeInfo.trailingStop }}
                </el-descriptions-item>

                <el-descriptions-item label="退出信号">
                    {{ tradeInfo.exitSignal }}
                </el-descriptions-item>
            </el-descriptions>

            <el-alert
                class="section-alert"
                type="info"
                :closable="false"
            >
                <div class="note-list">
                    <div
                        v-for="note in tradeInfo.notes"
                        :key="note"
                    >
                        {{ note }}
                    </div>
                </div>
            </el-alert>
        </el-card>

        <el-card class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">入场配置</span>
                    <span class="card-head__meta">
                        <el-text
                            type="info"
                            size="small"
                        >
                            主开仓以 BB + RSI 为准
                        </el-text>
                    </span>
                </div>
            </template>

            <div class="entry-grid">
                <section class="signal-card">
                    <div class="signal-head">
                        <div>
                            <div class="signal-name">RSI</div>
                            <div class="signal-subtitle">
                                {{
                                    config.side === "long"
                                        ? "低位确认后入场"
                                        : "高位确认后入场"
                                }}
                            </div>
                        </div>

                        <el-switch v-model="config.entry.rsi.enable" />
                    </div>

                    <el-form
                        class="compact-form"
                        label-width="54px"
                        size="small"
                    >
                        <el-form-item label="周期">
                            <el-input-number
                                v-model="config.entry.rsi.period"
                                class="compact-input-number"
                                controls-position="right"
                                :min="1"
                            />
                        </el-form-item>

                        <el-form-item label="阈值">
                            <el-input-number
                                v-model="config.entry.rsi.value"
                                class="compact-input-number"
                                controls-position="right"
                            />
                        </el-form-item>
                    </el-form>
                </section>

                <section class="signal-card">
                    <div class="signal-head">
                        <div>
                            <div class="signal-name">MACD</div>
                            <div class="signal-subtitle">
                                趋势与动能共振确认
                            </div>
                        </div>

                        <el-switch v-model="config.entry.macd.enable" />
                    </div>

                    <el-form
                        class="compact-form"
                        label-width="54px"
                        size="small"
                    >
                        <el-form-item label="快线">
                            <el-input-number
                                v-model="config.entry.macd.fast"
                                class="compact-input-number"
                                controls-position="right"
                                :min="1"
                            />
                        </el-form-item>

                        <el-form-item label="慢线">
                            <el-input-number
                                v-model="config.entry.macd.slow"
                                class="compact-input-number"
                                controls-position="right"
                                :min="1"
                            />
                        </el-form-item>

                        <el-form-item label="信号">
                            <el-input-number
                                v-model="config.entry.macd.signal"
                                class="compact-input-number"
                                controls-position="right"
                                :min="1"
                            />
                        </el-form-item>
                    </el-form>
                </section>

                <section class="signal-card">
                    <div class="signal-head">
                        <div>
                            <div class="signal-name">Bollinger</div>
                            <div class="signal-subtitle">
                                价格触及下轨时允许入场
                            </div>
                        </div>

                        <el-switch v-model="config.entry.bb.enable" />
                    </div>

                    <el-form
                        class="compact-form"
                        label-width="54px"
                        size="small"
                    >
                        <el-form-item label="周期">
                            <el-input-number
                                v-model="config.entry.bb.period"
                                class="compact-input-number"
                                controls-position="right"
                                :min="1"
                            />
                        </el-form-item>

                        <el-form-item label="STD">
                            <el-input-number
                                v-model="config.entry.bb.std"
                                class="compact-input-number"
                                controls-position="right"
                                :min="0.1"
                                :step="0.1"
                            />
                        </el-form-item>
                    </el-form>
                </section>

                <section class="signal-card">
                    <div class="signal-head">
                        <div>
                            <div class="signal-name">Volume</div>
                            <div class="signal-subtitle">
                                量能放大时增强突破有效性
                            </div>
                        </div>

                        <el-switch v-model="config.entry.volume.enable" />
                    </div>

                    <el-form
                        class="compact-form"
                        label-width="54px"
                        size="small"
                    >
                        <el-form-item label="状态">
                            <el-text type="info">作为辅助过滤条件</el-text>
                        </el-form-item>
                    </el-form>
                </section>
            </div>
        </el-card>

        <el-card class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">ROI止盈规则</span>
                    <span class="card-head__meta">
                        <el-text
                            type="info"
                            size="small"
                        >
                            达到目标收益后分批止盈
                        </el-text>

                        <el-button
                            size="small"
                            type="success"
                            plain
                            @click="addRoi"
                        >
                            新增规则
                        </el-button>
                    </span>
                </div>
            </template>

            <el-alert
                class="section-alert"
                type="success"
                :closable="false"
                show-icon
            >
                持仓达到指定时间后，收益率达到目标值触发 TP
            </el-alert>

            <div class="roi-list">
                <div
                    v-for="(roi, index) in config.tp.roi_levels"
                    :key="index"
                    class="roi-row"
                >
                    <div class="roi-index">
                        {{ index + 1 }}
                    </div>

                    <el-input-number
                        v-model="roi.minutes"
                        class="roi-input"
                        controls-position="right"
                        :min="0"
                        size="small"
                    />

                    <el-input-number
                        v-model="roi.roi"
                        class="roi-input"
                        controls-position="right"
                        size="small"
                    />

                    <el-button
                        type="danger"
                        size="small"
                        plain
                        @click="removeRoi(index)"
                    >
                        删除
                    </el-button>
                </div>
            </div>
        </el-card>

        <el-row
            class="panel-grid"
            :gutter="12"
        >
            <el-col :span="12">
                <el-card class="section-card">
                    <template #header>
                        <div class="card-head">
                            <span class="card-head__title">TP动作</span>
                            <span class="card-head__meta">
                                <el-text
                                    type="info"
                                    size="small"
                                >
                                    减仓后自动补回目标仓位
                                </el-text>
                            </span>
                        </div>
                    </template>

                    <el-alert
                        class="section-alert"
                        type="info"
                        :closable="false"
                    >
                        达到 ROI 后减仓，并自动补回目标仓位
                    </el-alert>

                    <el-form
                        class="compact-form"
                        label-width="128px"
                        size="small"
                    >
                        <el-form-item label="减仓比例%">
                            <el-input-number
                                v-model="config.tp.reduce_percent"
                                class="compact-input-number"
                                controls-position="right"
                                :min="0"
                                :max="100"
                            />
                        </el-form-item>

                        <el-form-item label="自动补仓">
                            <el-switch v-model="config.tp.rebuy_enable" />
                        </el-form-item>

                        <el-form-item label="目标仓位占总资金%">
                            <el-input-number
                                v-model="config.tp.target_wallet_percent"
                                class="compact-input-number"
                                controls-position="right"
                                :min="0"
                                :max="100"
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
                                <el-text
                                    type="info"
                                    size="small"
                                >
                                    达到设定亏损后强制平仓
                                </el-text>
                            </span>
                        </div>
                    </template>

                    <el-alert
                        class="section-alert"
                        type="warning"
                        :closable="false"
                    >
                        达到设定亏损比例后强制平仓
                    </el-alert>

                    <el-form
                        class="compact-form"
                        label-width="102px"
                        size="small"
                    >
                        <el-form-item label="启用止损">
                            <el-switch v-model="config.sl.enable" />
                        </el-form-item>

                        <el-form-item label="止损百分比">
                            <el-input-number
                                v-model="config.sl.stoploss"
                                class="compact-input-number"
                                controls-position="right"
                            />
                        </el-form-item>
                    </el-form>
                </el-card>
            </el-col>
        </el-row>

        <el-card class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">DCA配置</span>
                    <span class="card-head__meta">
                        <el-text
                            type="info"
                            size="small"
                        >
                            回撤满足条件时分层补仓
                        </el-text>

                        <el-button
                            size="small"
                            type="success"
                            plain
                            @click="addDca"
                        >
                            新增DCA
                        </el-button>
                    </span>
                </div>
            </template>

            <el-alert
                class="section-alert"
                type="warning"
                :closable="false"
                show-icon
            >
                回撤达到阈值且满足 RSI 或 KDJ 条件时加仓
            </el-alert>

            <el-form
                class="compact-form dca-top-form"
                label-width="110px"
                size="small"
            >
                <el-row :gutter="12">
                    <el-col :span="12">
                        <el-form-item label="启用DCA">
                            <el-switch v-model="config.dca.enable" />
                        </el-form-item>
                    </el-col>

                    <el-col :span="12">
                        <el-form-item label="最大加仓次数">
                            <el-input-number
                                v-model="config.dca.max_count"
                                class="compact-input-number"
                                controls-position="right"
                                :min="1"
                            />
                        </el-form-item>
                    </el-col>

                    <el-col :span="12">
                        <el-form-item label="DCA冷却时间">
                            <el-input-number
                                v-model="config.dca.cooldown_minutes"
                                class="compact-input-number"
                                controls-position="right"
                                :min="0"
                            />
                        </el-form-item>
                    </el-col>

                    <el-col :span="12">
                        <el-form-item label="条件模式">
                            <el-select
                                v-model="config.dca.condition"
                                class="full-width-control"
                            >
                                <el-option
                                    label="RSI或J满足"
                                    value="or"
                                />

                                <el-option
                                    label="RSI且J满足"
                                    value="and"
                                />
                            </el-select>
                        </el-form-item>
                    </el-col>
                </el-row>
            </el-form>

            <el-table
                :data="config.dca.levels"
                border
                size="small"
                style="width:100%"
            >
                <el-table-column label="回撤%">
                    <template #default="{ row }">
                        <el-input-number
                            v-model="row.drawdown"
                            class="table-input-number"
                            controls-position="right"
                            size="small"
                        />
                    </template>
                </el-table-column>

                <el-table-column
                    :label="config.side === 'long' ? 'RSI <' : 'RSI >'"
                >
                    <template #default="{ row }">
                        <el-input-number
                            v-model="row.rsi_limit"
                            class="table-input-number"
                            controls-position="right"
                            size="small"
                        />
                    </template>
                </el-table-column>

                <el-table-column
                    :label="config.side === 'long' ? 'J值 <' : 'J值 >'"
                >
                    <template #default="{ row }">
                        <el-input-number
                            v-model="row.j_limit"
                            class="table-input-number"
                            controls-position="right"
                            size="small"
                        />
                    </template>
                </el-table-column>

                <el-table-column label="倍率">
                    <template #default="{ row }">
                        <el-input-number
                            v-model="row.amount"
                            class="table-input-number"
                            controls-position="right"
                            :step="0.1"
                            :min="0"
                            size="small"
                        />
                    </template>
                </el-table-column>

                <el-table-column
                    width="90"
                    label="操作"
                >
                    <template #default="{ $index }">
                        <el-button
                            type="danger"
                            size="small"
                            plain
                            @click="removeDca($index)"
                        >
                            删除
                        </el-button>
                    </template>
                </el-table-column>
            </el-table>
        </el-card>

        <el-row
            class="panel-grid"
            :gutter="12"
        >
            <el-col :span="12">
                <el-card class="section-card">
                    <template #header>
                        <div class="card-head">
                            <span class="card-head__title">
                                趋势加仓
                            </span>

                            <span class="card-head__meta">
                                <el-text
                                    type="info"
                                    size="small"
                                >
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

                    <el-form
                        class="compact-form"
                        label-width="120px"
                        size="small"
                    >
                        <el-row :gutter="12">
                            <el-col :span="12">
                                <el-form-item label="启用趋势加仓">
                                    <el-switch v-model="config.trend_add.enable" />
                                </el-form-item>
                            </el-col>

                            <el-col :span="12">
                                <el-form-item label="最大次数">
                                    <el-input-number
                                        v-model="config.trend_add.max_count"
                                        :min="1"
                                    />
                                </el-form-item>
                            </el-col>

                            <el-col :span="12">
                                <el-form-item label="加仓比例%">
                                    <el-input-number
                                        v-model="config.trend_add.amount_percent"
                                        :min="0"
                                        :max="100"
                                    />
                                </el-form-item>
                            </el-col>

                            <el-col :span="12">
                                <el-form-item label="条件模式">
                                    <el-select
                                        v-model="config.trend_add.condition"
                                    >
                                        <el-option
                                            label="全部满足 AND"
                                            value="and"
                                        />

                                        <el-option
                                            label="任意满足 OR"
                                            value="or"
                                        />
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
                                    v-model="config.trend_add.macd.enable"
                                />

                            </el-form-item>


                        </el-col>


                        <el-col :span="8">

                            <el-form-item label="KDJ">

                                <el-switch
                                    v-model="config.trend_add.kdj.enable"
                                />

                            </el-form-item>


                        </el-col>


                        <el-col :span="8">

                            <el-form-item label="EMA">

                                <el-switch
                                    v-model="config.trend_add.ema.enable"
                                />

                            </el-form-item>


                        </el-col>


                    </el-row>

                    <el-divider>
                        MACD参数
                    </el-divider>


                    <el-row :gutter="12">


                        <el-col :span="8">

                            <el-form-item label="DIF周期">

                                <el-input-number

                                    v-model="
                                    config.trend_add.macd.fast
                                    "

                                    :min="1"

                                    :max="100"

                                    controls-position="right"

                                />


                            </el-form-item>


                        </el-col>



                        <el-col :span="8">

                            <el-form-item label="DEA周期">


                                <el-input-number

                                    v-model="
                                    config.trend_add.macd.slow
                                    "

                                    :min="1"

                                    :max="200"

                                    controls-position="right"

                                />


                            </el-form-item>


                        </el-col>



                        <el-col :span="8">

                            <el-form-item label="Signal">


                                <el-input-number

                                    v-model="
                                    config.trend_add.macd.signal
                                    "

                                    :min="1"

                                    :max="50"

                                    controls-position="right"

                                />


                            </el-form-item>


                        </el-col>


                    </el-row>

                    <el-divider>
                        KDJ参数
                    </el-divider>


                    <el-row :gutter="12">


                        <el-col :span="8">

                            <el-form-item label="FastK">

                                <el-input-number

                                    v-model="
                                    config.trend_add.kdj.fastk
                                    "

                                    :min="1"

                                    :max="50"

                                    controls-position="right"

                                />

                            </el-form-item>

                        </el-col>



                        <el-col :span="8">

                            <el-form-item label="SlowK">

                                <el-input-number

                                    v-model="
                                    config.trend_add.kdj.slowk
                                    "

                                    :min="1"

                                    :max="50"

                                    controls-position="right"

                                />

                            </el-form-item>

                        </el-col>



                        <el-col :span="8">

                            <el-form-item label="SlowD">

                                <el-input-number

                                    v-model="
                                    config.trend_add.kdj.slowd
                                    "

                                    :min="1"

                                    :max="50"

                                    controls-position="right"

                                />

                            </el-form-item>

                        </el-col>


                    </el-row>

                    <el-divider>
                        EMA参数
                    </el-divider>
                    <el-row :gutter="12">
                        <el-col :span="8">
                            <el-form-item label="EMA快">
                                <el-input-number
                                    v-model="config.trend_add.ema.fast"
                                    :min="1"
                                    :max="200"
                                    controls-position="right"
                                />
                            </el-form-item>
                        </el-col>

                        <el-col :span="8">
                            <el-form-item label="EMA中">
                                <el-input-number
                                    v-model="config.trend_add.ema.mid"
                                    :min="1"
                                    :max="300"
                                    controls-position="right"
                                />
                            </el-form-item>
                        </el-col>

                        <el-col :span="8">
                            <el-form-item label="EMA慢">
                                <el-input-number
                                    v-model="config.trend_add.ema.slow"
                                    :min="1"
                                    :max="500"
                                    controls-position="right"
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

                        <el-form
                            label-width="120px"
                            size="small"
                        >
                            <el-form-item label="启用KDJ减仓">

                            <el-switch
                                v-model="config.trend_add.kdj_reduce.enable"
                                :disabled="!config.trend_add.enable"
                            />

                            </el-form-item>


                            <el-form-item label="减仓比例%">

                            <el-input-number

                                v-model="
                                config.trend_add.kdj_reduce.reduce_percent
                                "

                                :disabled="
                                !config.trend_add.enable ||
                                !config.trend_add.kdj_reduce.enable
                                "

                                :min="0"

                                :max="100"

                                controls-position="right"
                            />

                            </el-form-item>
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
                                <el-text
                                    type="info"
                                    size="small"
                                >
                                    价格区间内自动分层挂单
                                </el-text>
                            </span>
                        </div>
                    </template>

                    <el-alert
                        class="section-alert"
                        type="warning"
                        :closable="false"
                    >
                        启用后将在当前仓位下方自动挂网格单</el-alert>

                    <el-form
                        class="compact-form"
                        label-width="116px"
                        size="small"
                    >
                        <el-row :gutter="12">
                            <el-col :span="12">
                                <el-form-item label="启用网格">
                                    <el-switch v-model="config.grid.enable" />
                                </el-form-item>
                            </el-col>

                            <el-col :span="12">
                                <el-form-item label="冷却时间">
                                    <el-input-number
                                        v-model="config.grid.cooldown_minutes"
                                        class="compact-input-number"
                                        controls-position="right"
                                        :min="0"
                                    />
                                </el-form-item>
                            </el-col>

                            <el-col :span="12">
                                <el-form-item label="网格下沿%">
                                    <el-input-number
                                        v-model="config.grid.grid_lower"
                                        class="compact-input-number"
                                        controls-position="right"
                                    />
                                </el-form-item>
                            </el-col>

                            <el-col :span="12">
                                <el-form-item label="网格上沿%">
                                    <el-input-number
                                        v-model="config.grid.grid_upper"
                                        class="compact-input-number"
                                        controls-position="right"
                                    />
                                </el-form-item>
                            </el-col>

                            <el-col :span="12">
                                <el-form-item label="加仓占总资金%">
                                    <el-input-number
                                        v-model="config.grid.buy_percent"
                                        class="compact-input-number"
                                        controls-position="right"
                                        :min="0"
                                        :max="100"
                                    />
                                </el-form-item>
                            </el-col>

                            <el-col :span="12">
                                <el-form-item label="减仓占总资金%">
                                    <el-input-number
                                        v-model="config.grid.sell_percent"
                                        class="compact-input-number"
                                        controls-position="right"
                                        :min="0"
                                        :max="100"
                                    />
                                </el-form-item>
                            </el-col>
                        </el-row>
                    </el-form>
                </el-card>
            </el-col>
        </el-row>

        <el-card class="section-card">
            <template #header>
                <div class="card-head">
                    <span class="card-head__title">浮亏止盈</span>
                    <span class="card-head__meta">
                        <el-text
                            type="info"
                            size="small"
                        >
                            先控回撤，再锁定反弹收益
                        </el-text>
                    </span>
                </div>
            </template>

            <el-form
                class="compact-form"
                label-width="118px"
                size="small"
            >
                <el-row :gutter="12">
                    <el-col :span="12">
                        <el-form-item label="启用">
                            <el-switch v-model="config.loss_tp.enable" />
                        </el-form-item>
                    </el-col>

                    <el-col :span="12">
                        <el-form-item label="保留仓位%">
                            <el-input-number
                                v-model="config.loss_tp.target_wallet_percent"
                                class="compact-input-number"
                                controls-position="right"
                                :min="0"
                                :max="100"
                            />
                        </el-form-item>
                    </el-col>

                    <el-col :span="12">
                        <el-form-item label="触发亏损%">
                            <el-input-number
                                v-model="config.loss_tp.trigger_loss"
                                class="compact-input-number"
                                controls-position="right"
                            />
                        </el-form-item>
                    </el-col>

                    <el-col :span="12">
                        <el-form-item label="反弹幅度%">
                            <el-input-number
                                v-model="config.loss_tp.trigger_rebound"
                                class="compact-input-number"
                                controls-position="right"
                            />
                        </el-form-item>
                    </el-col>
                </el-row>
            </el-form>
        </el-card>

        <div class="save-bar">
            <el-button
                type="primary"
                size="large"
                @click="emit('save')"
            >
                保存策略
            </el-button>
        </div>
    </div>
</template>

<script setup>
const props = defineProps({
    config: Object,
    tradeInfo: Object
})

const emit = defineEmits(["save"])

const addRoi = () => {
    props.config.tp.roi_levels.push({
        minutes: 60,
        roi: 1
    })
}

const removeRoi = (index) => {
    props.config.tp.roi_levels.splice(
        index,
        1
    )
}

const addDca = () => {
    if (props.config.side === "long") {
        props.config.dca.levels.push({
            drawdown: -5,
            rsi_limit: 20,
            j_limit: 0,
            amount: 1
        })
    } else {
        props.config.dca.levels.push({
            drawdown: -5,
            rsi_limit: 80,
            j_limit: 100,
            amount: 1
        })
    }
}

const removeDca = (index) => {
    props.config.dca.levels.splice(index, 1)
}

const addTrendAdd = () => {
    props.config.trend_add.levels.push({
        profit: 2,
        rsi:
            props.config.side === "long"
                ? 60
                : 40,
        amount: 0.5
    })
}

const removeTrendAdd = (index) =>{
    props.config.trend_add.levels.splice(
        index,
        1
    )
}

const syncKdjReduce = () => {
    if(!config.trend_add.enable) {
        config.trend_add.kdj_reduce.enable = false
    }
}
</script>

<style scoped>
.strategy-panel{
    display:flex;
    flex-direction:column;
    gap:12px;
}

.section-card{
    border-radius:12px;
}

.section-card :deep(.el-card__header){
    padding:10px 14px;
}

.section-card :deep(.el-card__body){
    padding:14px;
}

.card-head{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    width:100%;
}

.card-head__title{
    font-size:14px;
    font-weight:600;
    color:var(--el-text-color-primary);
}

.card-head__meta{
    display:flex;
    align-items:center;
    justify-content:flex-end;
    gap:8px;
    flex-wrap:wrap;
    text-align:right;
}

.entry-grid{
    display:grid;
    grid-template-columns:repeat(2, minmax(0, 1fr));
    gap:12px;
}

.signal-card{
    background:var(--el-fill-color-extra-light);
    border:1px solid var(--el-border-color-light);
    border-radius:10px;
    padding:12px;
    min-width:0;
}

.signal-head{
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    gap:10px;
    margin-bottom:8px;
}

.signal-name{
    font-size:13px;
    font-weight:600;
    line-height:1.2;
}

.signal-subtitle{
    margin-top:2px;
    font-size:12px;
    color:var(--el-text-color-secondary);
    line-height:1.4;
}

.compact-form :deep(.el-form-item){
    margin-bottom:8px;
}

.compact-form :deep(.el-form-item:last-child){
    margin-bottom:0;
}

.compact-form :deep(.el-form-item__label){
    line-height:28px;
}

.compact-form :deep(.el-form-item__content){
    line-height:28px;
}

.compact-input-number,
.full-width-control{
    width:100%;
}

.section-alert{
    margin-bottom:12px;
}

.trade-descriptions :deep(.el-descriptions__label){
    width:96px;
    white-space:nowrap;
}

.trade-descriptions :deep(.el-descriptions__content){
    word-break:break-word;
}

.roi-chip-wrap{
    display:flex;
    flex-wrap:wrap;
    gap:6px;
}

.note-list{
    display:flex;
    flex-direction:column;
    gap:4px;
}

.roi-list{
    display:flex;
    flex-direction:column;
    gap:8px;
}

.roi-row{
    display:grid;
    grid-template-columns:36px 1fr 1fr auto;
    gap:8px;
    align-items:center;
    padding:10px 12px;
    border:1px solid var(--el-border-color-lighter);
    border-radius:10px;
    background:var(--el-fill-color-extra-light);
}

.roi-index{
    width:28px;
    height:28px;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    background:var(--el-color-primary-light-9);
    color:var(--el-color-primary);
    font-size:12px;
    font-weight:600;
}

.roi-input{
    width:100%;
}

.panel-grid{
    margin:0;
}

.table-input-number{
    width:100%;
    min-width:78px;
}

.save-bar{
    display:flex;
    justify-content:flex-end;
    padding-top:4px;
}

@media (max-width: 1200px){
    .entry-grid{
        grid-template-columns:1fr;
    }
}

@media (max-width: 960px){
    .panel-grid :deep(.el-col){
        max-width:100%;
        flex:0 0 100%;
    }

    .roi-row{
        grid-template-columns:28px 1fr;
    }
}
</style>