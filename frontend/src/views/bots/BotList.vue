<template>
  <div class="bot-list-page">
    <el-card class="toolbar-card" shadow="never">
      <div class="toolbar">
        <el-radio-group v-model="filterStatus" size="default">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="running">运行中</el-radio-button>
          <el-radio-button value="stopped">已停止</el-radio-button>
        </el-radio-group>
        <div>
          <el-button type="warning" plain @click="openComboDialog">
            联合止盈设置
          </el-button>
          <el-button type="primary" :icon="Plus" @click="goCreate">
            新建机器人
          </el-button>
        </div>
      </div>

      <!-- 联合止盈弹窗 -->
      <el-dialog
        v-model="showComboDialog"
        title="多组联合止盈风控"
        width="750px"
        class="combo-dialog"
        destroy-on-close
      >
        <div class="combo-container">
          <!-- 顶部操作栏 -->
          <div class="combo-header">
            <span class="combo-tip">你可以创建多个组合，每个组合独立计算盈利并触发风控。</span>
            <el-button type="primary" plain size="small" @click="addComboGroup">
              + 新增组合
            </el-button>
          </div>

          <!-- 空状态 -->
          <el-empty
            v-if="comboConfig.groups.length === 0"
            description="暂无组合配置，点击上方新增"
            :image-size="80"
          />

          <!-- 多组折叠面板 -->
          <el-collapse v-else v-model="activeGroups" class="combo-collapse">
            <el-collapse-item
              v-for="(group, index) in comboConfig.groups"
              :key="group.id"
              :name="group.id"
            >
              <!-- 面板标题：组合名称 + 状态 + 实时收益展示 -->
              <template #title>
                <div class="group-title">
                  <el-tag :type="group.enabled ? 'success' : 'info'" size="small" effect="dark">
                    {{ group.enabled ? '已启用' : '已停用' }}
                  </el-tag>
                  <span class="group-name">{{ group.name || '未命名组合' }}</span>

                  <!-- 实时状态摘要 -->
                  <div class="group-summary" v-if="group.bot_ids.length">
                    <span style="margin-right: 12px;">({{ group.bot_ids.length }} 个机器人)</span>
                    <span>当前总利润：</span>
                    <span :class="getGroupCurrentProfit(group) >= 0 ? 'profit' : 'loss'" style="font-weight: 600;">
                      {{ getGroupCurrentProfit(group) >= 0 ? '+' : '' }}{{ getGroupCurrentProfit(group).toFixed(2) }} U
                    </span>
                    <span style="margin: 0 4px;">/ 目标 {{ group.target_profit }} U</span>
                  </div>
                </div>
              </template>

              <!-- 面板内容：具体配置 -->
              <div class="group-body">
                <el-form label-width="110px" size="default">

                  <div class="form-row-2">
                    <el-form-item label="组合名称">
                      <el-input v-model="group.name" placeholder="例如：BTC+ETH 网格组" />
                    </el-form-item>
                    <el-form-item label="启用此组">
                      <el-switch v-model="group.enabled" />
                    </el-form-item>
                  </div>

                  <el-form-item label="选择机器人">
                    <el-select
                      v-model="group.bot_ids"
                      multiple
                      placeholder="选择参与该组合的机器人"
                      style="width: 100%"
                    >
                      <el-option
                        v-for="bot in availableBotsForSelect"
                        :key="bot.id"
                        :label="`${bot.name} (${bot.status === 'running' ? '运行中' : '已停止'})`"
                        :value="bot.id"
                        :disabled="isBotUsedInOtherGroups(bot.id, group.id)"
                      />
                    </el-select>
                    <div class="hint" style="margin-top: 4px; font-size: 12px; color: var(--el-text-color-secondary);">
                      注：同一个机器人建议只参与一个组合，已被其他组合选中的机器人会置灰。
                    </div>
                  </el-form-item>

                  <div class="form-row-2">
                    <el-form-item label="目标总盈利 (USDT)">
                      <el-input-number
                        v-model="group.target_profit"
                        :min="1"
                        :step="10"
                        style="width: 100%"
                      />
                    </el-form-item>
                    <el-form-item label="触发后停止机器人">
                      <el-switch v-model="group.auto_stop" />
                    </el-form-item>
                  </div>

                  <!-- 底部详细实时收益提示 -->
                  <div class="live-profit-box" v-if="group.bot_ids.length">
                    <span>当前选中机器人累计总收益：</span>
                    <span :class="getGroupCurrentProfit(group) >= 0 ? 'profit' : 'loss'">
                      {{ getGroupCurrentProfit(group) >= 0 ? '+' : '' }}{{ getGroupCurrentProfit(group).toFixed(2) }} USDT
                    </span>
                    <span class="target-hint">
                      (距离目标还差 {{ Math.max(0, group.target_profit - getGroupCurrentProfit(group)).toFixed(2) }} U)
                    </span>
                  </div>

                  <!-- 删除按钮 -->
                  <div class="group-actions">
                    <el-button type="danger" plain size="small" @click="removeComboGroup(index)">
                      删除此组合
                    </el-button>
                  </div>

                </el-form>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>

        <template #footer>
          <el-button @click="showComboDialog = false">取消</el-button>
          <el-button type="primary" @click="saveComboConfig" :loading="comboSaving">
            保存全部配置
          </el-button>
        </template>
      </el-dialog>
    </el-card>

    <!-- 机器人卡片列表 -->
    <div v-if="filteredBots.length" class="bot-grid">
      <el-card
        v-for="bot in filteredBots"
        :key="bot.id"
        class="bot-card"
        shadow="hover"
      >
        <!-- 头部：名称 + 状态 + 更多菜单 -->
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

          <!-- 更多菜单 -->
          <el-dropdown
            trigger="click"
            @command="(cmd) => handleCommand(cmd, bot)"
          >
            <el-icon class="more-icon" @click.stop><MoreFilled /></el-icon>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">编辑配置</el-dropdown-item>
                <el-dropdown-item command="copy">复制配置</el-dropdown-item>
                <el-dropdown-item command="logs">查看日志</el-dropdown-item>
                <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <!-- 卡片主体信息 -->
        <div class="bot-card__body" @click="goDetail(bot.id)">
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
              <el-tag v-else-if="bot.enableShort" type="danger" size="small">空头</el-tag>
              <el-tag v-else type="info" size="small">未设置</el-tag>
            </span>
          </div>
          <div class="info-row">
            <span class="info-label">投入资金</span>
            <span class="info-value">{{ bot.capital }} USDT</span>
          </div>
          <div class="info-row">
            <span class="info-label">累计收益</span>
            <span class="info-value" :class="(bot.total_profit ?? 0) >= 0 ? 'profit' : 'loss'">
              {{ (bot.total_profit ?? 0) >= 0 ? '+' : '' }}{{ Number(bot.total_profit ?? 0).toFixed(2) }} USDT
            </span>
          </div>
        </div>

        <!-- 底部：创建时间 + 操作按钮组 -->
        <div class="bot-card__footer">
          <el-text type="info" size="small" class="created-at">
            创建于 {{ bot.createdAt }}
          </el-text>

          <div class="action-buttons" @click.stop>
            <!-- 启动 / 停止 -->
            <el-button
              v-if="bot.status !== 'running'"
              type="success"
              size="small"
              :icon="VideoPlay"
              :loading="loadingIds.has(bot.id)"
              @click="handleToggle(bot)"
            >
              启动
            </el-button>
            <el-button
              v-else
              type="warning"
              size="small"
              :icon="VideoPause"
              :loading="loadingIds.has(bot.id)"
              @click="handleToggle(bot)"
            >
              停止
            </el-button>

            <!-- 编辑 -->
            <el-button
              size="small"
              :icon="Setting"
              @click="goDetail(bot.id)"
            >
              编辑
            </el-button>

            <!-- 删除 -->
            <el-button
              type="danger"
              size="small"
              :icon="Delete"
              plain
              @click="handleDelete(bot)"
            >
              删除
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <el-empty v-else description="暂无机器人，点击右上角新建">
      <el-button type="primary" @click="goCreate">新建机器人</el-button>
    </el-empty>

    <!-- 策略选择弹窗 -->
    <StrategySelectDialog
      v-model="showStrategyDialog"
      @select="handleStrategySelect"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  Plus, MoreFilled, VideoPlay, VideoPause, Setting, Delete
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useBotStore } from '@/stores/botStore.js'
import { useModeStore } from '@/stores/modeStore'
import StrategySelectDialog from '@/components/common/StrategySelectDialog.vue'
import axios from 'axios'
const API = 'http://localhost:9000'

