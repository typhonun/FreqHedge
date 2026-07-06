<template>

<div v-if="config?.entry">

<!-- 入场配置 -->

<el-card class="mb20">

    <template #header>
        入场配置
    </template>

    <el-row :gutter="15">

        <!-- RSI -->
        <el-col :span="8">

            <el-card shadow="hover">

                <template #header>
                    RSI

                    <el-alert
                        :title="
                            config.side === 'long'
                            ? `RSI ≤ ${config.entry.rsi.value} 时允许入场`
                            : `RSI ≥ ${config.entry.rsi.value} 时允许入场`
                        "
                        type="info"
                        :closable="false"
                    />
                </template>

                <el-form label-width="80px">

                    <el-form-item label="启用">
                        <el-switch
                            v-model="config.entry.rsi.enable"
                        />
                    </el-form-item>

                    <el-form-item label="周期">
                        <el-input-number
                            v-model="config.entry.rsi.period"
                        />
                    </el-form-item>

                    <el-form-item label="阈值">
                        <el-input-number
                            v-model="config.entry.rsi.value"
                        />
                    </el-form-item>

                </el-form>

            </el-card>

        </el-col>

        <!-- BB -->
        <el-col :span="8">

            <el-card shadow="hover">

                <template #header>
                    Bollinger

                    <el-text
                        size="small"
                        type="info"
                    >
                        价格触及下轨时允许入场
                    </el-text>

                </template>

                <el-form label-width="80px">

                    <el-form-item label="启用">
                        <el-switch
                            v-model="config.entry.bb.enable"
                        />
                    </el-form-item>

                    <el-form-item label="周期">
                        <el-input-number
                            v-model="config.entry.bb.period"
                        />
                    </el-form-item>

                    <el-form-item label="STD">
                        <el-input-number
                            v-model="config.entry.bb.std"
                        />
                    </el-form-item>

                </el-form>

            </el-card>

        </el-col>

    </el-row>

</el-card>


<!-- ROI止盈 -->

<el-card class="mb20">

    <template #header>

        ROI止盈规则

        <el-button
            style="float:right"
            size="small"
            type="success"
            @click="addRoi"
        >
            新增规则
        </el-button>

    </template>

    <el-alert
        type="success"
        :closable="false"
        show-icon
    >
        持仓达到指定时间后，
        收益率达到目标值触发TP
    </el-alert>

    <div
        v-for="(roi,index) in config.tp.roi_levels"
        :key="index"
        class="rule-box"
    >

        <el-row :gutter="10">

            <el-col :span="8">

                <el-form-item label="持仓分钟">

                    <el-input-number
                        v-model="roi.minutes"
                    />

                </el-form-item>

            </el-col>

            <el-col :span="8">

                <el-form-item label="收益率%">

                    <el-input-number
                        v-model="roi.roi"
                    />

                </el-form-item>

            </el-col>

            <el-col :span="4">

                <el-button
                    type="danger"
                    @click="removeRoi(index)"
                >
                    删除
                </el-button>

            </el-col>

        </el-row>

    </div>

</el-card>


<!-- TP动作 -->

<el-card class="mb20">

    <template #header>
        TP动作
    </template>

    <el-alert
        type="info"
        :closable="false"
    >
        达到ROI后减仓，
        并自动补回目标仓位
    </el-alert>

    <el-form label-width="160px">

        <el-form-item label="减仓比例%">

            <el-input-number
                v-model="config.tp.reduce_percent"
            />

        </el-form-item>

        <el-form-item label="自动补仓">

            <el-switch
                v-model="config.tp.rebuy_enable"
            />

        </el-form-item>

        <el-form-item label="目标仓位占总资金%">

            <el-input-number
                v-model="
                    config.tp.target_wallet_percent
                "
            />

        </el-form-item>

    </el-form>

</el-card>


<!-- DCA -->
<el-card class="mb20">

    <template #header>

        DCA配置

        <el-button
            style="float:right"
            size="small"
            type="success"
            @click="addDca"
        >
            新增DCA
        </el-button>

    </template>

    <el-alert
        type="warning"
        :closable="false"
        show-icon
    >
        回撤达到阈值且满足 RSI 或 KDJ 条件时加仓
    </el-alert>

    <el-form label-width="140px">

        <el-form-item label="启用DCA">
            <el-switch
                v-model="config.dca.enable"
            />
        </el-form-item>

        <el-form-item label="最大加仓次数">
            <el-input-number
                v-model="config.dca.max_count"
            />
        </el-form-item>

        <el-form-item label="DCA冷却时间">
            <el-input-number
                v-model="config.dca.cooldown_minutes"
            />
        </el-form-item>

        <el-form-item label="条件模式">

            <el-select
                v-model="config.dca.condition"
                style="width:120px"
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

    </el-form>

    <el-table
        :data="config.dca.levels"
        border
        style="width:100%"
    >

        <el-table-column
            label="回撤%"
        >

            <template #default="{row}">

                <el-input-number
                    v-model="row.drawdown"
                />

            </template>

        </el-table-column>

        <el-table-column
            :label="
                config.side === 'long'
                ? 'RSI <'
                : 'RSI >'
            "
        >

            <template #default="{row}">

                <el-input-number
                    v-model="row.rsi_limit"
                />

            </template>

        </el-table-column>

        <el-table-column
            :label="
                config.side === 'long'
                ? 'J值 <'
                : 'J值 >'
            "
        >

            <template #default="{row}">

                <el-input-number
                    v-model="row.j_limit"
                />

            </template>

        </el-table-column>

        <el-table-column
            label="倍率"
        >

            <template #default="{row}">

                <el-input-number
                    v-model="row.amount"
                    :step="0.1"
                />

            </template>

        </el-table-column>

        <el-table-column
            width="100"
            label="操作"
        >

            <template #default="{ $index }">

                <el-button
                    type="danger"
                    size="small"
                    @click="removeDca($index)"
                >
                    删除
                </el-button>

            </template>

        </el-table-column>

    </el-table>

