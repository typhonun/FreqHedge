<template>

<el-card class="control-card">

<template #header>

<div class="card-title">
  ⚙️ 控制中心
</div>

  </template>

  <!-- 快捷操作 -->

  <div class="section-title">
    快捷操作
  </div>

  <div class="action-grid">

<el-button
  type="primary"
  size="large"
  @click="confirmStart"
>
  ▶ 启动机器人
</el-button>

<el-button
  type="danger"
  size="large"
  @click="confirmStop"
>
  ■ 停止机器人
</el-button>

<el-button
  type="success"
  size="large"
  @click="confirmReload"
>
  ↻ 重载配置
</el-button>

<el-button
  type="warning"
  size="large"
  @click="confirmDeleteTrade"
>
  🗑 删除数据库
</el-button>

  </div>

  <el-divider />

  <!-- 运行模式 -->

  <div class="section-title">
    运行模式
  </div>

  <div class="switch-grid">

<div class="switch-item">

  <span>📈 多头交易</span>

  <el-switch
    v-model="enableLong"
  />

</div>

<div class="switch-item">

  <span>📉 空头交易</span>

  <el-switch
    v-model="enableShort"
  />

</div>

<div class="switch-item">

  <span>🧪 Dry Run</span>

  <el-switch
    v-model="dryRun"
  />

</div>

<div class="switch-item">

  <span>⛔ 停止多头加仓</span>

  <el-switch
    v-model="stopLongEntry"
    @change="updateStopEntry"
  />

</div>

<div class="switch-item">

  <span>⛔ 停止空头加仓</span>

  <el-switch
    v-model="stopShortEntry"
    @change="updateStopEntry"
  />

</div>

<div class="switch-item">

  <span>🚀 手动开仓</span>

  <div>

    <el-button
      size="small"
      type="success"
      @click="openForceEnter('long')"
    >
      立即开多
    </el-button>

    <el-button
      size="small"
      type="danger"
      @click="openForceEnter('short')"
    >
      立即开空
    </el-button>

  </div>

</div>

  </div>

</el-card>

<el-dialog
    v-model="forceEnterVisible"
    title="立即开仓"
    width="25%"
    class="force-enter-dialog"
>

    <el-form
        label-position="top"
        class="force-form"
    >

        <el-form-item label="交易对">

            <el-select
                v-model="selectedPair"
                filterable
            >

                <el-option
                    v-for="pair in pairList"
                    :key="pair"
                    :label="pair"
                    :value="pair"
                />

            </el-select>

        </el-form-item>

        <el-form-item label="金额">

            <el-input-number
                v-model="stakeAmount"
                :min="1"
                style="width:100%"
            />

        </el-form-item>

    </el-form>

    <template #footer>

        <el-button
            @click="forceEnterVisible=false"
        >
            取消
        </el-button>

        <el-button
            type="primary"
            @click="submitForceEnter"
        >
            开仓
        </el-button>

    </template>

</el-dialog>

</template>

<script setup>

import { useRunControl }
from "../composables/useRunControl"

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

    updateStopEntry,

    forceEnterVisible,
    pairList,
    selectedPair,
    stakeAmount,

    openForceEnter,
    submitForceEnter

} = useRunControl()

</script>

<style scoped>

.control-card{
    border-radius:14px;
}

.card-title{
    font-size:18px;
    font-weight:700;
}

.section-title{
    font-size:15px;
    font-weight:600;
    margin-bottom:15px;
}

.action-grid{

    display:grid;

    grid-template-columns:
    repeat(2,1fr);

    gap:15px;
}

.action-grid .el-button{

    height:65px;

    font-size:15px;

    font-weight:600;

    border-radius:10px;
}

.switch-grid{

    display:flex;

    flex-direction:column;

    gap:12px;
}

.switch-item{

    display:flex;

    justify-content:space-between;

    align-items:center;

    padding:12px 15px;

    background:#fafafa;

    border-radius:10px;
}

.switch-item:hover{
    background:#f4f4f5;
}

:deep(.force-enter-dialog .el-dialog__body){

    min-height: 300px;

    display:flex;

    align-items:center;

    justify-content:center;
}

.force-form{

    width:100%;

    display:flex;

    flex-direction:column;

    align-items:center;
}

.force-form .el-form-item{

    width:80%;
}

</style>
