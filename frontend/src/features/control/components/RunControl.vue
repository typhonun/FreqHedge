<template>
  <el-card class="control-card">
    <!-- ======================
         运行模式
    ====================== -->
    <div class="panel-grid">
        <el-card class="inner-card">
          <template #header>
            <div class="card-title">
              🚀 运行模式
            </div>
          </template>

          <div class="switch-grid">
            <div class="switch-item">
              <span>📈 多头交易</span>

              <el-button
                :type="longRunning ? 'warning' : 'success'"
                size="default"
                @click="toggleSide('long')"
              >
                <el-icon style="margin-right: 4px;">
                  <VideoPause v-if="longRunning" />
                  <VideoPlay v-else />
                </el-icon>
                {{ longRunning ? "停止" : "启动" }}
              </el-button>
            </div>

            <div class="switch-item">
              <span>📉 空头交易</span>

              <el-button
                :type="shortRunning ? 'warning' : 'success'"
                size="default"
                @click="toggleSide('short')"
              >
                <el-icon style="margin-right: 4px;">
                  <VideoPause v-if="shortRunning" />
                  <VideoPlay v-else />
                </el-icon>
                {{ shortRunning ? "停止" : "启动" }}
              </el-button>
            </div>

            <div class="switch-item">
              <span>🧪 Dry Run</span>
              <el-switch v-model="dryRun" />
            </div>
          </div>

          <!-- 只留删除数据库 -->
          <div class="action-row">
            <el-button
              type="warning"
              size="large"
              @click="confirmDeleteTrade"
            >
              🗑 删除数据库
            </el-button>
          </div>
        </el-card>

      <!-- ======================
            手动交易
      ====================== -->
      <el-card class="inner-card">
        <template #header>
          <div class="card-title">
            ⚡ 手动交易
          </div>
        </template>

        <div class="manual-grid">
          <el-button
            type="success"
            size="large"
            @click="openForceEnter('long')"
          >
            ↑ 立即开多
          </el-button>

          <el-button
            type="danger"
            size="large"
            @click="openForceEnter('short')"
          >
            ↓ 立即开空
          </el-button>

          <el-button
            type="primary"
            plain
            @click="confirmCloseAll('long')"
          >
            全部平多
          </el-button>

          <el-button
            type="danger"
            plain
            @click="confirmCloseAll('short')"
          >
            全部平空
          </el-button>
        </div>

        <el-divider />

        <div class="switch-grid">
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
        </div>
      </el-card>
    </div>

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
        <el-button @click="forceEnterVisible=false">
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

    <el-card class="inner-card risk-card">
      <template #header>
        <div class="card-title">
          🎯 全局风控
        </div>
      </template>

      <div class="risk-grid">
        <div class="risk-item">
          <div>
            <span>🎯 启用全局止盈</span>
            <p>达到目标收益自动平仓</p>
          </div>

          <el-switch
            v-model="globalTpEnabled"
            @change="saveRiskConfig"
          />
        </div>

        <div class="risk-item">
          <div>
            <span>止盈阈值</span>
            <p>达到目标自动平仓</p>
          </div>

          <div class="risk-input">
            <el-radio-group
              v-model="globalTpMode"
              size="small"
              @change="saveRiskConfig"
            >
              <el-radio-button label="amount">金额</el-radio-button>
              <el-radio-button label="ratio">百分比</el-radio-button>
            </el-radio-group>

            <el-input-number
              v-if="globalTpMode === 'amount'"
              v-model="globalTpAmount"
              :min="5"
              :step="1"
              @change="saveRiskConfig"
            />

            <el-input-number
              v-else
              v-model="globalTpRatio"
              :min="1"
              :step="0.1"
              :precision="2"
              suffix="%"
              @change="saveRiskConfig"
            />
          </div>
        </div>

        <div class="risk-item">
          <div>
            <span>🛑 启用全局止损</span>
            <p>达到亏损限制自动止损</p>
          </div>

          <el-switch
            v-model="globalSlEnabled"
            @change="saveRiskConfig"
          />
        </div>

        <div class="risk-item">
          <div>
            <span>止损阈值</span>
            <p>达到亏损限制自动止损</p>
          </div>

          <div class="risk-input">
            <el-radio-group
              v-model="globalSlMode"
              size="small"
              @change="saveRiskConfig"
            >
              <el-radio-button label="amount">金额</el-radio-button>
              <el-radio-button label="ratio">百分比</el-radio-button>
            </el-radio-group>

            <el-input-number
              v-if="globalSlMode === 'amount'"
              v-model="globalSlAmount"
              :min="0"
              :step="1"
              @change="saveRiskConfig"
            />

            <el-input-number
              v-else
              v-model="globalSlRatio"
              :min="1"
              :step="0.1"
              :precision="2"
              suffix="%"
              @change="saveRiskConfig"
            />
          </div>
        </div>

        <!-- ===== 追踪止损 ===== -->
        <div class="risk-item">
          <div>
            <span>📈 启用追踪止损</span>
            <p>回撤或反弹到触发线自动平仓</p>
          </div>

          <el-switch
            v-model="globalTrailEnabled"
            @change="saveRiskConfig"
          />
        </div>

        <div class="risk-item">
          <div>
            <span>追踪参数</span>
            <p>触发盈亏可正可负，正数追踪盈利，负数追踪亏损</p>
          </div>

          <div class="risk-input">
            <el-radio-group
              v-model="globalTrailMode"
              size="small"
              @change="saveRiskConfig"
            >
              <el-radio-button label="amount">金额</el-radio-button>
              <el-radio-button label="ratio">百分比</el-radio-button>
            </el-radio-group>

            <template v-if="globalTrailMode === 'amount'">
              <el-input-number
                v-model="globalTrailActivateAmount"
                :step="1"
                @change="saveRiskConfig"
                placeholder="触发盈亏"
              />
              <el-input-number
                v-model="globalTrailDrawdownAmount"
                :min="0"
                :step="1"
                @change="saveRiskConfig"
                placeholder="追踪止损"
              />
            </template>

            <template v-else>
              <el-input-number
                v-model="globalTrailActivateRatio"
                :step="0.1"
                :precision="2"
                @change="saveRiskConfig"
                placeholder="触发盈亏"
              />
              <el-input-number
                v-model="globalTrailDrawdownRatio"
                :min="0"
                :step="0.1"
                :precision="2"
                @change="saveRiskConfig"
                placeholder="追踪止损"
              />
            </template>
          </div>
        </div>
      </div>
    </el-card>
  </el-card>
