<template>

<el-card>

<h2>机器人控制</h2>

<el-row>

<el-col :span="8">

<p>Long Bot</p>

<el-tag type="success">
运行中
</el-tag>

</el-col>

<el-col :span="8">

<p>Short Bot</p>

<el-tag type="success">
运行中
</el-tag>

</el-col>

<el-col :span="8">

<p>
余额：
{{ balance }}
USDT
</p>

</el-col>

</el-row>

<br>

<el-button
type="success"
@click="startBot"
>
启动
</el-button>

<el-button
type="danger"
@click="stopBot"
>
停止
</el-button>

</el-card>

</template>

<script setup>

import {
startBot,
stopBot
} from "../api/trade"

const props =
defineProps({
balance: Number
})

const startBotHandler =
async () => {

await startBot()

}

const stopBotHandler =
async () => {

await stopBot()

}

</script>