</el-card>


<!-- Trend Add -->
<el-card class="mb20">

    <template #header>

        趋势加仓

        <el-button
            style="float:right"
            size="small"
            type="success"
            @click="addTrendAdd"
        >
            新增规则
        </el-button>

    </template>

    <el-alert
        type="success"
        :closable="false"
        show-icon
    >
        {{
            config.side === 'long'
            ? '盈利状态下顺势做多加仓'
            : '盈利状态下顺势做空加仓'
        }}
    </el-alert>

    <el-form
        label-width="140px"
    >

        <el-form-item
            label="启用趋势加仓"
        >

            <el-switch
                v-model="
                    config.trend_add.enable
                "
            />

        </el-form-item>

        <el-form-item
            label="最大次数"
        >

            <el-input-number
                v-model="
                    config.trend_add.max_count
                "
            />

        </el-form-item>

    </el-form>

    <el-table
        :data="
            config.trend_add.levels
        "
        border
    >

        <el-table-column
            label="盈利%"
        >

            <template #default="{row}">

                <el-input-number
                    v-model="row.profit"
                />

            </template>

        </el-table-column>

        <el-table-column
            :label="
                config.side === 'long'
                ? 'RSI >'
                : 'RSI <'
            "
        >

            <template #default="{row}">

                <el-input-number
                    v-model="row.rsi"
                />

            </template>

        </el-table-column>

        <el-table-column
            label="加仓倍率"
        >

            <template #default="{row}">

                <el-input-number
                    v-model="row.amount"
                    :step="0.1"
                />

            </template>

        </el-table-column>

        <el-table-column
            label="操作"
            width="100"
        >

            <template #default="{ $index }">

                <el-button
                    type="danger"
                    size="small"
                    @click="
                        removeTrendAdd(
                            $index
                        )
                    "
                >
                    删除
                </el-button>

            </template>

        </el-table-column>

    </el-table>

</el-card>


<!-- Grid -->

<el-card class="mb20">

    <template #header>
        网格配置

        <el-alert
            type="warning"
            :closable="false"
        >
            启用后将在当前仓位下方自动挂网格单
        </el-alert>

    </template>

    <el-form label-width="120px">

        <el-form-item label="启用网格">
            <el-switch
                v-model="config.grid.enable"
            />
        </el-form-item>

        <el-form-item label="网格买入阈值%">
            <el-input-number
                v-model="config.grid.grid_lower"
            />
        </el-form-item>

        <el-form-item label="网格卖出阈值%">
            <el-input-number
                v-model="config.grid.grid_upper"
            />
        </el-form-item>

        <el-form-item label="加仓占总资金%">

            <el-input-number
                v-model="config.grid.buy_percent"
            />

        </el-form-item>

        <el-form-item label="减仓占总资金%">

            <el-input-number
                v-model="config.grid.sell_percent"
            />

        </el-form-item>

        <el-form-item label="冷却时间">

            <el-input-number
                v-model="config.grid.cooldown_minutes"
            />

        </el-form-item>

    </el-form>

</el-card>


<el-card class="mb20">

    <template #header>
        浮亏止盈
    </template>

    <el-form label-width="160px">

        <el-form-item label="启用">

            <el-switch
                v-model="config.loss_tp.enable"
            />

        </el-form-item>

        <el-form-item label="触发亏损%">

            <el-input-number
                v-model="config.loss_tp.trigger_loss"
            />

        </el-form-item>

        <el-form-item label="反弹幅度%">

            <el-input-number
                v-model="config.loss_tp.trigger_rebound"
            />

        </el-form-item>

        <el-form-item label="保留仓位%">

            <el-input-number
                v-model="config.loss_tp.target_wallet_percent"
            />

        </el-form-item>

    </el-form>

</el-card>


<!-- Stoploss -->

<el-card class="mb20">

    <template #header>
        止损配置

        <el-alert
            type="warning"
            :closable="false"
        >
            达到设定亏损比例后强制平仓
        </el-alert>
    </template>

    <el-form label-width="120px">

        <el-form-item label="启用止损">
            <el-switch
                v-model="config.sl.enable"
            />
        </el-form-item>

        <el-form-item label="止损百分比">
            <el-input-number
                v-model="config.sl.stoploss"
            />
        </el-form-item>

    </el-form>

</el-card>


<el-button
    type="primary"
    size="large"
    @click="$emit('save')"
>
    保存策略
</el-button>

</div>

</template>

<script setup>

const props = defineProps({
    config:Object
})

defineEmits(["save"])

const addRoi = () => {

    props.config.tp.roi_levels.push({
        minutes:60,
        roi:1
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

            drawdown:-5,

            rsi_limit:20,

            j_limit:0,

            amount:1
        })

    } else {

        props.config.dca.levels.push({

            drawdown:-5,

            rsi_limit:80,

            j_limit:100,

            amount:1
        })
    }
}

const removeDca = (index) => {

    props.config.dca.levels.splice(index,1)
}


const addTrendAdd = () => {

    props.config.trend_add.levels.push({

        profit:2,

        rsi:
            props.config.side === "long"
            ? 60
            : 40,

        amount:0.5
    })
}

const removeTrendAdd = (index) => {

    props.config.trend_add.levels.splice(
        index,
        1
    )
}

</script>

<style scoped>

.mb20{
    margin-bottom:20px;
}

</style>
