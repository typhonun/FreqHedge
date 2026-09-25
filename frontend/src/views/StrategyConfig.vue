<template>

<div class="strategy-page">

    <div class="strategy-column">

        <el-card class="title-card long">

            <h2>📈 多头策略</h2>

        </el-card>

        <StrategyPanel
            v-if="longConfig.entry"
            :config="longConfig"
            :trade-info="longTradeInfo"
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
            :trade-info="shortTradeInfo"
            @save="saveShort"
        />

    </div>

</div>

</template>

<script setup>

import { onMounted } from "vue"
import { ElMessage } from "element-plus"

import StrategyPanel from '@features/strategy/components/StrategyPanel.vue'
import { useStrategyConfig } from '@features/strategy/composables/useStrategyConfig.js'

const {
    longConfig,
    shortConfig,
    longTradeInfo,
    shortTradeInfo,
    loadConfig,
    saveConfig
} = useStrategyConfig()

const saveLong = async () => {
    try {
        const res = await saveConfig("long", longConfig.value)

        if (res.error) return

        if (res.changed) {
            const reloadOk = res?.data?.data?.reload_ok
            if (reloadOk === false) {
                const err = res?.data?.data?.reload_err
                ElMessage.warning(
                    "策略已保存，但热重载失败" + (err ? `：${err}` : "，请检查机器人状态")
                )
            } else {
                ElMessage.success("策略已保存并重载")
            }
            await loadConfig()
        } else {
            ElMessage.info("策略无变更")
        }
    } catch {
        ElMessage.error("多头策略保存失败")
    }
}

const saveShort = async () => {
    try {
        const res = await saveConfig("short", shortConfig.value)

        if (res.error) return

        if (res.changed) {
            const reloadOk = res?.data?.data?.reload_ok
            if (reloadOk === false) {
                const err = res?.data?.data?.reload_err
                ElMessage.warning(
                    "策略已保存，但热重载失败" + (err ? `：${err}` : "，请检查机器人状态")
                )
            } else {
                ElMessage.success("策略已保存并重载")
            }
            await loadConfig()
        } else {
            ElMessage.info("策略无变更")
        }
    } catch {
        ElMessage.error("空头策略保存失败")
    }
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