const router = useRouter()

// ==========================================
// 机器人列表相关逻辑
// ==========================================
const filterStatus = ref('all')
const showStrategyDialog = ref(false)

const { state, fetchBots, toggleBot, deleteBot, createDraft } = useBotStore()
const modeStore = useModeStore()
const bots = computed(() => state.bots)

const loadingIds = ref(new Set())

const filteredBots = computed(() => {
  const modeBots = bots.value.filter(b => Boolean(b.dryRun) === modeStore.isSimulation.value)
  if (filterStatus.value === 'all') return modeBots
  return modeBots.filter(b => b.status === filterStatus.value)
})

const goCreate = () => {
  showStrategyDialog.value = true
}

const handleStrategySelect = async (type) => {
  try {
    const bot = await createDraft(type)
    router.push({
      name: 'BotDetail',
      params: { id: bot.id },
      query: { strategyType: type }
    })
  } catch (e) {
    console.error('[goCreate] failed:', e)
    ElMessage.error('创建草稿失败：' + (e?.message || e))
  }
}

const goDetail = async (bot) => {
  const id = typeof bot === 'object' ? bot.id : bot
  let strategyType = typeof bot === 'object' ? bot.strategyType : null

  if (!strategyType) {
    try {
      const { data } = await axios.get(`${API}/bots/${id}`)
      strategyType = data.strategyType
    } catch (e) {
      console.warn('[goDetail] 拉取详情失败，默认 dca', e)
    }
  }

  router.push({
    name: 'BotDetail',
    params: { id },
    query: { strategyType: strategyType || 'dca' }
  })
}

