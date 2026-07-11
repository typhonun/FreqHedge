<template>

<el-card class="status-wrapper">

    <template #header>

        <div class="panel-header">
            🤖 Bot 监控中心
        </div>

    </template>

    <el-row :gutter="20">

        <!-- 多头 -->

        <el-col :span="12">

            <el-card class="bot-card">

                <div class="title">
                    📈 多头机器人
                </div>

                <div class="status">

                    <span
                        class="light"
                        :class="longRunning ? 'running' : 'stopped'"
                    />

                    <span
                        :class="
                        longRunning
                        ? 'running-text'
                        : 'stopped-text'
                        "
                    >
                        {{ longRunning ? "Running" : "Stopped" }}
                    </span>

                </div>

                <div class="metric">
                    <span>资金</span>
                    <span>{{ longBalance }} USDT</span>
                </div>

                <div class="metric">
                    <span>持仓数</span>
                    <span>{{ longTrades }}</span>
                </div>

                <div class="metric">
                    <span>收益率</span>

                    <span
                        :class="
                        longProfit > 0
                        ? 'profit'
                        : 'loss'
                        "
                    >
                        {{ longProfit }}%
                    </span>

                </div>

            </el-card>

        </el-col>

        <!-- 空头 -->

        <el-col :span="12">

            <el-card class="bot-card">

                <div class="title">
                    📉 空头机器人
                </div>

                <div class="status">

                    <span
                        class="light"
                        :class="shortRunning ? 'running' : 'stopped'"
                    />

                    <span
                        :class="
                        shortRunning
                        ? 'running-text'
                        : 'stopped-text'
                        "
                    >
                        {{ shortRunning ? "Running" : "Stopped" }}
                    </span>

                </div>

                <div class="metric">
                    <span>资金</span>
                    <span>{{ shortBalance }} USDT</span>
                </div>

                <div class="metric">
                    <span>持仓数</span>
                    <span>{{ shortTrades }}</span>
                </div>

                <div class="metric">
                    <span>收益率</span>

                    <span
                        :class="
                        shortProfit > 0
                        ? 'profit'
                        : 'loss'
                        "
                    >
                        {{ shortProfit }}%
                    </span>

                </div>

            </el-card>

        </el-col>

    </el-row>

</el-card>

</template>

<script setup>

import { useStatus } from "../composables/useStatus"

const {
    longRunning,
    shortRunning
} = useStatus()

</script>

<style scoped>

.status-wrapper{
    border-radius:14px;
}

.panel-header{

    font-size:18px;
    font-weight:700;

    display:flex;
    align-items:center;

    gap:10px;
}

.bot-card{

    border-radius:14px;

    transition:.3s;

    cursor:pointer;
}

.bot-card:hover{

    transform:translateY(-3px);

    box-shadow:
    0 8px 25px rgba(0,0,0,.12);
}

.title{

    font-size:18px;

    font-weight:600;

    margin-bottom:18px;
}

.status{

    display:flex;

    align-items:center;

    gap:10px;

    margin-bottom:18px;
}

.metric{

    display:flex;

    justify-content:space-between;

    align-items:center;

    margin:12px 0;

    color:#606266;
}

.light{

    width:10px;

    height:10px;

    border-radius:50%;
}

.running{

    background:#67c23a;

    box-shadow:
    0 0 6px #67c23a,
    0 0 12px #67c23a;
}

.stopped{

    background:#f56c6c;

    box-shadow:
    0 0 6px #f56c6c;
}

.running-text{

    color:#67c23a;

    font-weight:600;
}

.stopped-text{

    color:#f56c6c;

    font-weight:600;
}

.profit{

    color:#67c23a;

    font-weight:700;
}

.loss{

    color:#f56c6c;

    font-weight:700;
}

</style>