</template>

<script setup>
import { onMounted } from "vue"
import { VideoPlay, VideoPause } from "@element-plus/icons-vue"
import { useRunControl } from '@features/control/composables/useRunControl.js'

const {
  dryRun,

  longRunning,
  shortRunning,
  toggleSide,
  loadRunningStatus,

  confirmDeleteTrade,

  openForceEnter,
  confirmCloseAll,
  updateStopEntry,

  forceEnterVisible,
  pairList,
  selectedPair,
  stakeAmount,
  submitForceEnter,
  loadStopEntryStatus,

  globalTpEnabled,
  globalSlEnabled,
  globalTpAmount,
  globalSlAmount,
  globalTpMode,
  globalSlMode,
  globalTpRatio,
  globalSlRatio,
  globalTrailEnabled,
  globalTrailMode,
  globalTrailActivateAmount,
  globalTrailActivateRatio,
  globalTrailDrawdownAmount,
  globalTrailDrawdownRatio,
  loadRiskConfig,
  saveRiskConfig
} = useRunControl()

onMounted(async () => {
  await loadRunningStatus()
  await loadStopEntryStatus()
  await loadRiskConfig()
})
</script>

<style scoped>
.control-card {
  border-radius: 14px;
}

.card-title {
  font-size: 18px;
  font-weight: 700;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 15px;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.action-grid .el-button {
  height: 65px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 10px;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.inner-card {
  border-radius: 14px;
}

.manual-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.manual-grid .el-button {
  height: 45px;
  font-weight: 600;
}

.switch-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.switch-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 8px;
  font-size: 14px;
}

.switch-item:hover {
  background: #f3f4f6;
}

.switch-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.switch-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background: #fafafa;
  border-radius: 10px;
}

.switch-item:hover {
  background: #f4f4f5;
}

.risk-card {
  background: #fafafa;
}

.risk-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.risk-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px;
  border-radius: 12px;
  background: white;
  border: 1px solid #ebeef5;
}

.risk-item span {
  font-size: 15px;
  font-weight: 600;
}

.risk-item p {
  margin: 5px 0 0;
  color: #909399;
  font-size: 12px;
}

:deep(.force-enter-dialog .el-dialog__body) {
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.force-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.force-form .el-form-item {
  width: 80%;
}

.risk-input {
  display: flex;
  align-items: center;
  gap: 10px;
}

.risk-input .el-input-number {
  width: 110px;
}
</style>