// 查询机器人是否有未平仓持仓
const hasOpenPositions = async (botId) => {
  try {
    const { data } = await axios.get(`${API}/chart/bot-positions/${botId}`)
    return Array.isArray(data) && data.length > 0
  } catch (e) {
    // 查询失败时保守处理：视为有持仓，禁止停止（避免误停）
    console.warn(`[hasOpenPositions] 查询持仓失败 bot=${botId}`, e)
    return null // null 表示查询失败
  }
}

const handleToggle = async (bot) => {
  const isStopping = bot.status === 'running'

  // ── 停止前：校验是否有持仓 ──
  if (isStopping) {
    loadingIds.value.add(bot.id)
    let positions
    try {
      positions = await hasOpenPositions(bot.id)
    } finally {
      loadingIds.value.delete(bot.id)
    }

    if (positions === null) {
      ElMessage.error('无法确认持仓状态，请稍后重试')
      return
    }

    if (positions) {
      try {
        await ElMessageBox.confirm(
          `机器人「${bot.name}」当前仍有未平仓持仓。\n\n` +
          `直接停止可能导致持仓失去自动管理。\n` +
          `建议先平仓或等待策略自行平仓后再停止。\n\n是否仍要强制停止？`,
          '存在未平仓持仓',
          {
            type: 'warning',
            confirmButtonText: '强制停止',
            cancelButtonText: '取消',
            distinguishCancelAndClose: true,
          }
        )
      } catch {
        return // 用户取消
      }
    }
  }

  // ── 执行启停 ──
  loadingIds.value.add(bot.id)
  try {
    await toggleBot(bot.id, bot.status)
    ElMessage.success(isStopping ? '已停止' : '已启动')
    await fetchBots()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '操作失败')
  } finally {
    loadingIds.value.delete(bot.id)
  }
}

