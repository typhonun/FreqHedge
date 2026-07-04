<template>

<div class="strategy-page">

    <div class="strategy-column">

        <el-card class="title-card long">

            <h2>📈 多头策略</h2>

        </el-card>

        <StrategyPanel
            v-if="longConfig.entry"
            :config="longConfig"
            @save="saveLong"
        />

    </div>

    <div class="strategy-column">

        <el-card class="title-card short">

            <h2>📉 空头策略</h2>

        </el-card>

        <StrategyPanel
            v-if="shortConfig.entry"
            :config="shortConfig"
            @save="saveShort"
        />

    </div>

</div>

</template>

<script setup>

import { onMounted } from "vue"
import { ElMessage } from "element-plus"

import StrategyPanel from "@/components/StrategyPanel.vue"

import {
    useStrategyConfig
} from "@/composables/useStrategyConfig"

const {
    longConfig,
    shortConfig,
    loadConfig,
    saveConfig
} = useStrategyConfig()

const saveLong = async () => {

    await saveConfig(
        "long",
        longConfig.value
    )

    ElMessage.success(
        "多头策略已保存"
    )
}

const saveShort = async () => {

    await saveConfig(
        "short",
        shortConfig.value
    )

    ElMessage.success(
        "空头策略已保存"
    )
}

onMounted(loadConfig)

</script>


<style scoped>

.strategy-page{

    display:flex;

    gap:20px;

    align-items:flex-start;
}

.strategy-column{

    flex:1;

    min-width:0;
}

.title-card{

    margin-bottom:20px;
}

.long{

    border-left:6px solid #67c23a;
}

.short{

    border-left:6px solid #f56c6c;
}

</style>