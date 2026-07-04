<template>

<div class="status-panel">

    <div class="status-item">

        <span
            class="status-light"
            :class="longRunning ? 'running' : 'stopped'"
        />

        <span>
            多头：
            {{ longRunning ? "运行中" : "已停止" }}
        </span>

    </div>

    <div class="status-item">

        <span
            class="status-light"
            :class="shortRunning ? 'running' : 'stopped'"
        />

        <span>
            空头：
            {{ shortRunning ? "运行中" : "已停止" }}
        </span>

    </div>

</div>

</template>

<script setup>

import { useStatus } from "../composables/useStatus"

const {
    longRunning,
    shortRunning
} = useStatus()

</script>

<style scoped>

.status-panel{

    display:flex;
    flex-direction:column;
    gap:12px;
}

.status-item{

    display:flex;
    align-items:center;
    gap:10px;

    font-size:15px;
}

.status-light{

    width:14px;
    height:14px;

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

</style>