<!-- src/views/settings/Exchanges.vue -->
<template>
  <div class="exchanges-page">
    <!-- 顶部说明 + 添加按钮 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">交易所 API</h2>
        <p class="page-desc">
              {{ isSimulation
                ? '模拟盘只需选择交易所并设置账户别名，不需要填写任何 API 密钥。'
                : '配置正确的交易所 API Key 与 Secret，用于实盘下单、查询持仓和余额。' }}
          所有密钥仅保存在本机后端，不会上传到任何第三方服务器。
          <br />
        </p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">
        添加交易所
      </el-button>
    </div>

    <!-- ============ 模拟账户：置顶、独立、不可操作 ============ -->
    <div v-if="isSimulation" class="account-list">
      <div class="account-card account-card--dry-run">
        <div class="account-card__main">
          <div class="account-brand">
            <div
              class="brand-logo"
              :style="{ background: brandColor(DRY_RUN_EXCHANGE) }"
            >
              {{ brandInitial(DRY_RUN_EXCHANGE) }}
            </div>
            <div class="brand-info">
              <div class="brand-name">
                {{ exchangeLabel(DRY_RUN_EXCHANGE) }}
                <el-tag size="small" type="info" effect="plain">
                  内置
                </el-tag>
              </div>
              <div class="brand-alias">
                模拟运行
              </div>
            </div>
          </div>

          <div class="account-field">
            <div class="field-label">下单模式</div>
            <div class="field-value">
              模拟撮合，不产生真实订单
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ============ 真实账户列表 ============ -->
    <div v-if="accounts.length" class="account-list">
      <div
        v-for="acc in visibleAccounts"
        :key="acc.id"
        class="account-card"
      >
        <div class="account-card__main">
          <!-- 交易所图标 + 名称 -->
          <div class="account-brand">
            <div class="brand-logo" :style="{ background: brandColor(acc.exchange) }">
              {{ brandInitial(acc.exchange) }}
            </div>
            <div class="brand-info">
              <div class="brand-name">
                {{ exchangeLabel(acc.exchange) }}
                <el-tag
                  v-if="acc.isDefault"
                  size="small"
                  type="success"
                  effect="plain"
                >
                  默认
                </el-tag>
              </div>
              <div class="brand-alias">
                {{ acc.alias || '未命名账户' }}
              </div>
            </div>
          </div>

          <!-- API Key 掩码 -->
          <div class="account-field">
            <div class="field-label">API Key</div>
            <div class="field-value mono">{{ maskKey(acc.apiKey) }}</div>
          </div>

          <!-- 连接状态 -->
          <div class="account-field">
            <div class="field-label">状态</div>
            <div class="field-value">
              <span
                class="status-dot"
                :class="acc.status === 'ok' ? 'is-ok' : 'is-error'"
              />
              {{ acc.status === 'ok' ? '连接正常' : '连接失败' }}
              <span v-if="acc.lastChecked" class="status-time">
                · {{ acc.lastChecked }}
              </span>
            </div>
          </div>
        </div>

        <div class="account-card__actions">
          <el-button size="small" :loading="testingId === acc.id" @click="handleTest(acc)">
            测试连接
          </el-button>
          <el-button
            v-if="!acc.isDefault"
            size="small"
            @click="handleSetDefault(acc)"
          >
            设为默认
          </el-button>
          <el-button size="small" @click="openEdit(acc)">编辑</el-button>
          <el-button
            size="small"
            type="danger"
            plain
            @click="handleDelete(acc)"
          >
            删除
          </el-button>
        </div>
      </div>
    </div>

    <!-- ============ 弹窗：新增 / 编辑 ============ -->
    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑交易所 API' : '添加交易所 API'"
      width="560px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="110px"
        label-position="right"
      >
        <el-form-item label="交易所" prop="exchange">
          <el-select
            v-model="form.exchange"
            placeholder="请选择交易所"
            style="width: 100%"
          >
            <el-option
              v-for="ex in supportedExchanges"
              :key="ex.value"
              :label="ex.label"
              :value="ex.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="账户别名" prop="alias">
          <el-input
            v-model="form.alias"
            placeholder="如：主账户"
            maxlength="32"
          />
        </el-form-item>

        <el-form-item v-if="!isSimulation" label="API Key" prop="apiKey">
          <el-input
            v-model="form.apiKey"
            placeholder="从交易所 API 管理页面获取"
            autocomplete="off"
            show-password
          />
        </el-form-item>

        <el-form-item v-if="!isSimulation" label="API Secret" prop="apiSecret">
          <el-input
            v-model="form.apiSecret"
            type="password"
            placeholder="API Secret（仅保存到本机）"
            autocomplete="off"
            show-password
          />
        </el-form-item>

        <el-form-item
          v-if="!isSimulation && needPassphrase(form.exchange)"
          label="Passphrase"
          prop="passphrase"
        >
          <el-input
            v-model="form.passphrase"
            type="password"
            placeholder="OKX / KuCoin 等需要 Passphrase"
            autocomplete="off"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="form.isDefault">设为默认账户</el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="saving"
          @click="handleSave"
        >
          {{ editing ? '保存修改' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useExchangeAccounts } from '@/composables/useExchangeAccounts'
import axios from 'axios'
import { useModeStore } from '@/stores/modeStore'
const API = 'http://localhost:9000'
const modeStore = useModeStore()
const isSimulation = computed(() => modeStore.isSimulation.value)

/* ══════════════════════════════════════════════════════════════════
 * 常量 / 元数据
 * ══════════════════════════════════════════════════════════════════ */

/**
 * ★ 内置模拟账户的行情来源。
 * 后端在 dry_run=true 时，会把 config.exchange.name 写死为此值。
 * 如需切换（如 OKX Dry Run），改这一处即可。
 */
const DRY_RUN_EXCHANGE = 'binance'

const supportedExchanges = [
  { value: 'binance',  label: 'Binance 币安',      color: '#F0B90B', initial: 'B'  },
  { value: 'okx',      label: 'OKX 欧易',          color: '#000000', initial: 'OK' },
  { value: 'bybit',    label: 'Bybit',             color: '#F7A600', initial: 'By' },
  { value: 'kucoin',   label: 'KuCoin',            color: '#24AE8F', initial: 'K'  },
  { value: 'gate',     label: 'Gate.io 芝麻开门',  color: '#2354E6', initial: 'G'  },
  { value: 'huobi',    label: 'HTX 火币',          color: '#1D4ED8', initial: 'H'  },
]

const exchangeMap = Object.fromEntries(
  supportedExchanges.map((e) => [e.value, e])
)

const exchangeLabel = (v) => exchangeMap[v]?.label || v
const brandColor = (v) => exchangeMap[v]?.color || '#888'
const brandInitial = (v) => exchangeMap[v]?.initial || v.slice(0, 2).toUpperCase()

const needPassphrase = (ex) => ['okx', 'kucoin'].includes(ex)

/* ══════════════════════════════════════════════════════════════════
 * 状态
 * ══════════════════════════════════════════════════════════════════ */
const dialogVisible = ref(false)
const editing = ref(false)
const saving = ref(false)
const testingId = ref(null)
const formRef = ref(null)

const emptyForm = () => ({
  id: null,
  exchange: 'binance',
  alias: '',
  apiKey: '',
  apiSecret: '',
  passphrase: '',
  permissions: ['read', 'trade'],
  isDefault: false,
  status: 'ok',
  lastChecked: '',
})

const form = reactive(emptyForm())

const rules = computed(() => ({
  exchange: [{ required: true, message: '请选择交易所', trigger: 'change' }],
  alias: [{ required: true, message: '请输入账户别名', trigger: 'blur' }],
  apiKey: isSimulation.value ? [] : [
    { required: true, message: '请输入 API Key', trigger: 'blur' },
    { min: 8, message: 'API Key 长度不正确', trigger: 'blur' },
  ],
  apiSecret: isSimulation.value ? [] : [
    { required: true, message: '请输入 API Secret', trigger: 'blur' },
    { min: 8, message: 'API Secret 长度不正确', trigger: 'blur' },
  ],
  passphrase: needPassphrase(form.exchange)
    ? [{ required: true, message: '请输入 Passphrase', trigger: 'blur' }]
    : [],
}))

/* ══════════════════════════════════════════════════════════════════
 * 持久化
 * ══════════════════════════════════════════════════════════════════ */
const { accounts,
        reload,
        save: saveAccounts,
} = useExchangeAccounts()
const visibleAccounts = computed(() =>
  accounts.value.filter(acc => Boolean(acc.isSimulation) === isSimulation.value)
)

/* ══════════════════════════════════════════════════════════════════
 * 工具
 * ══════════════════════════════════════════════════════════════════ */
const maskKey = (k) => {
  if (!k) return '—'
  if (k.length <= 10) return k
  return `${k.slice(0, 6)}****${k.slice(-4)}`
}

const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8)

