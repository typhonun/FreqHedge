<template>
  <el-card>

    <h2>本轮收益</h2>

    <el-row :gutter="20">

      <el-col :span="8">
        <el-statistic
          title="总收益"
          :value="Number(profit.total_profit || 0)"
          :precision="2"
        >
          <template #suffix>
            <span
              :style="{
                color: Number(profit.round_ratio || 0) >= 0 ? '#67C23A' : '#F56C6C',
                fontSize: '14px',
                marginLeft: '4px'
              }"
            >
              ({{ Number(profit.round_ratio || 0).toFixed(2) }}%)
            </span>
          </template>
        </el-statistic>
      </el-col>

      <el-col :span="6">
        <el-statistic
          title="全局止盈次数"
          :value="Number(profit.global_tp_count || 0)"
          :precision="0"
        />
      </el-col>

      <el-col :span="6">
        <el-statistic
          title="全局止损次数"
          :value="Number(profit.global_sl_count || 0)"
          :precision="0"
        />
      </el-col>

      <!-- 多单区块：有多单持仓才显示 -->
      <template v-if="hasLong">

        <el-col :span="8">
          <el-statistic
            title="多单收益"
            :value="Number(profit.long_profit || 0)"
            :precision="2"
          >
            <template #suffix>
              <span
                :style="{
                  color: Number(profit.long_ratio || 0) >= 0 ? '#67C23A' : '#F56C6C',
                  fontSize: '14px',
                  marginLeft: '4px'
                }"
              >
                ({{ Number(profit.long_ratio || 0).toFixed(2) }}%)
              </span>
            </template>
          </el-statistic>
        </el-col>

        <el-col :span="6">
          <el-statistic
              title="多单已平仓"
              :value="Number(profit.long_closed || 0)"
              :precision="2"
          />
        </el-col>

        <el-col :span="6">
          <el-statistic
              title="多单浮盈"
              :value="Number(profit.long_float || 0)"
              :precision="2"
          />
        </el-col>

      </template>

      <!-- 空单区块：有空单持仓才显示 -->
      <template v-if="hasShort">

        <el-col :span="8">
          <el-statistic
            title="空单收益"
            :value="Number(profit.short_profit || 0)"
            :precision="2"
          >
            <template #suffix>
              <span
                :style="{
                  color: Number(profit.short_ratio || 0) >= 0 ? '#67C23A' : '#F56C6C',
                  fontSize: '14px',
                  marginLeft: '4px'
                }"
              >
                ({{ Number(profit.short_ratio || 0).toFixed(2) }}%)
              </span>
            </template>
          </el-statistic>
        </el-col>

        <el-col :span="6">
          <el-statistic
              title="空单已平仓"
              :value="Number(profit.short_closed || 0)"
              :precision="2"
          />
        </el-col>

        <el-col :span="6">
          <el-statistic
              title="空单浮盈"
              :value="Number(profit.short_float || 0)"
              :precision="2"
          />
        </el-col>

      </template>

    </el-row>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  profit: {
    type: Object,
    default: () => ({})
  }
})

const hasLong = computed(
  () => Number(props.profit?.position_count?.long || 0) > 0
)

const hasShort = computed(
  () => Number(props.profit?.position_count?.short || 0) > 0
)

</script>