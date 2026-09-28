<template>
  <div class="bot-list-page">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">机器人管理</h2>
        <el-text type="info" size="small">
          共 {{ bots.length }} 个机器人
        </el-text>
      </div>
      <div class="header-right">
        <el-button
          type="primary"
          size="large"
          :icon="Plus"
          @click="goCreate"
        >
          新建机器人
        </el-button>
      </div>
    </div>

    <!-- 筛选 -->
    <el-card class="filter-card" shadow="never">
      <el-radio-group v-model="filterStatus" size="default">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="running">运行中</el-radio-button>
        <el-radio-button value="stopped">已停止</el-radio-button>
      </el-radio-group>
    </el-card>

    <!-- 机器人卡片列表 -->
    <div v-if="filteredBots.length" class="bot-grid">
      <el-card
        v-for="bot in filteredBots"
        :key="bot.id"
        class="bot-card"
        shadow="hover"
        @click="goDetail(bot.id)"
      >
        <div class="bot-card__header">
          <div class="bot-name">
            <span class="bot-name__text">{{ bot.name }}</span>
            <el-tag
              :type="bot.status === 'running' ? 'success' : 'info'"
              size="small"
              effect="dark"
            >
              {{ bot.status === 'running' ? '运行中' : '已停止' }}
            </el-tag>
          </div>
          <el-dropdown
            trigger="click"
            @command="(cmd) => handleCommand(cmd, bot)"
            @click.stop
          >
            <el-icon class="more-icon"><MoreFilled /></el-icon>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">编辑</el-dropdown-item>
                <el-dropdown-item command="toggle">
                  {{ bot.status === 'running' ? '停止' : '启动' }}
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <div class="bot-card__body">
          <div class="info-row">
            <span class="info-label">交易对</span>
            <span class="info-value">
              {{ Array.isArray(bot.pair) ? bot.pair.join(', ') : bot.pair }}
            </span>
          </div>
          <div class="info-row">
              <span class="info-label">模式</span>
              <span class="info-value">
                <el-tag :type="bot.dryRun ? 'info' : 'warning'" size="small">
                  {{ bot.dryRun ? 'Dry Run' : '实盘' }}
                </el-tag>
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">杠杆</span>
              <span class="info-value">{{ bot.leverage }}x</span>
            </div>
          <div class="info-row">
            <span class="info-label">方向</span>
            <span class="info-value">
              <el-tag v-if="bot.enableLong" type="success" size="small">多头</el-tag>
              <el-tag v-if="bot.enableShort" type="danger" size="small">空头</el-tag>
            </span>
          </div>
          <div class="info-row">
            <span class="info-label">投入资金</span>
            <span class="info-value">{{ bot.capital }} USDT</span>
          </div>
          <div class="info-row">
            <span class="info-label">当前盈亏</span>
            <span
              class="info-value"
              :class="bot.pnl >= 0 ? 'profit' : 'loss'"
            >
              {{ bot.pnl >= 0 ? '+' : '' }}{{ bot.pnl }} USDT
            </span>
          </div>
        </div>

        <div class="bot-card__footer">
          <el-text type="info" size="small">
            创建于 {{ bot.createdAt }}
          </el-text>
        </div>
      </el-card>
    </div>

    <!-- 空状态 -->
    <el-empty
      v-else
      description="暂无机器人，点击右上角新建"
    >
      <el-button type="primary" @click="goCreate">新建机器人</el-button>
    </el-empty>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, MoreFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useBotStore } from '@/stores/botStore.js'

const router = useRouter()

const filterStatus = ref('all')
const { state, fetchBots, toggleBot, deleteBot } = useBotStore()
const bots = computed(() => state.bots)

const filteredBots = computed(() => {
  if (filterStatus.value === 'all') return bots.value
  return bots.value.filter(b => b.status === filterStatus.value)
})


// ============ 跳转 ============
const goCreate = () => {
  router.push({ name: 'BotNew' })
}

const goDetail = (id) => {
  router.push({ name: 'BotDetail', params: { id } })
}

// ============ 操作 ============
const handleCommand = async (cmd, bot) => {
  if (cmd === 'edit') {
    goDetail(bot.id)
    } else if (cmd === 'toggle') {
      try {
        await toggleBot(bot.id, bot.status)
        ElMessage.success(bot.status === 'running' ? '已停止' : '已启动')
      } catch (e) {
        ElMessage.error('切换失败')
      }
    } else if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm(
        `确认删除机器人「${bot.name}」？`,
        '删除确认',
        { type: 'warning' }
      )
      deleteBot(bot.id)
      ElMessage.success('已删除')
    } catch {}
  }
}

onMounted(fetchBots)
</script>

<style scoped>
.bot-list-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-main);
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.filter-card {
  border-radius: 12px;
}

/* 卡片网格 */
.bot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.bot-card {
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.bot-card:hover {
  transform: translateY(-2px);
}

.bot-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.bot-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bot-name__text {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.more-icon {
  cursor: pointer;
  color: var(--el-text-color-secondary);
  font-size: 18px;
}

.more-icon:hover {
  color: var(--el-color-primary);
}

.bot-card__body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
}

.info-label {
  color: var(--el-text-color-secondary);
}

.info-value {
  color: var(--text-main);
  font-weight: 500;
}

.profit {
  color: #67c23a;
}

.loss {
  color: #f56c6c;
}

.bot-card__footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}
</style>