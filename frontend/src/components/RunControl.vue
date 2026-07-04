<template>

<el-card>

    <template #header>
        运行控制
    </template>

    <div class="checkbox-group">

        <el-checkbox
            v-model="enableLong"
        >
            多头
        </el-checkbox>

        <el-checkbox
            v-model="enableShort"
        >
            空头
        </el-checkbox>

        <el-checkbox
            v-model="dryRun"
        >
            Dry Run
        </el-checkbox>

    </div>

    <div class="button-group">

        <el-button
            type="primary"
            @click="confirmStart"
        >
            开始运行
        </el-button>

        <el-button
            type="danger"
            @click="confirmStop"
        >
            停止运行
        </el-button>

        <el-button
            type="success"
            @click="confirmReload"
        >
            加载配置
        </el-button>

        <el-button
            type="warning"
            @click="confirmDeleteTrade"
        >
            删除数据库
        </el-button>

    </div>

    <el-divider />

    <el-checkbox
        v-model="stopLongEntry"
        @change="updateStopEntry"
    >
        停止多头加仓
    </el-checkbox>

    <br><br>

    <el-checkbox
        v-model="stopShortEntry"
        @change="updateStopEntry"
    >
        停止空头加仓
    </el-checkbox>

</el-card>

</template>

<script setup>

import {
    useRunControl
} from "../composables/useRunControl"

const {

    enableLong,
    enableShort,
    dryRun,

    stopLongEntry,
    stopShortEntry,

    confirmStart,
    confirmStop,
    confirmReload,
    confirmDeleteTrade,

    updateStopEntry

} = useRunControl()

</script>

<style scoped>

.checkbox-group{

    display:flex;
    gap:20px;

    margin-bottom:20px;
}

.button-group{

    display:flex;
    gap:10px;
    flex-wrap:wrap;
}

</style>