const handleDelete = async (bot) => {
  try {
    await ElMessageBox.confirm(
      `确认删除机器人「${bot.name}」？该操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  // ★ 新增：运行中且可能有持仓时二次确认
  if (bot.status === 'running') {
    loadingIds.value.add(bot.id)
    let positions
    try {
      positions = await hasOpenPositions(bot.id)
    } finally {
      loadingIds.value.delete(bot.id)
    }

    if (positions === null) {
      ElMessage.error('无法确认持仓状态，请稍后重试')
      return
    }
    if (positions) {
      try {
        await ElMessageBox.confirm(
          `机器人「${bot.name}」仍有未平仓持仓，删除前会先强制停止。\n确定继续？`,
          '存在未平仓持仓',
          { type: 'warning', confirmButtonText: '强制停止并删除', cancelButtonText: '取消' }
        )
      } catch {
        return
      }
    }
  }

  loadingIds.value.add(bot.id)
  try {
    if (bot.status === 'running') {
      await toggleBot(bot.id, 'running')
      await new Promise(r => setTimeout(r, 1500))
    }
    await deleteBot(bot.id)
    ElMessage.success('已删除')
    await fetchBots()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || '删除失败')
  } finally {
    loadingIds.value.delete(bot.id)
  }
}

const handleCommand = async (cmd, bot) => {
  switch (cmd) {
    case 'edit': goDetail(bot); break
    case 'copy': await goCopy(bot); break
    case 'logs': router.push({ name: 'BotLogs', params: { id: bot.id } }); break
    case 'delete': await handleDelete(bot); break
  }
}

const goCopy = async (bot) => {
  const draft = await createDraft(bot.strategyType || 'dca')
  router.push({
    name: 'BotDetail',
    params: { id: draft.id },
    query: {
      copyFrom: bot.id,
      strategyType: bot.strategyType || 'dca',
    },
  })
}

// ==========================================
// 联合止盈（多组）逻辑
// ==========================================
const showComboDialog = ref(false)
const comboSaving = ref(false)
const activeGroups = ref([]) // 控制哪些折叠面板展开

// 配置结构：包含多组
const comboConfig = ref({
  groups: []
})

// 创建空组
const createEmptyGroup = () => ({
  id: Date.now().toString() + Math.random().toString(36).substring(2, 6),
  name: '新组合',
  enabled: false,
  bot_ids: [],
  target_profit: 100,
  auto_stop: false
})

// 加载配置
const loadComboConfig = async () => {
  try {
    const { data } = await axios.get(`${API}/combo`)
    if (data && data.groups) {
      comboConfig.value.groups = data.groups
    } else {
      comboConfig.value.groups = []
    }
  } catch (e) {
    console.error('加载联合止盈配置失败', e)
  }
}

// 打开弹窗（先拉取最新，再显示）
const openComboDialog = async () => {
  await loadComboConfig()
  showComboDialog.value = true
}

// 保存配置
const saveComboConfig = async () => {
  // 校验
  for (const g of comboConfig.value.groups) {
    if (g.enabled && g.bot_ids.length === 0) {
      ElMessage.warning(`组合「${g.name}」已启用，但未选择任何机器人`)
      return
    }
  }

  comboSaving.value = true
  try {
    // ★ 清洗数据：防止 null 或 undefined 导致后端 Pydantic 报错
    const payload = {
      groups: comboConfig.value.groups.map(g => ({
        id: String(g.id),
        name: g.name || '未命名组合',
        bot_ids: g.bot_ids || [],
        target_profit: Number(g.target_profit) || 100,
        auto_stop: Boolean(g.auto_stop),
        enabled: Boolean(g.enabled)
      }))
    }

    await axios.post(`${API}/combo`, payload)
    ElMessage.success('多组联合止盈配置已保存')
    showComboDialog.value = false
  } catch (e) {
    console.error('保存错误详情:', e.response?.data || e)
    // ★ 把后端的详细报错打印出来，方便排查
    const detail = e.response?.data?.detail
    let errMsg = '保存配置失败'
    if (Array.isArray(detail) && detail.length > 0) {
       errMsg = `参数校验失败: ${detail[0].loc.join('.')} - ${detail[0].msg}`
    }
    ElMessage.error(errMsg)
  } finally {
    comboSaving.value = false
  }
}

// 计算属性：可选机器人列表
const availableBotsForSelect = computed(() => {
  return bots.value.filter(b => b.status !== 'draft')
})

// 检查某个机器人是否已被其他组选中（防止多组重复计算）
const isBotUsedInOtherGroups = (botId, currentGroupId) => {
  return comboConfig.value.groups.some(
    g => g.id !== currentGroupId && g.bot_ids.includes(botId)
  )
}

// 计算某个组当前的实时总利润
const getGroupCurrentProfit = (group) => {
  let total = 0
  for (const id of group.bot_ids) {
    const bot = bots.value.find(b => b.id === id)
    if (bot && bot.total_profit) {
      total += Number(bot.total_profit)
    }
  }
  return total
}

// 新增组合
const addComboGroup = () => {
  const newGroup = createEmptyGroup()
  comboConfig.value.groups.push(newGroup)
  activeGroups.value.push(newGroup.id) // 默认展开新建的组
}

// 删除组合
const removeComboGroup = (index) => {
  ElMessageBox.confirm('确定要删除这个联合止盈组合吗？', '提示', { type: 'warning' })
    .then(() => {
      comboConfig.value.groups.splice(index, 1)
    })
    .catch(() => {})
}

// ==========================================
// 定时刷新与生命周期
// ==========================================
let refreshTimer = null

const startTimer = () => {
  stopTimer()
  refreshTimer = setInterval(() => {
    fetchBots()
  }, 10000)
}

const stopTimer = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onMounted(async () => {
  await fetchBots()
  startTimer()
})

onUnmounted(stopTimer)

watch(modeStore.mode, async () => {
  filterStatus.value = 'all'
  await fetchBots()
})
</script>

<style scoped>
.bot-list-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar-card {
  border-radius: 12px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
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
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.created-at {
  font-size: 12px;
}

.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-buttons .el-button {
  flex: 1;
  min-width: 72px;
}

/* ==========================================
 * 联合止盈弹窗专属样式
 * ========================================== */
.combo-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.combo-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--el-fill-color-light);
  padding: 12px 16px;
  border-radius: 8px;
}

.combo-tip {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.combo-collapse {
  border: none;
}

/* 修改折叠面板的默认样式使其更像卡片 */
.combo-collapse :deep(.el-collapse-item__header) {
  background: var(--el-bg-color);
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  padding: 0 16px;
  height: 54px;
  margin-bottom: 8px;
}
.combo-collapse :deep(.el-collapse-item__wrap) {
  border: none;
  background: transparent;
}
.combo-collapse :deep(.el-collapse-item__content) {
  padding-bottom: 16px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.group-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.group-summary {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-weight: normal;
  margin-left: auto;
  margin-right: 16px;
}

.group-body {
  background: var(--el-fill-color-extra-light);
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
}

.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* 实时利润提示框 */
.live-profit-box {
  margin-top: 8px;
  padding: 10px 12px;
  background: var(--el-color-primary-light-9);
  border: 1px dashed var(--el-color-primary-light-5);
  border-radius: 6px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.live-profit-box .profit {
  color: var(--el-color-success);
  font-weight: 700;
  font-size: 16px;
}
.live-profit-box .loss {
  color: var(--el-color-danger);
  font-weight: 700;
  font-size: 16px;
}
.live-profit-box .target-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-left: auto;
}

.group-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>