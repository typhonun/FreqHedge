// src/composables/useExchangeAccounts.js
import { ref, computed } from 'vue'

import axios from "axios"

const STORAGE_KEY = 'exchange_api_accounts_v1'
const DEFAULT_SIM_ACCOUNT_ID = '__sim_binance_default__'

const accounts = ref([])

const createDefaultSimulationAccount = () => ({
  id: DEFAULT_SIM_ACCOUNT_ID,
  exchange: 'binance',
  alias: '默认模拟账户',
  apiKey: '',
  apiSecret: '',
  passphrase: '',
  permissions: ['read', 'trade'],
  isDefault: true,
  isSimulation: true,
  isProtected: true,
  totalCapital: 10000,
  status: 'ok',
  lastChecked: '',
})

const ensureDefaultSimulationAccount = () => {
  const simulationAccounts = accounts.value.filter((account) => account.isSimulation)
  if (!simulationAccounts.length) {
    accounts.value.push(createDefaultSimulationAccount())
    return true
  }
  const protectedAccount = simulationAccounts.find(
    (account) => account.id === DEFAULT_SIM_ACCOUNT_ID || account.isProtected
  )
  if (!protectedAccount) {
    accounts.value.push(createDefaultSimulationAccount())
    return true
  }
  let changed = false
  if (protectedAccount.id !== DEFAULT_SIM_ACCOUNT_ID) {
    protectedAccount.id = DEFAULT_SIM_ACCOUNT_ID
    changed = true
  }
  if (protectedAccount.exchange !== 'binance') {
    protectedAccount.exchange = 'binance'
    changed = true
  }
  if (!protectedAccount.isSimulation) {
    protectedAccount.isSimulation = true
    changed = true
  }
  if (!protectedAccount.isProtected) {
    protectedAccount.isProtected = true
    changed = true
  }
  const capital = Number(protectedAccount.totalCapital || 10000)
  if (protectedAccount.totalCapital !== capital) {
    protectedAccount.totalCapital = capital
    changed = true
  }
  return changed
}

const load = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    accounts.value = (raw ? JSON.parse(raw) : []).map((account) => ({
      ...account,
      totalCapital: account.totalCapital == null ? 0 : Number(account.totalCapital),
    }))
    if (ensureDefaultSimulationAccount()) {
      save()
    }
  } catch (e) {
    console.warn('[useExchangeAccounts] load failed', e)
    accounts.value = []
    ensureDefaultSimulationAccount()
    save()
  }
}

const save = () => {
  try {
    ensureDefaultSimulationAccount()
    localStorage.setItem(STORAGE_KEY, JSON.stringify(accounts.value))
  } catch (e) {
    console.warn('[useExchangeAccounts] save failed', e)
  }
}

const reload = () => load()
const defaultAccount = computed(() => accounts.value.find((a) => a.isDefault) || null)
const getById = (id) => accounts.value.find((a) => a.id === id) || null
const totalCapital = (isSimulation) => {
  const total = accounts.value
    .filter((account) => Boolean(account.isSimulation) === Boolean(isSimulation))
    .reduce((sum, account) => sum + Math.max(0, Number(account.totalCapital) || 0), 0)
  return total
}
const refreshLiveBalances = async () => {
  await Promise.allSettled(accounts.value
    .filter((account) => !account.isSimulation && account.apiKey && account.apiSecret)
    .map(async (account) => {
      const { data } = await axios.post('http://localhost:9000/exchange/wallets', {
        exchange: account.exchange,
        apiKey: account.apiKey,
        apiSecret: account.apiSecret,
        passphrase: account.passphrase || '',
      })
      account.totalCapital = Object.values(data)
        .reduce((sum, wallet) => sum + Number(wallet.total || 0), 0)
    }))
  save()
}

load()

export function useExchangeAccounts() {
  return {
    accounts,
    defaultAccount,
    totalCapital,
    refreshLiveBalances,
    getById,
    reload,
    save,
  }
}