const formatNow = () => {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/* ══════════════════════════════════════════════════════════════════
 * 弹窗
 * ══════════════════════════════════════════════════════════════════ */
const openCreate = () => {
  Object.assign(form, emptyForm())
  form.apiKey = ''
  form.apiSecret = ''
  form.passphrase = ''
  editing.value = false
  dialogVisible.value = true
}

const openEdit = (acc) => {
  Object.assign(form, emptyForm(), acc)
  editing.value = true
  dialogVisible.value = true
}

const resetForm = () => {
  formRef.value?.clearValidate()
  Object.assign(form, emptyForm())
}

/* ══════════════════════════════════════════════════════════════════
 * 保存 / 删除 / 测试 / 默认
 * ══════════════════════════════════════════════════════════════════ */
const handleSave = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    const isEditing = editing.value

    if (!isSimulation.value) {
      await axios.post(`${API}/exchange/test-connection`, {
        exchange: form.exchange,
        apiKey: form.apiKey,
        apiSecret: form.apiSecret,
        passphrase: form.passphrase || '',
      })
    }

    const payload = {
      ...form,
      id: isEditing ? form.id : uid(),
      isSimulation: isSimulation.value,
      apiKey: isSimulation.value ? '' : form.apiKey,
      apiSecret: isSimulation.value ? '' : form.apiSecret,
      passphrase: isSimulation.value ? '' : form.passphrase,
      status: 'ok',
      lastChecked: formatNow(),
    }

    // 若设为默认，先清掉其他默认
    if (payload.isDefault) {
      visibleAccounts.value.forEach((a) => { a.isDefault = false })
    }

    if (isEditing && !isSimulation.value) {
      const idx = accounts.value.findIndex((a) => a.id === payload.id)
      if (idx >= 0) accounts.value[idx] = payload
    } else {
      if (accounts.value.length === 0) payload.isDefault = true
      accounts.value.push(payload)
    }
    saveAccounts()

    // 编辑时，同步密钥到所有引用该账户的机器人
    if (isEditing) {
      try {
        await axios.post(`${API}/exchange/sync-to-bots`, {
          accountId: payload.id,
          account: {
            exchange: payload.exchange,
            apiKey: payload.apiKey,
            apiSecret: payload.apiSecret,
            passphrase: payload.passphrase || '',
          },
        })
        ElMessage.success('已保存修改')
      } catch (e) {
        console.warn('[exchanges] sync to bots failed', e)
        ElMessage.warning('已保存，但同步到机器人失败（请手动重保存机器人）')
      }
    } else {
      ElMessage.success('已添加交易所')
    }

    dialogVisible.value = false
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleDelete = async (acc) => {
  try {
    await ElMessageBox.confirm(
      `确认删除「${exchangeLabel(acc.exchange)} · ${acc.alias || '未命名'}」的 API 配置？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  accounts.value = accounts.value.filter((a) => a.id !== acc.id)
  if (acc.isDefault && visibleAccounts.value.length > 0) {
    visibleAccounts.value[0].isDefault = true
  }
  saveAccounts()
  ElMessage.success('已删除')
}

const handleSetDefault = (acc) => {
  accounts.value.forEach((a) => { a.isDefault = a.id === acc.id })
  saveAccounts()
  ElMessage.success('已设为默认账户')
}

const handleTest = async (acc) => {
  testingId.value = acc.id
  try {
    if (isSimulation.value) {
      acc.status = 'ok'
    } else {
      await axios.post(`${API}/exchange/test-connection`, {
        exchange: acc.exchange,
        apiKey: acc.apiKey,
        apiSecret: acc.apiSecret,
        passphrase: acc.passphrase || '',
      })
      acc.status = 'ok'
    }
    acc.lastChecked = formatNow()
    saveAccounts()
    ElMessage.success('连接正常')
  } catch (e) {
    acc.status = 'error'
    acc.lastChecked = formatNow()
    saveAccounts()
    ElMessage.error('连接失败：' + (e?.message || '未知错误'))
  } finally {
    testingId.value = null
  }
}

const refreshRealAccountStatuses = async () => {
  if (isSimulation.value) return
  await Promise.all(visibleAccounts.value.map(async (acc) => {
    try {
      await axios.post(`${API}/exchange/test-connection`, {
        exchange: acc.exchange,
        apiKey: acc.apiKey,
        apiSecret: acc.apiSecret,
        passphrase: acc.passphrase || '',
      })
      acc.status = 'ok'
    } catch {
      acc.status = 'error'
    }
    acc.lastChecked = formatNow()
  }))
  saveAccounts()
}

onMounted(async () => {
  reload()
  await refreshRealAccountStatuses()
})
</script>

<style scoped>
.exchanges-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ============ 顶部 ============ */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-title {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
  max-width: 720px;
  line-height: 1.6;
}

/* ============ 账户列表 ============ */
.account-list {
  display: flex;
  flex-direction: column;
  gap: 16px;               /* ★ 卡片等距 */
}

.account-list :deep(.el-empty) {
  padding: 24px 0;
}

.account-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px 20px;
  transition: all 0.2s;
}

.account-card:hover {
  border-color: var(--el-color-primary);
}

.account-card--dry-run:hover {
  border-color: var(--border-color);
}

.account-card__main {
  display: grid;
  grid-template-columns: minmax(220px, 1.4fr) minmax(140px, 1fr) minmax(120px, 1fr) minmax(140px, 1fr);
  gap: 20px;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--border-color);
  margin-bottom: 12px;
}

/* ★ 内置模拟账户：无 actions 行，底部不再分隔 */
.account-card--dry-run .account-card__main {
  padding-bottom: 0;
  border-bottom: none;
  margin-bottom: 0;
}

.account-card__hint {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--border-color);
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

.brand-logo {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}

.brand-info {
  min-width: 0;
}

.brand-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.brand-alias {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.account-field {
  min-width: 0;
}

.field-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.field-value {
  font-size: 13px;
  color: var(--text-main);
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.field-value.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: var(--text-muted);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 6px;
}

.status-dot.is-ok {
  background: #67c23a;
  box-shadow: 0 0 6px rgba(103, 194, 58, 0.6);
}

.status-dot.is-error {
  background: #f56c6c;
  box-shadow: 0 0 6px rgba(245, 108, 108, 0.6);
}

.status-time {
  color: var(--text-muted);
  font-size: 12px;
}

.account-card__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}
</style>