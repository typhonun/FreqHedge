<template>

<div v-if="config?.entry">

<!-- 入场配置 -->

<el-card class="mb20">

    <template #header>
        入场配置
    </template>

    <el-form label-width="120px">

        <!-- RSI -->

        <el-divider>RSI</el-divider>

        <el-form-item label="启用RSI">
            <el-switch
                v-model="config.entry.rsi.enable"
            />
        </el-form-item>

        <el-form-item label="RSI周期">
            <el-input-number
                v-model="config.entry.rsi.period"
            />
        </el-form-item>

        <el-form-item label="RSI阈值">
            <el-input-number
                v-model="config.entry.rsi.value"
            />
        </el-form-item>

        <!-- MACD -->

        <el-divider>MACD</el-divider>

        <el-form-item label="启用MACD">
            <el-switch
                v-model="config.entry.macd.enable"
            />
        </el-form-item>

        <el-form-item label="Fast">
            <el-input-number
                v-model="config.entry.macd.fast"
            />
        </el-form-item>

        <el-form-item label="Slow">
            <el-input-number
                v-model="config.entry.macd.slow"
            />
        </el-form-item>

        <el-form-item label="Signal">
            <el-input-number
                v-model="config.entry.macd.signal"
            />
        </el-form-item>

        <!-- BB -->

        <el-divider>布林带</el-divider>

        <el-form-item label="启用布林带">
            <el-switch
                v-model="config.entry.bb.enable"
            />
        </el-form-item>

        <el-form-item label="周期">
            <el-input-number
                v-model="config.entry.bb.period"
            />
        </el-form-item>

        <el-form-item label="标准差">
            <el-input-number
                v-model="config.entry.bb.std"
            />
        </el-form-item>

        <!-- 成交量 -->

        <el-divider>成交量过滤</el-divider>

        <el-form-item label="启用成交量过滤">
            <el-switch
                v-model="config.entry.volume.enable"
            />
        </el-form-item>

    </el-form>

</el-card>


<!-- TP -->

<el-card class="mb20">

    <template #header>

        止盈配置

        <el-button
            style="float:right"
            size="small"
            type="success"
            @click="addTp"
        >
            新增TP
        </el-button>

    </template>

    <div
        v-for="(tp,index) in config.tp.levels"
        :key="index"
    >

        <el-divider>
            TP {{ index + 1 }}
        </el-divider>

        <el-form
            label-width="120px"
        >

            <el-form-item label="止盈百分比">
                <el-input-number
                    v-model="tp.profit"
                />
            </el-form-item>

            <el-form-item label="卖出比例">
                <el-input-number
                    v-model="tp.sell"
                />
            </el-form-item>

            <el-button
                type="danger"
                size="small"
                @click="removeTp(index)"
            >
                删除
            </el-button>

        </el-form>

    </div>

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

    <el-form label-width="120px">

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

    </el-form>

    <div
        v-for="(dca,index) in config.dca.levels"
        :key="index"
    >

        <el-divider>
            DCA {{ index + 1 }}
        </el-divider>

        <el-form
            label-width="120px"
        >

            <el-form-item label="回撤阈值">
                <el-input-number
                    v-model="dca.drawdown"
                />
            </el-form-item>

            <el-form-item label="倍率">
                <el-input-number
                    v-model="dca.amount"
                />
            </el-form-item>

            <el-button
                type="danger"
                size="small"
                @click="removeDca(index)"
            >
                删除
            </el-button>

        </el-form>

    </div>

</el-card>


<!-- Grid -->

<el-card class="mb20">

    <template #header>
        网格配置
    </template>

    <el-form label-width="120px">

        <el-form-item label="启用网格">
            <el-switch
                v-model="config.grid.enable"
            />
        </el-form-item>

        <el-form-item label="网格数量">
            <el-input-number
                v-model="config.grid.count"
            />
        </el-form-item>

        <el-form-item label="网格间距">
            <el-input-number
                v-model="config.grid.distance"
            />
        </el-form-item>

    </el-form>

</el-card>


<!-- Stoploss -->

<el-card class="mb20">

    <template #header>
        止损配置
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

const addTp = () => {

    props.config.tp.levels.push({
        profit:1,
        sell:10
    })
}

const removeTp = (index) => {

    props.config.tp.levels.splice(index,1)
}

const addDca = () => {

    props.config.dca.levels.push({
        drawdown:-5,
        amount:1
    })
}

const removeDca = (index) => {

    props.config.dca.levels.splice(index,1)
}

</script>

<style scoped>

.mb20{
    margin-bottom:20px;
}

</style>
